import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QFileDialog, QProgressBar, QListWidget, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal

from engine.downloader import Downloader
from engine.signal_analyzer import SignalAnalyzer
from engine.renderer import Renderer

class WorkerThread(QThread):
    progress = Signal(str, int)
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, url=None, file_path=None):
        super().__init__()
        self.url = url
        self.file_path = file_path
        self.output_dir = os.path.join(os.getcwd(), "output")

    def run(self):
        try:
            target_file = self.file_path
            
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            if self.url:
                self.progress.emit("Downloading podcast video...", 10)
                downloader = Downloader()
                target_file = downloader.download(self.url, self.output_dir)
                if not target_file:
                    self.error.emit("Download failed.")
                    return
                    
            if not target_file or not os.path.exists(target_file):
                self.error.emit("Invalid file path.")
                return

            self.progress.emit("Analyzing audio signal & pitch variance...", 40)
            analyzer = SignalAnalyzer()
            clips = analyzer.analyze_audio(target_file)
            
            if not clips:
                self.error.emit("No candidate segments found.")
                return

            self.progress.emit("Rendering candidate shorts...", 70)
            renderer = Renderer()
            results = []
            
            for i, clip in enumerate(clips):
                out_path = os.path.join(self.output_dir, f"clipper_john_clip_{i+1}_score_{clip['score']}.mp4")
                self.progress.emit(f"Rendering segment {i+1}/{len(clips)} (Score: {clip['score']})...", 70 + (i * 20 // len(clips)))
                success = renderer.render_clip(target_file, clip['start'], clip['end'], out_path, "9:16")
                if success:
                    results.append(out_path)

            self.progress.emit("Done!", 100)
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))

class TheClipperJohnApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("The Clipper John - Beta 0.1")
        self.setMinimumSize(850, 620)
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; color: #f8fafc; }
            QLabel { color: #f8fafc; font-size: 14px; }
            QLineEdit { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 10px; border-radius: 6px; }
            QPushButton { background-color: #38bdf8; color: #0f172a; font-weight: bold; padding: 10px 16px; border-radius: 6px; }
            QPushButton:hover { background-color: #7dd3fc; }
            QProgressBar { border: 1px solid #334155; border-radius: 6px; text-align: center; color: #f8fafc; font-weight: bold; }
            QProgressBar::chunk { background-color: #4ade80; }
            QListWidget { background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 4px; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("The Clipper John - Beta 0.1")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #38bdf8;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Local Podcast Video Clipper & Audio Signal Analyzer")
        subtitle.setStyleSheet("font-size: 13px; color: #94a3b8;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube Podcast URL...")
        url_btn = QPushButton("Download & Clip URL")
        url_btn.clicked.connect(self.process_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(url_btn)
        layout.addLayout(url_layout)

        layout.addWidget(QLabel("OR"))

        # Local File Input
        file_layout = QHBoxLayout()
        self.file_label = QLabel("Drag & Drop Local Podcast File Here")
        file_label_box = QWidget()
        file_label_box.setStyleSheet("border: 2px dashed #334155; border-radius: 6px; padding: 10px;")
        box_layout = QHBoxLayout(file_label_box)
        box_layout.addWidget(self.file_label)
        
        file_btn = QPushButton("Browse File")
        file_btn.clicked.connect(self.select_file)
        process_file_btn = QPushButton("Process Local File")
        process_file_btn.clicked.connect(self.process_file)
        
        file_layout.addWidget(file_label_box)
        file_layout.addWidget(file_btn)
        file_layout.addWidget(process_file_btn)
        layout.addLayout(file_layout)

        # Progress
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Results
        layout.addWidget(QLabel("Generated Short Clips:"))
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.selected_file = None
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                self.selected_file = file_path
                self.file_label.setText(os.path.basename(file_path))
                break

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video/Audio", "", "Media Files (*.mp4 *.mkv *.avi *.mp3 *.wav)")
        if file_path:
            self.selected_file = file_path
            self.file_label.setText(os.path.basename(file_path))

    def process_url(self):
        url = self.url_input.text().strip()
        if url:
            self.start_worker(url=url)

    def process_file(self):
        if self.selected_file:
            self.start_worker(file_path=self.selected_file)

    def start_worker(self, url=None, file_path=None):
        self.results_list.clear()
        self.worker = WorkerThread(url, file_path)
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
        QMessageBox.information(self, "Success", f"The Clipper John generated {len(results)} short clips successfully!")

    def on_error(self, err):
        self.status_label.setText("Status: Error occurred")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", err)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TheClipperJohnApp()
    window.show()
    sys.exit(app.exec())
