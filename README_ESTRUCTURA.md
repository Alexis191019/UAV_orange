# Estructura del Proyecto - Detección UAV

## 📁 Organización del Código

El proyecto está organizado de forma modular separando la **lógica de negocio** de la **interfaz gráfica**.

```
RTMP/
├── src/                    # Lógica de negocio (backend)
│   ├── __init__.py
│   ├── config.py          # Configuraciones (rutas, constantes)
│   ├── utils.py           # Funciones utilitarias generales
│   ├── hotspot.py         # Gestión del hotspot WiFi
│   ├── mediamtx.py        # Gestión del servidor MediaMTX
│   ├── video.py           # Gestión de video/stream RTMP
│   └── detector.py        # Lógica de detección YOLO
│
├── gui/                   # Interfaz gráfica (frontend)
│   ├── __init__.py
│   └── app.py             # Aplicación CustomTkinter
│
├── main_gui.py            # Punto de entrada principal
├── main_all.py            # Versión original (sin GUI)
└── requirements.txt       # Dependencias del proyecto
```

## 🎯 Ventajas de esta Estructura

### ✅ Separación de Responsabilidades
- **`src/`**: Contiene toda la lógica de negocio
- **`gui/`**: Contiene solo la interfaz gráfica
- **`main_gui.py`**: Solo importa y ejecuta la GUI

### ✅ Reutilización de Código
- Las funciones en `src/` pueden usarse desde:
  - La GUI (`gui/app.py`)
  - Scripts de línea de comandos
  - Tests automatizados
  - Otras interfaces (web, API, etc.)

### ✅ Mantenibilidad
- Cada módulo tiene una responsabilidad clara
- Fácil de encontrar y modificar código
- Cambios en la GUI no afectan la lógica

### ✅ Escalabilidad
- Fácil agregar nuevas funcionalidades
- Puedes crear múltiples interfaces (GUI, CLI, web)
- Código más fácil de testear

## 📝 Descripción de Módulos

### `src/config.py`
- Todas las configuraciones centralizadas
- Rutas, constantes, parámetros del modelo
- **Cambia aquí** para ajustar el comportamiento

### `src/utils.py`
- Funciones utilitarias compartidas
- Ejecución de comandos del sistema

### `src/hotspot.py`
- Gestión completa del hotspot WiFi
- Funciones: `levantar_hotspot()`, `bajar_hotspot()`, `conexion_hotspot_activa()`

### `src/mediamtx.py`
- Gestión del servidor MediaMTX
- Funciones: `iniciar_mediamtx()`, `detener_mediamtx()`

### `src/video.py`
- Gestión de video y streaming RTMP
- Funciones: `abrir_stream()`, `lector_frames()`, `crear_writer()`

### `src/detector.py`
- Clase `DetectorYOLO` para detección de objetos
- Encapsula toda la lógica de YOLO

### `gui/app.py`
- Clase `DeteccionUAVApp` (hereda de `ctk.CTk`)
- Interfaz gráfica completa
- Usa los módulos de `src/` para la lógica

## 🚀 Cómo Usar

### Ejecutar la aplicación GUI:
```bash
python main_gui.py
```

### Usar módulos individuales:
```python
from src.hotspot import levantar_hotspot
from src.detector import DetectorYOLO

# Usar las funciones directamente
levantar_hotspot()
detector = DetectorYOLO()
```

## 🔄 Migración desde `main_all.py`

Si necesitas usar código de `main_all.py`:
- Las funciones ya están en `src/`
- La GUI está en `gui/app.py`
- Todo funciona igual, solo está mejor organizado

## 📚 Próximos Pasos Sugeridos

1. **Tests**: Crear carpeta `tests/` para probar cada módulo
2. **Logging**: Agregar sistema de logging profesional
3. **Configuración**: Mover configuraciones a archivo YAML/JSON
4. **CLI**: Crear versión de línea de comandos usando `src/`

