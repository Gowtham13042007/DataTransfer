# 🚁 Drone Data Commander

A desktop GUI application for managing and downloading files from a **NVIDIA Jetson** device over SSH/rsync — built with Python and Tkinter.

---

## 📸 Features

- **Connection Check** — Ping the Jetson device to verify network reachability
- **Remote File Listing** — Browse files on the Jetson over SSH
- **Smart File Download** — Transfer files via `rsync` with real-time dual progress bars
- **Per-file Progress** — See the current file name, transfer percentage, and speed
- **Overall Progress** — Track how many files have been transferred out of the total
- **Thread-safe UI** — All SSH/rsync operations run in background threads — the UI never freezes

---

## 🖥️ Requirements

### System
- Python 3.7+
- Linux / macOS (Windows untested)
- `rsync` ≥ 3.1.0 (required for `--info=progress2`)
- `ssh` with key-based authentication configured to the Jetson

### Python (stdlib only — no pip installs needed)
| Module | Use |
|--------|-----|
| `tkinter` | GUI framework |
| `subprocess` | Run SSH / rsync / ping |
| `threading` | Background workers |
| `re` | Parse rsync progress output |

---

## ⚙️ Configuration

Edit the constants at the top of `drone_app.py`:

```python
JETSON_USER = "your_username"          # SSH username on the Jetson
JETSON_IP   = "172.28.59.187"          # IP address of the Jetson device
JETSON_DIR  = "/home/your_username"    # Remote directory to download from
LOCAL_DIR   = "/home/you/ascend_data/" # Local destination directory
```

---

## 🔐 SSH Key Setup

The app uses passwordless SSH. Set it up once:

```bash
# Generate a key pair (skip if you already have one)
ssh-keygen -t ed25519 -C "drone-app"

# Copy your public key to the Jetson
ssh-copy-id your_username@172.28.59.187

# Verify it works without a password prompt
ssh your_username@172.28.59.187 "echo OK"
```

---

## 🚀 Usage

```bash
python drone_app.py
```

### Button Reference

| Button | Action |
|--------|--------|
| **Check Connection** | Pings the Jetson and reports online/offline |
| **List Files** | SSH into Jetson and lists files in `JETSON_DIR` |
| **Download All** | Dry-runs rsync to count files, then transfers all |

---

## 📊 Progress Bars Explained

```
Overall Progress  ████████████░░░░  45.0%    ← files transferred / total files
Current File      ██████████████░░  87%  10.25MB/s  ← active file transfer
```

- **Overall** is driven by rsync's `xfr#N / total` counters
- **Per-file** is driven by rsync's `--info=progress2` percentage
- A dry-run (`--dry-run --stats`) first counts exactly how many files will transfer

---

## 🗂️ Project Structure

```
drone_app.py   # Single-file application — all logic and UI in one place
README.md
```

---

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| `CRITICAL: Jetson is offline` | Check IP, cable, or Wi-Fi. Verify with `ping 172.28.59.187` |
| SSH password prompt appears | SSH key not installed — see SSH Key Setup above |
| Progress bar stuck at 0% | Ensure rsync ≥ 3.1.0: `rsync --version` |
| `Transfer failed (exit code 255)` | SSH connection dropped mid-transfer — retry |
| Empty file list | Check `JETSON_DIR` path is correct and accessible |
| Tkinter not found | Install with `sudo apt install python3-tk` |

---

## 📝 Notes

- The app uses `rsync -az --no-inc-recursive --info=progress2,name` for accurate progress tracking
- Transfers are **incremental** — re-running Download All only copies new or changed files
- The status log auto-scrolls and shows all activity including filenames and errors

---


