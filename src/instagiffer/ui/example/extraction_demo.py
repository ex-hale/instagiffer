"""Extraction Demo - hands-on test harness for FFmwrapp.extract_frames."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from PySide6 import QtCore, QtWidgets

import instagiffer.ffmpeg
from instagiffer.ffmpeg import FFmpegError, FFmpegNotFoundError, FFmwrapp
from instagiffer.ui.widget import a2slider
from instagiffer.ui.widget.path import DirRow, FileRow

logging.basicConfig()
log = logging.getLogger('ExtractionDemo')
log.setLevel(logging.DEBUG)
instagiffer.ffmpeg.log.setLevel(logging.DEBUG)


class ExtractionWorker(QtCore.QThread):
    """Runs frame extraction off the main thread."""

    progress = QtCore.Signal(int)  # 0-100
    finished = QtCore.Signal(int)  # frame count on success
    error = QtCore.Signal(str)  # error message on failure

    def __init__(self, ffmpeg_path: Path, video_path: Path, output_dir: Path, start: float, duration: float) -> None:
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.video_path = video_path
        self.output_dir = output_dir
        self._start_time = start
        self._duration = duration

    def run(self) -> None:
        try:
            wrapper = FFmwrapp(self.ffmpeg_path)
            info = wrapper.get_video_info(self.video_path)

            def on_progress(fraction: float) -> None:
                self.progress.emit(int(fraction * 100))

            frames = wrapper.extract_frames(
                self.video_path,
                output_dir=self.output_dir,
                fps=info.fps,
                start_time=self._start_time,
                duration=self._duration,
                progress_callback=on_progress,
            )
            self.finished.emit(len(frames))
        except Exception as exc:
            self.error.emit(str(exc))


class ExtractionDemo(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Instagiffer - Extraction Demo')
        self.setMinimumWidth(640)
        self._worker: ExtractionWorker | None = None

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # path rows
        self.ffmpeg_row = FileRow('FFmpeg path', parent=self)
        layout.addWidget(self.ffmpeg_row)
        self.temp_row = DirRow('Temp / output dir', parent=self)
        layout.addWidget(self.temp_row)
        self.video_row = FileRow(
            'Video file',
            placeholder='Drop or browse a video...',
            file_filter='Videos (*.mp4 *.mkv *.avi *.mov *.webm);;All files (*)',
            parent=self,
        )
        layout.addWidget(self.video_row)
        self.video_row.path_changed.connect(self._get_video_info)

        controls_form = QtWidgets.QFormLayout()
        controls_layout = QtWidgets.QHBoxLayout()
        controls_form.addRow('Resolution:', controls_layout)
        self.controls = {}
        for label, attr, decimals in (
            ('', 'width', 0),
            ('x', 'height', 0),
            ('Duration', 'duration', 3),
            ('FPS', 'fps', 3),
        ):
            if label:
                controls_layout.addWidget(QtWidgets.QLabel(label))
            field = QtWidgets.QDoubleSpinBox(self)
            field.setMinimum(1)
            field.setDecimals(decimals)
            field.setMaximum(65536)
            field.setReadOnly(True)
            field.setEnabled(False)
            field.setButtonSymbols(field.ButtonSymbols.NoButtons)
            controls_layout.addWidget(field)
            self.controls[attr] = field

        self.extract_btn = QtWidgets.QPushButton('Extract Frames')
        self.extract_btn.setFixedHeight(36)
        self.extract_btn.clicked.connect(self._start_extraction)
        self.extract_btn.setEnabled(False)
        controls_layout.addStretch()
        controls_layout.addWidget(self.extract_btn)

        layout.addLayout(controls_form)

        self.start_slider = a2slider.A2Slider(self)
        self.start_slider.setEnabled(False)
        controls_form.addRow('Start:', self.start_slider)
        self.dur_slider = a2slider.A2Slider(self)
        self.dur_slider.setEnabled(False)
        controls_form.addRow('Duration:', self.dur_slider)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.status_log = QtWidgets.QPlainTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setFixedHeight(120)
        layout.addWidget(self.status_log)
        layout.addStretch()

        # auto-detect defaults
        self._detect_defaults()

    def _detect_defaults(self) -> None:
        ffmpeg_bin = shutil.which('ffmpeg')
        if ffmpeg_bin:
            self.ffmpeg_row.set_path(Path(ffmpeg_bin))
            self._log(f'Found ffmpeg: {ffmpeg_bin}')
        else:
            self._log('ffmpeg not found in PATH - please set path manually.')

        temp_dir = Path(tempfile.gettempdir()) / 'instagiffer'
        self.temp_row.set_path(temp_dir)

    def _log(self, message: str) -> None:
        self.status_log.appendPlainText(message)

    def _set_busy(self, busy: bool) -> None:
        self.extract_btn.setEnabled(not busy)
        self.ffmpeg_row.setEnabled(not busy)
        self.temp_row.setEnabled(not busy)
        self.video_row.setEnabled(not busy)
        if busy:
            self.progress_bar.setValue(0)

    def _start_extraction(self) -> None:
        ffmpeg_path = self.ffmpeg_row.path
        video_path = self.video_row.path
        output_dir = self.temp_row.path

        if not ffmpeg_path.is_file():
            QtWidgets.QMessageBox.warning(self, 'Missing', f'FFmpeg not found:\n{ffmpeg_path}')
            return
        if not video_path.is_file():
            QtWidgets.QMessageBox.warning(self, 'Missing', f'Video file not found:\n{video_path}')
            return
        if not str(output_dir).strip():
            QtWidgets.QMessageBox.warning(self, 'Missing', 'Please set an output directory.')
            return

        try:
            FFmwrapp(ffmpeg_path)
        except FFmpegNotFoundError as exc:
            QtWidgets.QMessageBox.critical(self, 'FFmpeg error', str(exc))
            return

        self._log(f'Starting extraction of: {video_path.name}')
        self._log(f'Output directory: {output_dir}')
        self._set_busy(True)

        self._worker = ExtractionWorker(
            ffmpeg_path, video_path, output_dir, self.start_slider.value, self.dur_slider.value
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, value: int) -> None:
        print(f'PROGRESS_BAR VALUE: >{value}<')
        self.progress_bar.setValue(value)

    def _on_finished(self, frame_count: int) -> None:
        self.progress_bar.setValue(100)
        self._log(f'Done! Extracted {frame_count} frames -> {self.temp_row.path}')
        self._set_busy(False)

    def _on_error(self, message: str) -> None:
        self._log(f'ERROR: {message}')
        QtWidgets.QMessageBox.critical(self, 'Extraction failed', message)
        self._set_busy(False)

    def _get_video_info(self, path):
        video_path = self.video_row.path
        if not video_path.is_file():
            self.extract_btn.setEnabled(False)
            return

        try:
            ffmpg = FFmwrapp(self.ffmpeg_row.path)
        except FFmpegNotFoundError as error:
            self._log(f'ERROR: {error}')
            self.extract_btn.setEnabled(False)
            return

        try:
            nfo = ffmpg.get_video_info(video_path)
        except FFmpegError as error:
            self._log(f'ERROR: {error}')
            self.extract_btn.setEnabled(False)
            return

        self.controls['width'].setValue(nfo.width)
        self.controls['height'].setValue(nfo.height)
        self.controls['duration'].setValue(nfo.duration_sec)
        self.controls['fps'].setValue(nfo.fps)

        self.extract_btn.setEnabled(True)
        self.start_slider.setEnabled(True)
        self.start_slider.value = 0
        self.start_slider.minmax = (0, nfo.duration_sec)
        self.dur_slider.setEnabled(True)
        self.dur_slider.minmax = (0.1, nfo.duration_sec)
        self.dur_slider.value = 5
        self._log(str(nfo))


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    win = ExtractionDemo()
    win.show()
    app.exec()
