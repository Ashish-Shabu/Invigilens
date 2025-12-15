const API_URL = 'http://localhost:5000/api/alerts';
const EVIDENCE_BASE_URL = 'http://localhost:5000/evidence/';

// State
let alerts = [];

document.addEventListener('DOMContentLoaded', () => {
    // Check which page we are on
    const isDashboard = document.getElementById('dashboard-feed');
    const isAlertsPage = document.getElementById('alerts-grid');

    if (isDashboard) {
        initMonitoringUI();
        initVideoStream(); // Start Video Handler
        // Poll for new alerts every 2 seconds
        loadDashboardFeed();
        setInterval(loadDashboardFeed, 2000);
    }


    if (isAlertsPage) {
        loadReviewPage();
    }
});

// --- Dashboard Logic ---
async function loadDashboardFeed() {
    try {
        const res = await fetch(`${API_URL}?limit=10`);
        const data = await res.json();

        // Filter out cleared notifications
        const lastCleared = localStorage.getItem('lastClearedTime');
        const visibleAlerts = data.filter(alert => {
            if (!lastCleared) return true;
            return new Date(alert.timestamp).getTime() > parseInt(lastCleared);
        });

        // Render simple list
        const container = document.getElementById('dashboard-feed');
        if (!container) return;

        // If no data
        if (visibleAlerts.length === 0) {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:20px;">No recent alerts.</div>';
            return;
        }

        container.innerHTML = visibleAlerts.map(alert => `
            <div class="alert-item ${alert.violationType === 'Normal' ? 'normal' : ''}">
                <div class="alert-header">
                    <span>${alert.violationType}</span>
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</span>
                </div>
                <div style="font-size:0.85rem; color:var(--text-secondary);">Student: ${alert.studentId}</div>
                <div class="alert-confidence">${(alert.confidence * 100).toFixed(1)}% Confidence</div>
            </div>
        `).join('');

    } catch (error) {
        console.error("Error fetching alerts:", error);
    }
}

// --- Alerts Review Page Logic ---
async function loadReviewPage() {
    try {
        // Fetch only pending alerts
        const res = await fetch(`${API_URL}?status=pending`);
        const data = await res.json();

        const container = document.getElementById('alerts-grid');
        if (!container) return;

        if (data.length === 0) {
            container.innerHTML = '<h3 style="grid-column: 1/-1; text-align:center; color:var(--text-secondary);">No pending alerts to review. Great job!</h3>';
            return;
        }

        container.innerHTML = data.map(alert => {
            const isVideo = alert.evidencePath && (alert.evidencePath.endsWith('.mp4') || alert.evidencePath.endsWith('.webm'));
            const evidenceUrl = alert.evidencePath
                ? EVIDENCE_BASE_URL + alert.evidencePath
                : 'assets/placeholder.png'; // Fallback

            let mediaElement = '';
            if (isVideo) {
                mediaElement = `<video src="${evidenceUrl}" class="alert-img" controls></video>`;
            } else {
                mediaElement = `<img src="${evidenceUrl}" class="alert-img" alt="Evidence" onerror="this.src='https://via.placeholder.com/400x200?text=No+Evidence'">`;
            }

            return `
            <div class="alert-card" id="card-${alert._id}">
                ${mediaElement}
                <div class="card-body">
                    <div class="card-title-row">
                        <h3 class="card-title">${alert.violationType}</h3>
                        <span class="badge badge-red">${(alert.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div class="card-subtitle">
                        ID: ${alert.studentId} • ${new Date(alert.timestamp).toLocaleString()}
                    </div>
                    <div class="actions">
                        <button class="btn btn-accept" onclick="updateStatus('${alert._id}', 'verified')">Verify Malpractice</button>
                        <button class="btn btn-reject" onclick="updateStatus('${alert._id}', 'rejected')">Reject (False Alarm)</button>
                    </div>
                </div>
            </div>
            `;
        }).join('');

    } catch (error) {
        console.error("Error loading review page:", error);
    }
}

async function updateStatus(id, newStatus) {
    try {
        const res = await fetch(`${API_URL}/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (res.ok) {
            // Remove card with animation
            const card = document.getElementById(`card-${id}`);
            if (card) {
                card.style.opacity = '0';
                card.style.transform = 'scale(0.9)';
                setTimeout(() => card.remove(), 300);
            }
        }
    } catch (error) {
        alert("Failed to update status");
    }
}

// --- Monitoring Control ---
let isMonitoring = false;
const socket = io('http://localhost:5000'); // Ensure socket is accessible here

function initMonitoringUI() {
    const btn = document.getElementById('monitor-toggle');
    const statusDiv = document.getElementById('system-status');
    const pulse = statusDiv.querySelector('.pulse');

    if (!btn) return; // Guard clause if elements not found

    btn.addEventListener('click', () => {
        isMonitoring = !isMonitoring;

        // Emit State
        socket.emit('set_monitoring', { active: isMonitoring });

        // Update UI
        updateMonitorUI(isMonitoring);
    });
}

function updateMonitorUI(active) {
    const btn = document.getElementById('monitor-toggle');
    const statusDiv = document.getElementById('system-status');
    if (!btn || !statusDiv) return;

    const pulse = statusDiv.querySelector('.pulse');

    if (active) {
        btn.innerHTML = '<ion-icon name="pause-outline"></ion-icon> Stop Monitoring';
        btn.style.background = 'var(--accent-red)';

        statusDiv.innerHTML = '<div class="pulse"></div> System Active';
        statusDiv.style.background = 'rgba(16, 185, 129, 0.1)';
        statusDiv.style.color = 'var(--accent-green)';
    } else {
        btn.innerHTML = '<ion-icon name="play-outline"></ion-icon> Start Monitoring';
        btn.style.background = '#334155';

        statusDiv.innerHTML = '<div class="pulse" style="background:red; animation:none;"></div> System Inactive';
        statusDiv.style.background = 'rgba(239, 68, 68, 0.1)';
        statusDiv.style.color = 'var(--accent-red)';
    }
}

async function clearActivity() {
    // Only clear from UI (local notification clear)
    const container = document.getElementById('dashboard-feed');
    if (container) {
        // Simple slide-out animation for all items
        const items = container.querySelectorAll('.alert-item');
        items.forEach(item => {
            item.style.transform = 'translateX(100px)';
            item.style.opacity = '0';
        });

        setTimeout(() => {
            container.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:20px;">Notifications cleared.</div>';

            // Persist clear state (store current timestamp)
            localStorage.setItem('lastClearedTime', Date.now().toString());

        }, 300);
    }
}

// --- Video Stream Logic ---
function initVideoStream() {
    const img = document.getElementById('live-stream-img');
    const dot = document.querySelector('.live-dot');

    if (!img) return;

    socket.on('connect', () => {
        console.log('Connected to stream');
        if (dot) dot.style.background = '#10b981'; // Green

        // Ask system to start camera (Lazy Load)
        socket.emit('camera_control', { action: 'start' });
    });

    socket.on('disconnect', () => {
        if (dot) dot.style.background = 'red';
    });

    socket.on('live_stream', (base64Data) => {
        // Debounce or requestAnimationFrame could be optimized here if needed
        requestAnimationFrame(() => {
            img.src = 'data:image/jpeg;base64,' + base64Data;
        });
    });
}
