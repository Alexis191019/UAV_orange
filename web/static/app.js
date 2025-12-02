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
const availableClassesDiv = document.getElementById('available-classes');
const selectedClassesDiv = document.getElementById('selected-classes');
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
    // Limpiar contenedores
    availableClassesDiv.innerHTML = '';
    selectedClassesDiv.innerHTML = '';
    
    // Obtener todas las clases disponibles
    const allClassNames = Object.values(availableClasses);
    
    if (allClassNames.length === 0) {
        availableClassesDiv.innerHTML = '<p class="no-classes-msg">Selecciona un modelo primero</p>';
        selectedClassesDiv.innerHTML = '<p class="no-classes-msg">Arrastra clases aquí</p>';
        return;
    }
    
    // Renderizar clases disponibles (las que no están seleccionadas)
    const available = allClassNames.filter(name => !selectedClasses.includes(name));
    
    if (available.length === 0) {
        availableClassesDiv.innerHTML = '<p class="no-classes-msg">Todas las clases están seleccionadas</p>';
    } else {
        available.forEach(className => {
            const classItem = createClassItem(className, false);
            availableClassesDiv.appendChild(classItem);
        });
    }
    
    // Renderizar clases seleccionadas
    if (selectedClasses.length === 0) {
        selectedClassesDiv.innerHTML = '<p class="no-classes-msg">Arrastra clases aquí</p>';
    } else {
        selectedClasses.forEach(className => {
            const classItem = createClassItem(className, true);
            selectedClassesDiv.appendChild(classItem);
        });
    }
}

function createClassItem(className, isSelected) {
    const div = document.createElement('div');
    div.className = `class-item ${isSelected ? 'selected' : ''}`;
    div.draggable = true;
    div.dataset.className = className;
    
    const color = getClassColor(className);
    const displayName = getClassDisplayName(className);
    
    div.innerHTML = `
        <div class="class-color" style="background-color: rgb(${color[0]}, ${color[1]}, ${color[2]})"></div>
        <span class="class-name">${displayName}</span>
        ${isSelected ? '<button class="class-remove" onclick="removeClass(\'' + className + '\')">×</button>' : ''}
    `;
    
    // Eventos de drag and drop
    div.addEventListener('dragstart', handleDragStart);
    div.addEventListener('dragover', handleDragOver);
    div.addEventListener('drop', handleDrop);
    div.addEventListener('dragend', handleDragEnd);
    
    return div;
}

let draggedElement = null;

function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', this.dataset.className);
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    const className = e.dataTransfer.getData('text/plain');
    const isSelectedArea = this.closest('#selected-classes') !== null;
    const isAvailableArea = this.closest('#available-classes') !== null;
    
    if (isSelectedArea && !selectedClasses.includes(className)) {
        // Agregar a seleccionadas
        selectedClasses.push(className);
        updateInferenceConfig();
    } else if (isAvailableArea && selectedClasses.includes(className)) {
        // Remover de seleccionadas
        selectedClasses = selectedClasses.filter(c => c !== className);
        updateInferenceConfig();
    }
    
    renderClasses();
    return false;
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    draggedElement = null;
}

function removeClass(className) {
    selectedClasses = selectedClasses.filter(c => c !== className);
    renderClasses();
    updateInferenceConfig();
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

// Cargar estado inicial
loadStatus();
loadModelClasses();

// Enviar configuración inicial al backend (threshold por defecto)
setTimeout(() => {
    updateInferenceConfig();
}, 1000); // Esperar 1 segundo para que el servidor esté listo

