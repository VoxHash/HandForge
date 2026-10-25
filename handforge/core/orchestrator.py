"""Conversion orchestrator for HandForge."""

import os
import time
import subprocess
import sys
import platform
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition
from .models import Job
from .native_scheduler import estimate_job_rss_mb, recommend_parallel
from .progress import ProgressTracker
from ..util.errors import format_actionable_error
from ..util.ffmpeg import build_ffmpeg_cmd, run_ffmpeg, out_path, is_video_file
from ..util.hwaccel import is_hw_encoder

# Platform-specific imports for non-blocking I/O
if platform.system() == "Windows":
    import msvcrt
else:
    import select


class Worker(QThread):
    """Worker thread for FFmpeg conversion."""
    
    sig_progress = pyqtSignal(int, float, float, float, str, str, str)  # wid, progress, elapsed, eta, speed, peak, true_peak
    sig_done = pyqtSignal(int, bool, str, str)  # wid, success, message, output_path
    sig_log = pyqtSignal(int, str)  # wid, log_line
    
    def __init__(self, wid: int, job: Job, settings: Dict[str, Any]):
        super().__init__()
        self.wid = wid
        self.job = job
        self.settings = settings
        self._paused = False
        self._stopped = False
        self._mutex = QMutex()
        self._wait_condition = QWaitCondition()
    
    def pause(self):
        """Pause the worker."""
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()
    
    def resume(self):
        """Resume the worker."""
        self._mutex.lock()
        self._paused = False
        self._wait_condition.wakeAll()
        self._mutex.unlock()
    
    def stop(self):
        """Stop the worker."""
        self._mutex.lock()
        self._stopped = True
        self._paused = False
        self._wait_condition.wakeAll()
        self._mutex.unlock()

    def _fail(
        self,
        message: str,
        *,
        stderr: str = "",
        exc: Optional[BaseException] = None,
        output_path: str = "",
    ) -> None:
        """Emit a failed completion with an actionable user-facing message."""
        user_msg = format_actionable_error(
            message, stderr=stderr, exc=exc, include_solutions=True
        )
        self.sig_log.emit(self.wid, f"Error: {user_msg.splitlines()[0]}")
        self.sig_done.emit(self.wid, False, user_msg, output_path)

    def _build_ffmpeg_command(
        self,
        dst: str,
        *,
        hw_accel: Optional[str] = None,
        force_software: bool = False,
        two_pass: Optional[bool] = None,
    ) -> List[str]:
        """Build the FFmpeg argv for this job."""
        use_two_pass = self.job.two_pass if two_pass is None else two_pass
        pref = hw_accel
        if pref is None:
            pref = self.job.hw_accel or self.settings.get("hw_accel", "auto")
        return build_ffmpeg_cmd(
            src=self.job.src,
            dst=dst,
            fmt=self.job.format,
            mode=self.job.mode,
            bitrate=self.job.bitrate,
            vbrq=self.job.vbrq,
            sample_rate=self.job.sample_rate,
            channels=self.job.channels,
            metadata={
                "title": self.job.meta_title,
                "artist": self.job.meta_artist,
                "album": self.job.meta_album,
                "year": self.job.meta_year,
                "genre": self.job.meta_genre,
                "track": self.job.meta_track,
            }
            if not self.job.strip_meta
            else {},
            copy_meta=self.job.copy_meta and not self.job.strip_meta,
            prefer_external_cover=self.job.prefer_external_cover,
            normalize_lufs=self.job.normalize_lufs,
            target_lufs=self.job.target_lufs,
            eq_enabled=self.job.eq_enabled,
            eq_bass=self.job.eq_bass,
            eq_mid=self.job.eq_mid,
            eq_treble=self.job.eq_treble,
            compressor_enabled=self.job.compressor_enabled,
            compressor_threshold=self.job.compressor_threshold,
            compressor_ratio=self.job.compressor_ratio,
            compressor_attack=self.job.compressor_attack,
            compressor_release=self.job.compressor_release,
            compressor_makeup=self.job.compressor_makeup,
            limiter_enabled=self.job.limiter_enabled,
            limiter_limit=self.job.limiter_limit,
            limiter_attack=self.job.limiter_attack,
            limiter_release=self.job.limiter_release,
            denoise_enabled=self.job.denoise_enabled,
            denoise_nr=self.job.denoise_nr,
            denoise_nf=self.job.denoise_nf,
            denoise_track_noise=self.job.denoise_track_noise,
            video_color_enabled=self.job.video_color_enabled,
            video_brightness=self.job.video_brightness,
            video_contrast=self.job.video_contrast,
            video_saturation=self.job.video_saturation,
            video_stabilize_enabled=self.job.video_stabilize_enabled,
            video_stabilize_rx=self.job.video_stabilize_rx,
            video_stabilize_ry=self.job.video_stabilize_ry,
            video_stabilize_edge=self.job.video_stabilize_edge,
            threads=self.job.threads,
            custom_args=self.job.custom_args,
            video_codec=self.job.video_codec,
            video_bitrate=self.job.video_bitrate,
            video_quality=self.job.video_quality,
            resolution=self.job.resolution,
            fps=self.job.fps,
            extract_audio_only=self.job.extract_audio_only,
            reduce_size=self.job.reduce_size,
            size_reduction_factor=self.job.size_reduction_factor,
            use_hevc=self.job.use_hevc,
            two_pass=use_two_pass,
            subtitle_track=self.job.subtitle_track,
            trim_start=self.job.trim_start,
            trim_end=self.job.trim_end,
            fade_in=self.job.fade_in,
            fade_out=self.job.fade_out,
            video_trim_start=self.job.video_trim_start,
            video_trim_end=self.job.video_trim_end,
            crop_x=self.job.crop_x,
            crop_y=self.job.crop_y,
            crop_width=self.job.crop_width,
            crop_height=self.job.crop_height,
            video_quality_preset=self.job.video_quality_preset,
            audio_track=self.job.audio_track,
            hw_accel=pref,
            force_software=force_software,
        )

    @staticmethod
    def _video_codec_from_cmd(cmd: List[str]) -> Optional[str]:
        try:
            idx = cmd.index("-c:v")
            return cmd[idx + 1]
        except (ValueError, IndexError):
            return None

    def _software_fallback_encode(
        self,
        dst: str,
        *,
        stderr_hint: str = "",
    ) -> Optional[int]:
        """Retry once with software encoders. Returns exit code, or None if not attempted."""
        self.sig_log.emit(
            self.wid,
            "Hardware encode failed; falling back to software (libx264/libx265)...",
        )
        if stderr_hint:
            self.sig_log.emit(self.wid, f"HW error hint: {stderr_hint[:240]}")
        if dst not in ("NUL", "/dev/null") and os.path.exists(dst):
            try:
                os.remove(dst)
            except OSError:
                pass
        cmd = self._build_ffmpeg_command(
            dst, hw_accel="software", force_software=True, two_pass=False
        )
        self.sig_log.emit(
            self.wid,
            f"Software fallback encoder: {self._video_codec_from_cmd(cmd) or 'unknown'}",
        )
        proc = run_ffmpeg(cmd)
        if proc is None:
            return None
        try:
            return proc.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            proc.kill()
            return -1
    
    def run(self):
        """Run the conversion."""
        try:
            # Check if paused
            self._mutex.lock()
            while self._paused and not self._stopped:
                self._wait_condition.wait(self._mutex)
            self._mutex.unlock()
            
            if self._stopped:
                self._fail("Stopped by user")
                return
            
            # Verify source file exists
            if not os.path.exists(self.job.src):
                self._fail(f"Source file not found: {self.job.src}")
                return
            
            # Build output path
            try:
                dst = out_path(self.job.dst_dir, self.job.src, self.job.format)
            except PermissionError as e:
                self._fail(f"Permission error: {e}", exc=e)
                return
            
            # Verify output directory is writable before proceeding
            output_dir = os.path.dirname(dst)
            if not os.access(output_dir, os.W_OK):
                self._fail(
                    f"Output directory is not writable: {output_dir}",
                    exc=PermissionError(output_dir),
                )
                return
            
            # Check if output exists
            if os.path.exists(dst):
                on_exists = self.settings.get("on_exists", "overwrite")
                if on_exists == "skip":
                    self.sig_done.emit(self.wid, True, "Skipped (file exists)", dst)
                    return
                elif on_exists == "rename":
                    base, ext = os.path.splitext(dst)
                    counter = 1
                    while os.path.exists(dst):
                        dst = f"{base} ({counter}){ext}"
                        counter += 1
                elif on_exists == "overwrite":
                    # Try to make existing file writable if we're overwriting
                    try:
                        import stat
                        current_mode = os.stat(dst).st_mode
                        os.chmod(dst, current_mode | stat.S_IWUSR)
                    except (PermissionError, OSError):
                        # If we can't fix permissions, FFmpeg will fail with a clear error
                        pass
            
            # For two-pass encoding, first pass outputs to null device
            first_pass_dst = dst
            if self.job.two_pass and self.job.reduce_size and not self.job.extract_audio_only:
                import platform
                if platform.system() == "Windows":
                    first_pass_dst = "NUL"
                else:
                    first_pass_dst = "/dev/null"
            
            # Build FFmpeg command (use first_pass_dst for two-pass)
            hw_pref = self.job.hw_accel or self.settings.get("hw_accel", "auto")
            cmd = self._build_ffmpeg_command(
                first_pass_dst, hw_accel=hw_pref, force_software=False
            )
            
            # Run FFmpeg
            start_time = time.time()
            
            # Verify we can write to the output location before starting FFmpeg
            output_dir = os.path.dirname(dst)
            try:
                # Test write permission by trying to create a temporary file.
                # Include wid (not just pid): QThreads share one process, so parallel
                # workers must not collide on the same test path (ENOENT on remove).
                test_file = os.path.join(output_dir, f".handforge_test_{os.getpid()}_{self.wid}")
                try:
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                except (PermissionError, OSError) as e:
                    self._fail(
                        f"Cannot write to output directory '{output_dir}': {e}",
                        exc=e,
                    )
                    return
            except Exception as e:
                self.sig_log.emit(self.wid, f"Warning: Could not verify write permissions: {e}")
            
            # Log command details for debugging
            self.sig_log.emit(self.wid, f"Starting conversion: {os.path.basename(self.job.src)}")
            self.sig_log.emit(self.wid, f"Format: {self.job.format}, Mode: {self.job.mode}")
            self.sig_log.emit(self.wid, f"Output: {dst}")
            self.sig_log.emit(self.wid, f"FFmpeg command: {' '.join(cmd[:10])}...")  # Log first 10 args
            
            try:
                proc = run_ffmpeg(cmd)
            except Exception as e:
                self._fail(f"Failed to start FFmpeg: {e}", exc=e)
                return
            
            if proc is None:
                self._fail("Failed to start FFmpeg - check if FFmpeg is installed and on PATH")
                return
            
            # Verify process started successfully
            # Give it a moment to start, then check if it's still running.
            # Short/trimmed jobs often finish in <0.1s — only fail when exit code != 0.
            time.sleep(0.1)
            early_rc = proc.poll()
            if early_rc is not None and early_rc != 0:
                # Process finished immediately with a failure exit code
                try:
                    stderr_output = proc.stderr.read()
                    error_text = (
                        stderr_output.decode("utf-8", errors="ignore")
                        if stderr_output
                        else ""
                    )
                except Exception as e:
                    self._fail(f"FFmpeg process exited immediately: {e}", exc=e)
                    return
                vcodec = self._video_codec_from_cmd(cmd)
                if is_hw_encoder(vcodec):
                    fb_rc = self._software_fallback_encode(
                        dst, stderr_hint=error_text
                    )
                    if fb_rc == 0:
                        self.sig_done.emit(
                            self.wid,
                            True,
                            f"Conversion completed successfully (software fallback)\nSaved to: {dst}",
                            dst,
                        )
                        return
                self._fail(
                    "FFmpeg process exited immediately",
                    stderr=error_text,
                )
                return
            
            # Monitor progress (monotonic %, speed-aware ETA, EWMA, throttled emits)
            peak = ""
            true_peak = ""
            speed_str = "1.0x"
            elapsed = 0.0
            tracker = ProgressTracker(
                ewma_alpha=float(self.settings.get("ewma_alpha", 0.3) or 0.3),
                min_emit_interval=0.25,
            )
            
            # Use threading to read stderr without blocking
            import threading
            stderr_buffer = []
            stderr_done = threading.Event()
            
            def read_stderr():
                """Read stderr in background thread and parse FFmpeg progress."""
                nonlocal speed_str, elapsed
                try:
                    last_progress_time = start_time
                    no_output_timeout = 30.0
                    
                    self.sig_log.emit(self.wid, "Reading FFmpeg output...")
                    
                    while proc.poll() is None:
                        if (
                            time.time() - last_progress_time > no_output_timeout
                            and tracker.duration_seconds is None
                        ):
                            self.sig_log.emit(
                                self.wid,
                                f"Warning: No output from FFmpeg for {no_output_timeout}s. Process may be stuck.",
                            )
                        
                        line = None
                        try:
                            line = proc.stderr.readline()
                        except (OSError, ValueError, AttributeError) as e:
                            if "peek" not in str(e).lower():
                                self.sig_log.emit(self.wid, f"Read error: {e}")
                            time.sleep(0.1)
                            continue
                        
                        if line:
                            line_str = line.decode("utf-8", errors="ignore").strip()
                            if line_str:
                                last_progress_time = time.time()
                                stderr_buffer.append(line_str)
                                self.sig_log.emit(self.wid, line_str)
                                
                                prev_duration = tracker.duration_seconds
                                elapsed = time.time() - start_time
                                sample = tracker.update_from_line(line_str, elapsed)
                                if (
                                    tracker.duration_seconds is not None
                                    and prev_duration is None
                                ):
                                    self.sig_log.emit(
                                        self.wid,
                                        f"Detected duration: {tracker.duration_seconds:.2f}s",
                                    )
                                if sample.emitted:
                                    speed_str = sample.speed_str
                                    self.sig_progress.emit(
                                        self.wid,
                                        sample.progress,
                                        sample.elapsed,
                                        sample.eta,
                                        sample.speed_str,
                                        peak,
                                        true_peak,
                                    )
                                elif (
                                    "frame=" in line_str
                                    and tracker.duration_seconds is None
                                ):
                                    import re
                                    frame_match = re.search(r"frame=\s*(\d+)", line_str)
                                    if frame_match:
                                        self.sig_log.emit(
                                            self.wid,
                                            f"Processing frames... (frame {frame_match.group(1)})",
                                        )
                        else:
                            time.sleep(0.1)
                    
                    try:
                        remaining_stderr = proc.stderr.read()
                        if remaining_stderr:
                            for line in remaining_stderr.decode("utf-8", errors="ignore").splitlines():
                                line_str = line.strip()
                                if line_str:
                                    stderr_buffer.append(line_str)
                                    self.sig_log.emit(self.wid, line_str)
                    except Exception:
                        pass
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    self.sig_log.emit(self.wid, f"Error reading stderr: {e}")
                    self.sig_log.emit(self.wid, f"Traceback: {error_detail}")
                finally:
                    stderr_done.set()
            
            # Start stderr reader thread
            stderr_thread = threading.Thread(target=read_stderr, daemon=True)
            stderr_thread.start()
            
            # Monitor process; keepalive must not overwrite real progress
            last_check_time = time.time()
            while proc.poll() is None:
                self._mutex.lock()
                while self._paused and not self._stopped:
                    self._wait_condition.wait(self._mutex)
                self._mutex.unlock()
                
                if self._stopped:
                    proc.terminate()
                    break
                
                current_time = time.time()
                if current_time - last_check_time > 5.0:
                    elapsed = current_time - start_time
                    sample = tracker.keepalive(elapsed)
                    if sample.emitted:
                        speed_str = sample.speed_str
                        self.sig_progress.emit(
                            self.wid,
                            sample.progress,
                            sample.elapsed,
                            sample.eta,
                            sample.speed_str,
                            peak,
                            true_peak,
                        )
                    last_check_time = current_time
                
                time.sleep(0.5)
            
            # Wait for process to finish (with timeout to prevent hanging)
            try:
                return_code = proc.wait(timeout=3600)  # 1 hour max
            except subprocess.TimeoutExpired:
                proc.kill()
                return_code = -1
                self._fail("Conversion timed out after 1 hour")
                return
            
            # Wait for stderr thread to finish (with timeout)
            stderr_done.wait(timeout=2.0)
            
            # Handle two-pass encoding if enabled (second pass)
            if self.job.two_pass and self.job.reduce_size and not self.job.extract_audio_only and return_code == 0:
                # First pass completed, now run second pass
                # Update command for second pass
                try:
                    pass_idx = cmd.index("-pass")
                    cmd[pass_idx + 1] = "2"
                    # Change output from null to actual destination
                    output_idx = cmd.index(first_pass_dst)
                    cmd[output_idx] = dst
                except (ValueError, IndexError):
                    # Fallback: rebuild command for second pass
                    cmd = self._build_ffmpeg_command(
                        dst,
                        hw_accel="software",
                        force_software=True,
                        two_pass=False,
                    )
                    # Manually add second pass parameters
                    try:
                        passlog_idx = cmd.index("-passlogfile")
                        cmd.insert(passlog_idx + 2, "2")
                        cmd.insert(passlog_idx + 2, "-pass")
                    except ValueError:
                        pass_logfile = dst + ".ffmpeg2pass"
                        output_idx = cmd.index(dst)
                        cmd.insert(output_idx - 1, pass_logfile)
                        cmd.insert(output_idx - 1, "-passlogfile")
                        cmd.insert(output_idx - 1, "2")
                        cmd.insert(output_idx - 1, "-pass")
                
                # Run second pass
                proc2 = run_ffmpeg(cmd)
                if proc2:
                    while True:
                        # Check if paused
                        self._mutex.lock()
                        while self._paused and not self._stopped:
                            self._wait_condition.wait(self._mutex)
                        self._mutex.unlock()
                        
                        if self._stopped:
                            proc2.terminate()
                            proc2.wait()
                            return_code = 1
                            break
                        
                        # FFmpeg outputs to stderr, not stdout
                        if proc2.poll() is not None:
                            break
                        # Read from stderr in background (similar to first pass)
                        time.sleep(0.1)
                    if return_code == 0:
                        return_code = proc2.wait()
                        elapsed = time.time() - start_time
                        sample = tracker.force_complete(elapsed, speed_str or "1.0x")
                        speed_str = sample.speed_str
                        self.sig_progress.emit(
                            self.wid,
                            sample.progress,
                            sample.elapsed,
                            sample.eta,
                            sample.speed_str,
                            peak,
                            true_peak,
                        )
                    
                    # Clean up two-pass log file
                    try:
                        pass_logfile = dst + ".ffmpeg2pass-0.log"
                        if os.path.exists(pass_logfile):
                            os.remove(pass_logfile)
                        pass_logfile = dst + ".ffmpeg2pass-0.log.mbtree"
                        if os.path.exists(pass_logfile):
                            os.remove(pass_logfile)
                    except:
                        pass
                else:
                    return_code = 1
            
            # Get return code (wait if not already done)
            if return_code is None:
                return_code = proc.wait()
            
            # Read any remaining stderr output
            try:
                remaining_stderr = proc.stderr.read()
                if remaining_stderr:
                    stderr_text = remaining_stderr.decode("utf-8", errors="ignore")
                    # Log last few lines
                    lines = stderr_text.splitlines()
                    for line in lines[-5:]:  # Last 5 lines
                        if line.strip():
                            self.sig_log.emit(self.wid, line.strip())
            except:
                pass
            
            if return_code == 0:
                if elapsed == 0.0:
                    elapsed = time.time() - start_time
                sample = tracker.force_complete(elapsed, speed_str or "1.0x")
                speed_str = sample.speed_str
                self.sig_progress.emit(
                    self.wid,
                    sample.progress,
                    sample.elapsed,
                    sample.eta,
                    sample.speed_str,
                    peak,
                    true_peak,
                )
                
                # Verify output file was created and has content
                if not os.path.exists(dst):
                    self._fail(
                        f"Conversion completed but output file not found: {dst}",
                        output_path=dst,
                    )
                    return
                
                # Check if output file has reasonable size
                # For video files, check if video stream exists
                try:
                    output_size = os.path.getsize(dst)
                    # For video files, check minimum size (video files should be larger)
                    if self.job.reduce_size or (is_video_file(self.job.src) and is_video_file(dst)):
                        # Video files should be at least 100KB (very small videos)
                        min_size = 100 * 1024
                        if output_size < min_size:
                            self._fail(
                                f"Output file is too small ({output_size} bytes) - video stream may be missing",
                                output_path=dst,
                            )
                            return
                    elif output_size < 1024:  # Audio files: at least 1KB
                        self._fail(
                            f"Output file is too small ({output_size} bytes) - conversion may have failed",
                            output_path=dst,
                        )
                        return
                    
                    # Additional check: verify video stream exists for video-to-video conversions
                    if is_video_file(self.job.src) and is_video_file(dst):
                        from ..util.ffmpeg import find_ffprobe
                        ffprobe = find_ffprobe()
                        if ffprobe:
                            import json
                            check_cmd = [
                                ffprobe,
                                "-v", "quiet",
                                "-print_format", "json",
                                "-show_streams",
                                "-select_streams", "v",  # Only video streams
                                dst
                            ]
                            try:
                                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=5)
                                if result.returncode == 0:
                                    data = json.loads(result.stdout)
                                    video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
                                    if not video_streams:
                                        self._fail(
                                            "Conversion completed but output file has no video stream - video was not included",
                                            output_path=dst,
                                        )
                                        return
                            except:
                                pass  # If check fails, assume it's OK
                except Exception as e:
                    # If size check fails, log but don't fail the conversion
                    self.sig_log.emit(self.wid, f"Warning: Could not verify output file size: {e}")
                
                # Delete original file if requested
                if self.job.delete_original and os.path.exists(self.job.src):
                    try:
                        os.remove(self.job.src)
                        self.sig_done.emit(self.wid, True, f"Conversion completed, original file deleted\nSaved to: {dst}", dst)
                    except Exception as e:
                        self.sig_done.emit(self.wid, True, f"Conversion completed, but failed to delete original: {str(e)}\nSaved to: {dst}", dst)
                else:
                    self.sig_done.emit(self.wid, True, f"Conversion completed successfully\nSaved to: {dst}", dst)
            else:
                # Prefer buffered stderr (already consumed by the reader thread)
                stderr_text = "\n".join(stderr_buffer)
                if not stderr_text:
                    try:
                        remaining = proc.stderr.read()
                        if remaining:
                            stderr_text = remaining.decode("utf-8", errors="ignore")
                    except Exception:
                        pass
                vcodec = self._video_codec_from_cmd(cmd)
                if is_hw_encoder(vcodec):
                    fb_rc = self._software_fallback_encode(
                        dst, stderr_hint=stderr_text
                    )
                    if fb_rc == 0:
                        # Minimal success verification for fallback path
                        if os.path.exists(dst) and os.path.getsize(dst) > 0:
                            self.sig_done.emit(
                                self.wid,
                                True,
                                f"Conversion completed successfully (software fallback)\nSaved to: {dst}",
                                dst,
                            )
                            return
                self._fail(
                    f"Conversion failed with exit code {return_code}",
                    stderr=stderr_text,
                )
        
        except Exception as e:
            self._fail(f"Error: {e}", exc=e)


class Orchestrator(QObject):
    """Manages conversion workers and queue."""
    
    sig_worker_done = pyqtSignal(int, bool, str, str)  # wid, success, message, output_path
    sig_worker_progress = pyqtSignal(int, float, float, float, str, str, str)  # wid, progress, elapsed, eta, speed, peak, true_peak
    sig_worker_log = pyqtSignal(int, str)  # wid, log_line
    sig_worker_started = pyqtSignal(int, str)  # wid, file_path
    
    def __init__(self, threads_per_job: int = 1, max_parallel: int = 2):
        super().__init__()
        self.threads_per_job = threads_per_job
        self.max_parallel = max_parallel
        self.workers: Dict[int, Worker] = {}
        self.job_queue: List[Job] = []
        self.settings: Dict[str, Any] = {}
        self.next_wid = 1
    
    def set_settings(self, settings: Dict[str, Any]):
        """Set application settings."""
        self.settings = settings
        self.max_parallel = settings.get("parallel", 2)

    def _effective_max_parallel(self) -> int:
        """User parallel ceiling, optionally lowered by the adaptive scheduler.

        Uses the Rust native module when built; otherwise the Python fallback.
        Keeps headroom so HandForge can run beside other apps without saturating RAM.
        """
        user_max = int(self.settings.get("parallel", self.max_parallel) or 1)
        if not self.settings.get("adaptive_parallel", True):
            return max(1, user_max)
        avg_rss = 0
        if self.job_queue:
            avg_rss = estimate_job_rss_mb(is_video_file(self.job_queue[0].src))
        return recommend_parallel(user_max, len(self.workers), avg_rss)
    
    def enqueue(self, jobs: List[Job]):
        """Add jobs to the queue."""
        self.job_queue.extend(jobs)
        self._process_queue()
    
    def _process_queue(self):
        """Process queued jobs."""
        while self.job_queue:
            if len(self.workers) >= self._effective_max_parallel():
                break
            job = self.job_queue.pop(0)
            wid = self.next_wid
            self.next_wid += 1
            
            # Set threads based on codec
            codec_threads = self.settings.get("codec_threads", {})
            job.threads = codec_threads.get(job.format, 1)
            
            worker = Worker(wid, job, self.settings)
            worker.sig_done.connect(self._on_worker_done)
            worker.sig_progress.connect(self.sig_worker_progress)
            worker.sig_log.connect(self.sig_worker_log)
            
            self.workers[wid] = worker
            # Emit signal that worker is starting with file path
            self.sig_worker_started.emit(wid, job.src)
            worker.start()
    
    def _on_worker_done(self, wid: int, success: bool, message: str, output_path: str):
        """Handle worker completion."""
        if wid in self.workers:
            worker = self.workers[wid]
            worker.wait(5000)  # Wait up to 5 seconds for thread to finish
            if wid in self.workers:
                del self.workers[wid]
        
        self.sig_worker_done.emit(wid, success, message, output_path)
        self._process_queue()  # Process next job
    
    def pause_worker(self, wid: int):
        """Pause a specific worker."""
        if wid in self.workers:
            self.workers[wid].pause()
    
    def resume_worker(self, wid: int):
        """Resume a specific worker."""
        if wid in self.workers:
            self.workers[wid].resume()
    
    def stop_worker(self, wid: int):
        """Stop a specific worker."""
        if wid in self.workers:
            self.workers[wid].stop()
    
    def pause_all(self):
        """Pause all workers."""
        for worker in self.workers.values():
            worker.pause()
    
    def resume_all(self):
        """Resume all workers."""
        for worker in self.workers.values():
            worker.resume()
    
    def stop_all(self):
        """Stop all workers."""
        for worker in self.workers.values():
            worker.stop()
        
        # Wait for all workers to finish
        for worker in list(self.workers.values()):
            worker.wait()
        
        self.workers.clear()
        self.job_queue.clear()

