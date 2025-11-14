# 🚀 Guía para Transferir el Proyecto a Orange Pi

## Opción 1: GitHub (⭐ RECOMENDADO)

### Ventajas:
- ✅ Versionado automático
- ✅ Fácil de actualizar (solo `git pull`)
- ✅ Respaldo en la nube
- ✅ Puedes trabajar desde cualquier PC

### Pasos:

#### 1. En tu PC Windows:

```bash
# Si no tienes Git instalado, descárgalo de: https://git-scm.com/

# Inicializar repositorio
git init

# Agregar todos los archivos
git add .

# Hacer commit inicial
git commit -m "Primera versión: Sistema de detección UAV con GUI"

# Crear repositorio en GitHub (ve a github.com y crea uno nuevo)
# Luego conecta tu repositorio local:
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git

# Subir código
git push -u origin main
```

#### 2. En la Orange Pi:

```bash
# Instalar Git (si no lo tienes)
sudo apt update
sudo apt install git -y

# Clonar el repositorio
git clone https://github.com/TU-USUARIO/TU-REPO.git
cd TU-REPO

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main_gui.py
```

#### 3. Para actualizar después de hacer cambios:

```bash
# En tu PC:
git add .
git commit -m "Descripción de cambios"
git push

# En Orange Pi:
git pull
```

---

## Opción 2: SCP (Transferencia Directa)

### Ventajas:
- ✅ Rápido y directo
- ✅ No requiere GitHub
- ✅ Funciona con cualquier carpeta

### Pasos:

#### Desde Windows PowerShell:

```powershell
# Instalar OpenSSH si no lo tienes (Windows 10/11 ya lo incluye)

# Transferir carpeta completa
scp -r "D:\Proyecto G-nesis\proyectos_propios\Detección_UAV\RTMP" usuario@IP-ORANGE-PI:/home/usuario/

# Ejemplo:
# scp -r "D:\Proyecto G-nesis\proyectos_propios\Detección_UAV\RTMP" pi@192.168.1.100:/home/pi/
```

#### En la Orange Pi:

```bash
# Ya tendrás los archivos en /home/usuario/RTMP
cd RTMP
pip install -r requirements.txt
python main_gui.py
```

---

## Opción 3: Pendrive/USB

### Ventajas:
- ✅ No requiere conexión de red
- ✅ Muy simple

### Pasos:

1. Copia la carpeta `RTMP` completa` a un pendrive
2. Conecta el pendrive a la Orange Pi
3. Copia la carpeta desde el pendrive a la Orange Pi:

```bash
# Montar pendrive (generalmente en /media/usuario/)
# Copiar carpeta
cp -r /media/usuario/PENDRIVE/RTMP ~/RTMP
cd ~/RTMP
pip install -r requirements.txt
python main_gui.py
```

---

## Opción 4: WinSCP (Interfaz Gráfica)

### Ventajas:
- ✅ Interfaz visual (arrastrar y soltar)
- ✅ Fácil de usar

### Pasos:

1. Descarga WinSCP: https://winscp.net/
2. Conéctate a tu Orange Pi (usuario, IP, contraseña)
3. Arrastra la carpeta `RTMP` desde tu PC a la Orange Pi
4. En la Orange Pi, instala dependencias y ejecuta

---

## ⚠️ Notas Importantes

### Archivos que NO se suben a GitHub (por .gitignore):
- `entorno/` (entorno virtual)
- `__pycache__/` (archivos compilados)
- `Videos_test/*.mp4` (videos de prueba)
- Archivos temporales

### Archivos que SÍ necesitas en Orange Pi:
- ✅ Todo el código (`src/`, `gui/`, `main_gui.py`)
- ✅ `requirements.txt`
- ✅ `mediaMTX/` (servidor de streaming)
- ✅ `models/` (modelos YOLO)
- ✅ `README_ESTRUCTURA.md`

### Si usas GitHub:
Los modelos grandes (`.pt`, `.rknn`) pueden ser pesados. Opciones:
1. **Subirlos a GitHub** (si son < 100MB)
2. **Usar Git LFS** para archivos grandes
3. **Transferirlos por separado** con SCP

---

## 🎯 Recomendación Final

**Usa GitHub** porque:
- Es la forma más profesional
- Fácil de mantener actualizado
- Tienes respaldo automático
- Puedes trabajar desde cualquier PC

Si no quieres usar GitHub, **SCP es la segunda mejor opción** (rápida y directa).

