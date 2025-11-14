"""Módulo para gestión del servidor MediaMTX."""

import signal
import subprocess
import time
from . import config


def iniciar_mediamtx():
    """Inicia el servidor MediaMTX.
    
    Returns:
        subprocess.Popen: Proceso de MediaMTX
        
    Raises:
        FileNotFoundError: Si no se encuentra el binario de MediaMTX
        RuntimeError: Si MediaMTX termina inesperadamente
    """
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
        raise RuntimeError(f"MediaMTX terminó inesperadamente:\n{salida}")
    return proceso


def detener_mediamtx(proceso):
    """Detiene el servidor MediaMTX de forma segura.
    
    Args:
        proceso: Proceso de MediaMTX a detener
    """
    if proceso and proceso.poll() is None:
        print("[INFO] Deteniendo MediaMTX…")
        proceso.send_signal(signal.SIGINT)
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()
            print("[WARN] MediaMTX forzado con kill().")

