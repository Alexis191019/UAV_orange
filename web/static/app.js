// Conexión WebSocket
const socket = io();



// Estado de la aplicación
let inferenceActive = false;
let statusInterval = null;
let currentModel = 'uav';

// Elementos del DOM
const videoFrame = document.getElementById('video-frame');
const videoPlaceholder = document.getElementById('video-placeholder');
const btnInferencia = document.getElementById('btn-inferencia');
const btnHotspot = document.getElementById('btn-hotspot');
const btnShutdown = document.getElementById('btn-shutdown');
const connectionStatus = document.getElementById('connection-status');
const statusDot = connectionStatus.querySelector('.status-dot');

// Elementos de métricas
const fpsValue = document.getElementById('fps-value');
const fpsAvgValue = document.getElementById('fps-avg-value');
const framesValue = document.getElementById('frames-value');

// Elementos de estado
const hotspotStatus = document.getElementById('hotspot-status');
const mediamtxStatus = document.getElementById('mediamtx-status');
const streamStatus = document.getElementById('stream-status');
const detectionsContent = document.getElementById('detections-content');



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
        videoFrame.src = 'data:image/jpeg;base64,' + data.frame;
        videoPlaceholder.style.display = 'none';
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
        } else {
            alert('Error: ' + (data.error || 'No se pudo detener la inferencia'));
        }
    } catch (error) {
        console.error('Error al detener inferencia:', error);
        alert('Error de conexión al detener inferencia');
    }
}

async function toggleHotspot() {
    try {
        const response = await fetch('/api/hotspot/toggle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (response.ok) {
            loadStatus(); // Recargar estado
            console.log('Hotspot toggled:', data.status);
        } else {
            alert('Error: ' + (data.error || 'No se pudo alternar el hotspot'));
        }
    } catch (error) {
        console.error('Error al alternar hotspot:', error);
        alert('Error de conexión al alternar hotspot');
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
        
        // Actualizar estado del sistema
        if (data.hotspot_active) {
            const hotspotText = data.hotspot_name 
                ? `${data.hotspot_name} - IP: ${data.hotspot_ip || 'N/A'}`
                : 'Activo';
            hotspotStatus.textContent = hotspotText;
            btnHotspot.textContent = 'Desactivar Hotspot';
            btnHotspot.disabled = false;
        } else {
            hotspotStatus.textContent = 'Desactivado';
            btnHotspot.textContent = 'Activar Hotspot';
            btnHotspot.disabled = false;
        }
        
        if (data.rtmp_url) {
            mediamtxStatus.textContent = `Transmitir a: ${data.rtmp_url}`;
        } else {
            mediamtxStatus.textContent = 'IP: 127.0.0.1:1935';
        }
        
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
            // Aquí puedes actualizar la UI para mostrar el modelo seleccionado
            alert(`Modelo cambiado a: ${modelName}`);
        } else {
            alert('Error: ' + (data.error || 'No se pudo cambiar el modelo'));
        }
    } catch (error) {
        console.error('Error al cambiar modelo:', error);
        alert('Error de conexión al cambiar modelo');
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

btnHotspot.addEventListener('click', toggleHotspot);
btnShutdown.addEventListener('click', shutdownSystem);

// Cargar estado inicial
loadStatus();

