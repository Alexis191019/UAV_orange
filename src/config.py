"""Configuraciones generales del sistema."""

import pathlib

# Configuración de Hotspot
HOTSPOT_NAME = "RC-Hotspot"
HOTSPOT_IFACE = "wlan0"

# Rutas base
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
# Compatible con Windows (.exe) y Linux
import sys
if sys.platform == "win32":
    MEDIAMTX_BIN = BASE_DIR / "mediaMTX" / "mediamtx.exe"
    MEDIAMTX_CFG = BASE_DIR / "mediaMTX" / "mediamtx.yml"
else:
    MEDIAMTX_BIN = BASE_DIR / "mediaMTX" / "mediamtx"
    MEDIAMTX_CFG = BASE_DIR / "mediaMTX" / "mediamtx.yml"

# Configuración RTMP
RTMP_URL = "rtmp://127.0.0.1:1935/live/dron"

# Configuración del modelo
MODEL_PATH = "Visdrone_yolo11n_rknn_model"
CONF_THRESH = 0.3
MODEL_IMGSZ = 640
FRAME_SIZE = (640, 480)

# Configuración de salida de video
OUTPUT_VIDEO = None  # Por ejemplo "output_rknn.mp4" si quieres grabar
OUTPUT_FPS = 25

# Configuración de reintentos
RETRY_DELAY = 3
MAX_RETRIES = 5

