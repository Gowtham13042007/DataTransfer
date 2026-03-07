import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import re

# Configuration
JETSON_USER = "JETSON_USER"
JETSON_IP = "172.28.59.187"
JETSON_DIR = "/home/JESTON_USER"
LOCAL_DIR = "/home/gowtham-papani/ascend_data/"


class DroneApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Drone Data Commander")
        self.root.geometry("750x650")
        self.root.configure(bg="#2b2b2b")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TProgressbar", thickness=15, troughcolor='#1e1e1e', background='#00ff00')

        self.total_files = 0     
        self.files_done = 0       

        self.create_widgets()

    def create_widgets(self):
        header = tk.Label(self.root, text="JETSON FILE MANAGER", font=("Helvetica", 16, "bold"),
                          bg="#2b2b2b", fg="#ffffff", pady=10)
        header.pack()

        btn_frame = tk.Frame(self.root, bg="#2b2b2b")
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Check Connection",
                   command=lambda: self.start_thread(self.check_connection)).grid(row=0, column=0, padx=5)

        ttk.Button(btn_frame, text="List Files",
                   command=lambda: self.start_thread(self.manage_list)).grid(row=0, column=1, padx=5)

        ttk.Button(btn_frame, text="Download All",
                   command=lambda: self.start_thread(self.manage_download)).grid(row=0, column=2, padx=5)

    
        tk.Label(self.root, text="Overall Progress", bg="#2b2b2b", fg="#aaaaaa",
                 font=("Helvetica", 9)).pack()
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=(0, 2))
        self.percent_label = tk.Label(self.root, text="0%", bg="#2b2b2b", fg="#00ff00",
                                      font=("Helvetica", 10))
        self.percent_label.pack()

        # Per-file speed / progress bar
        tk.Label(self.root, text="Current File", bg="#2b2b2b", fg="#aaaaaa",
                 font=("Helvetica", 9)).pack()
        self.file_progress = ttk.Progressbar(self.root, orient="horizontal", length=500, mode="determinate")
        self.file_progress.pack(pady=(0, 2))
        self.file_label = tk.Label(self.root, text="—", bg="#2b2b2b", fg="#00ccff",
                                   font=("Helvetica", 9))
        self.file_label.pack()

        self.status_box = scrolledtext.ScrolledText(self.root, height=15, width=85,
                                                    bg="#1e1e1e", fg="#00ff00", font=("Courier", 10))
        self.status_box.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)

    # ── Thread-safe UI helpers ──────────────────────────────────────────────

    def log(self, message):
        """Always route through root.after so it's called on the main thread."""
        self.root.after(0, self._log, message)

    def _log(self, message):
        self.status_box.insert(tk.END, f"> {message}\n")
        self.status_box.see(tk.END)

    def update_overall_progress(self, val):
        self.root.after(0, self._set_overall, val)

    def _set_overall(self, val):
        self.progress['value'] = val
        self.percent_label.config(text=f"{val:.1f}%")

    def update_file_progress(self, val, label=""):
        self.root.after(0, self._set_file, val, label)

    def _set_file(self, val, label):
        self.file_progress['value'] = val
        if label:
            self.file_label.config(text=label)

    # ── Worker helpers ──────────────────────────────────────────────────────

    def start_thread(self, target_func):
        thread = threading.Thread(target=target_func, daemon=True)
        thread.start()

    def check_connection(self, silent=False):
        if not silent:
            self.log(f"Testing connection to {JETSON_IP}...")
        cmd = f"ping -c 1 -W 2 {JETSON_IP}"
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if "1 received" in result.stdout:
                if not silent:
                    self.log("Connection verified.")
                return True
        except Exception:
            pass
        self.log("CRITICAL: Jetson is offline.")
        return False

    def manage_list(self):
        if self.check_connection(silent=True):
            self.log("Fetching remote file list...")
            cmd = f"ssh {JETSON_USER}@{JETSON_IP} ls {JETSON_DIR}"
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                for line in result.stdout.strip().splitlines():
                    self.log(line)
            except Exception as e:
                self.log(f"Error: {str(e)}")

    def count_remote_files(self):
        """
        Use rsync dry-run to count how many files will actually be transferred.
        Returns 0 on failure (progress will still work, just less accurate).
        """
        cmd = (f"rsync -a --dry-run --stats "
               f"{JETSON_USER}@{JETSON_IP}:{JETSON_DIR} {LOCAL_DIR}")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            # rsync --stats prints "Number of files transferred: N"
            match = re.search(r'Number of files transferred:\s+(\d+)', result.stdout)
            if match:
                return int(match.group(1))
        except Exception:
            pass
        return 0

    def manage_download(self):
        if not self.check_connection(silent=True):
            self.log("Transfer aborted: No connection.")
            return

        # Reset state
        self.files_done = 0
        self.total_files = 0
        self.update_overall_progress(0)
        self.update_file_progress(0, "—")

        # --- Step 1: count files so we can show real overall progress ---
        self.log("Calculating transfer size (dry-run)...")
        self.total_files = self.count_remote_files()
        if self.total_files > 0:
            self.log(f"Files to transfer: {self.total_files}")
        else:
            self.log("Could not determine file count — progress bar will track per-file only.")

        # --- Step 2: real transfer ---
        self.log("Starting Rsync transfer...")

        # --info=progress2  → single-line overall progress (rsync ≥ 3.1.0)
        # -a                → archive (preserves metadata)
        # -z                → compress
        # --no-inc-recursive → count all files up front for accurate stats
        cmd = (f"rsync -az --no-inc-recursive --info=progress2,name "
               f"{JETSON_USER}@{JETSON_IP}:{JETSON_DIR} {LOCAL_DIR}")

        try:
            process = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1          # line-buffered
            )

            current_file = "—"

            for line in process.stdout:
                line = line.rstrip()
                if not line:
                    continue

                # --info=progress2 line looks like:
                #   "    123,456,789  45%   10.25MB/s    0:00:12 (xfr#3, to-chk=97/100)"
                progress2 = re.search(
                    r'(\d+)%.*xfr#(\d+).*to-chk=(\d+)/(\d+)', line
                )
                if progress2:
                    file_pct   = int(progress2.group(1))   # current file %
                    xfr_done   = int(progress2.group(2))   # files transferred so far
                    to_check   = int(progress2.group(3))   # files remaining to check
                    total_seen = int(progress2.group(4))   # total files rsync knows about

                    # Update per-file bar
                    speed_match = re.search(r'[\d.]+\s*[KMG]B/s', line)
                    speed = speed_match.group(0) if speed_match else ""
                    self.update_file_progress(file_pct, f"{current_file}  {speed}")

                    # Update overall bar using rsync's own file counter
                    if total_seen > 0:
                        overall = (xfr_done / total_seen) * 100
                        self.update_overall_progress(overall)

                    continue  # don't log raw progress lines

                # --info=name prints the filename on its own line
                # Filenames don't start with spaces and aren't pure numbers
                if not line.startswith(' ') and not re.match(r'^[\d,]+$', line):
                    current_file = line
                    self.log(f"↓ {line}")

            process.wait()

            if process.returncode == 0:
                self.log("SUCCESS: All files downloaded.")
                self.update_overall_progress(100)
                self.update_file_progress(100, "Done")
            else:
                self.log(f"Transfer failed (exit code {process.returncode}). "
                         "Check SSH keys / rsync version.")

        except Exception as e:
            self.log(f"Process Error: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DroneApp(root)
    root.mainloop()