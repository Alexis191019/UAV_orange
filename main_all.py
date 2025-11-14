print("[DEBUG] main_all.py importado")

import subprocess
import signal
import pathlib
import time
import threading
import queue
import cv2
from ultralytics import YOLO

# ----------------------------------------------------------------------
# Configuración general
# ----------------------------------------------------------------------
HOTSPOT_NAME = "RC-Hotspot"
HOTSPOT_IFACE = "wlan0"

BASE_DIR = pathlib.Path(__file__).resolve().parent
MEDIAMTX_BIN = BASE_DIR / "mediamtx" / "mediamtx"
MEDIAMTX_CFG = BASE_DIR / "mediamtx" / "mediamtx.yml"

RTMP_URL = "rtmp://127.0.0.1:1935/live/dron"             # ajusta a tu stream real

MODEL_PATH = "Visdrone_yolo11n_rknn_model"
CONF_THRESH = 0.3
MODEL_IMGSZ = 640
FRAME_SIZE = (640, 480)

OUTPUT_VIDEO = None   # por ejemplo "output_rknn.mp4" si quieres grabar
OUTPUT_FPS = 25

RETRY_DELAY = 3
MAX_RETRIES = 5

# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def ejecutar(cmd, descripcion):
    print(f"[INFO] {descripcion}: {' '.join(cmd)}", flush=True)
    proceso = subprocess.run(cmd, capture_output=True, text=True)
    if proceso.returncode != 0:
        raise RuntimeError(
            f"Falló {descripcion} (código {proceso.returncode})\n"
            f"STDOUT:\n{proceso.stdout}\nSTDERR:\n{proceso.stderr}"
        )
    return proceso.stdout.strip()


def conexion_hotspot_activa():
    consulta = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
        capture_output=True,
        text=True,
    )
    if consulta.returncode != 0:
        return False
    nombres = consulta.stdout.strip().splitlines()
    return HOTSPOT_NAME in nombres


def levantar_hotspot():
    print("[INFO] Reiniciando radio WiFi…")
    try:
        ejecutar(["nmcli", "radio", "wifi", "off"], "Apagando radio WiFi")
        time.sleep(2.0)
        ejecutar(["nmcli", "radio", "wifi", "on"], "Encendiendo radio WiFi")
    except Exception as exc:
        print(f"[WARN] No se pudo reiniciar la radio WiFi: {exc}")

    time.sleep(2.0)

    try:
        ejecutar(["nmcli", "connection", "down", HOTSPOT_NAME], "Apagando hotspot previo")
    except Exception as exc:
        print(f"[WARN] No se pudo apagar hotspot previo (posiblemente ya estaba abajo): {exc}")

    time.sleep(1.0)

    for intento in range(1, MAX_RETRIES + 1):
        try:
            ejecutar(["nmcli", "connection", "up", HOTSPOT_NAME], "Levantando hotspot")
            print("[OK] Hotspot activo.")
            return
        except Exception as exc:
            mensaje = str(exc).lower()
            if "already active" in mensaje:
                print("[WARN] Hotspot ya estaba activo, continúo.")
                return
            if "ip configuration could not be reserved" in mensaje:
                if conexion_hotspot_activa():
                    print("[WARN] Hotspot activo según nmcli, continúo.")
                    return
                print("[WARN] Reintentando activación tras error de IP…")
            elif "802.1x supplicant took too long" in mensaje:
                if conexion_hotspot_activa():
                    print("[WARN] Hotspot reportado activo pese al retraso del supplicant.")
                    return
                print("[WARN] Reintentando tras retraso de autenticación…")
            else:
                print(f"[ERROR] Hotspot intento {intento}: {exc}")

            if intento == MAX_RETRIES:
                print("[WARN] No se pudo activar el hotspot tras varios intentos.")
                return

            time.sleep(RETRY_DELAY)


def bajar_hotspot():
    try:
        ejecutar(["nmcli", "connection", "down", HOTSPOT_NAME], "Apagando hotspot")
        print("[OK] Hotspot desactivado.")
    except Exception as exc:
        print(f"[WARN] No se pudo bajar el hotspot: {exc}")


def iniciar_mediamtx():
    if not MEDIAMTX_BIN.exists():
        raise FileNotFoundError(f"No se encontró {MEDIAMTX_BIN}")

    cmd = [str(MEDIAMTX_BIN)]
    if MEDIAMTX_CFG.exists():
        cmd.append(str(MEDIAMTX_CFG))

    print(f"[INFO] Iniciando MediaMTX: {' '.join(cmd)}")
    proceso = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(1.5)
    if proceso.poll() is not None:
        salida = proceso.stdout.read()
        raise RuntimeError(f"MediaMTX terminó inesperadamente:\n{salida}")
    return proceso


def detener_mediamtx(proceso):
    if proceso and proceso.poll() is None:
        print("[INFO] Deteniendo MediaMTX…")
        proceso.send_signal(signal.SIGINT)
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            print("[WARN] MediaMTX forzado con kill().")


def abrir_stream():
    intentos = 0
    while True:
        cap = cv2.VideoCapture(RTMP_URL)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print("[OK] Conexión RTMP abierta.")
            return cap

        cap.release()
        intentos += 1
        print(f"[WARN] RTMP aún no disponible (intento {intentos}). Reintentando en {RETRY_DELAY}s…")
        time.sleep(RETRY_DELAY)


def lector_frames(cap, cola, stop_event):
    """Hilo que lee frames continuamente y los pone en la cola.
    
    Este hilo mantiene la conexión RTMP viva leyendo frames continuamente,
    incluso si la inferencia es lenta. Los frames intermedios se descartan
    para evitar que el buffer de OpenCV se llene y cause timeouts.
    """
    print("[INFO] Hilo lector iniciado.")
    frames_leidos = 0
    frames_descartados = 0
    
    while not stop_event.is_set():
        try:
            # Lee un frame (esto mantiene la conexión RTMP activa)
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frames_leidos += 1
            
            try:
                frame = cv2.resize(frame, FRAME_SIZE)
            except Exception as exc:
                print(f"[WARN] Fallo al redimensionar frame: {exc}")
                continue

            # Intenta poner el frame en la cola (no bloquea)
            try:
                cola.put_nowait(frame)
            except queue.Full:
                # Si la cola está llena, descarta el frame antiguo y pone el nuevo
                # Esto asegura que siempre procesemos el frame más reciente
                try:
                    cola.get_nowait()
                    cola.put_nowait(frame)
                    frames_descartados += 1
                except queue.Empty:
                    pass
                
        except Exception as exc:
            print(f"[WARN] Error en lector de frames: {exc}")
            time.sleep(0.1)
            continue

    print(f"[INFO] Hilo lector detenido. Frames leídos: {frames_leidos}, descartados: {frames_descartados}")


def crear_writer(ruta, frame_size, fps):
    if ruta is None:
        return None
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(ruta, fourcc, fps, frame_size)
    if not writer.isOpened():
        print(f"[WARN] No se pudo abrir el archivo de salida {ruta}.")
        return None
    print(f"[OK] Guardando resultado en {ruta}")
    return writer

# ----------------------------------------------------------------------
# Bucle de visualización + inferencia on-demand
# ----------------------------------------------------------------------
def bucle_visualizacion(model, cap, writer, frame_queue, stop_event):
    fps_hist = []
    frame_count = 0
    inferir = False

    print("[INFO] Esperando frames RTMP. Pulsa 'i' para iniciar/pausar inferencia, 'q' para salir.")

    while not stop_event.is_set():
        try:
            frame = frame_queue.get(timeout=0.5)
        except queue.Empty:
            print("[WARN] Sin frames disponibles, reintentando…")
            continue

        annotated = frame
        fps_text = "FPS: -- | Avg: --"
        if inferir:
            start_time = time.time()
            try:
                results = model.predict(
                    frame,
                    conf=CONF_THRESH,
                    verbose=False,
                    imgsz=MODEL_IMGSZ
                )
                annotated = results[0].plot()
            except Exception as exc:
                print(f"[WARN] Inferencia fallida: {exc}")
            else:
                elapsed = time.time() - start_time
                fps_actual = 1.0 / elapsed if elapsed > 0 else 0.0
                fps_hist.append(fps_actual)
                if len(fps_hist) > 30:
                    fps_hist.pop(0)
                fps_prom = sum(fps_hist) / len(fps_hist) if fps_hist else 0.0
                fps_text = f"FPS: {fps_actual:.1f} | Avg: {fps_prom:.1f}"

        cv2.putText(
            annotated,
            fps_text if inferir else "Visualización en vivo (pulsa i para inferir)",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
            cv2.LINE_AA
        )

        if writer is not None:
            try:
                writer.write(annotated)
            except Exception as exc:
                print(f"[WARN] No se pudo escribir en archivo: {exc}")

        cv2.imshow("RTMP Drone", annotated)
        frame_count += 1
        if inferir and frame_count % 100 == 0:
            print(f"[INFO] Frames inferidos: {frame_count}")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("[INFO] Salida solicitada por usuario.")
            stop_event.set()
            break
        elif key == ord('i'):
            inferir = not inferir
            estado = "Activada" if inferir else "Pausada"
            print(f"[INFO] Inferencia {estado}.")
        elif key == ord('p'):
            inferir = False
            print("[INFO] Inferencia pausada (tecla p).")

# ----------------------------------------------------------------------
# Flujo principal
# ----------------------------------------------------------------------
def main():
    print("[DEBUG] Entrando a main()", flush=True)
    mediamtx_proc = None
    cap = None
    writer = None
    lector_thread = None
    stop_event = None

    try:
        levantar_hotspot()

        try:
            mediamtx_proc = iniciar_mediamtx()
        except Exception as exc:
            print(f"[ERROR] No se pudo iniciar MediaMTX: {exc}")

        print("[INFO] Cargando modelo RKNN…")
        model = YOLO(MODEL_PATH, task='detect')
        print("[OK] Modelo cargado.")

        cap = abrir_stream()
        if cap is None:
            raise RuntimeError("No se pudo conectar al stream RTMP.")

        writer = crear_writer(OUTPUT_VIDEO, FRAME_SIZE, OUTPUT_FPS)

        # Crear cola de frames (solo almacena el más reciente)
        frame_queue = queue.Queue(maxsize=1)
        stop_event = threading.Event()

        # Iniciar hilo lector
        lector_thread = threading.Thread(
            target=lector_frames, args=(cap, frame_queue, stop_event), daemon=True
        )
        lector_thread.start()

        # Esperar un poco para que el lector comience a llenar la cola
        time.sleep(0.5)

        # Bucle principal de visualización e inferencia
        bucle_visualizacion(model, cap, writer, frame_queue, stop_event)

    except KeyboardInterrupt:
        print("\n[INFO] Interrupción manual recibida.")
    except Exception as exc:
        print(f"[ERROR] Excepción no controlada: {exc}")
    finally:
        print("[DEBUG] Entrando a finally()", flush=True)
        print("[INFO] Liberando recursos…")
        if stop_event is not None:
            stop_event.set()
        if lector_thread is not None:
            lector_thread.join(timeout=1.0)
        if cap is not None:
            cap.release()
        if writer is not None:
            writer.release()
        cv2.destroyAllWindows()
        detener_mediamtx(mediamtx_proc)
        bajar_hotspot()
        print("[INFO] Programa finalizado.")



main()
