document.addEventListener('DOMContentLoaded', () => {
    const genInput = document.getElementById('setting-gen');
    const genVal = document.getElementById('gen-val');

    genInput.addEventListener('input', (e) => {
        genVal.textContent = e.target.value;
    });

    fetchStatus();
});

async function fetchStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.active_checkpoint) {
            document.getElementById('ckpt-name').textContent = data.active_checkpoint;
        }
    } catch (e) {
        console.error("Failed to fetch status:", e);
    }
}

function setPrompt(text) {
    document.getElementById('prompt-input').value = text;
    document.getElementById('prompt-input').focus();
}

async function sendPrompt() {
    const input = document.getElementById('prompt-input');
    const promptText = input.value.trim();
    if (!promptText) return;

    const genCount = document.getElementById('setting-gen').value;
    const preset = document.getElementById('setting-preset').value;
    const viewport = document.getElementById('chat-viewport');
    const sendBtn = document.getElementById('send-btn');
    const statusText = document.getElementById('status-text');
    const dot = document.querySelector('.dot');

    // Append User Message
    const userMsgHTML = `
        <div class="message user-message">
            <div class="avatar">👤</div>
            <div class="msg-body">
                <p>${escapeHtml(promptText)}</p>
            </div>
        </div>
    `;
    viewport.insertAdjacentHTML('beforeend', userMsgHTML);
    input.value = '';
    viewport.scrollTop = viewport.scrollHeight;

    // Show loading state
    sendBtn.disabled = true;
    statusText.textContent = "Running C Engine...";
    dot.classList.add('loading');

    const startTime = performance.now();

    try {
        const res = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: promptText,
                gen: genCount,
                preset: preset
            })
        });

        const data = await res.json();
        const endTime = performance.now();
        const latency = Math.round(endTime - startTime);

        if (data.success && data.stats) {
            const stats = data.stats;
            const tokPerSec = stats.seconds_per_token ? (1 / stats.seconds_per_token).toFixed(1) : "0.0";
            const rssMB = stats.peak_rss_bytes ? (stats.peak_rss_bytes / 1024 / 1024).toFixed(2) : "8.95";
            
            // Update Telemetry UI
            document.getElementById('metric-speed').textContent = tokPerSec;
            document.getElementById('metric-rss').textContent = rssMB;
            document.getElementById('metric-latency').textContent = latency;

            const assistantMsgHTML = `
                <div class="message assistant-message">
                    <div class="avatar">⚡</div>
                    <div class="msg-body">
                        <p><strong>${escapeHtml(promptText)}</strong> ${escapeHtml(data.generated_text || "")}</p>
                        <div class="msg-meta">
                            <span>tokens: ${stats.generated_ids ? stats.generated_ids.length : 0}</span>
                            <span>speed: ${tokPerSec} tok/s</span>
                            <span>rss: ${rssMB} MB</span>
                        </div>
                    </div>
                </div>
            `;
            viewport.insertAdjacentHTML('beforeend', assistantMsgHTML);
        } else {
            const errorMsgHTML = `
                <div class="message assistant-message">
                    <div class="avatar">❌</div>
                    <div class="msg-body">
                        <p style="color: #ef4444;">Inference failed: ${escapeHtml(data.error || data.stderr || "Unknown error")}</p>
                    </div>
                </div>
            `;
            viewport.insertAdjacentHTML('beforeend', errorMsgHTML);
        }

    } catch (e) {
        console.error("Network / Server Error:", e);
    } finally {
        sendBtn.disabled = false;
        statusText.textContent = "Engine Ready";
        dot.classList.remove('loading');
        viewport.scrollTop = viewport.scrollHeight;
    }
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
