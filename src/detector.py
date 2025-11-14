"""Módulo para detección de objetos usando YOLO."""

import time
from ultralytics import YOLO
from . import config


class DetectorYOLO:
    """Clase para manejar la detección de objetos con YOLO."""
    
    def __init__(self):
        """Inicializa el detector cargando el modelo."""
        print("[INFO] Cargando modelo YOLO…")
        self.model = YOLO(config.MODEL_PATH, task='detect')
        print("[OK] Modelo cargado.")
    
    def detectar(self, frame):
        """Realiza detección en un frame.
        
        Args:
            frame: Frame de OpenCV (numpy array)
            
        Returns:
            tuple: (frame_anotado, tiempo_inferencia)
                - frame_anotado: Frame con las detecciones dibujadas
                - tiempo_inferencia: Tiempo que tardó la inferencia en segundos
        """
        start_time = time.time()
        try:
            results = self.model.predict(
                frame,
                conf=config.CONF_THRESH,
                verbose=False,
                imgsz=config.MODEL_IMGSZ
            )
            annotated = results[0].plot()
            elapsed = time.time() - start_time
            return annotated, elapsed
        except Exception as exc:
            print(f"[WARN] Inferencia fallida: {exc}")
            elapsed = time.time() - start_time
            return frame, elapsed

