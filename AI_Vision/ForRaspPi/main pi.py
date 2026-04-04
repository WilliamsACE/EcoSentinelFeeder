"""
main_pi.py
----------
Version para Raspberry Pi 4.
Diferencias vs main.py (Windows):
  - Backend de camara: solo V4L2 (Linux)
  - Resolucion reducida a 320x240 para aliviar CPU
  - sensor_triggered() usa GPIO real — configura PIR_PIN segun tu cableado
  - cv2.imshow deshabilitado por defecto (Pi sin pantalla)
"""

import time
import threading
import cv2
import uvicorn
from multiprocessing import Process, Queue

import RPi.GPIO as GPIO

from yolo_worker import yolo_worker
from detector import detect
from api import app as fastapi_app
import config

API_HOST      = "0.0.0.0"
API_PORT      = 8000
POLL_INTERVAL = 0.05
CAMERA_INDEX  = 0

# ── GPIO ─────────────────────────────────────────────────────────────────────
PIR_PIN = 17   # cambia al pin BCM donde conectaste el sensor

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
# ─────────────────────────────────────────────────────────────────────────────


def sensor_triggered() -> bool:
    return GPIO.input(PIR_PIN) == GPIO.HIGH


def open_camera(index: int):
    """En Pi solo intentamos V4L2 y auto."""
    backends = [
        (cv2.CAP_V4L2, "V4L2 (Linux/Pi)"),
        (cv2.CAP_ANY,  "auto"),
    ]
    for backend, name in backends:
        cap = cv2.VideoCapture(index, backend)
        if cap.isOpened():
            # Bajar resolucion para aliviar CPU de la Pi
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            cap.set(cv2.CAP_PROP_FPS, 30)
            ret, _ = cap.read()
            if ret:
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"[Main] Camara abierta con backend: {name} — {w}x{h}")
                return cap
            cap.release()
    return None


def main() -> None:
    # FastAPI en hilo daemon
    api_thread = threading.Thread(
        target=lambda: uvicorn.run(
            fastapi_app, host=API_HOST, port=API_PORT, log_level="warning"
        ),
        daemon=True,
    )
    api_thread.start()
    print(f"[Main] API disponible en http://0.0.0.0:{API_PORT}/docs\n")

    input_q = Queue()

    worker = Process(target=yolo_worker, args=(input_q,), daemon=True)
    worker.start()
    print("[Main] YOLO worker iniciado en segundo plano.")

    cap = open_camera(CAMERA_INDEX)
    if cap is None:
        print("[Main] Error: no se pudo abrir la camara.")
        input_q.put(None)
        GPIO.cleanup()
        return

    print("[Main] Esperando sensor...\n")

    event_id        = 0
    last_event_time = 0.0

    try:
        while True:
            now = time.time()

            # Modo debug — en Pi muestra solo si hay pantalla conectada (DISPLAY)
            if config.get("debug"):
                ret, frame = cap.read()
                if ret:
                    try:
                        cv2.imshow("Debug — camara en vivo", frame)
                        if cv2.waitKey(1) & 0xFF == ord("q"):
                            config.update({"debug": False})
                            cv2.destroyAllWindows()
                    except cv2.error:
                        # Sin pantalla disponible, desactivar debug automaticamente
                        print("[Main] Debug desactivado — sin display disponible")
                        config.update({"debug": False})
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

            # Sensor disparado
            event_start     = time.time()
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
        GPIO.cleanup()
        print("[Main] Recursos liberados.")


if __name__ == "__main__":
    main()