/**
 * Packaged Commodity Legal Metrology Compliance Checker
 * Strict scan_id State & Anti-Caching Pipeline
 */

// Application State
const state = {
    currentScanId: null,
    currentFilename: null,
    selectedPreset: null,
    uploadedFile: null,
    isProcessing: false,
    scansHistory: []
};

// API Base URL
const API_BASE = window.location.origin;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    checkForUrlScanId();
    loadScansHistory();
    logToConsole('SYSTEM', 'Packaged Commodity Compliance Checker initialized.');
    logToConsole('SYSTEM', 'Anti-caching and strict scan_id isolation are ENFORCED.');
});

// Check if loaded with /report/{id} in URL path or ?scan_id=...
function checkForUrlScanId() {
    const path = window.location.pathname;
    const match = path.match(/\/report\/(\d+)/);
    if (match) {
        const scanId = parseInt(match[1]);
        fetchAndDisplayReport(scanId);
        return;
    }

    const params = new URLSearchParams(window.location.search);
    const queryScanId = params.get('scan_id');
    if (queryScanId) {
        fetchAndDisplayReport(parseInt(queryScanId));
    }
}

// Event Listeners
function initEventListeners() {
    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            state.selectedPreset = {
                name: btn.dataset.name,
                filename: btn.dataset.filename,
                type: btn.dataset.type
            };
            state.uploadedFile = null;
            document.getElementById('file-input').value = '';
            document.getElementById('upload-preview-text').textContent = `Selected: ${state.selectedPreset.name} (${state.selectedPreset.filename})`;
            document.getElementById('start-btn').disabled = false;
        });
    });

    // Dropzone & File Input
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    dropzone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelected(e.dataTransfer.files[0]);
        }
    });

    // Run Scan Pipeline Button
    document.getElementById('start-btn').addEventListener('click', startScanPipeline);

    // History Refresh
    document.getElementById('refresh-history-btn').addEventListener('click', loadScansHistory);
}

function handleFileSelected(file) {
    state.uploadedFile = file;
    state.selectedPreset = null;
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('upload-preview-text').textContent = `Uploaded File: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    document.getElementById('start-btn').disabled = false;
    logToConsole('UI', `Selected user file: ${file.name}`);
}

/**
 * Robust Anti-Caching Fetch Wrapper
 * 1. Appends timestamp cache buster query `?_t=${Date.now()}`
 * 2. Sets Cache-Control, Pragma, and Expires headers
 * 3. Uses cache: 'no-store'
 */
async function antiCacheFetch(url, options = {}) {
    const separator = url.includes('?') ? '&' : '?';
    const cacheBustedUrl = `${url}${separator}_t=${Date.now()}`;

    const headers = {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        ...(options.headers || {})
    };

    return fetch(cacheBustedUrl, {
        ...options,
        headers,
        cache: 'no-store'
    });
}

/**
 * End-to-End Compliance Pipeline
 * Step 1: POST /upload -> returns unique scan_id
 * Step 2: POST /ocr/{scan_id} -> executes EasyOCR on that image & updates scan_id
 * Step 3: POST /check/{scan_id} -> evaluates Legal Metrology rules strictly on that scan_id
 * Step 4: Loads & opens /report/{scan_id}
 */
async function startScanPipeline() {
    if (state.isProcessing) return;
    state.isProcessing = true;
    document.getElementById('start-btn').disabled = true;

    resetPipelineSteps();
    showReportContainer(false);

    try {
        let filename = "uploaded_commodity.jpg";
        let commodityType = "Packaged Commodity";

        // 1. UPLOAD STEP
        setStepStatus(1, 'running', 'Uploading packaging image...');

        let uploadResp;
        if (state.uploadedFile) {
            filename = state.uploadedFile.name;
            const formData = new FormData();
            formData.append('file', state.uploadedFile);
            formData.append('commodity_type', commodityType);

            const res = await antiCacheFetch(`${API_BASE}/upload`, {
                method: 'POST',
                body: formData
            });
            uploadResp = await res.json();
        } else if (state.selectedPreset) {
            filename = state.selectedPreset.filename;
            commodityType = state.selectedPreset.type;

            const res = await antiCacheFetch(`${API_BASE}/upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: filename,
                    commodity_type: commodityType
                })
            });
            uploadResp = await res.json();
        } else {
            throw new Error('Please select a preset commodity or upload an image file.');
        }

        if (!uploadResp.success || !uploadResp.scan_id) {
            throw new Error(uploadResp.error || 'Upload failed to return a valid scan_id');
        }

        // Crucial Requirement: Store returned scan_id in state
        state.currentScanId = uploadResp.scan_id;
        state.currentFilename = uploadResp.filename || filename;

        setStepStatus(1, 'completed', `Uploaded successfully -> Generated scan_id: #${state.currentScanId}`);
        logToConsole('UPLOAD', `scan_id=${state.currentScanId} | filename='${state.currentFilename}'`);

        // 2. OCR STEP
        setStepStatus(2, 'running', `Running OCR extraction for scan_id #${state.currentScanId}...`);

        const ocrRes = await antiCacheFetch(`${API_BASE}/ocr/${state.currentScanId}`, {
            method: 'POST'
        });
        const ocrData = await ocrRes.json();

        if (!ocrData.success) {
            throw new Error(ocrData.error || `OCR extraction failed for scan_id ${state.currentScanId}`);
        }

        setStepStatus(2, 'completed', `OCR extracted (${ocrData.ocr_text.length} chars)`);
        logToConsole('OCR', `scan_id=${state.currentScanId} | filename='${state.currentFilename}' | preview='${ocrData.ocr_preview}'`);

        // 3. COMPLIANCE CHECK STEP
        setStepStatus(3, 'running', `Evaluating Legal Metrology Rules for scan_id #${state.currentScanId}...`);

        const checkRes = await antiCacheFetch(`${API_BASE}/check/${state.currentScanId}`, {
            method: 'POST'
        });
        const checkData = await checkRes.json();

        if (!checkData.success) {
            throw new Error(checkData.error || `Compliance check failed for scan_id ${state.currentScanId}`);
        }

        setStepStatus(3, 'completed', `Evaluated Score: ${checkData.compliance_score}% (${checkData.compliance_status})`);
        logToConsole('CHECK', `scan_id=${state.currentScanId} | filename='${state.currentFilename}' | score=${checkData.compliance_score}% | status=${checkData.compliance_status}`);

        // 4. OPEN DYNAMIC REPORT STEP
        setStepStatus(4, 'completed', `Opening /report/${state.currentScanId}`);

        // Update browser URL to /report/{scan_id} without page reload
        window.history.pushState({ scan_id: state.currentScanId }, '', `/report/${state.currentScanId}`);

        // Render the report
        renderComplianceReport(checkData);
        loadScansHistory();

    } catch (err) {
        console.error('Pipeline Error:', err);
        logToConsole('ERROR', err.message);
        alert(`Error: ${err.message}`);
    } finally {
        state.isProcessing = false;
        document.getElementById('start-btn').disabled = false;
    }
}

/**
 * Fetch and display report strictly for a given scan_id
 */
async function fetchAndDisplayReport(scanId) {
    try {
        logToConsole('API', `Fetching isolated report for scan_id #${scanId}...`);
        const res = await antiCacheFetch(`${API_BASE}/api/report/${scanId}`);
        const data = await res.json();

        if (!data.success) {
            throw new Error(data.error || `Scan #${scanId} not found`);
        }

        state.currentScanId = data.scan_id;
        state.currentFilename = data.filename;
        renderComplianceReport(data);
    } catch (err) {
        logToConsole('ERROR', `Failed to load report #${scanId}: ${err.message}`);
    }
}

/**
 * Render the rich compliance report view
 */
function renderComplianceReport(data) {
    showReportContainer(true);

    // Update header titles & metadata
    document.getElementById('report-scan-id-badge').textContent = `Scan ID: #${data.scan_id}`;
    document.getElementById('report-filename').textContent = data.filename;
    document.getElementById('report-status-badge').textContent = data.compliance_status || data.status;

    // Score Gauge
    const score = data.compliance_score || 0;
    document.getElementById('gauge-score-val').textContent = `${score}%`;

    // Animate circle gauge (circumference = 283)
    const offset = 283 - (283 * (score / 100));
    const gaugeFill = document.getElementById('gauge-fill-circle');
    gaugeFill.style.strokeDashoffset = offset;

    const statusBadge = document.getElementById('compliance-status-badge');
    statusBadge.className = 'score-badge';
    if (score >= 90) {
        statusBadge.classList.add('compliant');
        statusBadge.textContent = 'COMPLIANT WITH LEGAL METROLOGY';
        gaugeFill.style.stroke = 'var(--success)';
    } else if (score >= 60) {
        statusBadge.classList.add('partial');
        statusBadge.textContent = 'PARTIALLY COMPLIANT';
        gaugeFill.style.stroke = 'var(--warning)';
    } else {
        statusBadge.classList.add('non-compliant');
        statusBadge.textContent = 'NON-COMPLIANT / DEFECT DETECTED';
        gaugeFill.style.stroke = 'var(--danger)';
    }

    // Mandatory Declarations Checklist
    const rulesContainer = document.getElementById('rules-checklist');
    rulesContainer.innerHTML = '';

    const ruleResults = data.rule_results?.rules || {};
    const ruleKeys = Object.keys(ruleResults);

    if (ruleKeys.length === 0) {
        rulesContainer.innerHTML = '<div style="color: var(--text-muted); padding: 1rem;">No rule breakdowns available.</div>';
    } else {
        ruleKeys.forEach(k => {
            const rule = ruleResults[k];
            const row = document.createElement('div');
            row.className = 'rule-row';

            const isPass = rule.passed;
            row.innerHTML = `
        <div class="rule-meta">
          <div class="rule-name">${rule.name}</div>
          <div style="font-size: 0.75rem; color: var(--text-muted);">${rule.details || ''}</div>
          ${rule.extracted ? `<div class="rule-extracted">${escapeHtml(rule.extracted)}</div>` : ''}
        </div>
        <div class="rule-status ${isPass ? 'pass' : 'fail'}">
          ${isPass ? '✓ VALID' : '✗ MISSING'}
        </div>
      `;
            rulesContainer.appendChild(row);
        });
    }

    // Raw OCR text box
    document.getElementById('raw-ocr-text').textContent = data.ocr_text || '(No OCR text extracted for this scan)';

    // Scroll smoothly to report card
    document.getElementById('report-card').scrollIntoView({ behavior: 'smooth' });
}

/**
 * Load History of Scans
 */
async function loadScansHistory() {
    try {
        const res = await antiCacheFetch(`${API_BASE}/api/scans`);
        const data = await res.json();
        state.scansHistory = data.scans || [];

        const tbody = document.getElementById('history-tbody');
        tbody.innerHTML = '';

        if (state.scansHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No scans recorded yet.</td></tr>';
            return;
        }

        state.scansHistory.forEach(s => {
            const tr = document.createElement('tr');
            const scoreBadge = s.compliance_score >= 90 ? '#34d399' : (s.compliance_score >= 60 ? '#fbbf24' : '#f87171');

            tr.innerHTML = `
        <td><strong style="color: #818cf8;">#${s.id}</strong></td>
        <td>${escapeHtml(s.filename)}</td>
        <td><span style="color: ${scoreBadge}; font-weight: 700;">${s.compliance_score}%</span></td>
        <td><span style="font-size: 0.75rem; color: var(--text-muted);">${s.status}</span></td>
        <td>
          <button class="btn-view-report" onclick="fetchAndDisplayReport(${s.id})">
            Open Report #${s.id}
          </button>
        </td>
      `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Failed to load scan history:', err);
    }
}

// Helpers
function setStepStatus(stepNum, status, descText) {
    const stepEl = document.getElementById(`step-${stepNum}`);
    if (!stepEl) return;
    stepEl.className = `step-item ${status}`;
    if (descText) {
        stepEl.querySelector('.step-desc').textContent = descText;
    }
}

function resetPipelineSteps() {
    for (let i = 1; i <= 4; i++) {
        const stepEl = document.getElementById(`step-${i}`);
        if (stepEl) {
            stepEl.className = 'step-item';
            stepEl.querySelector('.step-desc').textContent = 'Pending...';
        }
    }
}

function showReportContainer(show) {
    const el = document.getElementById('report-card');
    if (el) {
        el.style.display = show ? 'block' : 'none';
    }
}

function logToConsole(tag, message) {
    const box = document.getElementById('console-log-box');
    if (!box) return;

    const entry = document.createElement('div');
    entry.className = 'console-entry';
    const time = new Date().toLocaleTimeString();

    entry.innerHTML = `<span class="ts">[${time}]</span> <span class="scan-tag">[${tag}]</span> ${escapeHtml(message)}`;
    box.appendChild(entry);
    box.scrollTop = box.scrollHeight;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}