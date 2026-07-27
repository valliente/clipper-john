import sys
import os
import gc
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QProgressBar, QListWidget, QListWidgetItem, 
                               QSlider, QComboBox, QMessageBox, QGroupBox, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen

from engine.downloader import Downloader
from engine.signal_analyzer import SignalAnalyzer
from engine.renderer import Renderer

class WaveformWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = [0.2, 0.4, 0.7, 0.9, 0.5, 0.3, 0.8, 0.6, 0.4, 0.9]
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: #1e293b; border: 1px solid #334155; border-radius: 6px;")

    def set_waveform(self, points):
        if points:
            self.points = points
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.points:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#38bdf8"), 2)
        painter.setPen(pen)

        w = self.width()
        h = self.height()
        n = len(self.points)
        dx = w / float(max(1, n - 1))

        for i in range(n - 1):
            x1 = i * dx
            y1 = h / 2.0 - (self.points[i] * (h / 2.0 - 4))
            x2 = (i + 1) * dx
            y2 = h / 2.0 - (self.points[i + 1] * (h / 2.0 - 4))
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))
            y1_b = h / 2.0 + (self.points[i] * (h / 2.0 - 4))
            y2_b = h / 2.0 + (self.points[i + 1] * (h / 2.0 - 4))
            painter.drawLine(int(x1), int(y1_b), int(x2), int(y2_b))

class AnalysisWorker(QThread):
    progress = Signal(str, int)
    finished = Signal(list, list, str)
    error = Signal(str)

    def __init__(self, url=None, file_path=None, sensitivity=1.0):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.sensitivity = sensitivity
        self.output_dir = os.path.join(os.getcwd(), "output")

    def run(self):
        try:
            target_file = self.file_path
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            if self.url:
                self.progress.emit("Downloading stream via yt-dlp...", 15)
                downloader = Downloader()
                target_file = downloader.download(self.url, self.output_dir)
                if not target_file:
                    self.error.emit("Download failed.")
                    return

            if not target_file or not os.path.exists(target_file):
                self.error.emit("Invalid video file path.")
                return

            self.progress.emit("Scanning audio PCM stream via NumPy vectors...", 45)
            analyzer = SignalAnalyzer()
            clips = analyzer.analyze_audio(target_file, sensitivity=self.sensitivity)
            
            self.progress.emit("Generating visual waveform preview...", 85)
            wf_points = analyzer.generate_waveform_points(target_file, num_points=100)

            self.progress.emit("Analysis Complete!", 100)
            self.finished.emit(clips, wf_points, target_file)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            gc.collect()

class RenderWorker(QThread):
    progress = Signal(str, int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, target_file, selected_clips, aspect_ratio="9:16"):
        super().__init__()
        self.target_file = target_file
        self.selected_clips = selected_clips
        self.aspect_ratio = aspect_ratio
        self.output_dir = os.path.join(os.getcwd(), "output")

    def run(self):
        try:
            renderer = Renderer()
            results = []
            total = len(self.selected_clips)

            for i, clip in enumerate(self.selected_clips):
                out_path = os.path.join(self.output_dir, f"clipper_john_clip_{i+1}_score_{int(clip['score'])}.mp4")
                self.progress.emit(f"Rendering Short {i+1}/{total} (FFmpeg fastdecode)...", int(10 + (i * 85 / total)))
                
                success = renderer.render_clip(self.target_file, clip['start'], clip['end'], out_path, self.aspect_ratio)
                if success:
                    results.append(out_path)

            self.progress.emit("Export Complete!", 100)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            gc.collect()

class TheClipperJohnApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Clipper John - 0.1.201")
        self.setMinimumSize(900, 650)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #f8fafc; font-size: 13px; }
            QGroupBox { color: #38bdf8; font-weight: bold; border: 1px solid #334155; border-radius: 8px; margin-top: 8px; padding-top: 8px; }
            QLineEdit { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 8px; border-radius: 6px; }
            QPushButton { background-color: #38bdf8; color: #0f172a; font-weight: bold; padding: 8px 14px; border-radius: 6px; }
            QPushButton:hover { background-color: #7dd3fc; }
            QComboBox { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 6px; border-radius: 6px; }
            QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #f8fafc; font-weight: bold; }
            QProgressBar::chunk { background-color: #4ade80; }
            QListWidget { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 4px; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        # Header
        title = QLabel("The Clipper John - 0.1.201")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #38bdf8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("High-Performance Audio Signal Scanner & FFmpeg Video Clipper")
        subtitle.setStyleSheet("font-size: 12px; color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Input Group
        input_group = QGroupBox("1. Video Source")
        input_layout = QVBoxLayout(input_group)

        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube Podcast URL...")
        url_layout.addWidget(self.url_input)
        input_layout.addLayout(url_layout)

        file_layout = QHBoxLayout()
        self.file_label = QLabel("Drag & drop local podcast video file here")
        self.file_label.setStyleSheet("color: #94a3b8;")
        file_btn = QPushButton("Browse File")
        file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(file_btn)
        input_layout.addLayout(file_layout)

        layout.addWidget(input_group)

        # Controls Group
        controls_group = QGroupBox("2. Parameters")
        controls_layout = QHBoxLayout(controls_group)

        sens_vbox = QVBoxLayout()
        self.sens_label = QLabel("Spike Sensitivity: 1.0x")
        self.sens_slider = QSlider(Qt.Horizontal)
        self.sens_slider.setMinimum(5)
        self.sens_slider.setMaximum(25)
        self.sens_slider.setValue(10)
        self.sens_slider.valueChanged.connect(self.update_sens_label)
        sens_vbox.addWidget(self.sens_label)
        sens_vbox.addWidget(self.sens_slider)
        controls_layout.addLayout(sens_vbox)

        crop_vbox = QVBoxLayout()
        crop_vbox.addWidget(QLabel("Aspect Ratio:"))
        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems(["9:16 (Vertical Short)", "1:1 (Square)", "16:9 (Standard)"])
        crop_vbox.addWidget(self.aspect_combo)
        controls_layout.addLayout(crop_vbox)

        layout.addWidget(controls_group)

        # Analyze Action Button
        self.analyze_btn = QPushButton("Run Fast Audio Signal Scan")
        self.analyze_btn.setStyleSheet("background-color: #38bdf8; color: #0f172a; font-size: 14px; font-weight: bold;")
        self.analyze_btn.clicked.connect(self.run_analysis)
        layout.addWidget(self.analyze_btn)

        # Waveform Display
        layout.addWidget(QLabel("Waveform Energy Profile:"))
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)

        # Candidate Clips Editor
        editor_header = QHBoxLayout()
        editor_header.addWidget(QLabel("3. Candidate Clips Batch Editor:"))
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_clips)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_clips)
        
        editor_header.addWidget(select_all_btn)
        editor_header.addWidget(deselect_all_btn)
        layout.addLayout(editor_header)

        self.clips_list = QListWidget()
        layout.addWidget(self.clips_list)

        # Render & Merge Buttons
        render_layout = QHBoxLayout()
        self.render_btn = QPushButton("Export Selected Shorts")
        self.render_btn.setStyleSheet("background-color: #4ade80; color: #0f172a; font-size: 14px; font-weight: bold;")
        self.render_btn.clicked.connect(self.run_render)

        self.merge_btn = QPushButton("Merge Selected Clips")
        self.merge_btn.setStyleSheet("background-color: #f59e0b; color: #0f172a; font-size: 14px; font-weight: bold;")
        self.merge_btn.clicked.connect(self.merge_clips)

        render_layout.addWidget(self.render_btn)
        render_layout.addWidget(self.merge_btn)
        layout.addLayout(render_layout)

        # Status & Progress
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.selected_file = None
        self.detected_clips = []
        self.rendered_clip_paths = []
        self.target_file_path = None

        self.setAcceptDrops(True)

    def update_sens_label(self, val):
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
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Media File", "", "Media Files (*.mp4 *.mkv *.avi *.mp3 *.wav)")
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(f"Selected: {os.path.basename(file_path)}")

    def run_analysis(self):
        url = self.url_input.text().strip()
        if not url and not self.selected_file:
            QMessageBox.warning(self, "Input Required", "Please provide a YouTube URL or select a local video file.")
            return

        self.clips_list.clear()
        sensitivity = self.sens_slider.value() / 10.0

        self.worker = AnalysisWorker(url=url if url else None, 
                                     file_path=self.selected_file if not url else None, 
                                     sensitivity=sensitivity)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_progress(self, msg, val):
        self.status_label.setText(f"Status: {msg}")
        self.progress_bar.setValue(val)

    def on_analysis_finished(self, clips, wf_points, target_file):
        self.detected_clips = clips
        self.target_file_path = target_file
        self.waveform_widget.set_waveform(wf_points)

        for i, clip in enumerate(clips):
            item_text = f"Segment #{i+1} | Score: {clip['score']}/100 | Timestamps: {clip['start']}s - {clip['end']}s (Duration: {round(clip['end']-clip['start'], 1)}s)"
            item = QListWidgetItem(item_text)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.clips_list.addItem(item)

        QMessageBox.information(self, "Analysis Complete", f"Fast scan detected {len(clips)} candidate short segments!")

    def select_all_clips(self):
        for i in range(self.clips_list.count()):
            self.clips_list.item(i).setCheckState(Qt.Checked)

    def deselect_all_clips(self):
        for i in range(self.clips_list.count()):
            self.clips_list.item(i).setCheckState(Qt.Unchecked)

    def run_render(self):
        if not self.target_file_path or not self.detected_clips:
            QMessageBox.warning(self, "No Analysis Data", "Please run audio signal scan first.")
            return

        selected_clips = []
        for i in range(self.clips_list.count()):
            item = self.clips_list.item(i)
            if item.checkState() == Qt.Checked and i < len(self.detected_clips):
                selected_clips.append(self.detected_clips[i])

        if not selected_clips:
            QMessageBox.warning(self, "No Clips Selected", "Please select at least one clip segment to export.")
            return

        aspect_mapping = {0: "9:16", 1: "1:1", 2: "16:9"}
        aspect_ratio = aspect_mapping.get(self.aspect_combo.currentIndex(), "9:16")

        self.render_worker = RenderWorker(self.target_file_path, selected_clips, aspect_ratio)
        self.render_worker.progress.connect(self.update_progress)
        self.render_worker.finished.connect(self.on_render_finished)
        self.render_worker.error.connect(self.on_error)
        self.render_worker.start()

    def on_render_finished(self, results):
        self.rendered_clip_paths = results
        QMessageBox.information(self, "Export Complete", f"Exported {len(results)} short clips using high-speed FFmpeg pipeline!")

    def merge_clips(self):
        if not self.rendered_clip_paths:
            QMessageBox.warning(self, "No Rendered Clips", "Please export selected shorts first before merging.")
            return

        renderer = Renderer()
        out_merge = os.path.join(os.getcwd(), "output", "clipper_john_merged_highlights.mp4")
        success = renderer.merge_clips(self.rendered_clip_paths, out_merge)

        if success:
            QMessageBox.information(self, "Merge Successful", f"Merged clips saved to:\n{out_merge}")
        else:
            QMessageBox.critical(self, "Merge Failed", "Could not concatenate selected clips.")

    def on_error(self, err):
        self.status_label.setText("Status: Error occurred")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", err)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TheClipperJohnApp()
    window.show()
    sys.exit(app.exec())
