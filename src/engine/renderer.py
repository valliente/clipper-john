import subprocess
import os
import concurrent.futures
from src.utils.binary_helper import get_binary_path
from src.engine.cropper import FaceCropper

class Renderer:
    def __init__(self):
        self.ffmpeg_path = get_binary_path("ffmpeg")
        self.cropper = FaceCropper()
        self.encoder = self.detect_gpu_encoder()

    def detect_gpu_encoder(self):
        """
        Probes FFmpeg for hardware encoders: h264_nvenc (NVIDIA), h264_qsv (Intel), h264_amf (AMD).
        Returns the first supported GPU encoder or 'libx264' (CPU fallback).
        """
        try:
            cmd = [self.ffmpeg_path, "-encoders"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, _ = process.communicate()
            
            if "h264_nvenc" in stdout:
                return "h264_nvenc"
            elif "h264_qsv" in stdout:
                return "h264_qsv"
            elif "h264_amf" in stdout:
                return "h264_amf"
        except Exception as e:
            print(f"GPU encoder detection error: {e}")
        return "libx264"

    def render_clip(self, input_file, start_time, end_time, output_file, aspect_ratio="9:16", use_gpu=True):
        """
        Trims and crops video using face detection and detected encoder.
        """
        codec = self.encoder if use_gpu else "libx264"

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-i", input_file
        ]
        
        crop_filter = self.cropper.get_crop_filter(input_file, aspect_ratio)
        if crop_filter:
            cmd.extend(["-vf", crop_filter])

        cmd.extend([
            "-c:v", codec,
            "-c:a", "aac",
            "-b:a", "192k",
            output_file
        ])
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr = process.communicate()
        
        # Fallback to libx264 if GPU encoder fails
        if process.returncode != 0 and codec != "libx264":
            print(f"GPU render failed with {codec}, falling back to libx264...")
            return self.render_clip(input_file, start_time, end_time, output_file, aspect_ratio, use_gpu=False)

        return process.returncode == 0

    def render_batch_parallel(self, clip_tasks, max_workers=2):
        """
        Executes multi-threaded parallel rendering for multiple short clips.
        clip_tasks: list of tuples (input_file, start_time, end_time, output_file, aspect_ratio, use_gpu)
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.render_clip, task[0], task[1], task[2], task[3], task[4], task[5]): task 
                for task in clip_tasks
            }
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    success = future.result()
                    results.append((task[3], success))
                except Exception as e:
                    print(f"Batch render error for {task[3]}: {e}")
                    results.append((task[3], False))
        return results

    def merge_clips(self, clip_files, output_file):
        """
        Concatenates multiple clip files into a single merged video.
        """
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
            process.communicate()
            
            if os.path.exists(list_path):
                os.remove(list_path)
            return process.returncode == 0
        except Exception as e:
            print(f"Merge error: {e}")
            return False
