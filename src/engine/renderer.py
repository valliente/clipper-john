import subprocess
import os
import concurrent.futures
from src.utils.binary_helper import get_binary_path

class Renderer:
    def __init__(self):
        self.ffmpeg_path = get_binary_path("ffmpeg")

    def render_clip(self, input_file, start_time, end_time, output_file, aspect_ratio="9:16"):
        """
        Optimized FFmpeg rendering pipeline with fast decode presets and automatic process cleanup.
        """
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", input_file
        ]

        if aspect_ratio == "9:16":
            cmd.extend(["-vf", "crop=ih*(9/16):ih"])
        elif aspect_ratio == "1:1":
            cmd.extend(["-vf", "crop=ih:ih"])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "fastdecode",
            "-c:a", "aac",
            "-b:a", "128k",
            output_file
        ])

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            _, stderr = process.communicate(timeout=600)
            return process.returncode == 0
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return False

    def render_batch_parallel(self, clip_tasks, max_workers=2):
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.render_clip, task[0], task[1], task[2], task[3], task[4]): task 
                for task in clip_tasks
            }
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success = future.result()
                    results.append((task[3], success))
                except Exception:
                    results.append((task[3], False))
        return results

    def merge_clips(self, clip_files, output_file):
        try:
            list_path = output_file + ".txt"
            with open(list_path, "w", encoding="utf-8") as f:
                for file_path in clip_files:
                    f.write(f"file '{os.path.abspath(file_path)}'\n")

            cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c", "copy",
                output_file
            ]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.communicate(timeout=300)
            
            if os.path.exists(list_path):
                os.remove(list_path)
            return process.returncode == 0
        except Exception as e:
            print(f"Merge error: {e}")
            return False
