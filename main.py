#en este script buscamos conectarnos al video de un dron en tiempo real a traves de RTMP
#URL del servidor: rtmp://192.168.137.1:1935/live
#Stream Key: dron1

import cv2
from ultralytics import YOLO
import time

# Configuración del stream
RTMP_URL = "rtmp://192.168.137.1:1935/live/dron1"
MAX_RETRIES = 5
RETRY_DELAY = 2  # segundos

def conectar_stream():
    """Intenta conectar al stream RTMP"""
    cap = cv2.VideoCapture(RTMP_URL)
    if cap.isOpened():
        print("Conexión exitosa al stream RTMP")
        return cap
    else:
        print("Error: No se pudo conectar al stream RTMP")
        return None

def procesar_stream():
    """Función principal de procesamiento"""
    cap = conectar_stream()
    if not cap:
        return False
    
    frame_count = 0
    
    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                print("No se pudo obtener el frame - reconectando...")
                cap.release()
                time.sleep(RETRY_DELAY)
                cap = conectar_stream()
                if not cap:
                    return False
                continue
            
            # Procesar frame
            frame = cv2.resize(frame, (640, 480))
            results = model(frame)
            annotated_frame = results[0].plot()
            
            # Mostrar frame
            cv2.imshow("RTMP Stream", annotated_frame)
            
            # Contador de frames
            frame_count += 1
            if frame_count % 100 == 0:
                print(f"Frames procesados: {frame_count}")
            
            # Salir con 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        except Exception as e:
            print(f"Error durante el procesamiento: {e}")
            print("Reintentando conexión...")
            cap.release()
            time.sleep(RETRY_DELAY)
            cap = conectar_stream()
            if not cap:
                return False
    
    cap.release()
    cv2.destroyAllWindows()
    return True

# Cargar modelo
print("Cargando modelo YOLO11...")
model = YOLO("models/Visdrone_yolo11n.pt")
print("Modelo cargado exitosamente")

# Ejecutar con reintentos
retry_count = 0
while retry_count < MAX_RETRIES:
    try:
        if procesar_stream():
            break
    except KeyboardInterrupt:
        print("Programa interrumpido por el usuario")
        break
    except Exception as e:
        print(f"Error crítico: {e}")
        retry_count += 1
        if retry_count < MAX_RETRIES:
            print(f"Reintentando en {RETRY_DELAY} segundos... ({retry_count}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
        else:
            print("Máximo de reintentos alcanzado")

print("Programa finalizado")
