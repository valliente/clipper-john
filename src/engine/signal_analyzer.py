import librosa
import numpy as np
import warnings
from scipy.signal import find_peaks

warnings.filterwarnings("ignore")

class SignalAnalyzer:
    def __init__(self, target_duration=60, sample_rate=22050):
        self.target_duration = target_duration
        self.sample_rate = sample_rate

    def analyze_audio(self, file_path):
        """
        Analyzes the audio and returns a list of high-energy clips.
        Returns a list of dicts: [{'start': float, 'end': float, 'score': float}]
        """
        try:
            # Load audio
            y, sr = librosa.load(file_path, sr=self.sample_rate, mono=True)
            
            # Calculate RMS energy
            rms = librosa.feature.rms(y=y)[0]
            
            # Smooth RMS
            window_length = int(sr * 1.0 / 512) # 1 sec window
            if window_length == 0:
                window_length = 1
            kernel = np.ones(window_length) / window_length
            rms_smoothed = np.convolve(rms, kernel, mode='same')
            
            # Find peaks in energy
            peaks, properties = find_peaks(rms_smoothed, distance=sr * 10 / 512, prominence=np.mean(rms_smoothed)*0.5)
            
            clips = []
            for peak in peaks:
                time_center = librosa.frames_to_time(peak, sr=sr)
                start_time = max(0, time_center - (self.target_duration / 2))
                end_time = min(len(y)/sr, time_center + (self.target_duration / 2))
                
                # Approximate score based on prominence
                prominences = properties.get("prominences", [0])
                score_val = (prominences[np.where(peaks == peak)[0][0]] / np.max(prominences)) * 100 if np.max(prominences) > 0 else 50
                
                clips.append({
                    'start': round(start_time, 2),
                    'end': round(end_time, 2),
                    'score': round(min(100, score_val), 1)
                })
            
            # Sort by score descending
            clips.sort(key=lambda x: x['score'], reverse=True)
            return clips[:5] # Top 5 clips
        except Exception as e:
            print(f"Error analyzing audio: {e}")
            return []
