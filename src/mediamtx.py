"""Módulo para gestión del servidor MediaMTX."""

import signal
import subprocess
import time
import os
from . import config


def verificar_puerto_rtmp():
    """Verifica si el puerto RTMP (1935) está escuchando.
    
    Returns:
        bool: True si el puerto 1935 está escuchando, False en caso contrario
    """
    try:
        import socket
        # Intentar conectar al puerto RTMP (TCP)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex(('127.0.0.1', 1935))
        sock.close()
        # Si result == 0, el puerto está escuchando
        return result == 0
    except Exception:
        return False


def mediamtx_ya_corriendo():
    """Verifica si MediaMTX ya está corriendo y funcionando correctamente.
    
    Returns:
        tuple: (bool, proceso_existente) 
            - bool: True si MediaMTX está corriendo Y el puerto RTMP está disponible
            - proceso_existente: subprocess.Popen del proceso existente o None
    """
    import sys
    
    proceso_encontrado = False
    
    try:
        if sys.platform == "win32":
            # Windows: usar tasklist para buscar proceso
            resultado = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq mediamtx.exe"],
                capture_output=True,
                text=True
            )
            if resultado.returncode == 0 and "mediamtx.exe" in resultado.stdout:
                proceso_encontrado = True
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
                    proceso_encontrado = True
    except Exception:
        pass
    
    # Si hay un proceso, verificar que el puerto RTMP esté realmente escuchando
    if proceso_encontrado:
        if verificar_puerto_rtmp():
            return True, None
        else:
            # Hay un proceso pero el puerto no está disponible - proceso zombie o mal configurado
            print("[WARN] Proceso MediaMTX encontrado pero puerto RTMP (1935) no está escuchando")
            print("[INFO] Intentando detener proceso MediaMTX existente...")
            # Intentar matar el proceso
            try:
                if sys.platform != "win32":
                    resultado = subprocess.run(
                        ["pkill", "-f", "mediamtx"],
                        capture_output=True,
                        text=True
                    )
                    time.sleep(1.0)
                    print("[INFO] Proceso MediaMTX detenido, se reiniciará")
            except Exception as exc:
                print(f"[WARN] No se pudo detener proceso MediaMTX: {exc}")
            return False, None
    
    return False, None


def iniciar_mediamtx():
    """Inicia el servidor MediaMTX.
    
    Si MediaMTX ya está corriendo y funcionando correctamente, no hace nada y retorna None.
    
    Returns:
        subprocess.Popen: Proceso de MediaMTX, o None si ya estaba corriendo
        
    Raises:
        FileNotFoundError: Si no se encuentra el binario de MediaMTX
        RuntimeError: Si MediaMTX termina inesperadamente
    """
    # Verificar primero si ya está corriendo Y funcionando
    ya_corriendo, proceso_existente = mediamtx_ya_corriendo()
    if ya_corriendo:
        print("[INFO] MediaMTX ya está corriendo y el puerto RTMP (1935) está disponible.")
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
    
    # Esperar a que MediaMTX inicie y verificar que el puerto esté disponible
    max_espera = 5  # Intentar hasta 5 segundos
    for i in range(max_espera):
        time.sleep(1.0)
        if proceso.poll() is not None:
            # El proceso terminó, leer salida
            salida = proceso.stdout.read()
            # Verificar si el error es porque el puerto está en uso
            if "bind" in salida.lower() or "address already in use" in salida.lower() or "Only one usage" in salida:
                print("[WARN] MediaMTX no pudo iniciar porque el puerto está en uso")
                # Verificar nuevamente si está corriendo
                ya_corriendo, _ = mediamtx_ya_corriendo()
                if ya_corriendo:
                    print("[INFO] MediaMTX confirmado como activo, reutilizando proceso existente")
                    return None
                else:
                    raise RuntimeError(f"Puerto ocupado por otra aplicación. MediaMTX no pudo iniciar:\n{salida}")
            else:
                raise RuntimeError(f"MediaMTX terminó inesperadamente:\n{salida}")
        
        # Verificar si el puerto RTMP ya está disponible
        if verificar_puerto_rtmp():
            print("[OK] MediaMTX iniciado correctamente - puerto RTMP (1935) disponible")
            return proceso
    
    # Si llegamos aquí, el proceso está corriendo pero el puerto aún no está disponible
    # Verificar una vez más
    if verificar_puerto_rtmp():
        print("[OK] MediaMTX iniciado correctamente - puerto RTMP (1935) disponible")
        return proceso
    else:
        # El proceso está corriendo pero el puerto no está disponible después de esperar
        print("[WARN] MediaMTX iniciado pero puerto RTMP (1935) aún no está disponible")
        print("[INFO] Continuando... el puerto debería estar disponible pronto")
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

