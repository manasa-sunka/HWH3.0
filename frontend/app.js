document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const historyList = document.getElementById('historyList');
  const historyCount = document.getElementById('historyCount');
  const btnNewIncident = document.getElementById('btnNewIncident');
  const btnLoadSample = document.getElementById('btnLoadSample');
  const btnFormMode = document.getElementById('btnFormMode');
  const btnJsonMode = document.getElementById('btnJsonMode');
  const incidentForm = document.getElementById('incidentForm');
  const jsonView = document.getElementById('jsonView');
  const jsonEditor = document.getElementById('jsonEditor');
  const eventsContainer = document.getElementById('eventsContainer');
  const btnAddEvent = document.getElementById('btnAddEvent');
  const inputSection = document.getElementById('inputSection');
  const reportSection = document.getElementById('reportSection');
  const btnBackToForm = document.getElementById('btnBackToForm');
  const btnSubmitAnalyze = document.getElementById('btnSubmitAnalyze');
  const btnSubmitJson = document.getElementById('btnSubmitJson');
  const btnCopyReport = document.getElementById('btnCopyReport');
  const btnExportJson = document.getElementById('btnExportJson');

  let currentReportData = null;
  let activeIncidentId = null;

  // Default sample data fallback
  const defaultSample = {
    incident_id: "INC-001",
    service: "Payment API",
    severity: "HIGH",
    events: [
      { timestamp: "10:01", type: "metric", message: "CPU usage increased to 92%" },
      { timestamp: "10:02", type: "metric", message: "API latency increased to 4.8 seconds" },
      { timestamp: "10:03", type: "error", message: "Database connection pool exhausted" },
      { timestamp: "10:04", type: "error", message: "Payment API requests failing with HTTP 503" },
      { timestamp: "10:05", type: "alert", message: "Payment API availability below threshold" }
    ]
  };

  // Initialize
  init();

  function init() {
    setupEventListeners();
    populateForm(defaultSample);
    loadHistory();
  }

  function setupEventListeners() {
    btnNewIncident.addEventListener('click', () => {
      activeIncidentId = null;
      document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
      populateForm({
        incident_id: `INC-${Math.floor(100 + Math.random() * 900)}`,
        service: "",
        severity: "HIGH",
        events: [{ timestamp: "10:00", type: "metric", message: "" }]
      });
      showInputView();
    });

    btnLoadSample.addEventListener('click', async () => {
      try {
        const res = await fetch('/api/sample');
        if (res.ok) {
          const data = await res.json();
          populateForm(data);
        } else {
          populateForm(defaultSample);
        }
      } catch {
        populateForm(defaultSample);
      }
    });

    btnFormMode.addEventListener('click', () => {
      btnFormMode.classList.add('active');
      btnJsonMode.classList.remove('active');
      incidentForm.classList.remove('hidden');
      jsonView.classList.add('hidden');
      try {
        const parsed = JSON.parse(jsonEditor.value);
        populateForm(parsed);
      } catch (e) {
        // keep current form
      }
    });

    btnJsonMode.addEventListener('click', () => {
      btnJsonMode.classList.add('active');
      btnFormMode.classList.remove('active');
      jsonView.classList.remove('hidden');
      incidentForm.classList.add('hidden');
      jsonEditor.value = JSON.stringify(getFormData(), null, 2);
    });

    btnAddEvent.addEventListener('click', () => {
      addEventRow("", "metric", "");
    });

    incidentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      await runInvestigation(getFormData());
    });

    btnSubmitJson.addEventListener('click', async () => {
      try {
        const data = JSON.parse(jsonEditor.value);
        await runInvestigation(data);
      } catch (err) {
        alert('Invalid JSON syntax: ' + err.message);
      }
    });

    btnBackToForm.addEventListener('click', () => {
      showInputView();
    });

    btnCopyReport.addEventListener('click', () => {
      if (!currentReportData) return;
      const text = `Incident: ${currentReportData.incident_id} (${currentReportData.service})\nRoot Cause: ${currentReportData.root_cause}\nConfidence: ${currentReportData.confidence}\n\nRecommended Actions:\n` +
        (currentReportData.recommended_actions || []).map(a => `- ${a}`).join('\n');
      navigator.clipboard.writeText(text);
      btnCopyReport.textContent = 'Copied!';
      setTimeout(() => btnCopyReport.textContent = 'Copy Report', 2000);
    });

    btnExportJson.addEventListener('click', () => {
      if (!currentReportData) return;
      const blob = new Blob([JSON.stringify(currentReportData, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentReportData.incident_id || 'incident'}_report.json`;
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  function addEventRow(timestamp = "", type = "metric", message = "") {
    const row = document.createElement('div');
    row.className = 'event-row';
    row.innerHTML = `
      <input type="text" placeholder="10:01" value="${escapeHtml(timestamp)}" required />
      <select>
        <option value="metric" ${type === 'metric' ? 'selected' : ''}>metric</option>
        <option value="error" ${type === 'error' ? 'selected' : ''}>error</option>
        <option value="alert" ${type === 'alert' ? 'selected' : ''}>alert</option>
        <option value="log" ${type === 'log' ? 'selected' : ''}>log</option>
      </select>
      <input type="text" placeholder="Log message or metric description" value="${escapeHtml(message)}" required />
      <button type="button" class="btn-remove-row" title="Remove event">&times;</button>
    `;

    row.querySelector('.btn-remove-row').addEventListener('click', () => {
      if (eventsContainer.children.length > 1) {
        row.remove();
      } else {
        alert('At least one event is required.');
      }
    });

    eventsContainer.appendChild(row);
  }

  function populateForm(data) {
    document.getElementById('incidentId').value = data.incident_id || data.id || '';
    document.getElementById('serviceName').value = data.service || data.services || '';
    document.getElementById('severity').value = data.severity || 'HIGH';

    eventsContainer.innerHTML = '';
    const events = data.events || data.logs || [];
    if (events.length === 0) {
      addEventRow("", "metric", "");
    } else {
      events.forEach(ev => {
        addEventRow(ev.timestamp || ev.time || '', ev.type || 'metric', ev.message || ev.msg || '');
      });
    }

    jsonEditor.value = JSON.stringify(data, null, 2);
  }

  function getFormData() {
    const incident_id = document.getElementById('incidentId').value.trim();
    const service = document.getElementById('serviceName').value.trim();
    const severity = document.getElementById('severity').value;

    const events = [];
    eventsContainer.querySelectorAll('.event-row').forEach(row => {
      const inputs = row.querySelectorAll('input');
      const select = row.querySelector('select');
      events.push({
        timestamp: inputs[0].value.trim(),
        type: select.value,
        message: inputs[1].value.trim()
      });
    });

    return { incident_id, service, severity, events };
  }

  async function runInvestigation(payload) {
    setLoading(true);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Analysis request failed');
      }

      const result = await res.json();
      currentReportData = result;
      renderReport(result);
      await loadHistory();
      highlightHistoryItem(result.incident_id);
    } catch (err) {
      alert('Investigation Error: ' + err.message);
    } finally {
      setLoading(false);
    }
  }

  function renderReport(data) {
    document.getElementById('reportIncId').textContent = data.incident_id || 'INC-UNKNOWN';
    document.getElementById('reportService').textContent = data.service || 'Service';
    
    const severityEl = document.getElementById('reportSeverity');
    severityEl.textContent = data.severity || 'UNKNOWN';
    severityEl.className = `badge severity-badge ${data.severity || ''}`;

    document.getElementById('reportRootCause').textContent = data.root_cause || 'Root cause under investigation';
    
    const confEl = document.getElementById('reportConfidence');
    confEl.textContent = data.confidence || 'MEDIUM';
    confEl.style.color = (data.confidence === 'HIGH') ? 'var(--accent-emerald)' : (data.confidence === 'LOW' ? 'var(--accent-rose)' : 'var(--accent-amber)');

    // Timeline
    const timelineEl = document.getElementById('reportTimeline');
    timelineEl.innerHTML = '';
    const timelineEvents = data.timeline || [];
    if (timelineEvents.length === 0 && data.events) {
      data.events.forEach(ev => {
        timelineEl.innerHTML += `
          <div class="timeline-item">
            <div class="timeline-meta">
              <span class="timeline-time">${escapeHtml(ev.timestamp || '')}</span>
              <span class="timeline-type-pill">${escapeHtml(ev.type || 'EVENT')}</span>
            </div>
            <div class="timeline-msg">${escapeHtml(ev.message || '')}</div>
          </div>
        `;
      });
    } else {
      timelineEvents.forEach(item => {
        const msg = (typeof item === 'string') ? item : (item.event || item.message || JSON.stringify(item));
        const time = item.time || item.timestamp || '';
        timelineEl.innerHTML += `
          <div class="timeline-item">
            <div class="timeline-meta">
              ${time ? `<span class="timeline-time">${escapeHtml(time)}</span>` : ''}
              <span class="timeline-type-pill">TIMELINE</span>
            </div>
            <div class="timeline-msg">${escapeHtml(msg)}</div>
          </div>
        `;
      });
    }

    // Observations
    renderList('reportObservations', data.observations);

    // Actions
    const actionsEl = document.getElementById('reportActions');
    actionsEl.innerHTML = '';
    (data.recommended_actions || []).forEach(act => {
      actionsEl.innerHTML += `<li>${escapeHtml(act)}</li>`;
    });
    if (!data.recommended_actions || data.recommended_actions.length === 0) {
      actionsEl.innerHTML = '<li>No immediate actions recommended</li>';
    }

    // Evidence
    renderList('reportEvidence', data.evidence);

    // Uncertainty
    renderList('reportUncertainty', data.uncertainty);

    showReportView();
  }

  function renderList(elementId, items) {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    if (!items || items.length === 0) {
      el.innerHTML = '<li class="text-dim">None recorded</li>';
      return;
    }
    items.forEach(it => {
      const text = (typeof it === 'string') ? it : JSON.stringify(it);
      el.innerHTML += `<li>${escapeHtml(text)}</li>`;
    });
  }

  async function loadHistory() {
    try {
      const res = await fetch('/api/incidents');
      if (!res.ok) return;
      const list = await res.json();
      historyCount.textContent = list.length;
      historyList.innerHTML = '';

      if (list.length === 0) {
        historyList.innerHTML = '<div class="history-loading">No incidents saved in database yet.</div>';
        return;
      }

      list.forEach(item => {
        const div = document.createElement('div');
        div.className = `history-item ${activeIncidentId === item.incident_id ? 'active' : ''}`;
        div.setAttribute('data-id', item.incident_id);
        div.innerHTML = `
          <div class="history-top">
            <span class="history-id">${escapeHtml(item.incident_id)}</span>
            <span class="badge ${item.severity}">${escapeHtml(item.severity)}</span>
          </div>
          <div class="history-service">${escapeHtml(item.service)}</div>
          <div class="history-cause" title="${escapeHtml(item.root_cause || '')}">${escapeHtml(item.root_cause || 'Analysis saved')}</div>
          <div class="history-bottom">
            <span>${formatTime(item.created_at)}</span>
            <span>Conf: ${escapeHtml(item.confidence || 'N/A')}</span>
          </div>
        `;

        div.addEventListener('click', () => loadIncidentDetail(item.incident_id));
        historyList.appendChild(div);
      });
    } catch (e) {
      console.error("Failed to load history", e);
    }
  }

  async function loadIncidentDetail(incidentId) {
    try {
      const res = await fetch(`/api/incidents/${incidentId}`);
      if (!res.ok) throw new Error('Incident not found');
      const data = await res.json();
      activeIncidentId = incidentId;
      highlightHistoryItem(incidentId);
      currentReportData = data.analysis_result;
      renderReport(data.analysis_result);
    } catch (err) {
      alert(err.message);
    }
  }

  function highlightHistoryItem(id) {
    document.querySelectorAll('.history-item').forEach(el => {
      if (el.getAttribute('data-id') === id) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });
  }

  function showInputView() {
    inputSection.classList.remove('hidden');
    reportSection.classList.add('hidden');
  }

  function showReportView() {
    inputSection.classList.add('hidden');
    reportSection.classList.remove('hidden');
  }

  function setLoading(isLoading) {
    btnSubmitAnalyze.disabled = isLoading;
    btnSubmitJson.disabled = isLoading;
    const loader1 = btnSubmitAnalyze.querySelector('.btn-loader');
    const loader2 = btnSubmitJson.querySelector('.btn-loader');
    if (isLoading) {
      loader1?.classList.remove('hidden');
      loader2?.classList.remove('hidden');
    } else {
      loader1?.classList.add('hidden');
      loader2?.classList.add('hidden');
    }
  }

  function formatTime(isoString) {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/[&<>"']/g, m => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[m]));
  }
});
