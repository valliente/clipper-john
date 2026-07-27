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
                self.progress.emit("Downloading video...", 10)
                downloader = Downloader()
                target_file = downloader.download(self.url, self.output_dir)
                if not target_file:
                    self.error.emit("Download failed.")
                    return
                    
            if not target_file or not os.path.exists(target_file):
                self.error.emit("Invalid file path.")
                return

            self.progress.emit("Analyzing audio for highlights...", 40)
            analyzer = SignalAnalyzer()
            clips = analyzer.analyze_audio(target_file)
            
            if not clips:
                self.error.emit("No highlights found.")
                return

            self.progress.emit("Rendering clips...", 70)
            renderer = Renderer()
            results = []
            
            for i, clip in enumerate(clips):
                out_path = os.path.join(self.output_dir, f"clip_{i+1}_score_{clip['score']}.mp4")
                self.progress.emit(f"Rendering clip {i+1}/{len(clips)}...", 70 + (i * 20 // len(clips)))
                success = renderer.render_clip(target_file, clip['start'], clip['end'], out_path, "9:16")
                if success:
                    results.append(out_path)

            self.progress.emit("Done!", 100)
            self.finished.emit(results)
            
        except Exception as e:
            self.error.emit(str(e))

class AutoClipperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoClipper - Podcast Shorts Generator")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; color: #cdd6f4; }
            QLabel { color: #cdd6f4; font-size: 14px; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 8px; border-radius: 4px; }
            QPushButton { background-color: #89b4fa; color: #11111b; font-weight: bold; padding: 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #b4befe; }
            QProgressBar { border: 1px solid #45475a; border-radius: 4px; text-align: center; }
            QProgressBar::chunk { background-color: #a6e3a1; }
            QListWidget { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("AutoClipper")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # URL Input
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube URL here...")
        url_btn = QPushButton("Process URL")
        url_btn.clicked.connect(self.process_url)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(url_btn)
        layout.addLayout(url_layout)

        layout.addWidget(QLabel("OR"))

        # Local File Input
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        file_btn = QPushButton("Select Local File")
        file_btn.clicked.connect(self.select_file)
        process_file_btn = QPushButton("Process File")
        process_file_btn.clicked.connect(self.process_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(file_btn)
        file_layout.addWidget(process_file_btn)
        layout.addLayout(file_layout)

        # Progress
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Results
        layout.addWidget(QLabel("Generated Clips:"))
        self.results_list = QListWidget()
        layout.addWidget(self.results_list)

        self.selected_file = None
        
        # Enable Drag and Drop
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
        self.status_label.setText(msg)
        self.progress_bar.setValue(val)

    def on_finished(self, results):
        for r in results:
            self.results_list.addItem(r)
        QMessageBox.information(self, "Success", f"Generated {len(results)} clips successfully!")

    def on_error(self, err):
        self.status_label.setText("Error occurred")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Error", err)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoClipperApp()
    window.show()
    sys.exit(app.exec())
