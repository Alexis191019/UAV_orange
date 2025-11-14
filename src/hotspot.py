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

