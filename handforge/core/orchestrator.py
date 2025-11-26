"""Conversion orchestrator for HandForge."""

import os
import time
import subprocess
import sys
import platform
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QMutex, QWaitCondition
from .models import Job
from ..util.ffmpeg import build_ffmpeg_cmd, run_ffmpeg, out_path

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
    
    def run(self):
        """Run the conversion."""
        try:
            # Check if paused
            self._mutex.lock()
            while self._paused and not self._stopped:
                self._wait_condition.wait(self._mutex)
            self._mutex.unlock()
            
            if self._stopped:
                self.sig_done.emit(self.wid, False, "Stopped by user", "")
                return
            
            # Verify source file exists
            if not os.path.exists(self.job.src):
                self.sig_done.emit(self.wid, False, f"Source file not found: {self.job.src}", "")
                return
            
            # Build output path
            dst = out_path(self.job.dst_dir, self.job.src, self.job.format)
            
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
            
            # For two-pass encoding, first pass outputs to null device
            first_pass_dst = dst
            if self.job.two_pass and self.job.reduce_size and not self.job.extract_audio_only:
                import platform
                if platform.system() == "Windows":
                    first_pass_dst = "NUL"
                else:
                    first_pass_dst = "/dev/null"
            
            # Build FFmpeg command (use first_pass_dst for two-pass)
            cmd = build_ffmpeg_cmd(
                src=self.job.src,
                dst=first_pass_dst,
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
                } if not self.job.strip_meta else {},
                copy_meta=self.job.copy_meta and not self.job.strip_meta,
                prefer_external_cover=self.job.prefer_external_cover,
                normalize_lufs=self.job.normalize_lufs,
                target_lufs=self.job.target_lufs,
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
                two_pass=self.job.two_pass,
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
            )
            
            # Run FFmpeg
            start_time = time.time()
            
            # Log command details for debugging
            self.sig_log.emit(self.wid, f"Starting conversion: {os.path.basename(self.job.src)}")
            self.sig_log.emit(self.wid, f"Format: {self.job.format}, Mode: {self.job.mode}")
            self.sig_log.emit(self.wid, f"Output: {dst}")
            self.sig_log.emit(self.wid, f"FFmpeg command: {' '.join(cmd[:10])}...")  # Log first 10 args
            
            try:
                proc = run_ffmpeg(cmd)
            except Exception as e:
                self.sig_done.emit(self.wid, False, f"Failed to start FFmpeg: {str(e)}", "")
                return
            
            if proc is None:
                self.sig_done.emit(self.wid, False, "Failed to start FFmpeg - check if FFmpeg is installed and on PATH", "")
                return
            
            # Verify process started successfully
            # Give it a moment to start, then check if it's still running
            time.sleep(0.1)
            if proc.poll() is not None:
                # Process finished immediately - likely an error
                try:
                    stderr_output = proc.stderr.read()
                    error_msg = "FFmpeg process exited immediately"
                    if stderr_output:
                        error_text = stderr_output.decode("utf-8", errors="ignore")
                        error_lines = [l for l in error_text.splitlines() if l.strip() and ("error" in l.lower() or "failed" in l.lower() or "invalid" in l.lower())]
                        if error_lines:
                            error_msg = error_lines[-1][:300]
                        else:
                            # Show last few lines
                            lines = error_text.splitlines()
                            if lines:
                                error_msg = "\n".join(lines[-3:])[:300]
                    self.sig_log.emit(self.wid, f"Error: {error_msg}")
                    self.sig_done.emit(self.wid, False, error_msg, "")
                except Exception as e:
                    self.sig_done.emit(self.wid, False, f"FFmpeg process exited immediately: {str(e)}", "")
                return
            
            # Monitor progress
            last_progress = 0.0
            last_time = start_time
            peak = ""
            true_peak = ""
            
            # Use threading to read stderr without blocking
            import threading
            stderr_buffer = []
            stderr_done = threading.Event()
            
            def read_stderr():
                """Read stderr in background thread and parse FFmpeg progress."""
                import re
                import select
                import msvcrt
                import platform
                try:
                    duration_seconds = None
                    last_progress_time = start_time
                    no_output_timeout = 30.0  # 30 seconds without output = potential issue
                    
                    # Log that we're starting to read stderr
                    self.sig_log.emit(self.wid, "Reading FFmpeg output...")
                    
                    while proc.poll() is None:
                        # Check for timeout - if no output for too long, something is wrong
                        if time.time() - last_progress_time > no_output_timeout and duration_seconds is None:
                            self.sig_log.emit(self.wid, f"Warning: No output from FFmpeg for {no_output_timeout}s. Process may be stuck.")
                        
                        # Try to read a line - use readline() directly
                        # With unbuffered mode (bufsize=0), this should work
                        line = None
                        try:
                            # Simple readline - it may block briefly but that's okay in a thread
                            line = proc.stderr.readline()
                        except (OSError, ValueError, AttributeError) as e:
                            # If read fails, log and continue
                            if "peek" not in str(e).lower():  # Don't log peek errors
                                self.sig_log.emit(self.wid, f"Read error: {e}")
                            time.sleep(0.1)
                            continue
                        
                        if line:
                            line_str = line.decode("utf-8", errors="ignore").strip()
                            if line_str:
                                last_progress_time = time.time()
                                stderr_buffer.append(line_str)
                                self.sig_log.emit(self.wid, line_str)
                                
                                # Parse duration from input (first time we see it)
                                if duration_seconds is None:
                                    # Try multiple duration formats
                                    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line_str)
                                    if duration_match:
                                        h, m, s, ms = map(int, duration_match.groups())
                                        duration_seconds = h * 3600 + m * 60 + s + ms / 100.0
                                        self.sig_log.emit(self.wid, f"Detected duration: {duration_seconds:.2f}s")
                                
                                # Parse progress from frame/time info
                                # Format: frame=  123 fps= 25 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.25x
                                progress_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line_str)
                                if progress_match and duration_seconds:
                                    h, m, s, ms = map(int, progress_match.groups())
                                    current_seconds = h * 3600 + m * 60 + s + ms / 100.0
                                    if duration_seconds > 0:
                                        progress = min(99.0, (current_seconds / duration_seconds) * 100.0)
                                        # Update progress immediately
                                        elapsed = time.time() - start_time
                                        remaining = (duration_seconds - current_seconds) if current_seconds < duration_seconds else 0
                                        
                                        # Parse speed if available
                                        speed_match = re.search(r'speed=\s*([\d.]+)x', line_str)
                                        speed_str = speed_match.group(1) + "x" if speed_match else "1.0x"
                                        
                                        self.sig_progress.emit(
                                            self.wid, progress, elapsed, remaining, speed_str, peak, true_peak
                                        )
                                # Also try to parse frame count for progress estimation
                                elif "frame=" in line_str and duration_seconds is None:
                                    # If we see frame info but no duration yet, at least log it
                                    frame_match = re.search(r'frame=\s*(\d+)', line_str)
                                    if frame_match:
                                        self.sig_log.emit(self.wid, f"Processing frames... (frame {frame_match.group(1)})")
                        else:
                            time.sleep(0.1)
                    
                    # Read remaining
                    try:
                        remaining = proc.stderr.read()
                        if remaining:
                            for line in remaining.decode("utf-8", errors="ignore").splitlines():
                                line_str = line.strip()
                                if line_str:
                                    stderr_buffer.append(line_str)
                                    self.sig_log.emit(self.wid, line_str)
                    except:
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
            
            # Monitor progress while process runs
            last_check_time = time.time()
            while proc.poll() is None:
                # Check if paused
                self._mutex.lock()
                while self._paused and not self._stopped:
                    self._wait_condition.wait(self._mutex)
                self._mutex.unlock()
                
                if self._stopped:
                    proc.terminate()
                    break
                
                # Emit a minimal progress update periodically if no progress has been reported
                # This helps detect if the process is actually running
                current_time = time.time()
                if current_time - last_check_time > 5.0:  # Every 5 seconds
                    elapsed = current_time - start_time
                    # Emit a small progress update to show the process is alive
                    # Use 0.1% to indicate "processing" without actual progress
                    self.sig_progress.emit(
                        self.wid, 0.1, elapsed, 0.0, "?", peak, true_peak
                    )
                    last_check_time = current_time
                
                # Progress is now parsed from FFmpeg stderr in read_stderr thread
                # Just check process status periodically
                time.sleep(0.5)  # Check every 0.5 seconds
            
            # Wait for process to finish (with timeout to prevent hanging)
            try:
                return_code = proc.wait(timeout=3600)  # 1 hour max
            except subprocess.TimeoutExpired:
                proc.kill()
                return_code = -1
                self.sig_done.emit(self.wid, False, "Conversion timed out after 1 hour", "")
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
                    cmd = build_ffmpeg_cmd(
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
                        } if not self.job.strip_meta else {},
                        copy_meta=self.job.copy_meta and not self.job.strip_meta,
                        prefer_external_cover=self.job.prefer_external_cover,
                        normalize_lufs=self.job.normalize_lufs,
                        target_lufs=self.job.target_lufs,
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
                        two_pass=False,  # Second pass, don't add pass parameter again
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
                        # Emit final 100% progress for second pass
                        current_time = time.time()
                        elapsed = current_time - start_time
                        self.sig_progress.emit(
                            self.wid, 100.0, elapsed, 0.0, speed_str, peak, true_peak
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
                # Emit final 100% progress before completion
                self.sig_progress.emit(
                    self.wid, 100.0, elapsed, 0.0, speed_str, peak, true_peak
                )
                
                # Verify output file was created and has content
                if not os.path.exists(dst):
                    self.sig_done.emit(self.wid, False, f"Conversion completed but output file not found: {dst}", "")
                    return
                
                # Check if output file has reasonable size (at least 1KB)
                try:
                    output_size = os.path.getsize(dst)
                    if output_size < 1024:  # Less than 1KB is suspicious
                        self.sig_done.emit(self.wid, False, f"Output file is too small ({output_size} bytes) - conversion may have failed", dst)
                        return
                except:
                    pass
                
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
                error_msg = f"Conversion failed with exit code {return_code}"
                try:
                    stderr_text = proc.stderr.read().decode("utf-8", errors="ignore")
                    if stderr_text:
                        # Get last error line
                        error_lines = [l for l in stderr_text.splitlines() if l.strip() and ("error" in l.lower() or "failed" in l.lower())]
                        if error_lines:
                            error_msg = error_lines[-1][:200]
                        else:
                            error_msg = stderr_text[-200:] if len(stderr_text) > 200 else stderr_text
                except:
                    pass
                self.sig_done.emit(self.wid, False, error_msg, "")
        
        except Exception as e:
            self.sig_done.emit(self.wid, False, f"Error: {str(e)}", "")


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
    
    def enqueue(self, jobs: List[Job]):
        """Add jobs to the queue."""
        self.job_queue.extend(jobs)
        self._process_queue()
    
    def _process_queue(self):
        """Process queued jobs."""
        while len(self.workers) < self.max_parallel and self.job_queue:
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

