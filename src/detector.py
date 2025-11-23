"""Módulo para detección de objetos usando YOLO."""

import time
from ultralytics import YOLO
from . import config


class DetectorYOLO:
    """Clase para manejar la detección de objetos con YOLO."""
    
    def __init__(self, model_path=None):
        """Inicializa el detector cargando el modelo.
        
        Args:
            model_path: Ruta al modelo. Si es None, usa config.MODEL_PATH
        """
        print("[INFO] Cargando modelo YOLO…")
        path = model_path if model_path else config.MODEL_PATH
        self.model = YOLO(path, task='detect')
        print("[OK] Modelo cargado.")
    
    def detectar(self, frame):
        """Realiza detección en un frame.
        
        Args:
            frame: Frame de OpenCV (numpy array)
            
        Returns:
            tuple: (frame_anotado, tiempo_inferencia, clases_detectadas)
                - frame_anotado: Frame con las detecciones dibujadas
                - tiempo_inferencia: Tiempo que tardó la inferencia en segundos
                - clases_detectadas: Diccionario con conteo de clases {nombre_clase: cantidad}
        """
        start_time = time.time()
        clases_detectadas = {}
        try:
            results = self.model.predict(
                frame,
                conf=config.CONF_THRESH,
                verbose=False,
                imgsz=config.MODEL_IMGSZ
            )
            annotated = results[0].plot()
            elapsed = time.time() - start_time
            
            # Extraer clases detectadas
            try:
                result = results[0]
                if result.boxes is not None and len(result.boxes) > 0:
                    # Obtener IDs de clases detectadas
                    cls_tensor = result.boxes.cls
                    # Convertir a numpy de forma segura
                    if hasattr(cls_tensor, 'cpu'):
                        class_ids = cls_tensor.cpu().numpy().astype(int)
                    else:
                        class_ids = cls_tensor.numpy().astype(int) if hasattr(cls_tensor, 'numpy') else cls_tensor.astype(int)
                    
                    # Contar cada clase
                    for class_id in class_ids:
                        if class_id in result.names:
                            class_name = result.names[class_id]
                            clases_detectadas[class_name] = clases_detectadas.get(class_name, 0) + 1
            except (AttributeError, IndexError, TypeError):
                # No hay detecciones o error al acceder
                pass
            
            return annotated, elapsed, clases_detectadas
        except Exception as exc:
            print(f"[WARN] Inferencia fallida: {exc}")
            elapsed = time.time() - start_time
            return frame, elapsed, clases_detectadas

