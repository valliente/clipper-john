import subprocess
import numpy as np
from scipy.signal import find_peaks
from src.utils.binary_helper import get_binary_path

class SignalAnalyzer:
    def __init__(self, target_duration=60, sample_rate=16000):
        self.target_duration = target_duration
        self.sample_rate = sample_rate
        self.ffmpeg_path = get_binary_path("ffmpeg")

    def stream_audio_rms_chunks(self, file_path, chunk_duration=30):
        """
        Streams audio via FFmpeg pipe in PCM s16le format and computes RMS energy 
        vectorized per chunk. Memory usage stays under 200MB even for 5-hour files.
        """
        cmd = [
            self.ffmpeg_path,
            "-v", "error",
            "-i", file_path,
            "-vn",
            "-ac", "1",
            "-ar", str(self.sample_rate),
            "-f", "s16le",
            "-"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        bytes_per_sample = 2
        chunk_size = self.sample_rate * bytes_per_sample * chunk_duration
        rms_values = []
        timestamps = []
        
        curr_sample = 0

        try:
            while True:
                raw_data = process.stdout.read(chunk_size)
                if not raw_data:
                    break
                
                audio_chunk = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
                if len(audio_chunk) == 0:
                    continue
                
                sub_window = self.sample_rate
                num_sub = max(1, len(audio_chunk) // sub_window)
                
                for s in range(num_sub):
                    sub = audio_chunk[s*sub_window : (s+1)*sub_window]
                    rms = np.sqrt(np.mean(sub**2))
                    rms_values.append(rms)
                    timestamps.append((curr_sample + s * sub_window) / float(self.sample_rate))
                
                curr_sample += len(audio_chunk)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()

        return np.array(rms_values, dtype=np.float32), np.array(timestamps, dtype=np.float32)

    def analyze_audio(self, file_path, sensitivity=1.0):
        """
        Scans long audio files in seconds with minimal RAM footprint.
        """
        try:
            rms_vals, timestamps = self.stream_audio_rms_chunks(file_path)
            if len(rms_vals) == 0:
                return []

            kernel_size = 3
            rms_smoothed = np.convolve(rms_vals, np.ones(kernel_size)/kernel_size, mode='same')

            prominence_thresh = np.mean(rms_smoothed) * (0.5 / max(0.1, sensitivity))
            peaks, properties = find_peaks(rms_smoothed, distance=10, prominence=prominence_thresh)

            clips = []
            max_duration = timestamps[-1] if len(timestamps) > 0 else 300.0

            for peak in peaks:
                time_center = timestamps[peak]
                start_time = max(0.0, time_center - (self.target_duration / 2.0))
                end_time = min(max_duration, time_center + (self.target_duration / 2.0))

                prominences = properties.get("prominences", [0])
                idx_arr = np.where(peaks == peak)[0]
                if len(idx_arr) > 0 and np.max(prominences) > 0:
                    score_val = (prominences[idx_arr[0]] / np.max(prominences)) * 100
                else:
                    score_val = 50.0

                clips.append({
                    'start': round(float(start_time), 2),
                    'end': round(float(end_time), 2),
                    'score': round(min(100.0, max(1.0, float(score_val))), 1)
                })

            clips.sort(key=lambda x: x['score'], reverse=True)
            return clips[:10]
        except Exception as e:
            print(f"Signal analyzer error: {e}")
            return []

    def generate_waveform_points(self, file_path, num_points=100):
        """
        Generates normalized waveform preview points.
        """
        try:
            rms_vals, _ = self.stream_audio_rms_chunks(file_path, chunk_duration=60)
            if len(rms_vals) == 0:
                return [0.5] * num_points

            step = max(1, len(rms_vals) // num_points)
            sampled = [float(rms_vals[i*step]) for i in range(num_points) if i*step < len(rms_vals)]
            max_val = max(sampled) if sampled and max(sampled) > 0 else 1.0
            return [s / max_val for s in sampled]
        except Exception:
            return [0.5] * num_points
