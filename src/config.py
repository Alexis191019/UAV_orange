"""Configuraciones generales del sistema."""

import pathlib

# Configuración de Hotspot
HOTSPOT_NAME = "RC-Hotspot"
HOTSPOT_IFACE = "wlan0"

# Rutas base
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
# Compatible con Windows (.exe) y Linux
# En Windows: mediaMTX/ (mayúsculas)
# En Linux/Orange Pi: mediamtx/ (minúsculas)
import sys
if sys.platform == "win32":
    MEDIAMTX_BIN = BASE_DIR / "mediaMTX" / "mediamtx.exe"
    MEDIAMTX_CFG = BASE_DIR / "mediaMTX" / "mediamtx.yml"
else:
    # Linux/Orange Pi: carpeta en minúsculas
    MEDIAMTX_BIN = BASE_DIR / "mediamtx" / "mediamtx"
    MEDIAMTX_CFG = BASE_DIR / "mediamtx" / "mediamtx.yml"

# Configuración RTMP
RTMP_URL = "rtmp://127.0.0.1:1935/live/dron"

# Configuración del modelo
# En Orange Pi: carpeta Visdrone_yolo11n_rknn_model/ al mismo nivel que src/
# Si el modelo está en una carpeta, YOLO buscará automáticamente el archivo .rknn o .pt dentro
MODEL_PATH = "Visdrone_yolo11n_rknn_model"
# Alternativa si el modelo es un archivo específico:
# MODEL_PATH = "Visdrone_yolo11n_rknn_model/modelo.rknn"  # o .pt
CONF_THRESH = 0.3
MODEL_IMGSZ = 1024 # 640 es el tamaño por defecto de los modelos de yolo, pero se puede aumentar para mejor precisión
FRAME_SIZE = (640, 480)

# Configuración de salida de video
OUTPUT_VIDEO = None  # Por ejemplo "output_rknn.mp4" si quieres grabar
OUTPUT_FPS = 25

# Configuración de reintentos
RETRY_DELAY = 3
MAX_RETRIES = 5

