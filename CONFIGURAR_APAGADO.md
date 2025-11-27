# Configuración de Permisos para Apagado Remoto

Para que el botón de apagado funcione desde la interfaz web, necesitas configurar permisos sudo sin contraseña para el comando `shutdown`.

## Pasos en la Orange Pi:

1. **Editar el archivo sudoers** (requiere cuidado):
   ```bash
   sudo visudo
   ```

2. **Agregar esta línea al final del archivo**:
   ```
   orangepi ALL=(ALL) NOPASSWD: /sbin/shutdown
   ```
   
   Esto permite que el usuario `orangepi` ejecute `sudo shutdown` sin contraseña.

3. **Guardar y salir**:
   - Presiona `Ctrl+O` para guardar
   - Presiona `Enter` para confirmar
   - Presiona `Ctrl+X` para salir

4. **Verificar que funciona** (opcional, prueba):
   ```bash
   sudo shutdown -h +1  # Apaga en 1 minuto (puedes cancelar con: sudo shutdown -c)
   ```

## Nota de Seguridad:

- Este permiso solo permite ejecutar `shutdown`, no otros comandos administrativos.
- Solo funciona desde la interfaz web cuando el servidor Flask está corriendo.
- El botón tiene una confirmación antes de apagar.

## Alternativa (menos segura):

Si prefieres dar permisos completos de sudo sin contraseña (NO recomendado para producción):
```
orangepi ALL=(ALL) NOPASSWD: ALL
```

