"""Módulo para detección de objetos usando YOLO."""

import time
import cv2
import numpy as np
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
    
    def detectar(self, frame, conf_threshold=None, selected_classes=None, class_colors=None):
        """Realiza detección en un frame.
        
        Args:
            frame: Frame de OpenCV (numpy array)
            conf_threshold: Threshold de confianza (None = usar config.CONF_THRESH)
            selected_classes: Lista de nombres de clases a detectar (None = todas)
            class_colors: Diccionario {nombre_clase: (B, G, R)} para colores de bboxes
            
        Returns:
            tuple: (frame_anotado, tiempo_inferencia, clases_detectadas)
                - frame_anotado: Frame con las detecciones dibujadas (solo bboxes, sin texto)
                - tiempo_inferencia: Tiempo que tardó la inferencia en segundos
                - clases_detectadas: Diccionario con conteo de clases {nombre_clase: cantidad}
        """
        start_time = time.time()
        clases_detectadas = {}
        annotated = frame.copy()
        
        try:
            # Usar threshold personalizado o el de config
            conf = conf_threshold if conf_threshold is not None else config.CONF_THRESH
            
            results = self.model.predict(
                frame,
                conf=conf,
                verbose=False,
                imgsz=config.MODEL_IMGSZ
            )
            elapsed = time.time() - start_time
            
            # Extraer detecciones y dibujar bboxes
            try:
                result = results[0]
                if result.boxes is not None and len(result.boxes) > 0:
                    # Obtener datos de las detecciones
                    boxes = result.boxes
                    
                    # Convertir a numpy de forma segura
                    if hasattr(boxes.cls, 'cpu'):
                        class_ids = boxes.cls.cpu().numpy().astype(int)
                        confidences = boxes.conf.cpu().numpy()
                        xyxy = boxes.xyxy.cpu().numpy()
                    else:
                        class_ids = boxes.cls.numpy().astype(int) if hasattr(boxes.cls, 'numpy') else boxes.cls.astype(int)
                        confidences = boxes.conf.numpy() if hasattr(boxes.conf, 'numpy') else boxes.conf
                        xyxy = boxes.xyxy.numpy() if hasattr(boxes.xyxy, 'numpy') else boxes.xyxy
                    
                    # Filtrar por clases seleccionadas si se especificó
                    if selected_classes is not None and len(selected_classes) > 0:
                        # Convertir selected_classes a set para búsqueda rápida
                        selected_set = set(selected_classes)
                        filtered_indices = []
                        for i, class_id in enumerate(class_ids):
                            if class_id in result.names:
                                class_name = result.names[class_id]
                                if class_name in selected_set:
                                    filtered_indices.append(i)
                        # Filtrar arrays
                        if filtered_indices:
                            class_ids = class_ids[filtered_indices]
                            confidences = confidences[filtered_indices]
                            xyxy = xyxy[filtered_indices]
                        else:
                            # No hay detecciones que coincidan con las clases seleccionadas
                            class_ids = np.array([], dtype=int)
                            confidences = np.array([])
                            xyxy = np.array([])
                    
                    # Dibujar bboxes sin texto, solo rectángulos con colores
                    # Verificar que hay detecciones antes de iterar
                    if len(xyxy) > 0 and len(class_ids) > 0 and len(confidences) > 0:
                        for i, (box, class_id, conf) in enumerate(zip(xyxy, class_ids, confidences)):
                            if class_id in result.names:
                                class_name = result.names[class_id]
                                
                                # Obtener color de la clase o usar color por defecto
                                if class_colors and class_name in class_colors:
                                    color = class_colors[class_name]
                                else:
                                    # Color por defecto (azul) si no se especifica
                                    color = (255, 0, 0)  # BGR: azul
                                
                                # Convertir coordenadas a enteros
                                x1, y1, x2, y2 = map(int, box)
                                
                                # Dibujar solo el rectángulo (sin texto)
                                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                                
                                # Contar clase
                                clases_detectadas[class_name] = clases_detectadas.get(class_name, 0) + 1
                            
            except (AttributeError, IndexError, TypeError) as exc:
                # No hay detecciones o error al acceder
                print(f"[DEBUG] Error al procesar detecciones: {exc}")
                pass
            
            return annotated, elapsed, clases_detectadas
        except Exception as exc:
            print(f"[WARN] Inferencia fallida: {exc}")
            elapsed = time.time() - start_time
            return frame, elapsed, clases_detectadas
    
    def get_class_names(self):
        """Obtiene los nombres de las clases disponibles en el modelo.
        
        Returns:
            dict: Diccionario {id_clase: nombre_clase}
        """
        try:
            return self.model.names
        except Exception:
            return {}

