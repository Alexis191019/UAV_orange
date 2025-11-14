"""Punto de entrada principal para la aplicación GUI de detección UAV."""

from gui.app import DeteccionUAVApp


def main():
    """Función principal que inicia la aplicación."""
    print("[DEBUG] Iniciando aplicación GUI", flush=True)
    app = DeteccionUAVApp()
    app.mainloop()


if __name__ == "__main__":
    main()
