//! Adaptive parallel-job scheduler for HandForge.
//!
//! Caps concurrent conversion slots from live memory and load so FFmpeg batches
//! leave headroom for other apps. Exposed as a C ABI for Python ctypes.

use std::cmp::{max, min};

/// Default estimated RSS (MiB) for one FFmpeg conversion when the caller passes 0.
pub const DEFAULT_JOB_RSS_MB: u64 = 350;

/// Minimum RAM (MiB) reserved for the OS and other applications.
pub const MIN_RESERVE_MB: u64 = 768;

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct HfSystemSnapshot {
    pub total_mem_mb: u64,
    pub avail_mem_mb: u64,
    pub cpu_count: u32,
    /// load average * 100 (1-minute), or 0 if unavailable
    pub load_x100: u32,
    pub recommended_parallel: u32,
}

/// Read total/available system memory in MiB.
fn read_memory_mb() -> (u64, u64) {
    #[cfg(target_os = "linux")]
    {
        if let Ok(text) = std::fs::read_to_string("/proc/meminfo") {
            let mut total_kb = 0u64;
            let mut avail_kb = 0u64;
            let mut free_kb = 0u64;
            let mut buffers_kb = 0u64;
            let mut cached_kb = 0u64;
            for line in text.lines() {
                let mut parts = line.split_whitespace();
                let key = match parts.next() {
                    Some(k) => k,
                    None => continue,
                };
                let val: u64 = match parts.next().and_then(|v| v.parse().ok()) {
                    Some(v) => v,
                    None => continue,
                };
                match key {
                    "MemTotal:" => total_kb = val,
                    "MemAvailable:" => avail_kb = val,
                    "MemFree:" => free_kb = val,
                    "Buffers:" => buffers_kb = val,
                    "Cached:" => cached_kb = val,
                    _ => {}
                }
            }
            if avail_kb == 0 {
                avail_kb = free_kb + buffers_kb + cached_kb;
            }
            return (total_kb / 1024, avail_kb / 1024);
        }
    }

    #[cfg(target_os = "macos")]
    {
        // sysctl hw.memsize + host_statistics64 would be ideal; use conservative
        // parse of `sysctl` / vm_stat via pure Rust std is limited. Fall back to
        // page-size heuristics from sysctlbyname through libc-free command is avoided;
        // use a best-effort sysctl file-free approach via `std::process` only if needed.
        // Prefer mach APIs without extra deps: read hw.memsize via sysctl.
        if let (Ok(total), Ok(avail)) = (macos_total_mb(), macos_avail_mb()) {
            return (total, avail);
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Some((total, avail)) = windows_memory_mb() {
            return (total, avail);
        }
    }

    // Unknown platform / read failure: assume modest laptop so we stay conservative.
    (8192, 4096)
}

#[cfg(target_os = "macos")]
fn macos_total_mb() -> Result<u64, ()> {
    use std::process::Command;
    let out = Command::new("sysctl")
        .args(["-n", "hw.memsize"])
        .output()
        .map_err(|_| ())?;
    if !out.status.success() {
        return Err(());
    }
    let s = String::from_utf8_lossy(&out.stdout);
    let bytes: u64 = s.trim().parse().map_err(|_| ())?;
    Ok(bytes / (1024 * 1024))
}

#[cfg(target_os = "macos")]
fn macos_avail_mb() -> Result<u64, ()> {
    use std::process::Command;
    let out = Command::new("vm_stat").output().map_err(|_| ())?;
    if !out.status.success() {
        return Err(());
    }
    let text = String::from_utf8_lossy(&out.stdout);
    let mut page_size = 4096u64;
    let mut free = 0u64;
    let mut inactive = 0u64;
    let mut speculative = 0u64;
    for line in text.lines() {
        if let Some(rest) = line.strip_prefix("Mach Virtual Memory Statistics:") {
            let _ = rest;
        }
        if line.contains("page size of") {
            for part in line.split_whitespace() {
                if let Ok(n) = part.parse::<u64>() {
                    page_size = n;
                    break;
                }
            }
        }
        let parse_pages = |prefix: &str| -> Option<u64> {
            let rest = line.strip_prefix(prefix)?;
            let num = rest.trim().trim_end_matches('.').replace(',', "");
            num.parse().ok()
        };
        if let Some(n) = parse_pages("Pages free:") {
            free = n;
        } else if let Some(n) = parse_pages("Pages inactive:") {
            inactive = n;
        } else if let Some(n) = parse_pages("Pages speculative:") {
            speculative = n;
        }
    }
    let pages = free + inactive + speculative;
    Ok(pages * page_size / (1024 * 1024))
}

#[cfg(target_os = "windows")]
fn windows_memory_mb() -> Option<(u64, u64)> {
    // MEMORYSTATUSEX via kernel32 without the `windows` crate: use GlobalMemoryStatusEx
    // through a tiny FFI binding.
    #[repr(C)]
    struct MemoryStatusEx {
        dw_length: u32,
        dw_memory_load: u32,
        ull_total_phys: u64,
        ull_avail_phys: u64,
        ull_total_page_file: u64,
        ull_avail_page_file: u64,
        ull_total_virtual: u64,
        ull_avail_virtual: u64,
        ull_avail_extended_virtual: u64,
    }

    #[link(name = "kernel32")]
    extern "system" {
        fn GlobalMemoryStatusEx(lpBuffer: *mut MemoryStatusEx) -> i32;
    }

    unsafe {
        let mut st = MemoryStatusEx {
            dw_length: std::mem::size_of::<MemoryStatusEx>() as u32,
            dw_memory_load: 0,
            ull_total_phys: 0,
            ull_avail_phys: 0,
            ull_total_page_file: 0,
            ull_avail_page_file: 0,
            ull_total_virtual: 0,
            ull_avail_virtual: 0,
            ull_avail_extended_virtual: 0,
        };
        if GlobalMemoryStatusEx(&mut st) == 0 {
            return None;
        }
        Some((
            st.ull_total_phys / (1024 * 1024),
            st.ull_avail_phys / (1024 * 1024),
        ))
    }
}

fn read_cpu_count() -> u32 {
    std::thread::available_parallelism()
        .map(|n| n.get() as u32)
        .unwrap_or(1)
        .max(1)
}

fn read_load_x100() -> u32 {
    #[cfg(target_os = "linux")]
    {
        if let Ok(text) = std::fs::read_to_string("/proc/loadavg") {
            if let Some(first) = text.split_whitespace().next() {
                if let Ok(v) = first.parse::<f64>() {
                    return (v * 100.0).round().max(0.0) as u32;
                }
            }
        }
    }
    #[cfg(any(target_os = "macos", target_os = "freebsd"))]
    {
        use std::process::Command;
        if let Ok(out) = Command::new("sysctl").args(["-n", "vm.loadavg"]).output() {
            if out.status.success() {
                let s = String::from_utf8_lossy(&out.stdout);
                // "{ 1.23 1.45 1.67 }" or "1.23 1.45 1.67"
                for part in s.split(|c: char| c == '{' || c == '}' || c.is_whitespace()) {
                    if let Ok(v) = part.parse::<f64>() {
                        return (v * 100.0).round().max(0.0) as u32;
                    }
                }
            }
        }
    }
    0
}

/// Pure scheduling decision (testable without live syscalls when metrics are injected).
pub fn recommend_parallel_from_metrics(
    user_max: u32,
    active_jobs: u32,
    avg_job_rss_mb: u64,
    total_mem_mb: u64,
    avail_mem_mb: u64,
    cpu_count: u32,
    load_x100: u32,
) -> u32 {
    let user_max = user_max.max(1);
    let job_mb = if avg_job_rss_mb == 0 {
        DEFAULT_JOB_RSS_MB
    } else {
        avg_job_rss_mb.max(64)
    };
    let cpu = cpu_count.max(1);

    // Keep ≥20% of RAM (or MIN_RESERVE_MB) free for desktop multitasking.
    let reserve = max(MIN_RESERVE_MB, total_mem_mb / 5);

    // Reconstruct soft capacity: available + memory attributed to our active slots.
    // Lets Python raise active_jobs in a spawn loop before RSS shows up in avail.
    let capacity_mb = avail_mem_mb.saturating_add(u64::from(active_jobs).saturating_mul(job_mb));
    let usable_mb = capacity_mb.saturating_sub(reserve);
    let max_by_mem = (usable_mb / job_mb) as u32;

    // Soft CPU cap: each parallel FFmpeg can already use multiple threads.
    let load = f64::from(load_x100) / 100.0;
    let mut cpu_cap = cpu;
    if load_x100 > 0 {
        if load > f64::from(cpu) * 0.90 {
            cpu_cap = max(1, cpu / 2);
        } else if load > f64::from(cpu) * 0.70 {
            cpu_cap = max(1, (f64::from(cpu) * 0.75).floor() as u32);
        }
    }

    let by_resource = min(max_by_mem.max(1), cpu_cap);
    min(user_max, by_resource.max(1))
}

fn snapshot_with_user_max(user_max: u32, avg_job_rss_mb: u64, active_jobs: u32) -> HfSystemSnapshot {
    let (total_mem_mb, avail_mem_mb) = read_memory_mb();
    let cpu_count = read_cpu_count();
    let load_x100 = read_load_x100();
    let recommended_parallel = recommend_parallel_from_metrics(
        user_max,
        active_jobs,
        avg_job_rss_mb,
        total_mem_mb,
        avail_mem_mb,
        cpu_count,
        load_x100,
    );
    HfSystemSnapshot {
        total_mem_mb,
        avail_mem_mb,
        cpu_count,
        load_x100,
        recommended_parallel,
    }
}

/// Recommend concurrent conversion slots (user_max is a hard ceiling).
#[no_mangle]
pub extern "C" fn hf_recommend_parallel(
    user_max: u32,
    active_jobs: u32,
    avg_job_rss_mb: u64,
) -> u32 {
    snapshot_with_user_max(user_max, avg_job_rss_mb, active_jobs).recommended_parallel
}

/// Fill a snapshot struct; returns 0 on success, non-zero on null pointer.
#[no_mangle]
pub extern "C" fn hf_system_snapshot(
    out: *mut HfSystemSnapshot,
    user_max: u32,
    active_jobs: u32,
    avg_job_rss_mb: u64,
) -> i32 {
    if out.is_null() {
        return 1;
    }
    let snap = snapshot_with_user_max(user_max, avg_job_rss_mb, active_jobs);
    unsafe {
        *out = snap;
    }
    0
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn respects_user_max() {
        let n = recommend_parallel_from_metrics(2, 0, 350, 32768, 30000, 16, 50);
        assert_eq!(n, 2);
    }

    #[test]
    fn tight_memory_reduces_slots() {
        // 2 GiB total, ~900 MiB avail, reserve max(768, 409)=768 → usable ~132 → 0 jobs by mem → clamped to 1
        let n = recommend_parallel_from_metrics(8, 0, 350, 2048, 900, 8, 100);
        assert_eq!(n, 1);
    }

    #[test]
    fn active_jobs_consume_budget() {
        // Plenty of RAM; active=3 with 350MB each should still allow up to user_max when capacity is high
        let n = recommend_parallel_from_metrics(4, 3, 350, 16384, 12000, 8, 50);
        assert!(n >= 3);
        assert!(n <= 4);
    }

    #[test]
    fn high_load_cuts_cpu_cap() {
        let low = recommend_parallel_from_metrics(16, 0, 64, 65536, 60000, 8, 50);
        let high = recommend_parallel_from_metrics(16, 0, 64, 65536, 60000, 8, 800); // load 8.0 on 8 CPUs
        assert!(high <= low);
        assert!(high <= 4); // half of 8
    }
}
