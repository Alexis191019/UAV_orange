"""Módulo para gestión del servidor MediaMTX."""

import signal
import subprocess
import time
import os
from . import config


def mediamtx_ya_corriendo():
    """Verifica si MediaMTX ya está corriendo.
    
    Returns:
        tuple: (bool, proceso_existente) 
            - bool: True si MediaMTX está corriendo
            - proceso_existente: subprocess.Popen del proceso existente o None
    """
    import sys
    
    try:
        if sys.platform == "win32":
            # Windows: usar tasklist para buscar proceso
            resultado = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq mediamtx.exe"],
                capture_output=True,
                text=True
            )
            if resultado.returncode == 0 and "mediamtx.exe" in resultado.stdout:
                return True, None
        else:
            # Linux: usar pgrep
            resultado = subprocess.run(
                ["pgrep", "-f", "mediamtx"],
                capture_output=True,
                text=True
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                pids = resultado.stdout.strip().splitlines()
                if pids:
                    return True, None
    except Exception:
        pass
    
    # También verificar si el puerto está en uso (indicador de que MediaMTX está corriendo)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(('127.0.0.1', 8000))
        sock.close()
        # Si el puerto está en uso, probablemente MediaMTX está corriendo
        if result == 0:
            return True, None
    except Exception:
        pass
    
    return False, None


def iniciar_mediamtx():
    """Inicia el servidor MediaMTX.
    
    Si MediaMTX ya está corriendo, no hace nada y retorna None.
    
    Returns:
        subprocess.Popen: Proceso de MediaMTX, o None si ya estaba corriendo
        
    Raises:
        FileNotFoundError: Si no se encuentra el binario de MediaMTX
        RuntimeError: Si MediaMTX termina inesperadamente
    """
    # Verificar primero si ya está corriendo
    ya_corriendo, proceso_existente = mediamtx_ya_corriendo()
    if ya_corriendo:
        print("[INFO] MediaMTX ya está corriendo, reutilizando proceso existente.")
        return proceso_existente  # Será None, pero indica que ya está activo
    
    if not config.MEDIAMTX_BIN.exists():
        raise FileNotFoundError(f"No se encontró {config.MEDIAMTX_BIN}")

    cmd = [str(config.MEDIAMTX_BIN)]
    if config.MEDIAMTX_CFG.exists():
        cmd.append(str(config.MEDIAMTX_CFG))

    print(f"[INFO] Iniciando MediaMTX: {' '.join(cmd)}")
    proceso = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    time.sleep(1.5)
    if proceso.poll() is not None:
        salida = proceso.stdout.read()
        # Verificar si el error es porque el puerto está en uso (MediaMTX ya corriendo)
        if "bind" in salida.lower() or "address already in use" in salida.lower() or "Only one usage" in salida:
            print("[INFO] MediaMTX no pudo iniciar porque el puerto está en uso (probablemente ya está corriendo)")
            # Verificar nuevamente si está corriendo
            ya_corriendo, _ = mediamtx_ya_corriendo()
            if ya_corriendo:
                print("[INFO] MediaMTX confirmado como activo, reutilizando proceso existente")
                return None  # Retornar None indica que ya está corriendo
            else:
                # El puerto está ocupado por otra aplicación
                raise RuntimeError(f"Puerto ocupado por otra aplicación. MediaMTX no pudo iniciar:\n{salida}")
        else:
            raise RuntimeError(f"MediaMTX terminó inesperadamente:\n{salida}")
    return proceso


def detener_mediamtx(proceso):
    """Detiene el servidor MediaMTX de forma segura.
    
    Args:
        proceso: Proceso de MediaMTX a detener
    """
    if proceso and proceso.poll() is None:
        print("[INFO] Deteniendo MediaMTX…")
        import sys
        if sys.platform == "win32":
            # Windows no soporta SIGINT, usar terminate()
            proceso.terminate()
        else:
            # Linux: usar SIGINT para cierre limpio
            proceso.send_signal(signal.SIGINT)
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            print("[WARN] MediaMTX forzado con kill().")

