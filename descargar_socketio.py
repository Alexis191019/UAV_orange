#!/usr/bin/env python3
"""Script para descargar socket.io.min.js localmente."""

import urllib.request
import os
from pathlib import Path

# Ruta del archivo de destino
script_dir = Path(__file__).parent
dest_file = script_dir / "web" / "static" / "socket.io.min.js"

# URL del archivo
url = "https://cdn.socket.io/4.5.4/socket.io.min.js"

print(f"[INFO] Descargando socket.io.min.js desde {url}")
print(f"[INFO] Guardando en: {dest_file}")

try:
    # Crear directorio si no existe
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Descargar archivo
    urllib.request.urlretrieve(url, dest_file)
    
    # Verificar que se descargó
    if dest_file.exists():
        size = dest_file.stat().st_size
        print(f"[OK] Archivo descargado correctamente: {size} bytes")
        print(f"[OK] Ubicación: {dest_file.absolute()}")
    else:
        print("[ERROR] El archivo no se descargó correctamente")
        exit(1)
        
except Exception as e:
    print(f"[ERROR] No se pudo descargar el archivo: {e}")
    exit(1)

