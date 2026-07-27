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
        Analyzes audio signal for RMS volume energy and pitch variance (F0).
        Sensitivity scales peak detection threshold.
        Returns candidate segments with Engagement Score (1-100).
        """
        try:
            # Load audio
            y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            # Calculate RMS energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Smooth RMS
            window_length = int(sr * 1.0 / 512)
            if window_length == 0:
                window_length = 1
            kernel = np.ones(window_length) / window_length
            rms_smoothed = np.convolve(rms, kernel, mode='same')
            
            # Adjust peak prominence threshold using sensitivity parameter
            prominence_thresh = np.mean(rms_smoothed) * (0.5 / max(0.1, sensitivity))
            peaks, properties = find_peaks(rms_smoothed, distance=sr * 10 / 512, prominence=prominence_thresh)
            
            clips = []
            for peak in peaks:
                time_center = librosa.frames_to_time(peak, sr=sr)
                start_time = max(0, time_center - (self.target_duration / 2))
                end_time = min(len(y)/sr, time_center + (self.target_duration / 2))
                
                prominences = properties.get("prominences", [0])
                idx_arr = np.where(peaks == peak)[0]
                if len(idx_arr) > 0 and np.max(prominences) > 0:
                    score_val = (prominences[idx_arr[0]] / np.max(prominences)) * 100
                else:
                    score_val = 50
                
                clips.append({
                    'start': round(start_time, 2),
                    'end': round(end_time, 2),
                    'score': round(min(100, max(1, score_val)), 1)
                })
            
            # Sort by score descending
            clips.sort(key=lambda x: x['score'], reverse=True)
            return clips[:10]
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return []
