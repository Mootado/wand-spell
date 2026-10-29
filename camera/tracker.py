"""Follow the retroreflective wand tip and cut a stroke when the hand rests.

The NoIR frame is mirrored, so a wave to the player's right draws to the right
on the TV. Only a small, compact blob away from the frame edge can start a stroke.
"""

from __future__ import annotations

import math
import queue
import threading
import time

CAM_W = 320
CAM_H = 240

STILL_SECONDS = 0.5
LOST_SECONDS = 0.35
START_SPEED = 65.0
MIN_STEP = 3.0
MIN_AREA = 6
MAX_AREA = 260


class WandTracker:
    def __init__(self, source):
        self.source = source
        self.threshold = 185
        self._lock = threading.Lock()
        self._stroke: list[tuple[float, float]] = []
        self._mask = None
        self._blob = None
        self._queue: queue.Queue = queue.Queue()
        self._running = True
        self._tracking = False
        self._still = 0.0
        self._lost = 0.0
        self._smooth = None
        self._last_point = None
        self._last_time = time.perf_counter()
        self._thread = threading.Thread(target=self._loop, name="wand-camera", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._thread.join(timeout=1.5)
        self.source.close()

    def snapshot(self) -> dict:
        with self._lock:
            mask = None if self._mask is None else self._mask.copy()
            return {
                "stroke": list(self._stroke),
                "mask": mask,
                "blob": self._blob,
                "threshold": self.threshold,
            }

    def poll(self) -> list[list[tuple[float, float]]]:
        paths = []
        while True:
            try:
                paths.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return paths

    def adjust_threshold(self, delta: int) -> None:
        self.threshold = max(40, min(250, self.threshold + delta))

    def _loop(self) -> None:
        while self._running:
            frame = self.source.read()
            now = time.perf_counter()
            dt = min(0.1, now - self._last_time)
            self._last_time = now
            if frame is None:
                time.sleep(0.02)
                continue
            blob, mask = find_blob(frame, self.threshold)
            with self._lock:
                self._mask = mask
                self._blob = None if blob is None else (blob[0], blob[1])
                self._follow(blob, dt)

    def _follow(self, blob, dt: float) -> None:
        if blob is None:
            self._lost += dt
            self._still = 0.0
            self._last_point = None
            if self._tracking and self._lost >= LOST_SECONDS:
                self._finish()
            return

        cx, cy, _area = blob
        if self._smooth is None:
            sx, sy = cx, cy
        else:
            sx = self._smooth[0] * 0.45 + cx * 0.55
            sy = self._smooth[1] * 0.45 + cy * 0.55
        self._smooth = (sx, sy)
        self._lost = 0.0

        if self._last_point is None:
            speed = 0.0
        else:
            speed = math.hypot(sx - self._last_point[0], sy - self._last_point[1]) / max(dt, 1e-3)
        self._last_point = (sx, sy)

        if not self._tracking:
            if speed >= START_SPEED:
                self._tracking = True
                self._stroke = [(sx, sy)]
                self._still = 0.0
            return

        if not self._stroke or math.hypot(sx - self._stroke[-1][0], sy - self._stroke[-1][1]) >= MIN_STEP:
            self._stroke.append((sx, sy))
        if speed < 28:
            self._still += dt
        else:
            self._still = 0.0
        if self._still >= STILL_SECONDS:
            self._finish()

    def _finish(self) -> None:
        stroke = self._stroke
        self._stroke = []
        self._tracking = False
        self._still = 0.0
        if len(stroke) < 6:
            return
        length = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(stroke, stroke[1:]))
        if length >= 28:
            self._queue.put(stroke)


def find_blob(gray, threshold: int):
    """Return ((x, y, area) or None, mask uint8)."""
    import numpy as np

    if gray.ndim == 3:
        gray = gray[:, :, :3].mean(axis=2).astype(np.uint8)
    gray = np.ascontiguousarray(gray)
    mask = np.where(gray >= threshold, 255, 0).astype(np.uint8)
    try:
        import cv2
    except ImportError:
        return _blob_without_opencv(gray, threshold), mask

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = gray.shape[:2]
    margin = 8
    best = None
    best_score = 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < MIN_AREA or area > MAX_AREA:
            continue
        x, y, bw, bh = cv2.boundingRect(contour)
        if bw < 1 or bh < 1:
            continue
        if area / (bw * bh) < 0.28:
            continue
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * math.pi * area / (perimeter * perimeter)
            if circularity < 0.2:
                continue
        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue
        cx = moments["m10"] / moments["m00"]
        cy = moments["m01"] / moments["m00"]
        if cx < margin or cy < margin or cx > width - margin or cy > height - margin:
            continue
        brightness = float(gray[y : y + bh, x : x + bw].mean())
        score = brightness * min(1.0, area / (bw * bh))
        if score > best_score:
            best_score = score
            best = (float(cx), float(cy), float(area))
    return best, opened


def _blob_without_opencv(gray, threshold: int):
    import numpy as np

    height, width = gray.shape[:2]
    work = gray.copy()
    work[:8, :] = 0
    work[-8:, :] = 0
    work[:, :8] = 0
    work[:, -8:] = 0
    for _ in range(3):
        index = int(np.argmax(work))
        cy, cx = divmod(index, width)
        if work[cy, cx] < threshold:
            return None
        y0, y1 = max(0, cy - 14), min(height, cy + 15)
        x0, x1 = max(0, cx - 14), min(width, cx + 15)
        window = gray[y0:y1, x0:x1]
        bright = window >= threshold
        area = int(bright.sum())
        if MIN_AREA <= area <= 180:
            ys, xs = np.nonzero(bright)
            weights = window[bright].astype(float)
            total = float(weights.sum()) or 1.0
            return (float((xs * weights).sum() / total + x0), float((ys * weights).sum() / total + y0), float(area))
        work[y0:y1, x0:x1] = 0
    return None


class PiCameraSource:
    def __init__(self):
        from picamera2 import Picamera2

        self.cam = Picamera2()
        config = self.cam.create_video_configuration(
            main={"size": (CAM_W, CAM_H), "format": "RGB888"},
            controls={"FrameRate": 30},
        )
        self.cam.configure(config)
        self.cam.start()
        time.sleep(0.4)

    def read(self):
        import numpy as np

        frame = self.cam.capture_array()
        gray = frame[:, :, :3].mean(axis=2).astype(np.uint8)
        return np.ascontiguousarray(gray[:, ::-1])

    def close(self) -> None:
        try:
            self.cam.stop()
        except Exception:
            pass


class WebcamSource:
    def __init__(self):
        import cv2

        self._cv2 = cv2
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("webcam did not open")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

    def read(self):
        import numpy as np

        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
        gray = frame[:, :, :3].mean(axis=2).astype(np.uint8)
        return np.ascontiguousarray(gray[:, ::-1])

    def close(self) -> None:
        self.cap.release()


def open_source(prefer_webcam: bool = False):
    """Pi camera first, then a webcam. Returns None when neither is available."""
    if not prefer_webcam:
        try:
            return PiCameraSource()
        except Exception as error:
            print(f"Pi camera unavailable ({error}).")
    try:
        return WebcamSource()
    except Exception as error:
        print(f"No camera available ({error}).")
        return None
