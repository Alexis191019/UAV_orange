"""Módulo para gestión de video y streaming RTMP."""

import time
import queue
import cv2
from . import config


def abrir_stream():
    """Abre una conexión al stream RTMP con reintentos automáticos.
    
    Returns:
        cv2.VideoCapture: Objeto de captura de video
    """
    intentos = 0
    while True:
        cap = cv2.VideoCapture(config.RTMP_URL)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            print("[OK] Conexión RTMP abierta.")
            return cap

        cap.release()
        intentos += 1
        print(f"[WARN] RTMP aún no disponible (intento {intentos}). Reintentando en {config.RETRY_DELAY}s…")
        time.sleep(config.RETRY_DELAY)


def lector_frames(cap, cola, stop_event):
    """Hilo que lee frames continuamente y los pone en la cola.
    
    Este hilo mantiene la conexión RTMP viva leyendo frames continuamente,
    incluso si la inferencia es lenta. Los frames intermedios se descartan
    para evitar que el buffer de OpenCV se llene y cause timeouts.
    
    Args:
        cap: Objeto cv2.VideoCapture
        cola: queue.Queue para almacenar frames
        stop_event: threading.Event para detener el hilo
    """
    print("[INFO] Hilo lector iniciado.")
    frames_leidos = 0
    frames_descartados = 0
    
    while not stop_event.is_set():
        try:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            frames_leidos += 1
            
            try:
                frame = cv2.resize(frame, config.FRAME_SIZE)
            except Exception as exc:
                print(f"[WARN] Fallo al redimensionar frame: {exc}")
                continue

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
    """Crea un VideoWriter para guardar video en archivo.
    
    Args:
        ruta: Ruta del archivo de salida (None para no grabar)
        frame_size: Tamaño de los frames (ancho, alto)
        fps: Frames por segundo
        
    Returns:
        cv2.VideoWriter o None si ruta es None
    """
    if ruta is None:
        return None
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(ruta, fourcc, fps, frame_size)
    if not writer.isOpened():
        print(f"[WARN] No se pudo abrir el archivo de salida {ruta}.")
        return None
    print(f"[OK] Guardando resultado en {ruta}")
    return writer

