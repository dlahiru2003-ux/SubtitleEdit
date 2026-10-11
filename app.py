import os
import re
import sys
import time
import shutil
import tempfile
import subprocess
import threading
import imageio_ffmpeg
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class SafeSubtitleMuxer(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Safe Window Icon Loader (Prevents PyInstaller Recursion Crashes)
        self.set_window_icon("icon.ico")

        self.title("SubtitleEdit - Video Subtitle Encoder v1.0.0")
        self.geometry("640x480")
        self.resizable(False, False)
        self.configure(bg="#181818")

        self.video_path = ""
        self.sub_path = ""
        self.output_dir = ""
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        self.setup_ui()

    def set_window_icon(self, icon_name):
        try:
            if getattr(sys, 'frozen', False):
                base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            
            icon_full_path = os.path.join(base_dir, icon_name)
            if os.path.exists(icon_full_path):
                self.iconbitmap(default=icon_full_path)
        except Exception:
            pass

    def setup_ui(self):
        # Header
        lbl_title = tk.Label(self, text="SubtitleEdit v1.0.0", font=("Segoe UI", 18, "bold"), fg="#ffffff", bg="#181818")

        lbl_subtitle = tk.Label(self, text="VIDEO SUBTITLE ENCODER", font=("Segoe UI", 9, "bold"), fg="#00a8ff", bg="#181818")
        lbl_subtitle.pack(pady=(0, 6))

        lbl_desc = tk.Label(self, text="CPU Usage: ~0% | Hardware Safe | Direct Stream Mux", font=("Segoe UI", 10), fg="#00cec9", bg="#181818")
        lbl_desc.pack(pady=2)

        # 1. Video Select
        self.btn_video = tk.Button(self, text="1. Select Video File", font=("Segoe UI", 10, "bold"), bg="#0984e3", fg="white", activebackground="#74b9ff", relief="flat", width=34, height=1, command=self.select_video)
        self.btn_video.pack(pady=6)
        self.lbl_video = tk.Label(self, text="No video selected", font=("Segoe UI", 9), fg="#b2bec3", bg="#181818")
        self.lbl_video.pack()

        # 2. Subtitle Select
        self.btn_sub = tk.Button(self, text="2. Select Subtitle File (.srt)", font=("Segoe UI", 10, "bold"), bg="#0984e3", fg="white", activebackground="#74b9ff", relief="flat", width=34, height=1, command=self.select_sub)
        self.btn_sub.pack(pady=6)
        self.lbl_sub = tk.Label(self, text="No subtitle selected", font=("Segoe UI", 9), fg="#b2bec3", bg="#181818")
        self.lbl_sub.pack()

        # 3. Save Location
        self.btn_out = tk.Button(self, text="3. Select Save Location (Optional)", font=("Segoe UI", 10), bg="#2d3436", fg="white", activebackground="#636e72", relief="flat", width=34, height=1, command=self.select_output_dir)
        self.btn_out.pack(pady=6)
        self.lbl_out = tk.Label(self, text="Default: Same folder as source video", font=("Segoe UI", 9), fg="#b2bec3", bg="#181818")
        self.lbl_out.pack()

        # Status Label
        self.lbl_status = tk.Label(self, text="Ready", font=("Segoe UI", 11, "bold"), fg="#74b9ff", bg="#181818")
        self.lbl_status.pack(pady=14)

        # Action Button
        self.btn_start = tk.Button(self, text="Start Fast Safe Mux", font=("Segoe UI", 12, "bold"), bg="#00b894", fg="white", activebackground="#55efc4", relief="flat", width=22, height=1, command=self.start_process)
        self.btn_start.pack(pady=8)

    def select_video(self):
        file = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov *.webm")])
        if file:
            self.video_path = os.path.normpath(file)
            self.lbl_video.config(text=os.path.basename(file), fg="#74b9ff")

    def select_sub(self):
        file = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.srt")])
        if file:
            self.sub_path = os.path.normpath(file)
            self.lbl_sub.config(text=os.path.basename(file), fg="#74b9ff")

    def select_output_dir(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_dir = os.path.normpath(folder)
            self.lbl_out.config(text=self.output_dir, fg="#74b9ff")

    def check_disk_space(self, target_folder, required_gb=1.5):
        try:
            free_bytes = shutil.disk_usage(target_folder).free
            free_gb = free_bytes / (1024 ** 3)
            return free_gb >= required_gb, free_gb
        except Exception:
            return True, 999.0

    def start_process(self):
        if not self.video_path or not self.sub_path:
            messagebox.showerror("Missing Files", "Please select both a video file and an SRT subtitle file.")
            return

        raw_name = os.path.splitext(os.path.basename(self.video_path))[0]
        clean_name = re.sub(r'[\\/*?:"<>|]', "", raw_name)
        base_name = f"{clean_name}_tv_ready.mkv"

        if self.output_dir:
            save_folder = os.path.normpath(self.output_dir)
        else:
            save_folder = os.path.dirname(os.path.abspath(self.video_path))

        output_file = os.path.normpath(os.path.join(save_folder, base_name))

        has_space, free_gb = self.check_disk_space(save_folder, required_gb=1.5)
        if not has_space:
            messagebox.showerror(
                "Disk Space Error",
                f"Insufficient disk space!\n\nAvailable space: {free_gb:.2f} GB.\nPlease select another drive with at least 1.5 GB free space."
            )
            return

        threading.Thread(target=self.run_muxing, args=(output_file,), daemon=True).start()

    def run_muxing(self, output_file):
        self.btn_start.config(state="disabled")
        self.btn_video.config(state="disabled")
        self.btn_sub.config(state="disabled")
        self.btn_out.config(state="disabled")
        self.lbl_status.config(text="Processing subtitles...", fg="#fdcb6e")

        start_time = time.time()

        try:
            with open(self.sub_path, 'rb') as f:
                raw = f.read()

            text = None
            for enc in ['utf-8-sig', 'utf-8', 'cp1252', 'latin-1']:
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                text = raw.decode('utf-8', errors='ignore')

            temp_dir = tempfile.gettempdir()
            safe_srt = os.path.normpath(os.path.join(temp_dir, "clean_sub.srt"))
            with open(safe_srt, "w", encoding="utf-8") as f:
                f.write(text)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read subtitle file: {e}")
            self.reset_ui()
            return

        self.lbl_status.config(text="Muxing streams (Direct Copy)...", fg="#00cec9")

        creationflags = 0x08000000 if os.name == 'nt' else 0

        cmd = [
            self.ffmpeg_exe, "-y",
            "-i", self.video_path,
            "-sub_charenc", "UTF-8",
            "-i", safe_srt,
            "-map", "0:v",
            "-map", "0:a?",
            "-map", "1:0",
            "-c:v", "copy",       # Direct video stream copy (0% CPU load)
            "-c:a", "copy",       # Direct audio stream copy
            "-c:s", "srt",        # Native subtitle stream for MKV
            "-metadata:s:s:0", "language=sin",
            "-metadata:s:s:0", "title=Sinhala",
            "-disposition:s:0", "default",
            output_file
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)

        if os.path.exists(safe_srt):
            try:
                os.remove(safe_srt)
            except Exception:
                pass

        elapsed = round(time.time() - start_time, 1)

        if p.returncode == 0:
            self.lbl_status.config(text=f"Completed in {elapsed}s!", fg="#00b894")
            messagebox.showinfo(
                "Success",
                f"Process completed successfully in {elapsed} seconds!\n\nCPU Load: ~0% (Hardware Safe)\nSaved to:\n{output_file}"
            )
        else:
            self.lbl_status.config(text="Muxing Failed!", fg="#d63031")
            err_msg = p.stderr.decode("utf-8", errors="ignore")[-350:]
            messagebox.showerror("Error", f"An error occurred during muxing:\n\n{err_msg}")

        self.reset_ui()

    def reset_ui(self):
        self.btn_start.config(state="normal")
        self.btn_video.config(state="normal")
        self.btn_sub.config(state="normal")
        self.btn_out.config(state="normal")

if __name__ == "__main__":
    app = SafeSubtitleMuxer()
    app.mainloop()