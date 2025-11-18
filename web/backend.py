"""Servidor Flask para PWA de detección UAV."""

import threading
import queue
import time
import cv2
import base64
import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import sys

from src import config
from src.hotspot import levantar_hotspot, bajar_hotspot, conexion_hotspot_activa, obtener_ip_hotspot
from src.mediamtx import iniciar_mediamtx, detener_mediamtx
from src.video import abrir_stream, lector_frames
from src.detector import DetectorYOLO

# Obtener ruta absoluta del directorio web
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')
CORS(app)  # Permitir CORS para acceso desde cualquier origen
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado global
detector = None
cap = None
writer = None
lector_thread = None
mediamtx_proc = None
stop_event = threading.Event()
frame_queue = queue.Queue(maxsize=1)
inferir = False
fps_hist = []
frame_count = 0


def inicializar_sistema():
    """Inicializa el sistema: hotspot, MediaMTX, modelo y stream."""
    global detector, cap, mediamtx_proc
    
    try:
        print("[INFO] Inicializando sistema...")
        
        # Levantar hotspot (solo en Linux, no en Windows)
        if sys.platform != "win32":
            print("[INFO] Configurando hotspot...")
            levantar_hotspot()
            ip_hotspot = obtener_ip_hotspot()
            if ip_hotspot:
                print(f"[OK] Hotspot activo - IP: {ip_hotspot}")
            else:
                print("[WARN] No se pudo obtener IP del hotspot")
        else:
            print("[INFO] Hotspot no disponible en Windows, omitiendo...")
        
        # Iniciar MediaMTX
        print("[INFO] Iniciando MediaMTX...")
        try:
            mediamtx_proc = iniciar_mediamtx()
            if mediamtx_proc:
                print("[OK] MediaMTX iniciado")
            else:
                print("[INFO] MediaMTX ya estaba corriendo, reutilizando proceso existente")
        except RuntimeError as exc:
            # Si el error es porque ya está corriendo, continuar
            error_msg = str(exc).lower()
            if "puerto ocupado" in error_msg or "bind" in error_msg or "already in use" in error_msg:
                print("[INFO] MediaMTX no pudo iniciar (puerto ocupado), pero continuando...")
                mediamtx_proc = None
            else:
                # Otro tipo de error, relanzar
                raise
        
        # Cargar modelo (solo si existe, en Windows puede no estar)
        print("[INFO] Cargando modelo YOLO...")
        try:
            detector = DetectorYOLO()
            print("[OK] Modelo cargado")
        except FileNotFoundError as exc:
            print(f"[WARN] Modelo no encontrado: {exc}")
            print("[INFO] El servidor funcionará en modo demo (sin inferencia)")
            detector = None  # Continuar sin modelo
        except Exception as exc:
            print(f"[ERROR] Error al cargar modelo: {exc}")
            print("[INFO] El servidor funcionará en modo demo (sin inferencia)")
            detector = None  # Continuar sin modelo
        
        # Abrir stream (con timeout para no bloquear)
        print("[INFO] Conectando a stream RTMP...")
        # Intentar conectar con timeout
        cap = None
        max_intentos = 3  # Solo intentar 3 veces antes de continuar
        for intento in range(max_intentos):
            try:
                cap = cv2.VideoCapture(config.RTMP_URL)
                if cap.isOpened():
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    print("[OK] Stream RTMP conectado")
                    # Iniciar hilo lector solo si hay stream
                    global lector_thread
                    lector_thread = threading.Thread(
                        target=lector_frames,
                        args=(cap, frame_queue, stop_event),
                        daemon=True
                    )
                    lector_thread.start()
                    break
                else:
                    cap.release()
                    cap = None
            except Exception as exc:
                print(f"[WARN] Error al conectar RTMP (intento {intento + 1}): {exc}")
            
            if intento < max_intentos - 1:
                time.sleep(2)  # Esperar 2 segundos entre intentos
        
        if cap is None:
            print("[WARN] No se pudo conectar al stream RTMP después de varios intentos")
            print("[INFO] El servidor web funcionará, pero no habrá video hasta que se conecte el stream")
            print("[INFO] Puedes conectar el stream más tarde y se detectará automáticamente")
        
        print("[OK] Sistema inicializado correctamente")
        
    except Exception as exc:
        print(f"[ERROR] Error en inicialización: {exc}")
        import traceback
        traceback.print_exc()
        raise


def process_and_stream():
    """Hilo que procesa frames y los envía a los clientes vía WebSocket."""
    global inferir, detector, frame_count, fps_hist, cap
    
    while not stop_event.is_set():
        try:
            # Si no hay stream, esperar un poco y continuar
            if cap is None:
                time.sleep(1.0)
                # Enviar mensaje de "sin stream" a los clientes
                socketio.emit('frame', {
                    'frame': None,
                    'detecciones': {},
                    'fps': 0,
                    'fps_prom': 0,
                    'frames': frame_count,
                    'error': 'Stream RTMP no disponible'
                })
                continue
            
            frame = frame_queue.get(timeout=0.1)
            
            if inferir and detector is not None:
                annotated, elapsed, clases_detectadas = detector.detectar(frame)
                fps_actual = 1.0 / elapsed if elapsed > 0 else 0.0
                fps_hist.append(fps_actual)
                if len(fps_hist) > 30:
                    fps_hist.pop(0)
                fps_prom = sum(fps_hist) / len(fps_hist) if fps_hist else 0.0
            else:
                annotated = frame
                clases_detectadas = {}
                fps_actual = 0.0
                fps_prom = 0.0
            
            frame_count += 1
            
            # Redimensionar para reducir tamaño de transmisión
            display_size = (640, 480)
            if annotated.shape[:2] != display_size:
                annotated = cv2.resize(annotated, display_size)
            
            # Codificar frame a JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]  # 75% calidad
            _, buffer = cv2.imencode('.jpg', annotated, encode_params)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Enviar a todos los clientes conectados
            socketio.emit('frame', {
                'frame': frame_base64,
                'detecciones': clases_detectadas,
                'fps': round(fps_actual, 1),
                'fps_prom': round(fps_prom, 1),
                'frames': frame_count
            })
            
        except queue.Empty:
            continue
        except Exception as exc:
            print(f"[WARN] Error en procesamiento de frame: {exc}")
            time.sleep(0.1)


# Rutas API REST
@app.route('/')
def index():
    """Sirve la página principal."""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/inference/start', methods=['POST'])
def start_inference():
    """Inicia la inferencia."""
    global inferir
    if detector is None:
        return jsonify({
            "error": "Modelo no cargado",
            "message": "El modelo YOLO no está disponible. Modo demo activo."
        }), 400
    inferir = True
    print("[INFO] Inferencia iniciada desde cliente web")
    return jsonify({"status": "started", "message": "Inferencia iniciada"})


@app.route('/api/inference/stop', methods=['POST'])
def stop_inference():
    """Detiene la inferencia."""
    global inferir
    inferir = False
    print("[INFO] Inferencia detenida desde cliente web")
    return jsonify({"status": "stopped", "message": "Inferencia detenida"})


@app.route('/api/status', methods=['GET'])
def get_status():
    """Obtiene el estado del sistema."""
    ip_hotspot = obtener_ip_hotspot()
    hotspot_activo = conexion_hotspot_activa()
    
    return jsonify({
        "inference": inferir,
        "model_loaded": detector is not None,
        "stream_connected": cap is not None and cap.isOpened() if cap else False,
        "hotspot_active": hotspot_activo,
        "hotspot_ip": ip_hotspot,
        "hotspot_name": config.HOTSPOT_NAME if hotspot_activo else None,
        "rtmp_url": f"rtmp://{ip_hotspot}:1935/live/dron" if ip_hotspot else None,
        "fps_actual": round(fps_hist[-1], 1) if fps_hist else 0,
        "fps_promedio": round(sum(fps_hist) / len(fps_hist), 1) if fps_hist else 0,
        "frames": frame_count
    })


@app.route('/api/hotspot/toggle', methods=['POST'])
def toggle_hotspot():
    """Alterna el estado del hotspot."""
    if sys.platform == "win32":
        return jsonify({"error": "Hotspot no disponible en Windows"}), 400
    
    try:
        if conexion_hotspot_activa():
            bajar_hotspot()
            return jsonify({"status": "stopped", "message": "Hotspot desactivado"})
        else:
            levantar_hotspot()
            ip_hotspot = obtener_ip_hotspot()
            return jsonify({
                "status": "started",
                "message": "Hotspot activado",
                "ip": ip_hotspot
            })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@socketio.on('connect')
def handle_connect():
    """Maneja la conexión de un cliente WebSocket."""
    print(f"[INFO] Cliente WebSocket conectado: {request.remote_addr}")
    emit('connected', {'message': 'Conectado al servidor'})


@socketio.on('disconnect')
def handle_disconnect():
    """Maneja la desconexión de un cliente WebSocket."""
    print(f"[INFO] Cliente WebSocket desconectado: {request.remote_addr}")


def cleanup():
    """Limpia recursos al cerrar."""
    global stop_event, lector_thread, cap, writer, mediamtx_proc
    
    print("[INFO] Cerrando servidor web...")
    stop_event.set()
    
    if lector_thread is not None:
        lector_thread.join(timeout=2.0)
    
    if cap is not None:
        cap.release()
    
    if writer is not None:
        writer.release()
    
    if mediamtx_proc is not None:
        detener_mediamtx(mediamtx_proc)
    
    # No bajamos el hotspot automáticamente (puede estar en uso)
    print("[INFO] Servidor web cerrado")


if __name__ == '__main__':
    try:
        # Inicializar sistema
        inicializar_sistema()
        
        # Iniciar hilo de procesamiento y streaming
        stream_thread = threading.Thread(target=process_and_stream, daemon=True)
        stream_thread.start()
        
        # Obtener IP del hotspot para mostrar en consola
        if sys.platform != "win32":
            ip_hotspot = obtener_ip_hotspot() or "127.0.0.1"
        else:
            ip_hotspot = "127.0.0.1"
        
        print("\n" + "="*60)
        print("[OK] Servidor web iniciado")
        if sys.platform != "win32" and ip_hotspot != "127.0.0.1":
            print(f"[INFO] Accede desde la tablet: http://{ip_hotspot}:5000")
            print(f"[INFO] (Conecta la tablet al hotspot '{config.HOTSPOT_NAME}')")
        print(f"[INFO] Acceso local: http://127.0.0.1:5000")
        print("="*60 + "\n")
        
        # Iniciar servidor Flask
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupción por usuario")
    except Exception as exc:
        print(f"[ERROR] Error fatal: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

