(function() {
    'use strict';
    
    const stream = document.getElementById('stream');
    const fpsDisplay = document.getElementById('fpsDisplay');
    const captureModeDisplay = document.getElementById('captureModeDisplay');
    const motionAlert = document.getElementById('motionAlert');
    const recIndicator = document.getElementById('recIndicator');
    const toasts = document.getElementById('toasts');
    
    const captureMode = document.getElementById('captureMode');
    const cameraId = document.getElementById('cameraId');
    const resolution = document.getElementById('resolution');
    const quality = document.getElementById('quality');
    const zoom = document.getElementById('zoom');
    const rotation = document.getElementById('rotation');
    const mirrorH = document.getElementById('mirrorH');
    const mirrorV = document.getElementById('mirrorV');
    const showTimestamp = document.getElementById('showTimestamp');
    const showGrid = document.getElementById('showGrid');
    const motionDetection = document.getElementById('motionDetection');
    const motionThreshold = document.getElementById('motionThreshold');
    const termuxOnly = document.getElementById('termuxOnly');
    
    const qualityLabel = document.getElementById('qualityLabel');
    const zoomLabel = document.getElementById('zoomLabel');
    const thresholdLabel = document.getElementById('thresholdLabel');
    
    const snapshotBtn = document.getElementById('snapshotBtn');
    const burstBtn = document.getElementById('burstBtn');
    const recordBtn = document.getElementById('recordBtn');
    const stopRecordBtn = document.getElementById('stopRecordBtn');
    const flashBtn = document.getElementById('flashBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const themeBtn = document.getElementById('themeBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    
    let isRecording = false;
    let currentMode = 'termux';
    
    // Update labels and send settings in real-time
    quality.addEventListener('input', () => {
        qualityLabel.textContent = quality.value;
        sendSettings();
    });
    
    zoom.addEventListener('input', () => {
        zoomLabel.textContent = parseFloat(zoom.value).toFixed(1);
        sendSettings();
    });
    
    motionThreshold.addEventListener('input', () => {
        thresholdLabel.textContent = motionThreshold.value;
        sendSettings();
    });
    
    function getSettingsFromForm() {
        const [w, h] = resolution.value.split('x');
        return {
            camera_id: parseInt(cameraId.value),
            width: parseInt(w),
            height: parseInt(h),
            quality: parseInt(quality.value),
            zoom: parseFloat(zoom.value),
            rotation: parseInt(rotation.value),
            mirror_h: mirrorH.checked,
            mirror_v: mirrorV.checked,
            show_timestamp: showTimestamp.checked,
            show_grid: showGrid.checked,
            motion_detection: motionDetection.checked,
            motion_threshold: parseInt(motionThreshold.value)
        };
    }
    
    let debounceTimer;
    function sendSettings() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            await apiPost('/settings', getSettingsFromForm());
        }, 200);
    }
    
    // Immediate send for selects and checkboxes
    [resolution, rotation, cameraId].forEach(el => {
        el.addEventListener('change', sendSettings);
    });
    
    [mirrorH, mirrorV, showTimestamp, showGrid, motionDetection].forEach(el => {
        el.addEventListener('change', sendSettings);
    });
    
    // Capture mode change
    captureMode.addEventListener('change', async () => {
        const mode = captureMode.value;
        currentMode = mode;
        
        await apiPost('/command', { 
            command: 'switch_capture', 
            mode: mode 
        });
        
        captureModeDisplay.textContent = `Mode: ${mode === 'browser' ? 'Browser' : 'Termux'}`;
        termuxOnly.style.display = mode === 'termux' ? 'block' : 'none';
        
        showToast(`Switched to ${mode} mode`, 'info');
        
        if (mode === 'browser') {
            showToast('Open /capture on your phone', 'warning');
        }
    });
    
    function showToast(msg, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = msg;
        toasts.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
    
    async function apiGet(path) {
        try {
            const res = await fetch('/api' + path);
            return await res.json();
        } catch(e) { return {}; }
    }
    
    async function apiPost(path, data = {}) {
        try {
            const res = await fetch('/api' + path, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            return await res.json();
        } catch(e) { return {}; }
    }
    
    async function loadSettings() {
        const settings = await apiGet('/settings');
        if (settings.camera_id !== undefined) cameraId.value = settings.camera_id;
        if (settings.width && settings.height) {
            resolution.value = `${settings.width}x${settings.height}`;
        }
        if (settings.quality) { quality.value = settings.quality; qualityLabel.textContent = settings.quality; }
        if (settings.zoom) { zoom.value = settings.zoom; zoomLabel.textContent = settings.zoom.toFixed(1); }
        if (settings.rotation !== undefined) rotation.value = settings.rotation;
        if (settings.mirror_h !== undefined) mirrorH.checked = settings.mirror_h;
        if (settings.mirror_v !== undefined) mirrorV.checked = settings.mirror_v;
        if (settings.show_timestamp !== undefined) showTimestamp.checked = settings.show_timestamp;
        if (settings.show_grid !== undefined) showGrid.checked = settings.show_grid;
        if (settings.motion_detection !== undefined) motionDetection.checked = settings.motion_detection;
        if (settings.motion_threshold) { 
            motionThreshold.value = settings.motion_threshold; 
            thresholdLabel.textContent = settings.motion_threshold;
        }
    }
    
    async function takeSnapshot() {
        const res = await fetch('/snapshot');
        if (res.ok) {
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `snapshot_${Date.now()}.jpg`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Snapshot saved!', 'success');
        }
    }
    
    async function takeBurst() {
        for (let i = 0; i < 5; i++) {
            await takeSnapshot();
            await new Promise(r => setTimeout(r, 300));
        }
    }
    
    async function toggleRecording() {
        if (!isRecording) {
            await fetch('/recording/start');
            isRecording = true;
            recordBtn.style.display = 'none';
            stopRecordBtn.style.display = 'inline-block';
            recIndicator.style.display = 'inline-block';
            showToast('Recording started');
        } else {
            await stopRecording();
        }
    }
    
    async function stopRecording() {
        const res = await fetch('/recording/stop');
        const data = await res.json();
        isRecording = false;
        recordBtn.style.display = 'inline-block';
        stopRecordBtn.style.display = 'none';
        recIndicator.style.display = 'none';
        showToast(`Saved: ${data.filename}`, 'success');
    }
    
    let flashOn = false;
    async function toggleFlash() {
        flashOn = !flashOn;
        await apiPost('/command', { command: flashOn ? 'flash_on' : 'flash_off' });
        showToast(flashOn ? 'Flash ON' : 'Flash OFF');
    }
    
    function toggleFullscreen() {
        const wrapper = document.querySelector('.stream-wrapper');
        if (!document.fullscreenElement) {
            wrapper.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
    
    function toggleTheme() {
        document.body.classList.toggle('light');
        localStorage.setItem('theme', document.body.classList.contains('light') ? 'light' : 'dark');
    }
    
    function downloadZip() {
        window.open('/download/zip', '_blank');
    }
    
    snapshotBtn.addEventListener('click', takeSnapshot);
    burstBtn.addEventListener('click', takeBurst);
    recordBtn.addEventListener('click', toggleRecording);
    stopRecordBtn.addEventListener('click', stopRecording);
    flashBtn.addEventListener('click', toggleFlash);
    fullscreenBtn.addEventListener('click', toggleFullscreen);
    themeBtn.addEventListener('click', toggleTheme);
    downloadBtn.addEventListener('click', downloadZip);
    
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
        if (e.key === ' ') { e.preventDefault(); takeSnapshot(); }
        if (e.key === 'f' || e.key === 'F') { e.preventDefault(); toggleFullscreen(); }
    });
    
    // Update stats and mode display
    setInterval(async () => {
        const stats = await apiGet('/stats');
        fpsDisplay.textContent = `FPS: ${stats.fps || 0}`;
        
        if (stats.motion_detected) {
            motionAlert.style.display = 'inline-block';
            setTimeout(() => motionAlert.style.display = 'none', 1000);
        }
        
        // Update mode display based on server state
        if (stats.use_browser_capture && captureMode.value !== 'browser') {
            captureMode.value = 'browser';
            captureModeDisplay.textContent = 'Mode: Browser';
            termuxOnly.style.display = 'none';
            currentMode = 'browser';
        } else if (!stats.use_browser_capture && captureMode.value !== 'termux') {
            captureMode.value = 'termux';
            captureModeDisplay.textContent = 'Mode: Termux';
            termuxOnly.style.display = 'block';
            currentMode = 'termux';
        }
    }, 500);
    
    if (localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light');
    }
    
    loadSettings();
    showToast('Ready! Change settings in real-time', 'success');
    
})();