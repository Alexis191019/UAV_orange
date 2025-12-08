"""Servidor Flask para PWA de detección UAV."""

import threading
import queue
import time
import cv2
import base64
import os
import tempfile
import subprocess
from flask import Flask, jsonify, request, send_from_directory, send_file
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
selected_classes = None  # Lista de clases seleccionadas para detectar
conf_threshold = None  # Threshold de confianza personalizado
class_colors = {}  # Diccionario {nombre_clase: (B, G, R)} para colores de bboxes

# Diccionario de modelos disponibles
MODELOS_DISPONIBLES = {
    'uav': 'Visdrone_yolo11n_rknn_model',  # Modelo por defecto (UAV)
    'fuego': 'incendio_yolo11s_rknn_model',  # Por ahora None, luego agregarás la ruta
    'personas-agua': None  # Por ahora None, luego agregarás la ruta
}


def inicializar_sistema():
    """Inicializa el sistema: hotspot, MediaMTX y modelo (sin RTMP)."""
    global detector, mediamtx_proc
    
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
            model_path = MODELOS_DISPONIBLES.get('uav')  # Modelo por defecto
            if model_path:
                detector = DetectorYOLO(model_path=model_path)
                print("[OK] Modelo cargado")
                # Mostrar clases disponibles
                class_names = detector.get_class_names()
                if class_names:
                    print(f"[INFO] Clases disponibles: {list(class_names.values())}")
            else:
                print("[WARN] Modelo por defecto no configurado")
                detector = None
        except FileNotFoundError as exc:
            print(f"[WARN] Modelo no encontrado: {exc}")
            print("[INFO] El servidor funcionará en modo demo (sin inferencia)")
            detector = None  # Continuar sin modelo
        except Exception as exc:
            print(f"[ERROR] Error al cargar modelo: {exc}")
            print("[INFO] El servidor funcionará en modo demo (sin inferencia)")
            detector = None  # Continuar sin modelo
        
        print("[OK] Sistema inicializado (servicios básicos listos)")
        print("[INFO] La conexión RTMP se intentará en segundo plano...")
        
    except Exception as exc:
        print(f"[ERROR] Error en inicialización: {exc}")
        import traceback
        traceback.print_exc()
        raise


def conectar_rtmp_en_background():
    """Monitorea y mantiene la conexión RTMP activa, reconectando automáticamente si se pierde.
    
    Esta función intenta reconectar indefinidamente (sin límite de intentos) hasta que:
    - Se establezca una conexión exitosa, o
    - Se detenga el servidor (stop_event activado)
    
    Si otro dispositivo se conecta mientras estamos intentando reconectar, MediaMTX lo aceptará
    y este código lo detectará en el siguiente intento (cada 1-3 segundos dependiendo del número de intentos).
    """
    global cap, lector_thread
    
    print("[INFO] Iniciando monitor de conexión RTMP en segundo plano...")
    print("[INFO] El sistema intentará reconectar indefinidamente hasta que se establezca una conexión.")
    intento = 0
    ultima_conexion_exitosa = False
    
    while not stop_event.is_set():
        try:
            # Verificar si necesitamos conectar o reconectar
            necesita_conexion = (
                cap is None or 
                not cap.isOpened() or
                (lector_thread is not None and not lector_thread.is_alive())
            )
            
            if necesita_conexion:
                # Limpiar conexión anterior si existe
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass
                    cap = None
                
                # Limpiar el hilo lector anterior si existe
                if lector_thread is not None and not lector_thread.is_alive():
                    lector_thread = None
                
                intento += 1
                if ultima_conexion_exitosa:
                    print(f"[WARN] Conexión RTMP perdida. Intentando reconectar (intento {intento})...")
                else:
                    print(f"[INFO] Intentando conectar RTMP (intento {intento})...")
                
                # Intentar conectar
                temp_cap = cv2.VideoCapture(config.RTMP_URL)
                if temp_cap.isOpened():
                    # Verificar que realmente esté recibiendo frames
                    temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    ret, test_frame = temp_cap.read()
                    
                    if ret and test_frame is not None:
                        # Conexión exitosa
                        cap = temp_cap
                        print("[OK] Stream RTMP conectado exitosamente")
                        
                        # Iniciar hilo lector
                        lector_thread = threading.Thread(
                            target=lector_frames,
                            args=(cap, frame_queue, stop_event),
                            daemon=True
                        )
                        lector_thread.start()
                        print("[OK] Lector de frames iniciado")
                        print(f"[DEBUG] Frame queue size: {frame_queue.qsize()}")
                        
                        ultima_conexion_exitosa = True
                        intento = 0  # Resetear contador de intentos
                        
                        # Esperar un poco antes de verificar de nuevo
                        time.sleep(2.0)
                        continue
                    else:
                        # No hay frames, cerrar y reintentar
                        temp_cap.release()
                        print(f"[WARN] RTMP conectado pero sin frames, reintentando...")
                else:
                    # No se pudo abrir, cerrar y reintentar
                    temp_cap.release()
                    print(f"[WARN] No se pudo abrir stream RTMP")
                
                ultima_conexion_exitosa = False
                
                # Esperar antes del siguiente intento
                # Usar tiempo corto (1-2s) para detectar rápidamente nuevas conexiones
                # pero aumentar ligeramente después de muchos intentos para no saturar
                if intento <= 5:
                    wait_time = 1.0  # Primeros 5 intentos: cada 1 segundo (rápido)
                elif intento <= 15:
                    wait_time = 2.0  # Siguientes 10 intentos: cada 2 segundos
                else:
                    wait_time = 3.0  # Después: cada 3 segundos (no saturar)
                
                if stop_event.wait(wait_time):  # Si se activó stop_event, salir
                    break
            else:
                # Conexión activa, verificar periódicamente
                time.sleep(2.0)
                
        except Exception as exc:
            print(f"[WARN] Error en monitor RTMP (intento {intento}): {exc}")
            ultima_conexion_exitosa = False
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
                cap = None
            time.sleep(3.0)
    
    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass
    print("[INFO] Monitor de conexión RTMP detenido")


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
            
            try:
                frame = frame_queue.get(timeout=0.1)
            except queue.Empty:
                # No hay frames disponibles, continuar
                continue
            
            if inferir and detector is not None:
                annotated, elapsed, clases_detectadas = detector.detectar(
                    frame,
                    conf_threshold=conf_threshold,
                    selected_classes=selected_classes,
                    class_colors=class_colors
                )
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
            
            # Debug: mostrar cada 30 frames que se están enviando
            if frame_count % 30 == 0:
                print(f"[DEBUG] Enviando frame #{frame_count} - FPS: {round(fps_actual, 1)}, Queue size: {frame_queue.qsize()}")
            
        except Exception as exc:
            print(f"[WARN] Error en procesamiento de frame: {exc}")
            import traceback
            traceback.print_exc()
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
    
    # Obtener IP local si está disponible
    ip_local = None
    if sys.platform != "win32":
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
            s.close()
        except Exception:
            pass
    
    # Determinar URL RTMP (preferir hotspot, luego local, luego localhost)
    rtmp_ip = ip_hotspot if ip_hotspot and ip_hotspot != "127.0.0.1" else (ip_local if ip_local else "127.0.0.1")
    rtmp_url = f"rtmp://{rtmp_ip}:1935/live/dron"
    
    return jsonify({
        "inference": inferir,
        "model_loaded": detector is not None,
        "stream_connected": cap is not None and cap.isOpened() if cap else False,
        "hotspot_active": hotspot_activo,
        "hotspot_ip": ip_hotspot,
        "hotspot_name": config.HOTSPOT_NAME if hotspot_activo else None,
        "rtmp_url": rtmp_url,
        "rtmp_url_hotspot": f"rtmp://{ip_hotspot}:1935/live/dron" if ip_hotspot and ip_hotspot != "127.0.0.1" else None,
        "rtmp_url_local": f"rtmp://{ip_local}:1935/live/dron" if ip_local and ip_local != ip_hotspot else None,
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

@app.route('/api/model/change', methods=['POST'])
def change_model():
    """Cambia el modelo de inferencia."""
    global detector, inferir
    
    try:
        # Obtener el modelo solicitado del request
        data = request.get_json()
        if not data or 'model' not in data:
            return jsonify({"error": "Parámetro 'model' requerido"}), 400
        
        model_name = data['model']
        
        # Validar que el modelo existe en el diccionario
        if model_name not in MODELOS_DISPONIBLES:
            return jsonify({
                "error": f"Modelo '{model_name}' no válido",
                "modelos_disponibles": list(MODELOS_DISPONIBLES.keys())
            }), 400
        
        # Obtener la ruta del modelo
        model_path = MODELOS_DISPONIBLES[model_name]
        
        # Verificar si el modelo está disponible (no es None)
        if model_path is None:
            return jsonify({
                "error": f"Modelo '{model_name}' aún no está disponible",
                "message": "La ruta del modelo no ha sido configurada"
            }), 400
        
        # Si la inferencia está activa, detenerla primero
        if inferir:
            print("[INFO] Deteniendo inferencia antes de cambiar modelo...")
            inferir = False
            time.sleep(0.5)  # Dar tiempo para que termine el frame actual
        
        # Cargar el nuevo modelo
        print(f"[INFO] Cargando modelo '{model_name}' desde: {model_path}")
        try:
            detector = DetectorYOLO(model_path=model_path)
            print(f"[OK] Modelo '{model_name}' cargado exitosamente")
        except FileNotFoundError as exc:
            return jsonify({
                "error": f"Modelo no encontrado: {exc}",
                "model": model_name,
                "path": model_path
            }), 404
        except Exception as exc:
            print(f"[ERROR] Error al cargar modelo: {exc}")
            import traceback
            traceback.print_exc()
            return jsonify({
                "error": f"Error al cargar modelo: {str(exc)}",
                "model": model_name
            }), 500
        
        # Obtener clases disponibles del nuevo modelo
        class_names = {}
        try:
            class_names = detector.get_class_names()
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "message": f"Modelo cambiado a '{model_name}'",
            "model": model_name,
            "classes": class_names
        })
    except Exception as exc:
        print(f"[ERROR] Error en change_model: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route('/api/model/classes', methods=['GET'])
def get_model_classes():
    """Obtiene las clases disponibles del modelo actual."""
    global detector
    if detector is None:
        return jsonify({
            "error": "Modelo no cargado",
            "classes": {}
        }), 400
    
    try:
        class_names = detector.get_class_names()
        return jsonify({
            "success": True,
            "classes": class_names
        })
    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "classes": {}
        }), 500


@app.route('/api/inference/config', methods=['POST'])
def config_inference():
    """Configura las clases seleccionadas y el threshold de confianza."""
    global selected_classes, conf_threshold, class_colors
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos no proporcionados"}), 400
        
        # Actualizar clases seleccionadas
        if 'selected_classes' in data:
            # Si es None o lista vacía, establecer como None
            if data['selected_classes'] and len(data['selected_classes']) > 0:
                selected_classes = data['selected_classes']
            else:
                selected_classes = None
            print(f"[INFO] Clases seleccionadas actualizadas: {selected_classes}")
        
        # Actualizar threshold
        if 'conf_threshold' in data:
            threshold = data['conf_threshold']
            if threshold is not None:
                # Validar que esté en rango [0, 1]
                threshold = max(0.0, min(1.0, float(threshold)))
            conf_threshold = threshold
            print(f"[INFO] Threshold de confianza actualizado: {conf_threshold}")
        
        # Actualizar colores de clases
        if 'class_colors' in data:
            # Convertir colores de formato RGB (frontend) a BGR (OpenCV)
            colors_dict = data['class_colors']
            class_colors = {}
            if isinstance(colors_dict, dict) and len(colors_dict) > 0:
                for class_name, color in colors_dict.items():
                    if isinstance(color, list) and len(color) >= 3:
                        # Frontend envía RGB, OpenCV usa BGR
                        r, g, b = color[0], color[1], color[2]
                        class_colors[class_name] = (b, g, r)  # Convertir a BGR
            print(f"[INFO] Colores de clases actualizados: {len(class_colors)} clases")
        
        return jsonify({
            "success": True,
            "message": "Configuración actualizada",
            "selected_classes": selected_classes,
            "conf_threshold": conf_threshold
        })
    except Exception as exc:
        print(f"[ERROR] Error al configurar inferencia: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


@app.route('/api/video/convert', methods=['POST'])
def convert_video_to_mp4():
    """Convierte un video WebM a MP4 y lo envía al cliente, luego elimina los archivos temporales."""
    try:
        # Verificar que se envió un archivo
        if 'video' not in request.files:
            return jsonify({'error': 'No se recibió ningún archivo de video'}), 400
        
        video_file = request.files['video']
        
        if video_file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        # Crear directorio temporal si no existe
        temp_dir = os.path.join(BASE_DIR, 'temp_videos')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generar nombres únicos para los archivos temporales
        import uuid
        unique_id = str(uuid.uuid4())
        webm_path = os.path.join(temp_dir, f'temp_{unique_id}.webm')
        mp4_path = os.path.join(temp_dir, f'temp_{unique_id}.mp4')
        
        try:
            # Guardar el archivo WebM temporalmente
            video_file.save(webm_path)
            print(f"[INFO] Video WebM recibido: {webm_path}")
            
            # Convertir WebM a MP4 usando ffmpeg
            print(f"[INFO] Convirtiendo a MP4...")
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', webm_path,
                '-c:v', 'libx264',
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-movflags', '+faststart',  # Optimizar para streaming
                '-y',  # Sobrescribir si existe
                mp4_path
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # Timeout de 5 minutos
            )
            
            if result.returncode != 0:
                print(f"[ERROR] Error en conversión ffmpeg: {result.stderr}")
                # Limpiar archivo WebM
                if os.path.exists(webm_path):
                    os.remove(webm_path)
                return jsonify({'error': 'Error al convertir video: ' + result.stderr[:200]}), 500
            
            if not os.path.exists(mp4_path):
                print(f"[ERROR] El archivo MP4 no se creó")
                # Limpiar archivo WebM
                if os.path.exists(webm_path):
                    os.remove(webm_path)
                return jsonify({'error': 'No se pudo crear el archivo MP4'}), 500
            
            print(f"[OK] Video convertido: {mp4_path}")
            
            # Generar nombre de archivo para descarga
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            download_filename = f'deteccion-uav-{timestamp}.mp4'
            
            # Enviar el archivo MP4 al cliente
            def remove_files():
                """Función para eliminar archivos temporales después de enviar."""
                try:
                    if os.path.exists(webm_path):
                        os.remove(webm_path)
                        print(f"[INFO] Archivo WebM eliminado: {webm_path}")
                    if os.path.exists(mp4_path):
                        os.remove(mp4_path)
                        print(f"[INFO] Archivo MP4 eliminado: {mp4_path}")
                except Exception as e:
                    print(f"[WARN] Error al eliminar archivos temporales: {e}")
            
            # Usar send_file para enviar el MP4
            response = send_file(
                mp4_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=download_filename
            )
            
            # Programar limpieza después de enviar (en un hilo separado con delay)
            def delayed_cleanup():
                time.sleep(10)  # Esperar 10 segundos para asegurar que el archivo se descargó
                try:
                    if os.path.exists(webm_path):
                        os.remove(webm_path)
                        print(f"[INFO] Archivo WebM eliminado: {webm_path}")
                    if os.path.exists(mp4_path):
                        os.remove(mp4_path)
                        print(f"[INFO] Archivo MP4 eliminado: {mp4_path}")
                except Exception as e:
                    print(f"[WARN] Error al eliminar archivos temporales: {e}")
            
            cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
            cleanup_thread.start()
            
            return response
            
        except subprocess.TimeoutExpired:
            print(f"[ERROR] Timeout al convertir video")
            # Limpiar archivos
            if os.path.exists(webm_path):
                os.remove(webm_path)
            if os.path.exists(mp4_path):
                os.remove(mp4_path)
            return jsonify({'error': 'Timeout al convertir video (muy largo)'}), 500
            
        except Exception as e:
            print(f"[ERROR] Error en conversión: {e}")
            import traceback
            traceback.print_exc()
            # Limpiar archivos en caso de error
            if os.path.exists(webm_path):
                try:
                    os.remove(webm_path)
                except:
                    pass
            if os.path.exists(mp4_path):
                try:
                    os.remove(mp4_path)
                except:
                    pass
            return jsonify({'error': f'Error al procesar video: {str(e)}'}), 500
            
    except Exception as e:
        print(f"[ERROR] Error en endpoint de conversión: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Error interno del servidor'}), 500


@app.route('/api/shutdown', methods=['POST'])
def shutdown_system():
    """Apaga la Orange Pi de forma segura."""
    if sys.platform == "win32":
        return jsonify({"error": "Apagado no disponible en Windows"}), 400
    
    try:
        print("[INFO] Solicitud de apagado recibida desde cliente web")
        
        # Cerrar recursos primero
        cleanup()
        
        # Ejecutar comando de apagado (requiere permisos sudo)
        import subprocess
        result = subprocess.run(
            ['sudo', 'shutdown', '-h', 'now'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return jsonify({
                "success": True,
                "message": "Sistema apagándose..."
            })
        else:
            return jsonify({
                "error": f"No se pudo apagar el sistema: {result.stderr}",
                "message": "Verifica que el usuario tenga permisos sudo sin contraseña para 'shutdown'"
            }), 500
            
    except subprocess.TimeoutExpired:
        # El comando se ejecutó pero el sistema está apagándose
        return jsonify({
            "success": True,
            "message": "Sistema apagándose..."
        })
    except Exception as exc:
        print(f"[ERROR] Error al apagar sistema: {exc}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error al apagar sistema: {str(exc)}"
        }), 500


@socketio.on('connect')
def handle_connect():
    """Maneja la conexión de un cliente WebSocket."""
    print(f"[INFO] Cliente WebSocket conectado: {request.remote_addr}")
    print(f"[DEBUG] Estado del sistema - cap: {cap is not None}, detector: {detector is not None}, frame_queue size: {frame_queue.qsize()}")
    emit('connected', {'message': 'Conectado al servidor'})


@socketio.on('disconnect')
def handle_disconnect():
    """Maneja la desconexión de un cliente WebSocket."""
    print(f"[INFO] Cliente WebSocket desconectado: {request.remote_addr}")


def cleanup_temp_videos():
    """Limpia archivos temporales de video antiguos (más de 1 hora)."""
    try:
        temp_dir = os.path.join(BASE_DIR, 'temp_videos')
        if not os.path.exists(temp_dir):
            return
        
        current_time = time.time()
        max_age = 3600  # 1 hora en segundos
        
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age:
                        os.remove(file_path)
                        print(f"[INFO] Archivo temporal antiguo eliminado: {filename}")
            except Exception as e:
                print(f"[WARN] Error al eliminar archivo temporal {filename}: {e}")
    except Exception as e:
        print(f"[WARN] Error en limpieza de archivos temporales: {e}")


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
    
    # Limpiar archivos temporales de video
    cleanup_temp_videos()
    
    # No bajamos el hotspot automáticamente (puede estar en uso)
    print("[INFO] Servidor web cerrado")


# Limpieza periódica de archivos temporales (cada 30 minutos)
def periodic_cleanup():
    """Ejecuta limpieza periódica de archivos temporales."""
    while not stop_event.is_set():
        time.sleep(1800)  # 30 minutos
        if not stop_event.is_set():
            cleanup_temp_videos()

if __name__ == '__main__':
    try:
        # Inicializar sistema (hotspot, MediaMTX, modelo - sin RTMP)
        inicializar_sistema()
        
        # Iniciar hilo de conexión RTMP en segundo plano
        rtmp_thread = threading.Thread(target=conectar_rtmp_en_background, daemon=True)
        rtmp_thread.start()
        
        # Iniciar hilo de procesamiento y streaming
        stream_thread = threading.Thread(target=process_and_stream, daemon=True)
        stream_thread.start()
        
        # Obtener IPs disponibles para mostrar en consola
        if sys.platform != "win32":
            ip_hotspot = obtener_ip_hotspot() or "127.0.0.1"
            # Obtener IP local (ethernet/wifi) si está disponible
            ip_local = None
            try:
                import socket
                # Conectar a un servidor externo para obtener la IP local
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_local = s.getsockname()[0]
                s.close()
            except Exception:
                pass
        else:
            ip_hotspot = "127.0.0.1"
            ip_local = None
        
        print("\n" + "="*60)
        print("[OK] Servidor web iniciado")
        print(f"[INFO] Acceso local (mismo dispositivo): http://127.0.0.1:5000")
        if sys.platform != "win32":
            if ip_hotspot != "127.0.0.1":
                print(f"[INFO] Acceso por hotspot '{config.HOTSPOT_NAME}': http://{ip_hotspot}:5000")
                print(f"[INFO]   → Conecta tu PC/tablet al WiFi '{config.HOTSPOT_NAME}'")
                print(f"[INFO] URL RTMP para transmitir: rtmp://{ip_hotspot}:1935/live/dron")
            if ip_local and ip_local != ip_hotspot:
                print(f"[INFO] Acceso por red local: http://{ip_local}:5000")
                print(f"[INFO]   → Conecta tu PC a la misma red WiFi/Ethernet que la Orange Pi")
                print(f"[INFO] URL RTMP para transmitir (red local): rtmp://{ip_local}:1935/live/dron")
        else:
            print(f"[INFO] URL RTMP para transmitir: rtmp://127.0.0.1:1935/live/dron")
        print("[INFO] El servidor está intentando conectar RTMP en segundo plano...")
        print("="*60 + "\n")
        
        # Iniciar servidor Flask (esto se ejecuta inmediatamente)
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupción por usuario")
    except Exception as exc:
        print(f"[ERROR] Error fatal: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

