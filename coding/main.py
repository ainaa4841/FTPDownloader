# main.py
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import calendar
from contextlib import suppress
import json
import os
from downloader import download_files_range, set_cancel

PAD = {"padx": 5, "pady": 5}
SETTINGS_FILE = "settings.json"

def build_date(year_box, month_box, day_box):
    try:
        y = int(year_box.get())
        m = int(month_box.get())
        d = int(day_box.get())
        return datetime(y, m, d)
    except Exception:
        return None

def update_days(year_box, month_box, day_box):
    with suppress(Exception):
        y = int(year_box.get())
        m = int(month_box.get())
        days_in_month = calendar.monthrange(y, m)[1]
        valid_days = [str(d).zfill(2) for d in range(1, days_in_month + 1)]
        day_box["values"] = valid_days
        if day_box.get() not in valid_days:
            day_box.set(valid_days[0])

def update_preview(*args):
    station_id = station_entry.get().strip()
    state = state_entry.get().strip()
    start_date = build_date(start_year_box, start_month_box, start_day_box)
    end_date = build_date(end_year_box, end_month_box, end_day_box)

    try:
        start_hour = int(start_hour_box.get())
        start_minute = int(start_minute_box.get())
        end_hour = int(end_hour_box.get())
        end_minute = int(end_minute_box.get())
    except Exception:
        preview_label.config(text="Please complete selections above...")
        return

    if not station_id or not state or not start_date or not end_date:
        preview_label.config(text="Please complete selections above...")
        return

    date_diff = (end_date - start_date).days + 1
    if date_diff <= 0:
        preview_label.config(text="Invalid date range")
        return

    total_files = date_diff * ((end_hour - start_hour + 1) * 4)
    preview_label.config(
        text=f"State: {state} | Station: {station_id}\n"
             f"{start_date.strftime('%Y-%m-%d')} {start_hour:02d}:{start_minute:02d} → "
             f"{end_date.strftime('%Y-%m-%d')} {end_hour:02d}:{end_minute:02d}\n"
             f"Range: {date_diff} days, ~{total_files} files expected"
    )

def start_download():
    ftp_host = ftp_host_entry.get().strip()
    ftp_user = ftp_user_entry.get().strip()
    ftp_pass = ftp_pass_entry.get().strip()
    remote_base = remote_base_entry.get().strip()
    station_id = station_entry.get().strip()
    state = state_entry.get().strip()

    if not ftp_host or not ftp_user or not ftp_pass:
        messagebox.showerror("Error", "Please fill in FTP settings in 'Settings' tab.")
        return
    if not station_id or not state:
        messagebox.showerror("Error", "Please enter Station ID and State.")
        return

    start_date = build_date(start_year_box, start_month_box, start_day_box)
    end_date = build_date(end_year_box, end_month_box, end_day_box)
    if not start_date or not end_date:
        messagebox.showerror("Error", "Invalid dates selected")
        return

    try:
        start_hour = int(start_hour_box.get())
        start_minute = int(start_minute_box.get())
        end_hour = int(end_hour_box.get())
        end_minute = int(end_minute_box.get())
    except Exception:
        messagebox.showerror("Error", "Invalid times selected")
        return

    try:
        max_days = int(max_days_entry.get())
    except Exception:
        max_days = 31

    date_diff = (end_date - start_date).days + 1
    if date_diff > max_days:
        messagebox.showerror("Error", f"Date range too large. Please select {max_days} days or less.")
        return

    try:
        progress_bar["value"] = 0
        status_label.config(text="Starting download...")
        root.update_idletasks()

        downloaded, failed = download_files_range(
            ftp_host, ftp_user, ftp_pass,
            station_id, state,
            start_date, end_date,
            start_hour, start_minute,
            end_hour, end_minute,
            remote_base,
            progress_callback=update_progress,
            max_workers=5
        )

        msg = f"Downloaded {len(downloaded)} files.\n"
        if failed:
            msg += f"Failed {len(failed)} files."
        messagebox.showinfo("Done", msg)
        status_label.config(text="Download complete.")

    except Exception as e:
        messagebox.showerror("Error", str(e))
        status_label.config(text="Error occurred.")

def update_progress(current, total, filename):
    progress_bar["maximum"] = total
    progress_bar["value"] = current
    status_label.config(text=f"Downloading {current}/{total}: {filename}")
    root.update_idletasks()

def cancel_download():
    set_cancel()
    status_label.config(text="Cancelling... please wait")

# Settings persistence
def save_settings():
    settings = {
        "ftp_host": ftp_host_entry.get().strip(),
        "ftp_user": ftp_user_entry.get().strip(),
        "ftp_pass": ftp_pass_entry.get().strip(),
        "remote_base": remote_base_entry.get().strip(),
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
    messagebox.showinfo("Settings", "Settings saved successfully!")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
        ftp_host_entry.insert(0, settings.get("ftp_host", ""))
        ftp_user_entry.insert(0, settings.get("ftp_user", ""))
        ftp_pass_entry.insert(0, settings.get("ftp_pass", ""))
        remote_base_entry.delete(0, tk.END)
        remote_base_entry.insert(0, settings.get("remote_base", "/forecast/stations"))

# GUI setup
root = tk.Tk()
root.title("FTP Downloader")

notebook = ttk.Notebook(root)
notebook.pack(pady=10, expand=True)

# Settings tab
settings_frame = ttk.Frame(notebook)
settings_frame.pack(fill="both", expand=True)

tk.Label(settings_frame, text="FTP Host").grid(row=0, column=0, sticky="w", **PAD)
ftp_host_entry = tk.Entry(settings_frame, width=30)
ftp_host_entry.grid(row=0, column=1, **PAD)

tk.Label(settings_frame, text="FTP User").grid(row=1, column=0, sticky="w", **PAD)
ftp_user_entry = tk.Entry(settings_frame, width=30)
ftp_user_entry.grid(row=1, column=1, **PAD)

tk.Label(settings_frame, text="FTP Pass").grid(row=2, column=0, sticky="w", **PAD)
ftp_pass_entry = tk.Entry(settings_frame, width=30, show="*")
ftp_pass_entry.grid(row=2, column=1, **PAD)

tk.Label(settings_frame, text="Remote Base Path").grid(row=3, column=0, sticky="w", **PAD)
remote_base_entry = tk.Entry(settings_frame, width=40)
remote_base_entry.insert(0, "/forecast/stations")
remote_base_entry.grid(row=3, column=1, **PAD)

tk.Button(settings_frame, text="Save Settings", command=save_settings).grid(row=4, column=0, columnspan=2, pady=10)

# Main tab
main_frame = ttk.Frame(notebook)
main_frame.pack(fill="both", expand=True)

tk.Label(main_frame, text="Station ID").grid(row=0, column=0, **PAD)
station_entry = tk.Entry(main_frame, width=20)
station_entry.grid(row=0, column=1, **PAD)

tk.Label(main_frame, text="State").grid(row=1, column=0, **PAD)
state_entry = tk.Entry(main_frame, width=20)
state_entry.grid(row=1, column=1, **PAD)

years = [str(y) for y in range(2020, datetime.now().year + 1)]
months = [str(m).zfill(2) for m in range(1, 13)]

# Start date
tk.Label(main_frame, text="Start Date").grid(row=2, column=0, **PAD)
start_year_box = ttk.Combobox(main_frame, values=years, width=6)
start_year_box.set(str(datetime.now().year))
start_year_box.grid(row=2, column=1, sticky="w", **PAD)
start_month_box = ttk.Combobox(main_frame, values=months, width=4)
start_month_box.set("01")
start_month_box.grid(row=2, column=1, **PAD)
start_day_box = ttk.Combobox(main_frame, width=4)
start_day_box.grid(row=2, column=1, sticky="e", **PAD)
update_days(start_year_box, start_month_box, start_day_box)

# End date
tk.Label(main_frame, text="End Date").grid(row=3, column=0, **PAD)
end_year_box = ttk.Combobox(main_frame, values=years, width=6)
end_year_box.set(str(datetime.now().year))
end_year_box.grid(row=3, column=1, sticky="w", **PAD)
end_month_box = ttk.Combobox(main_frame, values=months, width=4)
end_month_box.set(str(datetime.now().month).zfill(2))
end_month_box.grid(row=3, column=1, **PAD)
end_day_box = ttk.Combobox(main_frame, width=4)
end_day_box.grid(row=3, column=1, sticky="e", **PAD)
update_days(end_year_box, end_month_box, end_day_box)

# Start time
tk.Label(main_frame, text="Start Time").grid(row=4, column=0, **PAD)
start_hour_box = ttk.Combobox(main_frame, values=[str(h).zfill(2) for h in range(24)], width=5)
start_hour_box.set("00")
start_hour_box.grid(row=4, column=1, sticky="w", **PAD)
start_minute_box = ttk.Combobox(main_frame, values=["00", "15", "30", "45"], width=5)
start_minute_box.set("00")
start_minute_box.grid(row=4, column=1, sticky="e", **PAD)

# End time
tk.Label(main_frame, text="End Time").grid(row=5, column=0, **PAD)
end_hour_box = ttk.Combobox(main_frame, values=[str(h).zfill(2) for h in range(24)], width=5)
end_hour_box.set("23")
end_hour_box.grid(row=5, column=1, sticky="w", **PAD)
end_minute_box = ttk.Combobox(main_frame, values=["00", "15", "30", "45"], width=5)
end_minute_box.set("45")
end_minute_box.grid(row=5, column=1, sticky="e", **PAD)

# Max days limit
tk.Label(main_frame, text="Max Days Allowed").grid(row=6, column=0, **PAD)
max_days_entry = tk.Entry(main_frame, width=5)
max_days_entry.insert(0, "31")
max_days_entry.grid(row=6, column=1, **PAD)

# Preview label
preview_label = tk.Label(main_frame, text="Please complete selections above...", fg="blue", justify="left")
preview_label.grid(row=7, column=0, columnspan=2, **PAD)

# Buttons
tk.Button(main_frame, text="Download", command=start_download).grid(row=8, column=0, pady=10)
tk.Button(main_frame, text="Cancel", command=cancel_download).grid(row=8, column=1, pady=10)

# Progress + Status
progress_bar = ttk.Progressbar(main_frame, length=300, mode="determinate")
progress_bar.grid(row=9, column=0, columnspan=2, pady=5)
status_label = tk.Label(main_frame, text="Idle", anchor="w")
status_label.grid(row=10, column=0, columnspan=2, pady=2)

notebook.add(main_frame, text="Main")
notebook.add(settings_frame, text="Settings")

load_settings()
root.mainloop()