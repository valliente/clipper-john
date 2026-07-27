import cv2

class FaceCropper:
    def __init__(self):
        # Load OpenCV Haar cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

    def detect_speaker_x_center(self, video_path, sample_frames=10):
        """
        Samples frames from video file and detects average face x-center position.
        Returns normalized x ratio (0.0 to 1.0) or 0.5 as fallback.
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return 0.5
                
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            if total_frames <= 0 or width <= 0:
                return 0.5

            step = max(1, total_frames // sample_frames)
            x_centers = []

            for i in range(sample_frames):
                frame_idx = i * step
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                for (x, y, w, h) in faces:
                    x_center = x + (w / 2.0)
                    x_centers.append(x_center / width)

            cap.release()

            if x_centers:
                x_centers.sort()
                return x_centers[len(x_centers) // 2]
            return 0.5
        except Exception as e:
            print(f"FaceCropper error: {e}")
            return 0.5

    def get_crop_filter(self, video_path, aspect_ratio="9:16"):
        """
        Generates FFmpeg crop filter string centered around detected face position.
        """
        if aspect_ratio == "16:9":
            return None

        x_ratio = self.detect_speaker_x_center(video_path)

        if aspect_ratio == "9:16":
            filter_str = f"crop=ih*(9/16):ih:max(0\\,min(iw-ih*(9/16)\\,iw*{x_ratio:.2f}-ih*(9/16)/2)):0"
            return filter_str
        elif aspect_ratio == "1:1":
            filter_str = f"crop=ih:ih:max(0\\,min(iw-ih\\,iw*{x_ratio:.2f}-ih/2)):0"
            return filter_str
            
        return "crop=ih*(9/16):ih"
