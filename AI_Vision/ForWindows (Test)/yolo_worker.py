"""
yolo_worker.py
"""

from multiprocessing import Queue
from collections import defaultdict
import os
import shutil
import time

from ultralytics import YOLO
from dispenser import requestDispenser
import config

YOLO_MODEL      = "yolov5n.pt"
TARGET_CLASSES  = [0, 15, 16]
LABEL_MAP       = {0: "person", 15: "cat", 16: "dog"}
EVENTS_SAVE_DIR = "events_photos"


def yolo_worker(input_q: Queue) -> None:
    print("[YOLO] Cargando yolov5n... (solo ocurre una vez)")
    model = YOLO(YOLO_MODEL)
    print("[YOLO] Listo, esperando fotos.\n")

    os.makedirs(EVENTS_SAVE_DIR, exist_ok=True)

    confirmations: dict[int, int]   = defaultdict(int)
    dispatched:    dict[int, bool]  = defaultdict(bool)
    received:      dict[int, int]   = defaultdict(int)
    last_label:    dict[int, str]   = defaultdict(str)
    saved_photo:   dict[int, bool]  = defaultdict(bool)
    event_starts:  dict[int, float] = {}   # event_id → timestamp del sensor

    while True:
        item = input_q.get()

        if item is None:
            print("[YOLO] Senal de cierre. Saliendo.")
            break

        event_id, photo_index, total_photos, img_path, event_start = item

        # Registrar el start del evento la primera vez que llega una foto suya
        if event_id not in event_starts:
            event_starts[event_id] = event_start

        t_inference_start = time.time()

        try:
            # Pasada RAW
            results_all = model(img_path, verbose=False)
            all_boxes = [
                f"{model.names[int(box.cls)]}({round(float(box.conf),3)})"
                for r in results_all for box in r.boxes
            ]

            t_inference = time.time() - t_inference_start
            elapsed     = time.time() - event_start

            print(f"[YOLO] evento {event_id} · foto {photo_index} — "
                  f"inferencia: {t_inference*1000:.0f}ms | "
                  f"total desde sensor: {elapsed*1000:.0f}ms")

            if all_boxes:
                print(f"[YOLO] RAW: {', '.join(all_boxes)}")
            else:
                print(f"[YOLO] RAW: ninguna deteccion")

            # Pasada con filtro
            min_conf = config.get("min_confidence")
            results  = model(img_path, conf=min_conf, classes=TARGET_CLASSES, verbose=False)
            detected = any(len(r.boxes) > 0 for r in results)
            print(f"[YOLO] Filtro conf>={min_conf} → detectado={detected}")

            if detected:
                for r in results:
                    for box in r.boxes:
                        label = LABEL_MAP.get(int(box.cls), "unknown")
                        conf  = round(float(box.conf), 3)
                        print(f"[YOLO] >> {label} ({conf})")
                        last_label[event_id] = label
                confirmations[event_id] += 1

                if not saved_photo[event_id]:
                    save_name = f"evento{event_id}_{last_label[event_id]}_foto{photo_index}.jpg"
                    save_path = os.path.join(EVENTS_SAVE_DIR, save_name)
                    shutil.copy(img_path, save_path)
                    print(f"[YOLO] Foto guardada → {save_path}")
                    saved_photo[event_id] = True
            else:
                print(f"[YOLO] Sin deteccion con filtro")

        except Exception as e:
            print(f"[YOLO] Error en evento {event_id} foto {photo_index}: {e}")

        finally:
            try:
                os.remove(img_path)
            except OSError:
                pass

        received[event_id] += 1

        # Salida temprana
        if not dispatched[event_id] and confirmations[event_id] >= config.get("min_confirmations"):
            label        = last_label[event_id]
            total_elapsed = time.time() - event_starts[event_id]
            print(f"\n[YOLO] ✓ evento {event_id} — {confirmations[event_id]} confirmaciones ({label})")
            print(f"[YOLO] ✓ Tiempo total sensor → dispenser: {total_elapsed:.3f}s")
            print(f"[YOLO] ── Llamando requestDispenser ──────────────────────\n")
            requestDispenser(label)
            dispatched[event_id] = True

        # Evento completo
        if received[event_id] == total_photos:
            if not dispatched[event_id]:
                total_elapsed = time.time() - event_starts[event_id]
                print(f"[YOLO] evento {event_id} — {confirmations[event_id]}/{total_photos} confirmaciones. "
                      f"No se dispensa. Tiempo total: {total_elapsed:.3f}s\n")
            del confirmations[event_id]
            del dispatched[event_id]
            del received[event_id]
            saved_photo.pop(event_id, None)
            event_starts.pop(event_id, None)
            last_label.pop(event_id, None)