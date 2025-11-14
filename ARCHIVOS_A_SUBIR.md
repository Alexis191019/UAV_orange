# 📦 Archivos a Subir a GitHub

## ✅ Archivos que SÍ debes subir:

```
RTMP/
├── src/                    # ✅ Toda la carpeta
│   ├── __init__.py
│   ├── config.py
│   ├── utils.py
│   ├── hotspot.py
│   ├── mediamtx.py
│   ├── video.py
│   └── detector.py
│
├── gui/                   # ✅ Toda la carpeta
│   ├── __init__.py
│   └── app.py
│
├── main_gui.py            # ✅ Punto de entrada
├── requirements.txt       # ✅ Dependencias
├── .gitignore            # ✅ Configuración Git
├── README_ESTRUCTURA.md   # ✅ Documentación
└── GUIA_TRANSFERENCIA.md  # ✅ Guía (opcional)
```

## ❌ Archivos que NO debes subir (ya están en .gitignore):

- `mediaMTX/` - Servidor de streaming (se instala por separado)
- `models/` - Modelos YOLO (muy pesados)
- `Videos_test/` - Videos de prueba
- `entorno/` - Entorno virtual
- `main_all.py` - Versión antigua
- `main.py` - Versión antigua
- `manual_inference.py` - Scripts antiguos
- `inference_test.py` - Scripts antiguos
- `docs/` - Documentación antigua
- `crear_hotspot.txt` - Archivo antiguo

## 🚀 Comandos para subir solo lo necesario:

```bash
# 1. Inicializar Git (si no lo has hecho)
git init

# 2. Agregar solo los archivos nuevos
git add src/
git add gui/
git add main_gui.py
git add requirements.txt
git add .gitignore
git add README_ESTRUCTURA.md
git add GUIA_TRANSFERENCIA.md
git add ARCHIVOS_A_SUBIR.md

# 3. Verificar qué se va a subir (revisa que NO aparezcan mediaMTX, models, etc.)
git status

# 4. Hacer commit
git commit -m "Estructura reorganizada: GUI con CustomTkinter"

# 5. Conectar con GitHub y subir
git remote add origin https://github.com/TU-USUARIO/TU-REPO.git
git push -u origin main
```

## 📝 Nota Importante:

Los archivos `mediaMTX/` y `models/` NO se suben porque:
- Son muy pesados (GitHub tiene límites)
- Se instalan/configuran por separado en cada máquina
- No son código fuente, son recursos/binarios

En la Orange Pi tendrás que:
1. Clonar el repositorio
2. Copiar manualmente `mediaMTX/` y `models/` (o instalarlos por separado)
3. Instalar dependencias: `pip install -r requirements.txt`
4. Ejecutar: `python main_gui.py`

