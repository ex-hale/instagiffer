"""Extraction Demo - hands-on test harness for FFmWrap.extract_frames."""

from __future__ import annotations
import time

import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6 import QtCore, QtWidgets

import instagiffer.ffmpeg
from instagiffer.ffmpeg import FFmpegError, FFmpegNotFoundError, FFmWrap
from instagiffer.ui.widget import a2slider, timeline
from instagiffer.ui.widget.path import DirRow, FileRow

logging.basicConfig()
log = logging.getLogger('ExtractionDemo')
log.setLevel(logging.DEBUG)
instagiffer.ffmpeg.log.setLevel(logging.DEBUG)

MAX_DURATION = 10


class ExtractionDemo(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._detect_defaults()

    def _setup_ui(self):
        self.setWindowTitle('Instagiffer - Extraction Demo')
        self.setMinimumWidth(640)

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
        self.scale_slider = a2slider.A2Slider(self, value=1.0, mini=0.1, maxi=1.0)
        self.scale_slider.setEnabled(False)
        controls_form.addRow('Scale:', self.scale_slider)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.timeline = timeline.TimeLine(self)
        layout.addWidget(self.timeline)

        self.status_log = QtWidgets.QPlainTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setFixedHeight(120)
        layout.addWidget(self.status_log)
        layout.addStretch()

    def _detect_defaults(self) -> None:
        wrapper = FFmWrap()
        if wrapper.ffmpeg.is_file():
            self._log(f'FFmWrap found executable: {wrapper.ffmpeg}')
            self.ffmpeg_row.set_path(wrapper.ffmpeg)
        else:
            self._log('ffmpeg not found! - Please set path manually.')

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
            FFmWrap(ffmpeg_path)
        except FFmpegNotFoundError as exc:
            QtWidgets.QMessageBox.critical(self, 'FFmpeg error', str(exc))
            return

        self._log(f'Starting extraction of: {video_path.name}')
        self._log(f'Output directory: {output_dir}')
        self._set_busy(True)

        worker = ExtractionWorker(
            self,
            ffmpeg_path,
            video_path,
            output_dir,
            self.controls['fps'].value(),
            self.start_slider.value,
            self.dur_slider.value,
            self.scale_slider.value,
        )
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(self._on_error)
        worker.start()

    def _on_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def _on_finished(self, frame_count: int) -> None:
        self.progress_bar.setValue(100)
        self._log(f'Done! Extracted {frame_count} frames -> {self.temp_row.path}')
        self._set_busy(False)

    def _on_error(self, message: str) -> None:
        if not message:
            return
        self._log(f'ERROR: {message}')
        QtWidgets.QMessageBox.critical(self, 'Extraction failed', message)
        self._set_busy(False)

    def _get_video_info(self, path):
        video_path = self.video_row.path
        enable = True
        if not video_path.is_file():
            enable = False

        if enable:
            try:
                ffm_wrap = FFmWrap(self.ffmpeg_row.path)
            except FFmpegNotFoundError as error:
                self._log(f'ERROR: {error}')
                enable = False

        if enable:
            try:
                nfo = ffm_wrap.get_video_info(video_path)
            except FFmpegError as error:
                self._log(f'ERROR: {error}')
                enable = False

        self.extract_btn.setEnabled(enable)
        self.start_slider.setEnabled(enable)
        self.dur_slider.setEnabled(enable)
        self.scale_slider.setEnabled(enable)

        if not enable:
            return

        thumb_width, thumb_height, num_thumbs = self.timeline.initial_frames(nfo.width, nfo.height)
        self.timeline.set_chunk_data(thumb_width, num_thumbs)
        timestamps = [nfo.duration_sec * i / num_thumbs for i in range(num_thumbs)]

        self._thumb_thread = QtCore.QThread(self)
        self._worker = ThumbnailWorker(self.ffmpeg_row.path, self.video_row.path, timestamps, thumb_width, thumb_height)
        self._worker.moveToThread(self._thumb_thread)
        self._thumb_thread.started.connect(self._worker.run)
        self._worker.frame_ready.connect(self._on_thumb_progress)
        self._worker.finished.connect(self._on_thumb_finished)
        self._worker.error.connect(self._on_error)
        self._thumb_thread.start()
        self._thumb_t0 = time.perf_counter()

        self.controls['width'].setValue(nfo.width)
        self.controls['height'].setValue(nfo.height)
        self.controls['duration'].setValue(nfo.duration_sec)
        self.controls['fps'].setValue(nfo.fps)
        self.start_slider.value = 0
        self.start_slider.minmax = (0, nfo.duration_sec)
        self.dur_slider.minmax = (0.1, min(nfo.duration_sec, MAX_DURATION))
        self.dur_slider.value = 5
        self._log(str(nfo))

    def _on_thumb_progress(self, index: int, chunk: bytes):
        print(f'push_chunk {index}')
        self.timeline.push_chunk(index, chunk)
        self.timeline.update()

    def _on_thumb_finished(self):
        self._thumb_thread.quit()
        self._thumb_thread.deleteLater()
        self._worker.deleteLater()
        print(f'thumbs took: {time.perf_counter() - self._thumb_t0:.2f}s')


class ExtractionWorker(QtCore.QThread):
    """Runs frame extraction off the main thread."""

    progress = QtCore.Signal(int)  # 0-100
    finished = QtCore.Signal(int)  # frame count on success
    error = QtCore.Signal(str)  # error message on failure

    def __init__(
        self,
        parent,
        ffmpeg_path: Path,
        video_path: Path,
        output_dir: Path,
        fps: int | float,
        start: float,
        duration: float,
        scale: float,
    ) -> None:
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.video_path = video_path
        self.output_dir = output_dir
        self._fps = fps
        self._start_time = start
        self._duration = duration
        self._scale = scale

    def _progress(self, fraction: float) -> None:
        self.progress.emit(int(fraction * 100))

    def run(self) -> None:
        try:
            wrapper = FFmWrap(self.ffmpeg_path)
            frames = wrapper.extract_frames(
                self.video_path,
                output_dir=self.output_dir,
                fps=self._fps,
                start_time=self._start_time,
                duration=self._duration,
                scale=self._scale,
                progress_callback=self._progress,
            )
            self.finished.emit(len(frames))
        except Exception as exc:
            self.error.emit(str(exc))


class ThumbnailWorker(QtCore.QObject):
    """Runs frame extraction off the main thread."""

    frame_ready = QtCore.Signal(int, bytes)
    finished = QtCore.Signal()
    error = QtCore.Signal(str)

    def __init__(self, ffmpeg_path: Path, video_path: Path, timestamps: list[int | float], width: int, height: int):
        super().__init__()
        self._video_path = video_path
        self._timestamps = timestamps
        self._width = width
        self._height = height
        self._wrapper = FFmWrap(ffmpeg_path)

    def run(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(self._extract, i, t): i for i, t in enumerate(self._timestamps)}
            for future in as_completed(futures):
                i, chunk = future.result()
                self.frame_ready.emit(i, chunk)
        self.finished.emit()

    def _extract(self, index: int, timestamp: int | float):
        # pure Python, no Qt here!
        chunk = self._wrapper.extract_single_frame(self._video_path, timestamp, self._width, self._height)
        return index, chunk


# class ThumbnailWorker(QtCore.QThread):
#     """Runs frame extraction off the main thread."""

#     frame_ready = QtCore.Signal(int, bytes)
#     error = QtCore.Signal(str)

#     def __init__(
#         self,
#         parent,
#         ffmpeg_path: Path,
#         video_path: Path,
#         fps: int | float,
#         start: int | float,
#         duration: int | float,
#         width: int,
#         height: int,
#     ) -> None:
#         super().__init__(parent)
#         self.ffmpeg_path = ffmpeg_path
#         self.video_path = video_path
#         self._fps = fps
#         self._start_time = start
#         self._duration = duration
#         self._width = width
#         self._height = height

#     def run(self) -> None:
#         try:
#             wrapper = FFmWrap(self.ffmpeg_path)
#             wrapper.extract_frame_bytes(
#                 self.video_path,
#                 fps=self._fps,
#                 start_time=self._start_time,
#                 duration=self._duration,
#                 width=self._width,
#                 height=self._height,
#                 progress_callback=self.frame_ready.emit,
#             )
#         except Exception as exc:
#             self.error.emit(str(exc))


if __name__ == '__main__':
    app = QtWidgets.QApplication([])
    win = ExtractionDemo()
    win.show()
    app.exec()
