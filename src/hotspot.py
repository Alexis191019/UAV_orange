"""Módulo para gestión del hotspot WiFi."""

import time
import subprocess
from . import config
from .utils import ejecutar


def conexion_hotspot_activa():
    """Verifica si el hotspot está activo.
    
    Returns:
        bool: True si el hotspot está activo, False en caso contrario
    """
    consulta = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show", "--active"],
        capture_output=True,
        text=True,
    )
    if consulta.returncode != 0:
        return False
    nombres = consulta.stdout.strip().splitlines()
    return config.HOTSPOT_NAME in nombres


def levantar_hotspot():
    """Activa el hotspot WiFi con reintentos automáticos."""
    print("[INFO] Reiniciando radio WiFi…")
    try:
        ejecutar(["nmcli", "radio", "wifi", "off"], "Apagando radio WiFi")
        time.sleep(2.0)
        ejecutar(["nmcli", "radio", "wifi", "on"], "Encendiendo radio WiFi")
    except Exception as exc:
        print(f"[WARN] No se pudo reiniciar la radio WiFi: {exc}")

    time.sleep(2.0)

    try:
        ejecutar(["nmcli", "connection", "down", config.HOTSPOT_NAME], "Apagando hotspot previo")
    except Exception as exc:
        print(f"[WARN] No se pudo apagar hotspot previo (posiblemente ya estaba abajo): {exc}")

    time.sleep(1.0)

    for intento in range(1, config.MAX_RETRIES + 1):
        try:
            ejecutar(["nmcli", "connection", "up", config.HOTSPOT_NAME], "Levantando hotspot")
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

            if intento == config.MAX_RETRIES:
                print("[WARN] No se pudo activar el hotspot tras varios intentos.")
                return

            time.sleep(config.RETRY_DELAY)


def bajar_hotspot():
    """Desactiva el hotspot WiFi."""
    try:
        ejecutar(["nmcli", "connection", "down", config.HOTSPOT_NAME], "Apagando hotspot")
        print("[OK] Hotspot desactivado.")
    except Exception as exc:
        print(f"[WARN] No se pudo bajar el hotspot: {exc}")


def obtener_ip_hotspot():
    """Obtiene la IP del hotspot WiFi.
    
    Returns:
        str: IP del hotspot (ej: "192.168.1.1") o None si no se puede obtener
    """
    try:
        # Obtener la IP de la interfaz del hotspot
        resultado = subprocess.run(
            ["nmcli", "-t", "-f", "IP4.ADDRESS", "connection", "show", config.HOTSPOT_NAME],
            capture_output=True,
            text=True
        )
        if resultado.returncode == 0 and resultado.stdout.strip():
            # El formato es: IP/MASK, solo necesitamos la IP
            ip_line = resultado.stdout.strip().splitlines()[0]
            ip = ip_line.split('/')[0]
            return ip
    except Exception as exc:
        print(f"[WARN] No se pudo obtener IP del hotspot: {exc}")
    
    # Intentar método alternativo: obtener IP de la interfaz
    try:
        resultado = subprocess.run(
            ["ip", "addr", "show", config.HOTSPOT_IFACE],
            capture_output=True,
            text=True
        )
        if resultado.returncode == 0:
            for line in resultado.stdout.splitlines():
                if "inet " in line and "127.0.0.1" not in line:
                    # Extraer IP (formato: inet 192.168.1.1/24)
                    ip = line.split()[1].split('/')[0]
                    return ip
    except Exception as exc:
        print(f"[WARN] No se pudo obtener IP por método alternativo: {exc}")
    
    return None

