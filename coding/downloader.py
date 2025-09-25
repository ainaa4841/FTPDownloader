# downloader.py
import os
import time
from ftplib import FTP
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

cancel_flag = threading.Event()

def set_cancel():
    """Signal cancellation of ongoing downloads."""
    cancel_flag.set()

def ftp_connect(host, user, passwd, retries=3, delay=5):
    """Establish an FTP connection with retries."""
    last_exc = None
    for _ in range(retries):
        try:
            ftp = FTP(host, timeout=30)
            ftp.login(user, passwd)
            return ftp
        except Exception as e:
            last_exc = e
            time.sleep(delay)
    raise ConnectionError(f"FTP connection failed: {last_exc}")

def download_single_file(host, user, passwd, remote_path, local_path):
    """Download a single file from FTP."""
    if cancel_flag.is_set():
        return None, "Cancelled"

    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        ftp = ftp_connect(host, user, passwd)
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_path}", f.write)
        ftp.quit()
        return local_path, None
    except Exception as e:
        return None, str(e)

def download_files_range(host, user, passwd,
                         station_id, state,
                         start_date, end_date,
                         start_hour, start_minute,
                         end_hour, end_minute,
                         remote_base, progress_callback=None,
                         max_workers=5):
    """
    Multi-threaded download of files from FTP.
    """
    cancel_flag.clear()
    downloaded = []
    failed = []
    tasks = []

    # Build all file paths (simplified example for demo)
    date_range = (end_date - start_date).days + 1
    files_to_download = []
    for d in range(date_range):
        day = start_date + (end_date - start_date) * d // (date_range - 1 if date_range > 1 else 1)
        for h in range(start_hour, end_hour + 1):
            for m in [0, 15, 30, 45]:  # quarter-hour steps
                if (h == start_hour and m < start_minute) or (h == end_hour and m > end_minute):
                    continue
                filename = f"{station_id}_{day.strftime('%Y%m%d')}{h:02d}{m:02d}.txt"
                remote_path = f"{remote_base}/{state}/{station_id}/{filename}"
                local_path = os.path.join("stations", state, station_id, filename)
                files_to_download.append((remote_path, local_path))

    total_files = len(files_to_download)
    current = 0

    # Use ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(download_single_file, host, user, passwd, remote, local): (remote, local)
            for remote, local in files_to_download
        }
        for future in as_completed(future_to_file):
            current += 1
            remote, local = future_to_file[future]
            try:
                result, error = future.result()
                if result:
                    downloaded.append(result)
                else:
                    failed.append((remote, error))
            except Exception as e:
                failed.append((remote, str(e)))

            if progress_callback:
                progress_callback(current, total_files, os.path.basename(remote))

            if cancel_flag.is_set():
                break

    return downloaded, failed