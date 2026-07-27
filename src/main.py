import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QProgressBar, QListWidget, QListWidgetItem, 
                               QSlider, QComboBox, QDoubleSpinBox, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QThread, Signal

from engine.downloader import Downloader
from engine.signal_analyzer import SignalAnalyzer
from engine.renderer import Renderer

class WorkerThread(QThread):
    progress = Signal(str, int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, url=None, file_path=None, sensitivity=1.0, aspect_ratio="9:16"):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.sensitivity = sensitivity
        self.aspect_ratio = aspect_ratio
        self.output_dir = os.path.join(os.getcwd(), "output")

    def run(self):
        try:
            target_file = self.file_path
            
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            if self.url:
                self.progress.emit("Downloading podcast video via yt-dlp...", 10)
                downloader = Downloader()
                target_file = downloader.download(self.url, self.output_dir)
                if not target_file:
                    self.error.emit("Download failed.")
                    return
                    
            if not target_file or not os.path.exists(target_file):
                self.error.emit("Invalid file path.")
                return

            self.progress.emit("Analyzing waveform RMS volume spikes & pitch variance...", 40)
            analyzer = SignalAnalyzer()
            clips = analyzer.analyze_audio(target_file, sensitivity=self.sensitivity)
            
            if not clips:
                self.error.emit("No high-energy candidate segments detected.")
                return

            self.progress.emit("Rendering candidate shorts via FFmpeg...", 70)
            renderer = Renderer()
            results = []
            
            for i, clip in enumerate(clips):
                out_path = os.path.join(self.output_dir, f"clipper_john_clip_{i+1}_score_{int(clip['score'])}.mp4")
                self.progress.emit(f"Rendering candidate clip {i+1}/{len(clips)} (Score: {clip['score']})...", 70 + (i * 25 // len(clips)))
                success = renderer.render_clip(target_file, clip['start'], clip['end'], out_path, self.aspect_ratio)
                if success:
                    results.append(f"Clip #{i+1} | Score: {clip['score']} | {clip['start']}s - {clip['end']}s -> {os.path.basename(out_path)}")

            self.progress.emit("Batch Processing Complete!", 100)
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))

class TheClipperJohnApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Clipper John - Beta 0.1")
        self.setMinimumSize(900, 680)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QGroupBox { color: #38bdf8; font-weight: bold; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 10px; }
            QLineEdit { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 8px; border-radius: 6px; }
            QPushButton { background-color: #38bdf8; color: #0f172a; font-weight: bold; padding: 10px 16px; border-radius: 6px; }
            QPushButton:hover { background-color: #7dd3fc; }
            QComboBox { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 6px; border-radius: 6px; }
            QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #f8fafc; font-weight: bold; }
            QProgressBar::chunk { background-color: #4ade80; }
            QListWidget { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 4px; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        title = QLabel("The Clipper John - Beta 0.1")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #38bdf8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Input Group
        input_group = QGroupBox("Video Input Source")
        input_layout = QVBoxLayout(input_group)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube Podcast URL...")
        url_layout.addWidget(self.url_input)
        input_layout.addLayout(url_layout)

        file_layout = QHBoxLayout()
        self.file_label = QLabel("Drag & drop local podcast video file here")
        self.file_label.setStyleSheet("color: #94a3b8;")
        file_btn = QPushButton("Browse Local File")
        file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(file_btn)
        input_layout.addLayout(file_layout)

        layout.addWidget(input_group)

        # Controls Group
        controls_group = QGroupBox("Signal Analysis & Export Settings")
        controls_layout = QHBoxLayout(controls_group)

        # Sensitivity Slider
        sens_vbox = QVBoxLayout()
        self.sens_label = QLabel("Spike Sensitivity: 1.0x")
        self.sens_slider = QSlider(Qt.Horizontal)
        self.sens_slider.setMinimum(5)
        self.sens_slider.setMaximum(25)
        self.sens_slider.setValue(10)
        self.sens_slider.valueChanged.connect(self.update_sensitivity_label)
        sens_vbox.addWidget(self.sens_label)
        sens_vbox.addWidget(self.sens_slider)
        controls_layout.addLayout(sens_vbox)

        # Crop Aspect Ratio
        crop_vbox = QVBoxLayout()
        crop_vbox.addWidget(QLabel("Aspect Ratio:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["9:16 (Vertical Short)", "1:1 (Square)", "16:9 (Standard)"])
        crop_vbox.addWidget(self.aspect_combo)
        controls_layout.addLayout(crop_vbox)

        # Trim Handle Offset
        trim_vbox = QVBoxLayout()
        trim_vbox.addWidget(QLabel("Trim Start Offset (s):"))
        self.trim_offset_spin = QDoubleSpinBox()
        self.trim_offset_spin.setStyleSheet("background-color: #1e293b; color: #f8fafc;")
        self.trim_offset_spin.setRange(-10.0, 10.0)
        self.trim_offset_spin.setValue(0.0)
        trim_vbox.addWidget(self.trim_offset_spin)
        controls_layout.addLayout(trim_vbox)

        layout.addWidget(controls_group)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.process_btn = QPushButton("Run Signal Analysis & Batch Export Shorts")
        self.process_btn.setStyleSheet("background-color: #4ade80; color: #0f172a; font-size: 15px;")
        self.process_btn.clicked.connect(self.process_video)
        btn_layout.addWidget(self.process_btn)
        layout.addLayout(btn_layout)

        # Progress
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Candidate Clip Preview Cards List
        layout.addWidget(QLabel("Candidate Clips Preview & Export Log:"))
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.selected_file = None
        self.setAcceptDrops(True)

    def update_sensitivity_label(self, val):
        self.sens_label.setText(f"Spike Sensitivity: {val/10.0:.1f}x")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.selected_file = file_path
                self.file_label.setText(f"Selected: {os.path.basename(file_path)}")
                break

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video/Audio", "", "Media Files (*.mp4 *.mkv *.avi *.mp3 *.wav)")
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"Selected: {os.path.basename(file_path)}")

    def process_video(self):
        url = self.url_input.text().strip()
        if not url and not self.selected_file:
            QMessageBox.warning(self, "Input Required", "Please provide a YouTube URL or select a local video file.")
            return

        aspect_mapping = {
            0: "9:16",
            1: "1:1",
            2: "16:9"
        }
        aspect_ratio = aspect_mapping.get(self.aspect_combo.currentIndex(), "9:16")
        sensitivity = self.sens_slider.value() / 10.0

        self.results_list.clear()
        self.worker = WorkerThread(url=url if url else None, 
                                   file_path=self.selected_file if not url else None, 
                                   sensitivity=sensitivity, 
                                   aspect_ratio=aspect_ratio)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_progress(self, msg, val):
        self.status_label.setText(f"Status: {msg}")
        self.progress_bar.setValue(val)

    def on_finished(self, results):
        for r in results:
            self.results_list.addItem(r)
        QMessageBox.information(self, "Success", f"The Clipper John exported {len(results)} candidate short clips successfully!")

    def on_error(self, err):
        self.status_label.setText("Status: Error occurred")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", err)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TheClipperJohnApp()
    window.show()
    sys.exit(app.exec())
