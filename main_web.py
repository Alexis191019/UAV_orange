"""Punto de entrada para el servidor web (PWA) de detección UAV."""

# Importar funciones del backend y ejecutar servidor
if __name__ == '__main__':
    from web.backend import (
        app, socketio, inicializar_sistema, cleanup, 
        process_and_stream, stop_event
    )
    import threading
    import sys
    from src.hotspot import obtener_ip_hotspot
    from src import config
    
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

