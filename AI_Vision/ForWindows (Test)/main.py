"""
main.py
"""

import time
import sys
import threading
import cv2
import uvicorn
from multiprocessing import Process, Queue

from yolo_worker import yolo_worker
from detector import detect
from api import app as fastapi_app
import config

API_HOST      = "0.0.0.0"
API_PORT      = 8000
POLL_INTERVAL = 0.05
CAMERA_INDEX  = 0


def sensor_triggered() -> bool:
    return True   # implementar con GPIO


def open_camera(index: int):
    if sys.platform == "win32":
        backends = [
            (cv2.CAP_DSHOW,        "DirectShow (Windows)"),
            (cv2.CAP_ANY,          "auto"),
        ]
    elif sys.platform == "darwin":
        backends = [
            (cv2.CAP_AVFOUNDATION, "AVFoundation (Mac)"),
            (cv2.CAP_ANY,          "auto"),
        ]
    else:
        backends = [
            (cv2.CAP_V4L2,         "V4L2 (Linux/Pi)"),
            (cv2.CAP_ANY,          "auto"),
        ]
    for backend, name in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print(f"[Main] Camara abierta con backend: {name}")
                return cap
            cap.release()
    return None


def main() -> None:
    api_thread = threading.Thread(
        target=lambda: uvicorn.run(
            fastapi_app, host=API_HOST, port=API_PORT, log_level="warning"
        ),
        daemon=True,
    )
    api_thread.start()
    print(f"[Main] API disponible en http://localhost:{API_PORT}/docs\n")

    input_q = Queue()

    worker = Process(target=yolo_worker, args=(input_q,), daemon=True)
    worker.start()
    print("[Main] YOLO worker iniciado en segundo plano.")

    cap = open_camera(CAMERA_INDEX)
    if cap is None:
        print("[Main] Error: ningun backend pudo abrir la camara.")
        input_q.put(None)
        return

    print("[Main] Esperando sensor...\n")

    event_id        = 0
    last_event_time = 0.0

    try:
        while True:
            now = time.time()

            # Modo debug
            if config.get("debug"):
                ret, frame = cap.read()
                if ret:
                    cv2.imshow("Debug — camara en vivo", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    config.update({"debug": False})
                    cv2.destroyAllWindows()
                time.sleep(POLL_INTERVAL)
                continue

            # Cooldown activo
            if config.get("cooldown") - (now - last_event_time) > 0:
                time.sleep(POLL_INTERVAL)
                continue

            # Sensor inactivo
            if not sensor_triggered():
                time.sleep(POLL_INTERVAL)
                continue

            # Sensor disparado — iniciar timer aqui
            event_start = time.time()
            last_event_time = event_start
            print(f"\n[Main] ── Evento {event_id} iniciado ──────────────────────")
            print(f"[Main] Sensor activo — llamando detector")

            triggered = detect(cap, input_q, event_id, event_start)

            if triggered:
                event_id += 1
            else:
                elapsed = time.time() - event_start
                print(f"[Main] Sin movimiento — descartado en {elapsed:.3f}s\n")

    except KeyboardInterrupt:
        print("\n[Main] Detenido por el usuario.")

    finally:
        input_q.put(None)
        worker.join(timeout=3)
        cap.release()
        cv2.destroyAllWindows()
        print("[Main] Recursos liberados.")


if __name__ == "__main__":
    main()