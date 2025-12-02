# 🚀 Guía Completa para Transferir y Replicar el Proyecto en Orange Pi 5 Pro

## 📋 Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Transferencia desde GitHub](#transferencia-desde-github)
3. [Instalación en Orange Pi](#instalación-en-orange-pi)
4. [Configuración del Entorno](#configuración-del-entorno)
5. [Instalación de RKNN Runtime](#instalación-de-rknn-runtime)
6. [Instalación de MediaMTX](#instalación-de-mediamtx)
7. [Configuración del Modelo](#configuración-del-modelo)
8. [Configuración del Servicio Systemd](#configuración-del-servicio-systemd)
9. [Configuración de Permisos](#configuración-de-permisos)
10. [Verificación y Pruebas](#verificación-y-pruebas)
11. [Estructura del Proyecto](#estructura-del-proyecto)

---

## 📦 Requisitos Previos

### En tu PC (Windows):
- ✅ Git instalado ([Descargar Git](https://git-scm.com/))
- ✅ Cuenta de GitHub
- ✅ Código del proyecto listo para subir

### En la Orange Pi 5 Pro:
- ✅ Sistema operativo instalado (Ubuntu/Debian)
- ✅ Python 3.8 o superior
- ✅ Conexión a Internet (para clonar y descargar dependencias)
- ✅ Acceso SSH o acceso físico a la Orange Pi

---

## 🔄 Transferencia desde GitHub

### Paso 1: Subir el Proyecto a GitHub (desde tu PC)

```bash
# 1. Navegar a la carpeta del proyecto
cd "D:\Proyecto G-nesis\proyectos_propios\Detección_UAV\RTMP"

# 2. Inicializar Git (si no está inicializado)
git init

# 3. Verificar que .gitignore esté configurado correctamente
# (debe excluir: entorno/, __pycache__/, Videos_test/, etc.)

# 4. Agregar todos los archivos necesarios
git add .

# 5. Verificar qué se va a subir (IMPORTANTE: revisa que NO aparezcan carpetas grandes)
git status

# 6. Hacer commit inicial
git commit -m "Sistema completo: GUI desktop + PWA web con detección UAV"

# 7. Crear repositorio en GitHub (ve a github.com y crea uno nuevo)
#    - Nombre sugerido: "deteccion-uav-rtmp" o similar
#    - Puede ser privado o público

# 8. Conectar tu repositorio local con GitHub
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git

# 9. Subir código a GitHub
git push -u origin main
```

### Paso 2: Clonar el Proyecto en la Orange Pi

```bash
# 1. Conectarse a la Orange Pi por SSH
ssh orangepi@IP-DE-TU-ORANGE-PI

# 2. Navegar a la carpeta donde quieres el proyecto (recomendado: Desktop)
cd ~/Desktop

# 3. Clonar el repositorio
git clone https://github.com/TU-USUARIO/TU-REPO.git

# 4. Renombrar la carpeta si es necesario (opcional)
# mv TU-REPO deteccion-uav
cd deteccion-uav  # o el nombre que hayas elegido
```

---

## 🛠️ Instalación en Orange Pi

### Paso 1: Actualizar el Sistema

```bash
sudo apt update
sudo apt upgrade -y
```

### Paso 2: Instalar Dependencias del Sistema

```bash
# Herramientas básicas
sudo apt install -y git python3 python3-pip python3-venv

# Dependencias para OpenCV
sudo apt install -y libopencv-dev python3-opencv

# Dependencias para NetworkManager (hotspot)
sudo apt install -y network-manager

# Dependencias para compilación (por si acaso)
sudo apt install -y build-essential cmake
```

### Paso 3: Crear Entorno Virtual

```bash
# Navegar a la carpeta del proyecto
cd ~/Desktop/deteccion-uav  # o la ruta donde clonaste

# Crear entorno virtual
python3 -m venv entorno-produccion

# Activar entorno virtual
source entorno-produccion/bin/activate

# Verificar que esté activado (deberías ver "(entorno-produccion)" en el prompt)
```

### Paso 4: Instalar Dependencias de Python

```bash
# Asegúrate de que el entorno virtual esté activado
# (deberías ver "(entorno-produccion)" en el prompt)

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias desde requirements.txt
pip install -r requirements.txt
```

---

## 🔧 Configuración del Entorno

### Paso 1: Verificar Estructura del Proyecto

Asegúrate de que la estructura sea la siguiente:

```
deteccion-uav/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── detector.py
│   ├── hotspot.py
│   ├── mediamtx.py
│   └── video.py
├── gui/
│   ├── __init__.py
│   └── app.py
├── web/
│   ├── __init__.py
│   ├── backend.py
│   └── static/
│       ├── index.html
│       ├── style.css
│       ├── app.js
│       └── socket.io.min.js
├── main_gui.py
├── main_web.py
├── start_web.sh
├── drone-web.service
├── requirements.txt
└── .gitignore
```

---

## 🎯 Instalación de RKNN Runtime

**IMPORTANTE:** Para ejecutar modelos RKNN en la Orange Pi, necesitas instalar el **runtime** de RKNN, no el toolkit completo.

### Paso 1: Descargar RKNN-Toolkit-Lite2

El runtime se llama `rknn-toolkit-lite2` y viene en formato `.whl` (wheel).

```bash
# 1. Activar el entorno virtual
source entorno-produccion/bin/activate

# 2. Descargar el archivo .whl desde el repositorio oficial de Rockchip
#    Opción A: Descargar manualmente desde:
#    https://github.com/rockchip-linux/rknn-toolkit2/releases
#    
#    Busca el archivo: rknn_toolkit_lite2-X.X.X+XXXXXXXX-cp3X-cp3X-linux_aarch64.whl
#    (X.X.X es la versión, cp3X es la versión de Python, aarch64 es para ARM64)

# 3. Si lo descargaste manualmente, instálalo así:
pip install rknn_toolkit_lite2-X.X.X+XXXXXXXX-cp3X-cp3X-linux_aarch64.whl

#    Opción B: Si está disponible en PyPI (versiones más recientes):
pip install rknn-toolkit-lite2
```

### Paso 2: Verificar Instalación

```bash
# Probar que se puede importar
python3 -c "from rknnlite.api import RKNNLite; print('RKNN Runtime instalado correctamente')"
```

### Nota Importante sobre RKNN:

- **rknn-toolkit2**: Se usa para **exportar** modelos a formato RKNN (solo en PC con Linux/Windows)
- **rknn-toolkit-lite2**: Se usa para **ejecutar** modelos RKNN (runtime, en Orange Pi)
- Para este proyecto, **solo necesitas rknn-toolkit-lite2** en la Orange Pi
- El modelo ya debe estar convertido a `.rknn` antes de transferirlo

---

## 📡 Instalación de MediaMTX

MediaMTX es el servidor de streaming RTMP/RTSP.

### Paso 1: Descargar MediaMTX

```bash
# 1. Crear carpeta para MediaMTX
mkdir -p mediamtx
cd mediamtx

# 2. Descargar la versión para Linux ARM64
#    Ve a: https://github.com/bluenviron/mediamtx/releases
#    Descarga: mediamtx_vX.X.X_linux_arm64v8.tar.gz

# 3. Si tienes wget instalado:
wget https://github.com/bluenviron/mediamtx/releases/download/v1.5.0/mediamtx_v1.5.0_linux_arm64v8.tar.gz

# 4. Descomprimir
tar -xzf mediamtx_v1.5.0_linux_arm64v8.tar.gz

# 5. Hacer ejecutable
chmod +x mediamtx

# 6. Volver a la carpeta del proyecto
cd ..
```

### Paso 2: Configurar MediaMTX

```bash
# 1. Crear archivo de configuración básico
cat > mediamtx/mediamtx.yml << 'EOF'
# Configuración básica de MediaMTX
paths:
  all:
    source: publisher
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
  live:
    source: publisher
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
  dron:
    source: publisher
    sourceOnDemand: yes
    sourceOnDemandStartTimeout: 10s
    sourceOnDemandCloseAfter: 10s
EOF

# 2. Verificar que el archivo se creó
ls -la mediamtx/
```

---

## 🤖 Configuración del Modelo

### Paso 1: Transferir el Modelo RKNN

El modelo debe estar en formato RKNN y en una carpeta específica:

```bash
# 1. Crear carpeta para el modelo (si no existe)
mkdir -p Visdrone_yolo11n_rknn_model

# 2. Transferir el modelo desde tu PC o desde donde lo tengas
#    Opción A: Si está en GitHub (con Git LFS):
git lfs pull

#    Opción B: Si lo tienes en tu PC, usar SCP:
#    Desde tu PC (PowerShell):
#    scp -r "D:\ruta\al\modelo\Visdrone_yolo11n_rknn_model" orangepi@IP:/home/orangepi/Desktop/deteccion-uav/

#    Opción C: Si lo tienes en un pendrive:
#    Copiar desde el pendrive a la carpeta del proyecto
```

### Paso 2: Verificar Estructura del Modelo

El modelo debe tener esta estructura:

```
Visdrone_yolo11n_rknn_model/
├── Visdrone_yolo11n_rknn_model.rknn  # Archivo principal del modelo
└── metadata.yaml                      # Metadatos (opcional)
```

### Paso 3: Verificar que el Modelo Funciona

```bash
# Activar entorno virtual
source entorno-produccion/bin/activate

# Probar carga del modelo
python3 -c "
from ultralytics import YOLO
model = YOLO('Visdrone_yolo11n_rknn_model', task='detect')
print('Modelo cargado correctamente')
print('Clases disponibles:', model.names)
"
```

---

## ⚙️ Configuración del Servicio Systemd

Para que la aplicación web se inicie automáticamente al encender la Orange Pi:

### Paso 1: Crear Script de Inicio

```bash
# 1. Verificar que start_web.sh existe y tiene los permisos correctos
chmod +x start_web.sh

# 2. Verificar que las rutas en start_web.sh sean correctas
#    Editar si es necesario:
nano start_web.sh

#    Debe contener:
#    #!/bin/bash
#    cd /home/orangepi/Desktop/deteccion-uav  # Ajustar ruta si es necesario
#    source entorno-produccion/bin/activate
#    exec python main_web.py
```

### Paso 2: Instalar el Servicio Systemd

```bash
# 1. Copiar el archivo de servicio a systemd
sudo cp drone-web.service /etc/systemd/system/

# 2. Editar el archivo si las rutas son diferentes
sudo nano /etc/systemd/system/drone-web.service

#    Verificar que las rutas sean correctas:
#    - WorkingDirectory: /home/orangepi/Desktop/deteccion-uav
#    - ExecStart: /bin/bash /home/orangepi/Desktop/deteccion-uav/start_web.sh
#    - User: orangepi (o el usuario que uses)

# 3. Recargar systemd
sudo systemctl daemon-reload

# 4. Habilitar el servicio para que inicie al arrancar
sudo systemctl enable drone-web.service

# 5. Iniciar el servicio ahora (sin reiniciar)
sudo systemctl start drone-web.service

# 6. Verificar que está corriendo
sudo systemctl status drone-web.service
```

### Paso 3: Ver Logs del Servicio

```bash
# Ver logs en tiempo real
sudo journalctl -u drone-web.service -f

# Ver últimos 100 líneas
sudo journalctl -u drone-web.service -n 100 --no-pager
```

---

## 📡 Configuración del Hotspot WiFi

**IMPORTANTE:** Esta es una de las partes más críticas. El hotspot debe estar correctamente configurado antes de ejecutar la aplicación.

### Paso 1: Verificar Compatibilidad con Modo AP (Access Point)

Primero, verifica que tu adaptador WiFi soporte el modo Access Point:

```bash
# Verificar modos soportados por el adaptador WiFi
iw list | grep -A3 "Supported interface modes"

# Debe mostrar "* AP" en la lista. Si no aparece, el adaptador no soporta modo AP.

# Verificar el estado de los dispositivos de red
nmcli device status

# Debe mostrar "wlan0" (o similar) como dispositivo WiFi disponible
```

### Paso 2: Verificar que NetworkManager Está Instalado y Activo

```bash
# Verificar que NetworkManager está instalado
which nmcli

# Si no está instalado:
sudo apt install -y network-manager

# Verificar que el servicio está corriendo
sudo systemctl status NetworkManager

# Si no está activo, iniciarlo:
sudo systemctl start NetworkManager
sudo systemctl enable NetworkManager
```

### Paso 3: Eliminar Perfiles de Hotspot Previos (si existen)

Si ya intentaste crear un hotspot antes, elimínalo primero:

```bash
# Eliminar conexión previa (si existe)
nmcli connection delete RC-Hotspot 2>/dev/null || true

# Verificar que no quedan conexiones con ese nombre
nmcli connection show | grep RC-Hotspot
```

### Paso 4: Crear el Hotspot "RC-Hotspot"

Ahora crearemos el hotspot con la configuración correcta:

```bash
# 1. Crear la conexión de tipo Access Point
nmcli connection add type wifi ifname wlan0 mode ap \
  con-name RC-Hotspot ssid ORANGE-RC

# 2. Configurar la banda WiFi (2.4 GHz)
nmcli connection modify RC-Hotspot wifi.band bg

# 3. Configurar el canal (6 es un canal común, puedes usar 1-11)
nmcli connection modify RC-Hotspot 802-11-wireless.channel 6

# 4. Configurar seguridad WPA2-PSK (contraseña)
nmcli connection modify RC-Hotspot 802-11-wireless-security.key-mgmt wpa-psk

# 5. Establecer la contraseña (cambia "12345678" por la que quieras)
nmcli connection modify RC-Hotspot 802-11-wireless-security.psk 12345678

# 6. Configurar método de IP como "shared" (compartido - activa DHCP/NAT automático)
nmcli connection modify RC-Hotspot ipv4.method shared

# 7. Deshabilitar IPv6 (opcional, pero recomendado)
nmcli connection modify RC-Hotspot ipv6.method disabled
```

**Notas importantes:**
- El modo `shared` es crucial: activa automáticamente DHCP y NAT, permitiendo que los dispositivos conectados obtengan IP y accedan a Internet (si la Orange Pi tiene conexión).
- **NO intentes configurar `ipv4.dns` manualmente** cuando usas modo `shared`, NetworkManager lo gestiona automáticamente.
- El SSID `ORANGE-RC` es el nombre que verán los dispositivos. Puedes cambiarlo si quieres.
- La contraseña `12345678` es un ejemplo. **Cámbiala por una más segura** en producción.

### Paso 5: Activar el Hotspot

La secuencia correcta para activar el hotspot es importante:

```bash
# 1. Apagar la radio WiFi
nmcli radio wifi off

# 2. Esperar 2 segundos
sleep 2

# 3. Encender la radio WiFi
nmcli radio wifi on

# 4. Esperar 2 segundos más
sleep 2

# 5. Activar la conexión del hotspot
nmcli connection up RC-Hotspot
```

**Si tienes otras conexiones WiFi activas** (por ejemplo, conectado a otra red), bájalas primero:

```bash
# Ver conexiones activas
nmcli connection show --active

# Bajar una conexión específica (reemplaza "NOMBRE" con el nombre real)
nmcli connection down "NOMBRE-DE-LA-CONEXION"
```

### Paso 6: Verificar que el Hotspot Está Activo

```bash
# Verificar que la conexión está activa
nmcli connection show --active

# Debe mostrar "RC-Hotspot" en la lista

# Verificar el estado de los dispositivos
nmcli device status

# wlan0 debe mostrar "connected" o "connected (externally managed)"

# Obtener la IP asignada al hotspot
ip -4 addr show wlan0

# También puedes usar:
nmcli -t -f IP4.ADDRESS connection show RC-Hotspot
```

**La IP típica será:** `10.42.0.1/24` o similar. Esta es la IP a la que los dispositivos se conectarán.

### Paso 7: Probar la Conexión desde Otro Dispositivo

1. **Desde tu teléfono o PC:**
   - Busca la red WiFi llamada `ORANGE-RC` (o el SSID que configuraste)
   - Conéctate usando la contraseña que configuraste (`12345678` en el ejemplo)
   - Deberías obtener una IP automáticamente (típicamente `10.42.0.X`)

2. **Verificar desde la Orange Pi que hay dispositivos conectados:**
   ```bash
   # Ver clientes conectados (requiere hostapd-cli, opcional)
   # O simplemente verificar que puedes hacer ping desde el dispositivo conectado
   ```

### Paso 8: Configurar el SSID y Contraseña Personalizados (Opcional)

Si quieres cambiar el SSID o la contraseña después de crear el hotspot:

```bash
# Cambiar SSID
nmcli connection modify RC-Hotspot 802-11-wireless.ssid MI-NUEVO-SSID

# Cambiar contraseña
nmcli connection modify RC-Hotspot 802-11-wireless-security.psk MI-NUEVA-CONTRASEÑA

# Aplicar cambios (bajar y subir la conexión)
nmcli connection down RC-Hotspot
nmcli connection up RC-Hotspot
```

### Solución de Problemas del Hotspot

#### Error: "Device or resource busy"
```bash
# Bajar todas las conexiones WiFi primero
nmcli connection down --all
nmcli radio wifi off
sleep 2
nmcli radio wifi on
sleep 2
nmcli connection up RC-Hotspot
```

#### Error: "IP configuration could not be reserved"
```bash
# Esto a veces ocurre. Intenta:
nmcli connection down RC-Hotspot
nmcli radio wifi off
sleep 3
nmcli radio wifi on
sleep 3
nmcli connection up RC-Hotspot

# Si persiste, verifica que no hay conflictos de IP
ip addr show wlan0
```

#### El hotspot no aparece en otros dispositivos
```bash
# Verificar que está realmente activo
nmcli connection show --active | grep RC-Hotspot

# Verificar logs de NetworkManager
sudo journalctl -u NetworkManager -n 50 --no-pager

# Reiniciar NetworkManager (último recurso)
sudo systemctl restart NetworkManager
```

#### El hotspot se desactiva automáticamente
```bash
# Verificar que no hay políticas de ahorro de energía
nmcli radio wifi

# Deshabilitar ahorro de energía (si es necesario)
sudo nmcli radio wifi off
sudo nmcli radio wifi on
```

### Monitoreo de Logs en Tiempo Real

Para diagnosticar problemas, monitorea los logs de NetworkManager en otra terminal:

```bash
# Ver logs en tiempo real
sudo journalctl -u NetworkManager -f

# Ver últimos 100 logs
sudo journalctl -u NetworkManager -n 100 --no-pager
```

---

## 🔐 Configuración de Permisos

### Paso 1: Permisos para el Hotspot

El usuario necesita permisos para gestionar NetworkManager. Generalmente, el usuario ya tiene estos permisos, pero verifica:

```bash
# Verificar que el usuario esté en el grupo network (opcional)
groups

# Si no está, agregarlo (generalmente no es necesario)
sudo usermod -aG network orangepi

# Verificar que NetworkManager permite gestionar conexiones
nmcli connection show
```

### Paso 2: Permisos para Apagar el Sistema

Para que el botón de "Apagar Orange Pi" funcione:

```bash
# 1. Editar sudoers de forma segura
sudo visudo

# 2. Agregar al final del archivo (reemplaza 'orangepi' con tu usuario):
orangepi ALL=(ALL) NOPASSWD: /sbin/shutdown

# 3. Guardar y salir (Ctrl+O, Enter, Ctrl+X en nano)

# 4. Verificar que funciona (CUIDADO: esto apagará el sistema)
# sudo shutdown -h now
```

**⚠️ IMPORTANTE:** Solo agrega esta línea si realmente necesitas el botón de apagado. Es una configuración sensible de seguridad.

---

## ✅ Verificación y Pruebas

### Paso 1: Probar la Aplicación Desktop

```bash
# Activar entorno virtual
source entorno-produccion/bin/activate

# Ejecutar aplicación desktop
python main_gui.py
```

### Paso 2: Probar la Aplicación Web

```bash
# Activar entorno virtual
source entorno-produccion/bin/activate

# Ejecutar aplicación web
python main_web.py

# Deberías ver algo como:
# [INFO] Inicializando sistema...
# [OK] Hotspot activo - IP: 10.42.0.1
# [OK] MediaMTX iniciado
# [OK] Modelo cargado
# * Running on http://127.0.0.1:5000
# * Running on http://10.42.0.1:5000
```

### Paso 3: Acceder desde el Navegador

1. **Desde la Orange Pi (local):**
   - Abre el navegador y ve a: `http://127.0.0.1:5000`

2. **Desde otro dispositivo (en la misma red del hotspot):**
   - Conéctate al hotspot: `RC-Hotspot` (o el nombre configurado)
   - Abre el navegador y ve a: `http://10.42.0.1:5000`

### Paso 4: Probar Transmisión RTMP

Desde tu PC o dispositivo que transmite:

```bash
# Ejemplo con ffmpeg
ffmpeg -re -i video.mp4 -c:v libx264 -preset fast -c:a aac -f flv rtmp://10.42.0.1:1935/live/dron
```

---

## 📁 Estructura del Proyecto

```
deteccion-uav/
├── src/                          # Módulos principales
│   ├── __init__.py
│   ├── config.py                 # Configuraciones generales
│   ├── detector.py               # Detección YOLO
│   ├── hotspot.py                # Gestión de hotspot
│   ├── mediamtx.py               # Gestión de MediaMTX
│   └── video.py                  # Captura de video RTMP
│
├── gui/                          # Aplicación desktop
│   ├── __init__.py
│   └── app.py                    # GUI con CustomTkinter
│
├── web/                          # Aplicación web (PWA)
│   ├── __init__.py
│   ├── backend.py                # Servidor Flask + SocketIO
│   └── static/                   # Frontend
│       ├── index.html            # Interfaz web
│       ├── style.css             # Estilos
│       ├── app.js                # Lógica JavaScript
│       └── socket.io.min.js      # Socket.IO cliente
│
├── main_gui.py                   # Punto de entrada GUI
├── main_web.py                   # Punto de entrada web
├── start_web.sh                  # Script de inicio para systemd
├── drone-web.service             # Configuración systemd
├── requirements.txt               # Dependencias Python
│
├── mediamtx/                     # Servidor de streaming (NO en GitHub)
│   ├── mediamtx                  # Ejecutable
│   └── mediamtx.yml              # Configuración
│
├── Visdrone_yolo11n_rknn_model/  # Modelo RKNN (NO en GitHub)
│   ├── Visdrone_yolo11n_rknn_model.rknn
│   └── metadata.yaml
│
└── entorno-produccion/           # Entorno virtual (NO en GitHub)
```

---

## 🔄 Actualizar el Proyecto (después de cambios)

### Desde tu PC:

```bash
# 1. Hacer cambios en el código
# 2. Agregar cambios
git add .

# 3. Hacer commit
git commit -m "Descripción de los cambios"

# 4. Subir a GitHub
git push
```

### En la Orange Pi:

```bash
# 1. Navegar a la carpeta del proyecto
cd ~/Desktop/deteccion-uav

# 2. Detener el servicio (si está corriendo)
sudo systemctl stop drone-web.service

# 3. Actualizar desde GitHub
git pull

# 4. Si hay cambios en requirements.txt, actualizar dependencias
source entorno-produccion/bin/activate
pip install -r requirements.txt

# 5. Reiniciar el servicio
sudo systemctl start drone-web.service

# 6. Verificar que funciona
sudo systemctl status drone-web.service
```

---

## 🐛 Solución de Problemas Comunes

### Error: "Modelo no encontrado"
- Verifica que la carpeta `Visdrone_yolo11n_rknn_model/` existe
- Verifica que contiene el archivo `.rknn`
- Verifica la ruta en `src/config.py`

### Error: "RKNN Runtime no disponible"
- Verifica que `rknn-toolkit-lite2` esté instalado: `pip list | grep rknn`
- Verifica que estés usando Python 3.8 o superior
- Reinstala: `pip install --force-reinstall rknn-toolkit-lite2`

### Error: "MediaMTX no inicia"
- Verifica que el ejecutable existe: `ls -la mediamtx/mediamtx`
- Verifica permisos: `chmod +x mediamtx/mediamtx`
- Verifica que el puerto 1935 no esté ocupado: `sudo netstat -tulpn | grep 1935`

### Error: "Hotspot no se activa"
- Verifica que NetworkManager esté instalado: `sudo systemctl status NetworkManager`
- Verifica permisos del usuario
- Verifica que la interfaz WiFi sea `wlan0`: `ip link show`

### Error: "Servicio no inicia"
- Verifica logs: `sudo journalctl -u drone-web.service -n 50`
- Verifica rutas en `drone-web.service`
- Verifica que `start_web.sh` tenga permisos de ejecución: `chmod +x start_web.sh`

---

## 📝 Notas Finales

### Archivos que NO están en GitHub:
- `entorno-produccion/` - Entorno virtual (se crea en cada máquina)
- `mediamtx/` - Servidor de streaming (se descarga por separado)
- `Visdrone_yolo11n_rknn_model/` - Modelo RKNN (se transfiere por separado)
- `__pycache__/` - Archivos compilados de Python
- `Videos_test/` - Videos de prueba

### Archivos que SÍ están en GitHub:
- ✅ Todo el código fuente (`src/`, `gui/`, `web/`)
- ✅ `requirements.txt`
- ✅ `main_gui.py`, `main_web.py`
- ✅ `start_web.sh`, `drone-web.service`
- ✅ `.gitignore`
- ✅ Documentación

### Recomendaciones:
1. **Siempre usa un entorno virtual** para aislar dependencias
2. **Mantén el modelo RKNN fuera de GitHub** (es muy pesado)
3. **Usa Git LFS** si necesitas subir archivos grandes
4. **Documenta cualquier cambio** en el código
5. **Prueba en desarrollo antes de subir** a producción

---

## 🎯 Resumen Rápido

Para replicar en una nueva Orange Pi:

```bash
# 1. Clonar repositorio
git clone https://github.com/TU-USUARIO/TU-REPO.git
cd TU-REPO

# 2. Instalar dependencias del sistema
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv network-manager

# 3. Crear entorno virtual
python3 -m venv entorno-produccion
source entorno-produccion/bin/activate

# 4. Instalar dependencias Python
pip install --upgrade pip
pip install -r requirements.txt
pip install rknn-toolkit-lite2-X.X.X+XXXXXXXX-cp3X-cp3X-linux_aarch64.whl

# 5. Instalar MediaMTX (descargar y descomprimir en mediamtx/)

# 6. Transferir modelo RKNN (copiar Visdrone_yolo11n_rknn_model/)

# 7. Configurar hotspot WiFi (IMPORTANTE - hacer antes de ejecutar)
nmcli connection add type wifi ifname wlan0 mode ap con-name RC-Hotspot ssid ORANGE-RC
nmcli connection modify RC-Hotspot wifi.band bg
nmcli connection modify RC-Hotspot 802-11-wireless.channel 6
nmcli connection modify RC-Hotspot 802-11-wireless-security.key-mgmt wpa-psk
nmcli connection modify RC-Hotspot 802-11-wireless-security.psk 12345678
nmcli connection modify RC-Hotspot ipv4.method shared
nmcli connection modify RC-Hotspot ipv6.method disabled

# 8. Configurar servicio systemd
sudo cp drone-web.service /etc/systemd/system/
# Editar rutas en /etc/systemd/system/drone-web.service si es necesario
sudo systemctl daemon-reload
sudo systemctl enable drone-web.service
sudo systemctl start drone-web.service

# 9. Configurar permisos de apagado (opcional)
sudo visudo  # Agregar: orangepi ALL=(ALL) NOPASSWD: /sbin/shutdown

# 10. Verificar que todo funciona
sudo systemctl status drone-web.service
nmcli connection show --active  # Debe mostrar RC-Hotspot cuando se active

# 11. ¡Listo! Acceder a http://10.42.0.1:5000 (o la IP que muestre el hotspot)
```

---

**¡Éxito! 🎉** Tu sistema de detección UAV está listo para funcionar en la Orange Pi 5 Pro.
