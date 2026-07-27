import subprocess
import os
from src.utils.binary_helper import get_binary_path

class Renderer:
    def __init__(self):
        self.ffmpeg_path = get_binary_path("ffmpeg")
        
    def render_clip(self, input_file, start_time, end_time, output_file, aspect_ratio="9:16"):
        """
        Trims and crops video using ffmpeg
        aspect_ratio: '9:16', '1:1', '16:9'
        """
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", input_file
        ]
        
        # Apply cropping filter based on aspect ratio
        if aspect_ratio == "9:16":
            # Crop to vertical 9:16 from center
            filter_str = "crop=ih*(9/16):ih"
            cmd.extend(["-vf", filter_str])
        elif aspect_ratio == "1:1":
            filter_str = "crop=ih:ih"
            cmd.extend(["-vf", filter_str])
            
        cmd.extend([
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            output_file
        ])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        return process.returncode == 0
