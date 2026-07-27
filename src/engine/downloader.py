import subprocess
import os
from src.utils.binary_helper import get_binary_path

class Downloader:
    def __init__(self):
        self.ytdlp_path = get_binary_path("yt-dlp")
        
    def download(self, url, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
        cmd = [
            self.ytdlp_path,
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_template,
            url
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        filename = None
        for line in process.stdout:
            print(line.strip())
            if "[download] Destination:" in line:
                filename = line.split("Destination:")[1].strip()
            elif "has already been downloaded" in line:
                filename = line.split("[download]")[1].split("has already been downloaded")[0].strip()
        
        process.wait()
        if process.returncode == 0 and filename:
            return filename
        return None
