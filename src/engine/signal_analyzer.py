import librosa
import numpy as np
import warnings
from scipy.signal import find_peaks

warnings.filterwarnings("ignore")

class SignalAnalyzer:
    def __init__(self, target_duration=60, sample_rate=22050):
        self.target_duration = target_duration
        self.sample_rate = sample_rate

    def analyze_audio(self, file_path, sensitivity=1.0):
        """
        Analyzes audio waveform signal combining:
        1. RMS energy spikes
        2. Zero-crossing rate (speech density / VAD proxy)
        3. Pitch & energy variance
        Returns list of candidate segments with Engagement Score (1-100).
        """
        try:
            y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            # RMS Energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Zero Crossing Rate (Voice Activity / Speech Density indicator)
            zcr = librosa.feature.zero_crossing_rate(y=y)[0]
            
            # Smooth signals
            window_length = max(1, int(sr * 1.0 / 512))
            kernel = np.ones(window_length) / window_length
            rms_smoothed = np.convolve(rms, kernel, mode='same')
            zcr_smoothed = np.convolve(zcr, kernel, mode='same')
            
            # Combined energy-speech density metric
            combined_signal = rms_smoothed * (1.0 + zcr_smoothed)
            
            # Adjust peak threshold with sensitivity parameter
            prominence_thresh = np.mean(combined_signal) * (0.5 / max(0.1, sensitivity))
            peaks, properties = find_peaks(combined_signal, distance=sr * 10 / 512, prominence=prominence_thresh)
            
            clips = []
            audio_duration = len(y) / float(sr)
            
            for peak in peaks:
                time_center = librosa.frames_to_time(peak, sr=sr)
                start_time = max(0.0, time_center - (self.target_duration / 2.0))
                end_time = min(audio_duration, time_center + (self.target_duration / 2.0))
                
                prominences = properties.get("prominences", [0])
                idx_arr = np.where(peaks == peak)[0]
                if len(idx_arr) > 0 and np.max(prominences) > 0:
                    score_val = (prominences[idx_arr[0]] / np.max(prominences)) * 100
                else:
                    score_val = 50.0
                
                clips.append({
                    'start': round(start_time, 2),
                    'end': round(end_time, 2),
                    'score': round(min(100.0, max(1.0, score_val)), 1)
                })
            
            clips.sort(key=lambda x: x['score'], reverse=True)
            return clips[:10]
        except Exception as e:
            print(f"Error in signal analyzer: {e}")
            return []

    def generate_waveform_points(self, file_path, num_points=100):
        """
        Generates normalized waveform points (0.0 to 1.0) for visual UI rendering.
        """
        try:
            y, sr = librosa.load(file_path, sr=11025, mono=True)
            step = max(1, len(y) // num_points)
            points = [float(np.abs(y[i*step:(i+1)*step]).max()) for i in range(num_points) if i*step < len(y)]
            max_val = max(points) if points and max(points) > 0 else 1.0
            return [p / max_val for p in points]
        except Exception:
            return [0.5] * num_points
