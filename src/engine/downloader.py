import subprocess
import os
from src.utils.binary_helper import get_binary_path

class Downloader:
    def __init__(self):
        self.ytdlp_path = get_binary_path("yt-dlp")
        
    def download(self, url, output_dir, retries=3):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        cmd = [
            self.ytdlp_path,
            "--no-playlist",
            "--retries", str(retries),
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_template,
            url
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        filename = None
        try:
            for line in process.stdout:
                line_str = line.strip()
                if "[download] Destination:" in line_str:
                    filename = line_str.split("Destination:")[1].strip()
                elif "has already been downloaded" in line_str:
                    filename = line_str.split("[download]")[1].split("has already been downloaded")[0].strip()
            
            process.wait(timeout=1800)
            if process.returncode == 0 and filename:
                return filename
        except Exception as e:
            print(f"Downloader error: {e}")
            if process.poll() is None:
                process.kill()
        return None
