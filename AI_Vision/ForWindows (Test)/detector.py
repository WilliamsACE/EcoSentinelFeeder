"""
detector.py
"""

import cv2
import time
import tempfile
from multiprocessing import Queue

import config

_back_sub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50)


def detect(cap: cv2.VideoCapture, input_q: Queue, event_id: int, event_start: float) -> bool:
    ret, frame = cap.read()
    if not ret:
        print(f"[Detector] ERROR: no se pudo leer frame de la camara")
        return False

    t_mog2_start = time.time()
    fg_mask = _back_sub.apply(frame)
    contours, _ = cv2.findContours(
        fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    t_mog2 = time.time() - t_mog2_start

    min_area    = config.get("min_contour_area")
    areas       = [int(cv2.contourArea(c)) for c in contours]
    significant = [a for a in areas if a > min_area]

    print(f"[Detector] MOG2 en {t_mog2*1000:.1f}ms — "
          f"contornos: {len(areas)} | top areas: {sorted(areas, reverse=True)[:3]} | "
          f"umbral: {min_area}px² | significativos: {len(significant)}")

    if not significant:
        return False

    total_photos = config.get("total_photos")
    interval     = config.get("capture_interval")

    print(f"[Detector] Movimiento OK — capturando {total_photos} fotos "
          f"(+{(time.time()-event_start)*1000:.0f}ms desde sensor)")

    for i in range(total_photos):
        t_cap = time.time()
        # Vaciar buffer de la camara (descarta frames acumulados)
        # cap.grab() es mucho mas rapido que cap.read() y no decodifica
        for _ in range(3):
            cap.grab()
        ret, frame = cap.retrieve()
        if ret:
            tmp = tempfile.mktemp(suffix=".jpg")
            cv2.imwrite(tmp, frame)
            # Pasar event_start junto con la foto para que YOLO calcule el tiempo total
            input_q.put((event_id, i, total_photos, img_path := tmp, event_start))
            print(f"[Detector] foto {i} capturada en {(time.time()-t_cap)*1000:.0f}ms "
                  f"(+{(time.time()-event_start)*1000:.0f}ms desde sensor)")
        else:
            print(f"[Detector] foto {i} ERROR al capturar frame")
        if i < total_photos - 1:
            time.sleep(interval)

    return True