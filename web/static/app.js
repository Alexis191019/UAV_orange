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

// Cargar estado inicial
loadStatus();
loadModelClasses();

// Enviar configuración inicial al backend (threshold por defecto)
setTimeout(() => {
    updateInferenceConfig();
}, 1000); // Esperar 1 segundo para que el servidor esté listo

