"""Aplicación de interfaz gráfica para detección UAV."""

import threading
import queue
import time
import cv2
from PIL import Image, ImageTk
import customtkinter as ctk

from src import config
from src.hotspot import levantar_hotspot, bajar_hotspot, conexion_hotspot_activa, obtener_ip_hotspot
from src.mediamtx import iniciar_mediamtx, detener_mediamtx
from src.video import abrir_stream, lector_frames, crear_writer
from src.detector import DetectorYOLO

# Configurar tema de CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Diccionario de modelos disponibles
MODELOS_DISPONIBLES = {
    'uav': 'Visdrone_yolo11n_rknn_model',  # Modelo por defecto (UAV)
    'fuego': None,  # Por ahora None, luego agregarás la ruta
    'personas-agua': None  # Por ahora None, luego agregarás la ruta
}


class DeteccionUAVApp(ctk.CTk):
    """Aplicación principal de detección UAV con interfaz gráfica."""
    
    def __init__(self):
        super().__init__()
        
        # Variables de estado
        self.detector = None
        self.cap = None
        self.writer = None
        self.lector_thread = None
        self.mediamtx_proc = None
        self.stop_event = threading.Event()
        self.frame_queue = queue.Queue(maxsize=1)
        self.inferir = False
        self.fps_hist = []
        self.frame_count = 0
        self.current_model = 'uav'  # Modelo actual seleccionado
        
        # Configurar ventana
        self.title("Detección UAV - Sistema RTMP")
        self.geometry("1200x700")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Crear interfaz
        self.crear_interfaz()
        
        # Iniciar proceso de inicialización en hilo separado
        threading.Thread(target=self.inicializar_sistema, daemon=True).start()
    
    def crear_interfaz(self):
        """Crea todos los elementos de la interfaz gráfica."""
        
        # Frame principal (horizontal)
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel izquierdo: Video
        video_frame = ctk.CTkFrame(main_frame)
        video_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        video_label = ctk.CTkLabel(
            video_frame, 
            text="Video en Tiempo Real", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        video_label.pack(pady=10)
        
        self.video_label = ctk.CTkLabel(
            video_frame, 
            text="Esperando conexión RTMP...", 
            width=640, 
            height=480
        )
        self.video_label.pack(pady=10)
        
        # Panel derecho: Controles y métricas
        control_frame = ctk.CTkFrame(main_frame, width=300)
        control_frame.pack(side="right", fill="y", padx=(10, 0))
        control_frame.pack_propagate(False)
        
        # Título
        title_label = ctk.CTkLabel(
            control_frame, 
            text="Controles", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=15)
        
        # Botón de inferencia
        self.btn_inferencia = ctk.CTkButton(
            control_frame,
            text="Iniciar Inferencia",
            command=self.toggle_inferencia,
            font=ctk.CTkFont(size=14),
            height=40,
            state="disabled"
        )
        self.btn_inferencia.pack(pady=10, padx=20, fill="x")
        
        # Selector de modelo
        model_label = ctk.CTkLabel(
            control_frame,
            text="Modelo de Inferencia",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        model_label.pack(pady=(10, 5), padx=20)
        
        # Crear opciones para el menú desplegable
        model_options = []
        model_display_names = {
            'uav': 'General UAV',
            'fuego': 'Detección Fuego',
            'personas-agua': 'Personas en Agua'
        }
        
        for model_key in MODELOS_DISPONIBLES.keys():
            display_name = model_display_names.get(model_key, model_key)
            if MODELOS_DISPONIBLES[model_key] is not None:
                model_options.append(display_name)
            else:
                model_options.append(f"{display_name} (No disponible)")
        
        self.model_selector = ctk.CTkOptionMenu(
            control_frame,
            values=model_options,
            command=self.cambiar_modelo,
            font=ctk.CTkFont(size=12),
            height=35,
            state="disabled"
        )
        self.model_selector.set(model_display_names.get('uav', 'General UAV'))
        self.model_selector.pack(pady=5, padx=20, fill="x")
        
        # Separador
        separator1 = ctk.CTkFrame(control_frame, height=2, fg_color="gray")
        separator1.pack(fill="x", padx=20, pady=10)
        
        # Métricas
        metrics_label = ctk.CTkLabel(
            control_frame, 
            text="Métricas", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        metrics_label.pack(pady=(10, 5))
        
        self.fps_label = ctk.CTkLabel(
            control_frame, 
            text="FPS: --", 
            font=ctk.CTkFont(size=12)
        )
        self.fps_label.pack(pady=5)
        
        self.fps_avg_label = ctk.CTkLabel(
            control_frame, 
            text="FPS Promedio: --", 
            font=ctk.CTkFont(size=12)
        )
        self.fps_avg_label.pack(pady=5)
        
        self.frames_label = ctk.CTkLabel(
            control_frame, 
            text="Frames: 0", 
            font=ctk.CTkFont(size=12)
        )
        self.frames_label.pack(pady=5)
        
        # Separador
        separator2 = ctk.CTkFrame(control_frame, height=2, fg_color="gray")
        separator2.pack(fill="x", padx=20, pady=10)
        
        # Estado del sistema
        status_label = ctk.CTkLabel(
            control_frame, 
            text="Estado del Sistema", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        status_label.pack(pady=(10, 5))
        
        self.hotspot_status = ctk.CTkLabel(
            control_frame, 
            text="Hotspot: Iniciando...", 
            font=ctk.CTkFont(size=11)
        )
        self.hotspot_status.pack(pady=5)
        
        self.mediamtx_status = ctk.CTkLabel(
            control_frame, 
            text="MediaMTX: Iniciando...", 
            font=ctk.CTkFont(size=11)
        )
        self.mediamtx_status.pack(pady=5)
        
        self.stream_status = ctk.CTkLabel(
            control_frame, 
            text="Stream RTMP: Desconectado", 
            font=ctk.CTkFont(size=11)
        )
        self.stream_status.pack(pady=5)
        
        # Separador
        separator3 = ctk.CTkFrame(control_frame, height=2, fg_color="gray")
        separator3.pack(fill="x", padx=20, pady=10)
        
        # Botón de hotspot
        self.btn_hotspot = ctk.CTkButton(
            control_frame,
            text="Desactivar Hotspot",
            command=self.toggle_hotspot,
            font=ctk.CTkFont(size=12),
            height=35,
            fg_color="gray",
            state="disabled"
        )
        self.btn_hotspot.pack(pady=10, padx=20, fill="x")
        
        # Botón de salir
        self.btn_salir = ctk.CTkButton(
            control_frame,
            text="Salir",
            command=self.on_closing,
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="red",
            hover_color="darkred"
        )
        self.btn_salir.pack(pady=20, padx=20, fill="x")
    
    def inicializar_sistema(self):
        """Inicializa el sistema en un hilo separado para no bloquear la GUI."""
        try:
            # Actualizar estado
            self.after(0, lambda: self.hotspot_status.configure(text="Hotspot: Activando..."))
            
            # Levantar hotspot
            levantar_hotspot()
            
            # Obtener IP del hotspot y actualizar estado
            ip_hotspot = obtener_ip_hotspot()
            if ip_hotspot:
                hotspot_text = f"Hotspot: {config.HOTSPOT_NAME} - IP: {ip_hotspot}"
                rtmp_url = f"rtmp://{ip_hotspot}:1935/live/dron"
                mediamtx_text = f"MediaMTX: Transmitir a: {rtmp_url}"
            else:
                hotspot_text = f"Hotspot: {config.HOTSPOT_NAME} - Activo"
                mediamtx_text = "MediaMTX: IP: 127.0.0.1:1935"
            
            self.after(0, lambda: self.hotspot_status.configure(text=hotspot_text))
            
            # Iniciar MediaMTX
            self.after(0, lambda: self.mediamtx_status.configure(text="MediaMTX: Iniciando..."))
            try:
                self.mediamtx_proc = iniciar_mediamtx()
                # Actualizar con la URL RTMP completa
                self.after(0, lambda: self.mediamtx_status.configure(text=mediamtx_text))
            except Exception as exc:
                print(f"[ERROR] No se pudo iniciar MediaMTX: {exc}")
                self.after(0, lambda: self.mediamtx_status.configure(
                    text=f"MediaMTX: Error - {str(exc)[:30]}"
                ))
            
            # Cargar modelo
            self.after(0, lambda: self.video_label.configure(text="Cargando modelo..."))
            model_path = MODELOS_DISPONIBLES.get(self.current_model)
            if model_path:
                self.detector = DetectorYOLO(model_path=model_path)
            else:
                self.detector = DetectorYOLO()  # Usar modelo por defecto
            
            # Abrir stream
            self.after(0, lambda: self.stream_status.configure(text="Stream RTMP: Conectando..."))
            self.cap = abrir_stream()
            if self.cap is None:
                raise RuntimeError("No se pudo conectar al stream RTMP.")
            
            self.after(0, lambda: self.stream_status.configure(text="Stream RTMP: Conectado"))
            
            # Crear writer si es necesario
            self.writer = crear_writer(config.OUTPUT_VIDEO, config.FRAME_SIZE, config.OUTPUT_FPS)
            
            # Iniciar hilo lector
            self.lector_thread = threading.Thread(
                target=lector_frames, 
                args=(self.cap, self.frame_queue, self.stop_event), 
                daemon=True
            )
            self.lector_thread.start()
            
            time.sleep(0.5)
            
            # Habilitar controles
            self.after(0, lambda: self.btn_inferencia.configure(state="normal"))
            self.after(0, lambda: self.btn_hotspot.configure(state="normal"))
            self.after(0, lambda: self.model_selector.configure(state="normal"))
            
            # Iniciar bucle de actualización de video
            self.actualizar_video()
            
        except Exception as exc:
            print(f"[ERROR] Error en inicialización: {exc}")
            self.after(0, lambda: self.video_label.configure(text=f"Error: {str(exc)}"))
    
    def actualizar_video(self):
        """Actualiza el video en la GUI."""
        if self.stop_event.is_set():
            return
        
        try:
            frame = self.frame_queue.get(timeout=0.1)
        except queue.Empty:
            self.after(50, self.actualizar_video)
            return
        
        annotated = frame.copy()
        
        if self.inferir and self.detector:
            annotated, elapsed, _ = self.detector.detectar(frame)  # Ignoramos clases_detectadas por ahora
            fps_actual = 1.0 / elapsed if elapsed > 0 else 0.0
            self.fps_hist.append(fps_actual)
            if len(self.fps_hist) > 30:
                self.fps_hist.pop(0)
            fps_prom = sum(self.fps_hist) / len(self.fps_hist) if self.fps_hist else 0.0
            
            # Actualizar métricas
            self.after(0, lambda: self.fps_label.configure(text=f"FPS: {fps_actual:.1f}"))
            self.after(0, lambda: self.fps_avg_label.configure(text=f"FPS Promedio: {fps_prom:.1f}"))
        
        # Actualizar contador de frames
        self.frame_count += 1
        self.after(0, lambda: self.frames_label.configure(text=f"Frames: {self.frame_count}"))
        
        # Guardar video si es necesario
        if self.writer is not None:
            try:
                self.writer.write(annotated)
            except Exception as exc:
                print(f"[WARN] No se pudo escribir en archivo: {exc}")
        
        # Convertir frame de OpenCV a formato para CustomTkinter
        # OpenCV usa BGR, necesitamos RGB
        annotated_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
        
        # Redimensionar si es necesario para ajustar al widget
        display_size = (640, 480)
        if annotated_rgb.shape[:2] != display_size:
            annotated_rgb = cv2.resize(annotated_rgb, display_size)
        
        # Convertir a PIL Image y luego a PhotoImage
        image = Image.fromarray(annotated_rgb)
        photo = ImageTk.PhotoImage(image=image)
        
        # Actualizar label con la imagen
        self.video_label.configure(image=photo, text="")
        self.video_label.image = photo  # Mantener referencia
        
        # Programar próxima actualización
        self.after(33, self.actualizar_video)  # ~30 FPS
    
    def toggle_inferencia(self):
        """Alterna el estado de inferencia."""
        self.inferir = not self.inferir
        if self.inferir:
            self.btn_inferencia.configure(text="Detener Inferencia", fg_color="orange")
            print("[INFO] Inferencia activada.")
        else:
            self.btn_inferencia.configure(
                text="Iniciar Inferencia", 
                fg_color=("gray75", "gray25")
            )
            print("[INFO] Inferencia detenida.")
    
    def toggle_hotspot(self):
        """Alterna el estado del hotspot."""
        if conexion_hotspot_activa():
            bajar_hotspot()
            self.hotspot_status.configure(text="Hotspot: Desactivado")
            self.btn_hotspot.configure(text="Activar Hotspot", fg_color="green")
        else:
            levantar_hotspot()
            self.hotspot_status.configure(text="Hotspot: Activo")
            self.btn_hotspot.configure(text="Desactivar Hotspot", fg_color="gray")
    
    def cambiar_modelo(self, selected_display_name):
        """Cambia el modelo de inferencia según la selección del usuario."""
        # Limpiar el nombre (remover "(No disponible)" si está presente)
        clean_name = selected_display_name.replace(" (No disponible)", "").strip()
        
        # Mapear nombre de visualización a clave del modelo
        model_display_to_key = {
            'General UAV': 'uav',
            'Detección Fuego': 'fuego',
            'Personas en Agua': 'personas-agua'
        }
        
        # Buscar la clave del modelo
        model_key = model_display_to_key.get(clean_name)
        
        if model_key is None:
            print(f"[ERROR] No se pudo identificar el modelo: {selected_display_name}")
            return
        
        # Verificar que el modelo esté disponible
        model_path = MODELOS_DISPONIBLES.get(model_key)
        if model_path is None:
            print(f"[ERROR] Modelo '{model_key}' aún no está disponible")
            # Mostrar mensaje de error en la GUI
            self.after(0, lambda: self.video_label.configure(
                text=f"Modelo '{clean_name}' no disponible"
            ))
            # Revertir la selección
            model_display_names = {
                'uav': 'General UAV',
                'fuego': 'Detección Fuego',
                'personas-agua': 'Personas en Agua'
            }
            current_display = model_display_names.get(self.current_model, 'General UAV')
            # Agregar "(No disponible)" si el modelo actual no está disponible
            if MODELOS_DISPONIBLES.get(self.current_model) is None:
                current_display += " (No disponible)"
            self.after(0, lambda: self.model_selector.set(current_display))
            return
        
        # Si la inferencia está activa, detenerla primero
        if self.inferir:
            print("[INFO] Deteniendo inferencia antes de cambiar modelo...")
            self.inferir = False
            self.after(0, lambda: self.btn_inferencia.configure(
                text="Iniciar Inferencia",
                fg_color=("gray75", "gray25")
            ))
            time.sleep(0.5)  # Dar tiempo para que termine el frame actual
        
        # Cargar el nuevo modelo en un hilo separado para no bloquear la GUI
        def cargar_modelo():
            try:
                print(f"[INFO] Cargando modelo '{model_key}' desde: {model_path}")
                self.after(0, lambda: self.video_label.configure(text=f"Cargando modelo {selected_display_name}..."))
                
                new_detector = DetectorYOLO(model_path=model_path)
                self.detector = new_detector
                self.current_model = model_key
                
                print(f"[OK] Modelo '{model_key}' cargado exitosamente")
                self.after(0, lambda: self.video_label.configure(text="Modelo cargado correctamente"))
                
            except FileNotFoundError as exc:
                print(f"[ERROR] Modelo no encontrado: {exc}")
                self.after(0, lambda: self.video_label.configure(
                    text=f"Error: Modelo no encontrado"
                ))
                # Revertir la selección
                model_display_names = {
                    'uav': 'General UAV',
                    'fuego': 'Detección Fuego',
                    'personas-agua': 'Personas en Agua'
                }
                self.after(0, lambda: self.model_selector.set(
                    model_display_names.get(self.current_model, 'General UAV')
                ))
            except Exception as exc:
                print(f"[ERROR] Error al cargar modelo: {exc}")
                self.after(0, lambda: self.video_label.configure(
                    text=f"Error al cargar modelo: {str(exc)[:50]}"
                ))
                # Revertir la selección
                model_display_names = {
                    'uav': 'General UAV',
                    'fuego': 'Detección Fuego',
                    'personas-agua': 'Personas en Agua'
                }
                self.after(0, lambda: self.model_selector.set(
                    model_display_names.get(self.current_model, 'General UAV')
                ))
        
        # Ejecutar en hilo separado
        threading.Thread(target=cargar_modelo, daemon=True).start()
    
    def on_closing(self):
        """Maneja el cierre de la aplicación."""
        print("[INFO] Cerrando aplicación...")
        self.stop_event.set()
        
        if self.lector_thread is not None:
            self.lector_thread.join(timeout=1.0)
        
        if self.cap is not None:
            self.cap.release()
        
        if self.writer is not None:
            self.writer.release()
        
        detener_mediamtx(self.mediamtx_proc)
        bajar_hotspot()
        
        self.destroy()
        print("[INFO] Programa finalizado.")

