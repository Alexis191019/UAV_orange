# Guía: Preparar el hotspot en Orange Pi 5 Pro

Esta guía resume el procedimiento que seguimos para configurar el punto de acceso Wi-Fi y dejar funcionando el flujo de RTMP/inferencia en una Orange Pi 5 Pro limpia.

## 1. Requerimientos base
- Orange Pi 5 Pro con Ubuntu u otra distribución compatible.
- Módulo Wi-Fi funcional (interfaz `wlan0`).
- Python 3.12 (según proyecto) y entorno virtual creado.
- MediaMTX descomprimido en `mediamtx/` dentro del proyecto.
- Modelo RKNN (por ejemplo `Visdrone_yolo11n_rknn_model`).

## 2. Verificar compatibilidad con modo AP
```bash
iw list | grep -A3 "Supported interface modes"
```
Debe listar `* AP`. Identifica la interfaz Wi-Fi (normalmente `wlan0`):
```bash
nmcli device status
```

## 3. Crear el hotspot `RC-Hotspot`
1. Eliminar perfiles previos que molesten:
   ```bash
   nmcli connection delete RC-Hotspot || true
   ```
2. Crear la nueva conexión AP:
   ```bash
   nmcli connection add type wifi ifname wlan0 mode ap \
     con-name RC-Hotspot ssid ORANGE-RC
   nmcli connection modify RC-Hotspot wifi.band bg
   nmcli connection modify RC-Hotspot 802-11-wireless.channel 6
   nmcli connection modify RC-Hotspot 802-11-wireless-security.key-mgmt wpa-psk
   nmcli connection modify RC-Hotspot 802-11-wireless-security.psk 12345678
   nmcli connection modify RC-Hotspot ipv4.method shared
   nmcli connection modify RC-Hotspot ipv6.method disabled
   ```
   - El modo `shared` activa DHCP/NAT automático. No intentar fijar `ipv4.dns` en este modo.
   - Ajusta SSID/clave a tus necesidades.

## 4. Secuencia recomendada para activarlo
Antes de levantar el hotspot usamos la secuencia que mejor funcionó:
```bash
nmcli radio wifi off
sleep 2
nmcli radio wifi on
sleep 2
nmcli connection up RC-Hotspot
```
- Si había conexiones previas (`iPhone de ...`), bájalas primero con `nmcli connection down "NOMBRE"`.
- Para diagnosticar, monitorea los logs de NetworkManager en otra terminal:
  ```bash
  journalctl -u NetworkManager -f
  ```

## 5. Comprobar estado
- Verifica que la conexión quedó activa:
  ```bash
  nmcli connection show --active
  ```
- Consulta IP asignada a `wlan0` (será usada por el RC):
  ```bash
  ip -4 addr show wlan0
  ```
  Habitualmente `10.42.0.1/24`. El RC debe transmitir a `rtmp://<esa IP>:1935/live/dron`.

## 6. Preparar MediaMTX
1. Ubica el binario en `mediamtx/mediamtx` y el archivo `mediamtx/mediamtx.yml`.
2. Ejecútalo manualmente para probar:
   ```bash
   cd /ruta/del/proyecto
   ./mediamtx/mediamtx mediamtx/mediamtx.yml
   ```
   Mantén esta terminal abierta para ver logs cuando el RC se conecte.

## 7. Scripts de inferencia
- `main_all.py` automatiza hotspot + MediaMTX + inferencia.
  - Usa `RTMP_URL = "rtmp://127.0.0.1:1935/live/dron"` para consumir el stream local.
  - En `levantar_hotspot()` se integra la secuencia `radio off/on` y reintentos.
- `manual_inference.py` sirve para demostraciones manuales: solo captura/infiere, asumiendo que tú ya levantaste hotspot y MediaMTX aparte.

### Consejos de operación
- Ejecuta `python -u main_all.py` para ver logs en tiempo real.
- El script intentará abrir el RTMP indefinidamente; verás mensajes de “RTMP aún no disponible” hasta que llegue la señal.
- Pulsa `i` para activar/pausar inferencia, `p` para pausar y `q` para salir.

## 8. Alternar con redes cliente
Cuando necesites volver a conectarte a otro Wi-Fi (por ejemplo el iPhone):
1. Baja el hotspot: `nmcli connection down RC-Hotspot`.
2. Sube la conexión cliente: `nmcli connection up "iPhone de ..."`.
3. Para retomar el AP, repite la secuencia del punto 4.

---
Con estos pasos puedes replicar la configuración en otra Orange Pi 5 Pro. Si algo falla, revisa `journalctl -u NetworkManager` y verifica la IP/SSID antes de pasar al siguiente paso.
