"""Funciones utilitarias generales."""

import subprocess


def ejecutar(cmd, descripcion):
    """Ejecuta un comando del sistema y retorna su salida.
    
    Args:
        cmd: Lista con el comando y sus argumentos
        descripcion: Descripción del comando para mensajes de error
        
    Returns:
        str: Salida estándar del comando
        
    Raises:
        RuntimeError: Si el comando falla
    """
    print(f"[INFO] {descripcion}: {' '.join(cmd)}", flush=True)
    proceso = subprocess.run(cmd, capture_output=True, text=True)
    if proceso.returncode != 0:
        raise RuntimeError(
            f"Falló {descripcion} (código {proceso.returncode})\n"
            f"STDOUT:\n{proceso.stdout}\nSTDERR:\n{proceso.stderr}"
        )
    return proceso.stdout.strip()

