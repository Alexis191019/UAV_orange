#!/bin/bash
# Script para descargar socket.io.min.js localmente
# Ejecutar solo si el archivo no existe o necesita actualizarse

cd "$(dirname "$0")"

if [ ! -f "socket.io.min.js" ]; then
    echo "[INFO] Descargando socket.io.min.js..."
    curl -L -o socket.io.min.js https://cdn.socket.io/4.5.4/socket.io.min.js
    
    if [ $? -eq 0 ]; then
        echo "[OK] socket.io.min.js descargado correctamente"
        ls -lh socket.io.min.js
    else
        echo "[ERROR] No se pudo descargar socket.io.min.js"
        echo "[INFO] Asegúrate de tener conexión a internet"
        exit 1
    fi
else
    echo "[INFO] socket.io.min.js ya existe"
    ls -lh socket.io.min.js
fi

