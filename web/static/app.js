// Conexión WebSocket
const socket = io();



// Estado de la aplicación
let inferenceActive = false;
let statusInterval = null;
let currentModel = 'uav';
let availableClasses = {}; // Diccionario {id: nombre} de clases disponibles
let selectedClasses = []; // Lista de nombres de clases seleccionadas
let classColors = {}; // Diccionario {nombre_clase: [R, G, B]} para colores
let confidenceThreshold = 0.3; // Threshold de confianza (0-1)

// Variables para grabación de video
let mediaRecorder = null;
let recordedChunks = [];
let recordingCanvas = null;
let recordingContext = null;
let recordingStream = null;
let isRecording = false;
let recordedFrames = []; // Almacenar frames individuales para MP4
let recordingStartTime = null;

// Traducción de clases al español
const classTranslations = {
    'pedestrian': 'Persona',
    'people': 'Gente',
    'bicycle': 'Bicicleta',
    'car': 'Auto',
    'van': 'Camioneta',
    'truck': 'Camión',
    'tricycle': 'Triciclo',
    'awning-tricycle': 'Triciclo con toldo',
    'bus': 'Autobús',
    'motor': 'Motocicleta'
};

// Generar colores para las clases (paleta de colores)
const colorPalette = [
    [0, 100, 255],    // Azul
    [255, 0, 0],      // Rojo
    [0, 255, 0],      // Verde
    [255, 255, 0],    // Amarillo
    [255, 0, 255],    // Magenta
    [0, 255, 255],    // Cyan
    [255, 128, 0],    // Naranja
    [128, 0, 255],    // Púrpura
    [255, 0, 128],    // Rosa
    [0, 128, 255],    // Azul claro
    [128, 255, 0],    // Verde lima
    [255, 128, 128]   // Rosa claro
];

// Elementos del DOM
const videoFrame = document.getElementById('video-frame');
const videoPlaceholder = document.getElementById('video-placeholder');
const videoContainer = document.getElementById('video-container');
const btnFullscreen = document.getElementById('btn-fullscreen');
const btnInferencia = document.getElementById('btn-inferencia');
const btnShutdown = document.getElementById('btn-shutdown');
const connectionStatus = document.getElementById('connection-status');
const statusDot = connectionStatus.querySelector('.status-dot');

// Crear canvas oculto para grabación
recordingCanvas = document.createElement('canvas');
recordingCanvas.style.display = 'none';
recordingCanvas.width = 640;
recordingCanvas.height = 480;
document.body.appendChild(recordingCanvas);
recordingContext = recordingCanvas.getContext('2d');

// Elementos de métricas
const fpsValue = document.getElementById('fps-value');
const fpsAvgValue = document.getElementById('fps-avg-value');
const framesValue = document.getElementById('frames-value');

// Elementos de estado
const streamStatus = document.getElementById('stream-status');
const detectionsContent = document.getElementById('detections-content');

// Elementos de clases y confianza
const classesListDiv = document.getElementById('classes-list');
const confidenceSlider = document.getElementById('confidence-slider');
const confidenceValue = document.getElementById('confidence-value');



// Eventos WebSocket
socket.on('connect', () => {
    console.log('Conectado al servidor');
    updateConnectionStatus(true);
    loadStatus();
    startStatusPolling();
});

socket.on('disconnect', () => {
    console.log('Desconectado del servidor');
    updateConnectionStatus(false);
    stopStatusPolling();
});

socket.on('connected', (data) => {
    console.log('Mensaje del servidor:', data.message);
});

socket.on('frame', (data) => {
    // Manejar error de stream
    if (data.error) {
        videoPlaceholder.textContent = data.error;
        videoPlaceholder.style.display = 'block';
        videoFrame.src = '';
        return;
    }
    
    // Mostrar frame
    if (data.frame) {
        const frameSrc = 'data:image/jpeg;base64,' + data.frame;
        videoFrame.src = frameSrc;
        videoPlaceholder.style.display = 'none';
        
        // Si estamos grabando, capturar el frame en el canvas
        if (isRecording && recordingContext) {
            const img = new Image();
            img.crossOrigin = 'anonymous'; // Permitir CORS si es necesario
            img.onload = () => {
                try {
                    // Limpiar canvas antes de dibujar
                    recordingContext.clearRect(0, 0, recordingCanvas.width, recordingCanvas.height);
                    // Dibujar el frame en el canvas
                    recordingContext.drawImage(img, 0, 0, recordingCanvas.width, recordingCanvas.height);
                    
                    // Si usamos MediaRecorder, ya está grabando automáticamente
                    // Si no, guardar frame individual para MP4
                    if (!mediaRecorder || mediaRecorder.state !== 'recording') {
                        // Guardar frame como imagen para luego crear MP4
                        const timestamp = Date.now() - (recordingStartTime || Date.now());
                        recordingCanvas.toBlob((blob) => {
                            if (blob) {
                                recordedFrames.push({
                                    blob: blob,
                                    timestamp: timestamp
                                });
                            }
                        }, 'image/jpeg', 0.92);
                    }
                } catch (error) {
                    console.error('Error al dibujar frame en canvas:', error);
                }
            };
            img.onerror = () => {
                console.error('Error al cargar imagen para grabación');
            };
            img.src = frameSrc;
        }
    } else {
        videoPlaceholder.textContent = 'Esperando video...';
        videoPlaceholder.style.display = 'block';
    }
    
    // Actualizar métricas
    if (data.fps !== undefined) {
        fpsValue.textContent = data.fps.toFixed(1);
    }
    if (data.fps_prom !== undefined) {
        fpsAvgValue.textContent = data.fps_prom.toFixed(1);
    }
    if (data.frames !== undefined) {
        framesValue.textContent = data.frames;
    }
    
    // Actualizar detecciones
    updateDetections(data.detecciones || {});
});

// Funciones de UI
function updateConnectionStatus(connected) {
    if (connected) {
        statusDot.classList.add('connected');
        connectionStatus.querySelector('span:last-child').textContent = 'Conectado';
    } else {
        statusDot.classList.remove('connected');
        connectionStatus.querySelector('span:last-child').textContent = 'Desconectado';
    }
}

function updateDetections(detecciones) {
    if (!detecciones || Object.keys(detecciones).length === 0) {
        detectionsContent.textContent = inferenceActive 
            ? 'No se detectaron objetos en este frame.' 
            : 'Inferencia pausada. Activa la inferencia para ver detecciones.';
        return;
    }
    
    // Ordenar por cantidad (mayor a menor) y luego alfabéticamente
    const items = Object.entries(detecciones)
        .sort((a, b) => {
            if (b[1] !== a[1]) return b[1] - a[1]; // Por cantidad
            return a[0].localeCompare(b[0]); // Alfabético
        });
    
    let texto = 'Objetos detectados:\n';
    items.forEach(([nombre, cantidad]) => {
        const nombreFormateado = nombre.charAt(0).toUpperCase() + nombre.slice(1);
        texto += `  • ${cantidad} ${nombreFormateado}\n`;
    });
    
    detectionsContent.textContent = texto;
}

// Funciones de grabación de video
function startRecording() {
    if (isRecording) {
        console.log('Ya se está grabando');
        return;
    }
    
    try {
        // Verificar soporte de MediaRecorder
        if (!navigator.mediaDevices || !MediaRecorder) {
            alert('Tu navegador no soporta la grabación de video. Por favor, usa Chrome, Firefox o Edge.');
            return;
        }
        
        recordedChunks = [];
        
        // Asegurar que el canvas tenga el tamaño correcto
        if (videoFrame.complete && videoFrame.naturalWidth > 0) {
            // Si la imagen ya está cargada, usar su tamaño real
            recordingCanvas.width = videoFrame.naturalWidth || 640;
            recordingCanvas.height = videoFrame.naturalHeight || 480;
        } else {
            // Usar tamaño por defecto
            recordingCanvas.width = 640;
            recordingCanvas.height = 480;
        }
        
        // Obtener stream del canvas (ajustar FPS según el stream real)
        const fps = 30; // FPS de grabación
        recordingStream = recordingCanvas.captureStream(fps);
        
        // Configurar MediaRecorder
        const options = {
            mimeType: 'video/webm;codecs=vp9',
            videoBitsPerSecond: 2500000 // 2.5 Mbps
        };
        
        // Intentar con codec vp9, si falla usar vp8
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'video/webm;codecs=vp8';
        }
        
        // Si vp8 tampoco está disponible, usar el tipo por defecto
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'video/webm';
        }
        
        mediaRecorder = new MediaRecorder(recordingStream, options);
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data && event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = () => {
            console.log('MediaRecorder detenido. Chunks guardados:', recordedChunks.length);
        };
        
        mediaRecorder.onerror = (event) => {
            console.error('Error en MediaRecorder:', event.error);
            alert('Error al grabar video: ' + (event.error?.message || 'Error desconocido'));
            stopRecording();
        };
        
        // Iniciar grabación
        mediaRecorder.start(1000); // Capturar datos cada segundo
        isRecording = true;
        recordingStartTime = Date.now();
        recordedFrames = []; // Limpiar frames anteriores
        console.log('Grabación iniciada - Resolución:', recordingCanvas.width, 'x', recordingCanvas.height);
        
    } catch (error) {
        console.error('Error al iniciar grabación:', error);
        alert('No se pudo iniciar la grabación de video: ' + error.message);
        isRecording = false;
    }
}

function stopRecording() {
    if (!isRecording || !mediaRecorder) return;
    
    try {
        if (mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        
        if (recordingStream) {
            recordingStream.getTracks().forEach(track => track.stop());
            recordingStream = null;
        }
        
        isRecording = false;
        console.log('Grabación detenida');
        
    } catch (error) {
        console.error('Error al detener grabación:', error);
        isRecording = false;
    }
}

async function downloadVideo() {
    if (recordedChunks.length === 0 && recordedFrames.length === 0) {
        alert('No hay video grabado para descargar');
        return;
    }
    
    try {
        // Mostrar mensaje de procesamiento
        const processingMsg = document.createElement('div');
        processingMsg.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 10px; z-index: 10000; text-align: center;';
        processingMsg.innerHTML = 'Convirtiendo video a MP4 en el servidor...<br>Por favor espera.';
        document.body.appendChild(processingMsg);
        
        // Si tenemos chunks de MediaRecorder, enviar al servidor para conversión
        if (recordedChunks.length > 0) {
            const webmBlob = new Blob(recordedChunks, { type: 'video/webm' });
            
            // Crear FormData para enviar el video
            const formData = new FormData();
            formData.append('video', webmBlob, 'recording.webm');
            
            try {
                // Enviar al servidor para conversión
                const response = await fetch('/api/video/convert', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    // El servidor envía el MP4 directamente como descarga
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    
                    // Obtener nombre del archivo del header Content-Disposition o generar uno
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = 'deteccion-uav.mp4';
                    if (contentDisposition) {
                        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                        if (filenameMatch && filenameMatch[1]) {
                            filename = filenameMatch[1].replace(/['"]/g, '');
                        }
                    }
                    
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    
                    // Liberar URL
                    setTimeout(() => {
                        URL.revokeObjectURL(url);
                    }, 100);
                    
                    // Remover mensaje de procesamiento
                    document.body.removeChild(processingMsg);
                    
                    // Limpiar
                    recordedChunks = [];
                    recordedFrames = [];
                    
                    console.log('Video descargado en formato MP4');
                    return;
                } else {
                    // Error en el servidor
                    const errorData = await response.json().catch(() => ({ error: 'Error desconocido' }));
                    throw new Error(errorData.error || 'Error al convertir video en el servidor');
                }
            } catch (error) {
                console.error('Error al convertir video:', error);
                document.body.removeChild(processingMsg);
                
                // Si falla la conversión, ofrecer descargar como WebM
                const userAgent = navigator.userAgent;
                const isIOS = /iPad|iPhone|iPod/.test(userAgent);
                
                if (isIOS) {
                    const message = 'No se pudo convertir a MP4 en el servidor.\n\n' +
                                  'El video se descargará como WebM (formato no nativo en iPad).\n\n' +
                                  'Opciones para verlo en iPad:\n' +
                                  '1. Usar la app "WebM Video Reader MP4 Convert" (gratis en App Store)\n' +
                                  '2. Convertir online usando un servicio como cloudconvert.com\n' +
                                  '3. Transferir a una computadora y convertir allí\n\n' +
                                  '¿Deseas descargarlo como WebM de todas formas?';
                    
                    if (confirm(message)) {
                        downloadBlob(webmBlob, 'webm');
                    }
                } else {
                    alert('Error al convertir video: ' + error.message + '\n\nSe descargará como WebM.');
                    downloadBlob(webmBlob, 'webm');
                }
                return;
            }
        } else {
            // No hay chunks, solo frames (no debería pasar con MediaRecorder)
            document.body.removeChild(processingMsg);
            alert('No se pudo crear el video. Por favor intenta de nuevo.');
        }
        
    } catch (error) {
        console.error('Error al descargar video:', error);
        alert('Error al descargar el video: ' + error.message);
    }
}

async function createMP4FromFrames(frames) {
    // Esta función crearía un MP4 desde frames individuales
    // Por ahora, retornamos null ya que requiere una librería compleja
    // La mejor solución es usar ffmpeg.wasm o procesar en el servidor
    console.log('Crear MP4 desde frames no está implementado aún');
    return null;
}

function downloadBlob(blob, extension) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Generar nombre de archivo con fecha y hora
    const now = new Date();
    const timestamp = now.toISOString().replace(/[:.]/g, '-').slice(0, -5);
    a.download = `deteccion-uav-${timestamp}.${extension}`;
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    // Liberar URL después de un tiempo
    setTimeout(() => {
        URL.revokeObjectURL(url);
    }, 100);
}

async function convertWebMToMP4(webmBlob) {
    // Nota: La conversión real de WebM a MP4 en el navegador requiere ffmpeg.wasm
    // que es una librería grande (~20MB). Por ahora, retornamos null y el usuario
    // puede descargar como WebM o usar una app de conversión en iPad.
    
    // Para una solución completa, se recomienda:
    // 1. Usar ffmpeg.wasm (pesado pero completo)
    // 2. Procesar la conversión en el servidor
    // 3. Usar una app de conversión en el dispositivo del cliente
    
    console.log('Conversión WebM a MP4 requiere ffmpeg.wasm o procesamiento en servidor');
    return null;
}

// Funciones de API
async function startInference() {
    try {
        const response = await fetch('/api/inference/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (response.ok) {
            inferenceActive = true;
            btnInferencia.textContent = 'Detener Inferencia';
            btnInferencia.classList.add('active');
            
            // Iniciar grabación automáticamente
            startRecording();
            
            console.log('Inferencia iniciada');
        } else {
            alert('Error: ' + (data.error || 'No se pudo iniciar la inferencia'));
        }
    } catch (error) {
        console.error('Error al iniciar inferencia:', error);
        alert('Error de conexión al iniciar inferencia');
    }
}

async function stopInference() {
    try {
        // Detener grabación primero
        stopRecording();
        
        const response = await fetch('/api/inference/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (response.ok) {
            inferenceActive = false;
            btnInferencia.textContent = 'Iniciar Inferencia';
            btnInferencia.classList.remove('active');
            updateDetections({}); // Limpiar detecciones
            console.log('Inferencia detenida');
            
            // Esperar un momento para que MediaRecorder termine de procesar
            setTimeout(() => {
                // Mostrar diálogo para guardar video
                if (recordedChunks.length > 0) {
                    const saveVideo = confirm(
                        '¿Deseas guardar el video de las detecciones?\n\n' +
                        'El video se descargará en tu dispositivo.'
                    );
                    
                    if (saveVideo) {
                        downloadVideo();
                    } else {
                        // Limpiar chunks si no quiere guardar
                        recordedChunks = [];
                    }
                } else {
                    console.log('No hay video grabado para guardar');
                }
            }, 1000); // Aumentar tiempo de espera para asegurar que MediaRecorder termine
            
        } else {
            alert('Error: ' + (data.error || 'No se pudo detener la inferencia'));
        }
    } catch (error) {
        console.error('Error al detener inferencia:', error);
        alert('Error de conexión al detener inferencia');
    }
}


async function shutdownSystem() {
    if (!confirm('¿Estás seguro de que deseas apagar la Orange Pi?\n\nEsto cerrará el servidor y apagará el dispositivo.')) {
        return;
    }
    
    try {
        btnShutdown.disabled = true;
        btnShutdown.textContent = 'Apagando...';
        
        const response = await fetch('/api/shutdown', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (response.ok) {
            alert('Sistema apagándose... La Orange Pi se apagará en unos segundos.');
            // El servidor se cerrará, así que la conexión se perderá
        } else {
            alert('Error: ' + (data.error || 'No se pudo apagar el sistema'));
            btnShutdown.disabled = false;
            btnShutdown.textContent = 'Apagar Orange Pi';
        }
    } catch (error) {
        console.error('Error al apagar sistema:', error);
        alert('Error de conexión. El sistema puede estar apagándose...');
    }
}

async function loadStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Actualizar estado de inferencia
        inferenceActive = data.inference || false;
        btnInferencia.textContent = inferenceActive ? 'Detener Inferencia' : 'Iniciar Inferencia';
        btnInferencia.disabled = !data.model_loaded;
        if (inferenceActive) {
            btnInferencia.classList.add('active');
        }
        
        // Actualizar estado del stream
        streamStatus.textContent = data.stream_connected ? 'Conectado' : 'Desconectado';
        
        // Actualizar métricas
        if (data.fps_actual !== undefined) {
            fpsValue.textContent = data.fps_actual.toFixed(1);
        }
        if (data.fps_promedio !== undefined) {
            fpsAvgValue.textContent = data.fps_promedio.toFixed(1);
        }
        if (data.frames !== undefined) {
            framesValue.textContent = data.frames;
        }
        
    } catch (error) {
        console.error('Error al cargar estado:', error);
    }
}

function startStatusPolling() {
    // Actualizar estado cada 5 segundos
    statusInterval = setInterval(loadStatus, 5000);
}

function stopStatusPolling() {
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

// Función para cambiar el modelo
async function changeModel(modelName) {
    try {
        const response = await fetch('/api/model/change', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: modelName })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            console.log('Modelo cambiado a:', modelName);
            currentModel = modelName;
            
            // Cargar clases disponibles del nuevo modelo
            await loadModelClasses();
            
            // Limpiar clases seleccionadas al cambiar modelo
            selectedClasses = [];
            classColors = {};
            renderClasses();
            updateInferenceConfig();
        } else {
            alert('Error: ' + (data.error || 'No se pudo cambiar el modelo'));
        }
    } catch (error) {
        console.error('Error al cambiar modelo:', error);
        alert('Error de conexión al cambiar modelo');
    }
}

async function loadModelClasses() {
    try {
        const response = await fetch('/api/model/classes');
        const data = await response.json();
        
        if (response.ok && data.classes) {
            availableClasses = data.classes;
            renderClasses();
        } else {
            console.error('Error al cargar clases:', data.error);
            availableClasses = {};
            renderClasses();
        }
    } catch (error) {
        console.error('Error al cargar clases:', error);
        availableClasses = {};
        renderClasses();
    }
}

function getClassDisplayName(className) {
    // Retorna el nombre traducido o el original si no hay traducción
    return classTranslations[className.toLowerCase()] || className;
}

function getClassColor(className) {
    // Si ya tiene color asignado, retornarlo
    if (classColors[className]) {
        return classColors[className];
    }
    
    // Asignar un color de la paleta basado en el índice
    const classList = Object.values(availableClasses);
    const index = classList.indexOf(className);
    const colorIndex = index % colorPalette.length;
    const color = colorPalette[colorIndex];
    
    // Guardar el color
    classColors[className] = color;
    return color;
}

function renderClasses() {
    // Limpiar contenedor
    classesListDiv.innerHTML = '';
    
    // Obtener todas las clases disponibles
    const allClassNames = Object.values(availableClasses);
    
    if (allClassNames.length === 0) {
        classesListDiv.innerHTML = '<p class="no-classes-msg">Selecciona un modelo primero</p>';
        return;
    }
    
    // Renderizar todas las clases con checkboxes
    allClassNames.forEach(className => {
        const classItem = createClassItem(className);
        classesListDiv.appendChild(classItem);
    });
}

function createClassItem(className) {
    const div = document.createElement('div');
    const isSelected = selectedClasses.includes(className);
    div.className = `class-item ${isSelected ? 'selected' : ''}`;
    div.dataset.className = className;
    
    const color = getClassColor(className);
    const displayName = getClassDisplayName(className);
    
    // Crear estructura del checkbox
    const checkboxContainer = document.createElement('div');
    checkboxContainer.className = 'class-checkbox';
    
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = `checkbox-${className.replace(/\s+/g, '-').replace(/[^a-zA-Z0-9-]/g, '')}`;
    checkbox.checked = isSelected;
    
    const checkmark = document.createElement('span');
    checkmark.className = 'checkmark';
    
    checkboxContainer.appendChild(checkbox);
    checkboxContainer.appendChild(checkmark);
    
    // Crear color indicator
    const colorDiv = document.createElement('div');
    colorDiv.className = 'class-color';
    colorDiv.style.backgroundColor = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
    
    // Crear nombre
    const nameSpan = document.createElement('span');
    nameSpan.className = 'class-name';
    nameSpan.textContent = displayName;
    
    // Ensamblar elementos
    div.appendChild(checkboxContainer);
    div.appendChild(colorDiv);
    div.appendChild(nameSpan);
    
    // Función para actualizar el estado
    const updateSelection = (checked) => {
        if (checked) {
            // Agregar a seleccionadas si no está ya
            if (!selectedClasses.includes(className)) {
                selectedClasses.push(className);
            }
        } else {
            // Remover de seleccionadas
            selectedClasses = selectedClasses.filter(c => c !== className);
        }
        // Actualizar clase visual
        div.classList.toggle('selected', checked);
        // Sincronizar checkbox
        checkbox.checked = checked;
        // Actualizar configuración en el backend
        updateInferenceConfig();
    };
    
    // Manejar clicks en el checkbox directamente
    const handleCheckboxChange = (e) => {
        if (e) {
            e.stopPropagation();
        }
        updateSelection(checkbox.checked);
    };
    
    // Evento de cambio en el checkbox
    checkbox.addEventListener('change', handleCheckboxChange);
    
    // Evento click en el checkbox (para asegurar que funcione)
    checkbox.addEventListener('click', (e) => {
        e.stopPropagation();
    });
    
    // Evento click en el contenedor del checkbox (incluyendo el checkmark visual)
    checkboxContainer.addEventListener('click', (e) => {
        e.stopPropagation();
        // Si el click fue directamente en el input, no hacer nada (ya se maneja)
        if (e.target === checkbox) {
            return;
        }
        // Si el click fue en el contenedor o checkmark, toggle el checkbox
        checkbox.checked = !checkbox.checked;
        handleCheckboxChange(null);
    });
    
    // Permitir hacer click en toda la fila para activar/desactivar
    div.addEventListener('click', (e) => {
        // Si el click fue en el checkbox o su contenedor, no hacer nada
        // (ya se maneja arriba)
        if (checkboxContainer.contains(e.target)) {
            return;
        }
        
        // Si el click fue en otra parte de la fila, toggle el checkbox
        checkbox.checked = !checkbox.checked;
        handleCheckboxChange(null);
    });
    
    return div;
}

async function updateInferenceConfig() {
    try {
        const response = await fetch('/api/inference/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                selected_classes: selectedClasses.length > 0 ? selectedClasses : null,
                conf_threshold: confidenceThreshold,
                class_colors: Object.keys(classColors).length > 0 ? classColors : {}
            })
        });
        
        const data = await response.json();
        if (response.ok) {
            console.log('Configuración de inferencia actualizada');
        } else {
            console.error('Error al actualizar configuración:', data.error);
        }
    } catch (error) {
        console.error('Error al actualizar configuración:', error);
    }
}

// Manejo del dropdown de modelos (click en lugar de hover)
const modelSelector = document.getElementById('model-selector');

if (modelSelector) {
    const dropbtn = modelSelector.querySelector('.dropbtn');
    const dropdownContent = modelSelector.querySelector('.dropdown-content');
    const modelOptions = modelSelector.querySelectorAll('a[data-model]');
    
    // Toggle del dropdown al hacer click en el botón
    dropbtn.addEventListener('click', (event) => {
        event.stopPropagation();
        modelSelector.classList.toggle('show');
    });
    
    // Cerrar el dropdown al hacer click fuera
    document.addEventListener('click', (event) => {
        if (!modelSelector.contains(event.target)) {
            modelSelector.classList.remove('show');
        }
    });
    
    // Manejar selección de modelo
    modelOptions.forEach(option => {
        option.addEventListener('click', (event) => {
            event.preventDefault();
            event.stopPropagation();
            const selectedModel = event.target.getAttribute('data-model');
            currentModel = selectedModel;
            changeModel(selectedModel);
            // Cerrar el dropdown después de seleccionar
            modelSelector.classList.remove('show');
        });
    });
} else {
    console.warn('No se encontró el selector de modelos en el DOM');
}



// Event listeners
btnInferencia.addEventListener('click', () => {
    if (inferenceActive) {
        stopInference();
    } else {
        startInference();
    }
});

btnShutdown.addEventListener('click', shutdownSystem);

// Event listener para el slider de confianza
confidenceSlider.addEventListener('input', (e) => {
    const value = parseInt(e.target.value);
    confidenceThreshold = value / 100.0; // Convertir de 0-100 a 0-1
    confidenceValue.textContent = value + '%';
    updateInferenceConfig();
});

// Funcionalidad de pantalla completa
function toggleFullscreen() {
    if (!document.fullscreenElement && 
        !document.webkitFullscreenElement && 
        !document.mozFullScreenElement && 
        !document.msFullscreenElement) {
        // Entrar en pantalla completa
        if (videoContainer.requestFullscreen) {
            videoContainer.requestFullscreen();
        } else if (videoContainer.webkitRequestFullscreen) {
            videoContainer.webkitRequestFullscreen();
        } else if (videoContainer.mozRequestFullScreen) {
            videoContainer.mozRequestFullScreen();
        } else if (videoContainer.msRequestFullscreen) {
            videoContainer.msRequestFullscreen();
        }
    } else {
        // Salir de pantalla completa
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

function updateFullscreenButton() {
    const isFullscreen = !!(document.fullscreenElement || 
                            document.webkitFullscreenElement || 
                            document.mozFullScreenElement || 
                            document.msFullscreenElement);
    
    const enterIcon = btnFullscreen.querySelector('.fullscreen-enter');
    const exitIcon = btnFullscreen.querySelector('.fullscreen-exit');
    
    if (isFullscreen) {
        // Mostrar icono de salir
        enterIcon.style.display = 'none';
        exitIcon.style.display = 'block';
        btnFullscreen.title = 'Salir de pantalla completa (ESC)';
    } else {
        // Mostrar icono de entrar
        enterIcon.style.display = 'block';
        exitIcon.style.display = 'none';
        btnFullscreen.title = 'Pantalla completa';
    }
}

// Event listener para el botón de pantalla completa
if (btnFullscreen) {
    btnFullscreen.addEventListener('click', toggleFullscreen);
    
    // Escuchar cambios en el estado de pantalla completa
    document.addEventListener('fullscreenchange', updateFullscreenButton);
    document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
    document.addEventListener('mozfullscreenchange', updateFullscreenButton);
    document.addEventListener('MSFullscreenChange', updateFullscreenButton);
    
    // Permitir salir de pantalla completa con la tecla ESC (ya está implementado por defecto)
    // También podemos agregar soporte para la tecla F11
    document.addEventListener('keydown', (e) => {
        if (e.key === 'F11') {
            e.preventDefault();
            toggleFullscreen();
        }
    });
}

// Limpiar grabación si el usuario cierra la página
window.addEventListener('beforeunload', () => {
    if (isRecording) {
        stopRecording();
    }
});

// Cargar estado inicial
loadStatus();
loadModelClasses();

// Enviar configuración inicial al backend (threshold por defecto)
setTimeout(() => {
    updateInferenceConfig();
}, 1000); // Esperar 1 segundo para que el servidor esté listo

