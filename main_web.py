"""Punto de entrada para el servidor web (PWA) de detección UAV."""

# Importar funciones del backend y ejecutar servidor
if __name__ == '__main__':
    from web.backend import (
        app, socketio, inicializar_sistema, cleanup, 
        process_and_stream, conectar_rtmp_en_background
    )
    import threading
    import sys
    from src.hotspot import obtener_ip_hotspot
    from src import config
    
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
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("\n[INFO] Interrupción por usuario")
    except Exception as exc:
        print(f"[ERROR] Error fatal: {exc}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()

