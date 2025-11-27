#!/bin/bash
cd /home/orangepi/Desktop/proyectos_cv/drone2/produccion

# Activar entorno virtual
source entorno-produccion/bin/activate

# Lanzar la app web
exec python main_web.py

