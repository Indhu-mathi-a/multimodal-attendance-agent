/**
 * engagement.js – Engagement analytics page logic
 */

let gaugeChart = null;
let trendChart = null;
let timelineChart = null;
let currentEngSessionId = null;

// Populate session selects
populateSessionSelect('engSessionSelect');

// ── Load Score ────────────────────────────────────────────────────────────────
document.getElementById('loadScoreBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('engSessionSelect').value;
  if (!sessionId) { showToast('Select a session.', 'warning'); return; }
  currentEngSessionId = parseInt(sessionId);
  await loadScore(currentEngSessionId);
  await loadParticipation(currentEngSessionId);
  loadStudentsForEvent(currentEngSessionId);
  document.getElementById('participationLogArea').style.removeProperty('display');
});

async function loadScore(sessionId) {
  const data = await apiFetch('/api/engagement/score/' + sessionId);
  if (!data) return;

  document.getElementById('scorePlaceholder').style.setProperty('display','none','important');
  document.getElementById('scoreDisplay').style.removeProperty('display');

  const score = data.composite_score;
  document.getElementById('scoreValue').textContent = score !== null ? score + '/100' : 'N/A';
  document.getElementById('scoreDisclaimer').textContent = data.disclaimer;

  // Gauge chart
  if (gaugeChart) gaugeChart.destroy();
  gaugeChart = new Chart(document.getElementById('scoreGauge'), {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [score || 0, 100 - (score || 0)],
        backgroundColor: [
          score >= 75 ? CHART_COLORS.green : score >= 50 ? CHART_COLORS.amber : CHART_COLORS.red,
          'rgba(0,0,0,.06)'
        ],
        borderWidth: 0,
      }]
    },
    options: {
      cutout: '78%',
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      rotation: -90,
      circumference: 180,
    }
  });

  // Components list
  const comps = data.components || {};
  const compHtml = Object.values(comps).map(c => `
    <div class="d-flex justify-content-between align-items-center mb-2">
      <div>
        <div class="fw-semibold small">${c.label}</div>
        <div class="text-muted" style="font-size:.72rem">${c.description}</div>
      </div>
      <span class="badge bg-primary fs-6 ms-3">${c.value}</span>
    </div>`).join('');
  document.getElementById('componentsList').innerHTML = compHtml ||
    '<p class="text-muted small">No analysis data available yet. Upload a video or audio file first.</p>';

  // Timeline
  if (data.activity_timeline && data.activity_timeline.length) {
    document.getElementById('timelineCard').style.removeProperty('display');
    if (timelineChart) timelineChart.destroy();
    timelineChart = new Chart(document.getElementById('timelineChart'), {
      type: 'line',
      data: {
        labels: data.activity_timeline.map(p => p.t + 's'),
        datasets: [{
          label: 'Activity',
          data: data.activity_timeline.map(p => p.s),
          borderColor: CHART_COLORS.blue,
          backgroundColor: 'rgba(59,130,246,.1)',
          fill: true,
          tension: 0.4,
        }]
      },
      options: { responsive: true, scales: { y: { min: 0, max: 100 } } }
    });
  }
}

// ── Trend Chart ───────────────────────────────────────────────────────────────
async function loadTrend() {
  const data = await apiFetch('/api/engagement/trend') || [];
  if (trendChart) trendChart.destroy();
  trendChart = new Chart(document.getElementById('trendChart'), {
    type: 'line',
    data: {
      labels: data.map(d => d.session_date + ' ' + d.session_name),
      datasets: [{
        label: 'Activity Score',
        data: data.map(d => d.composite_score),
        borderColor: CHART_COLORS.purple,
        backgroundColor: 'rgba(139,92,246,.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 5,
        pointBackgroundColor: CHART_COLORS.purple,
      }]
    },
    options: {
      responsive: true,
      scales: { y: { min: 0, max: 100 } },
      plugins: { legend: { display: false } }
    }
  });
}

// ── Participation Events ──────────────────────────────────────────────────────
async function loadStudentsForEvent(sessionId) {
  const data = await apiFetch('/api/attendance/session/' + sessionId);
  if (!data) return;
  const sel = document.getElementById('eventStudent');
  const present = data.records.filter(r => r.status !== 'absent');
  sel.innerHTML = '<option value="">Class-wide (no student)</option>' +
    present.map(r =>
      `<option value="${r.student_id}">${r.name}</option>`
    ).join('');
}

document.getElementById('logEventBtn').addEventListener('click', async () => {
  if (!currentEngSessionId) return;
  const payload = {
    session_id:  currentEngSessionId,
    student_id:  document.getElementById('eventStudent').value || null,
    event_type:  document.getElementById('eventType').value,
  };
  const res = await apiFetch('/api/engagement/participation', {
    method: 'POST', body: JSON.stringify(payload)
  });
  if (res) {
    showToast('Participation event logged.', 'success');
    loadParticipation(currentEngSessionId);
  }
});

async function loadParticipation(sessionId) {
  const events = await apiFetch('/api/engagement/participation/' + sessionId) || [];
  const el = document.getElementById('recentEvents');
  if (!events.length) {
    el.innerHTML = '<p class="text-muted small mb-0">No events logged yet.</p>';
    return;
  }
  el.innerHTML = '<p class="fw-semibold small mb-1">Recent Events</p>' +
    events.slice(0, 5).map(e => `
    <div class="d-flex justify-content-between align-items-center border-bottom py-1">
      <div class="small">
        <span class="badge bg-primary me-1">${e.event_type.replace('_',' ')}</span>
        ${e.student_name || 'Class-wide'}
      </div>
      <div class="text-muted" style="font-size:.7rem">${fmtDateTime(e.event_time)}</div>
    </div>`).join('');
}

document.getElementById('loadTrendBtn').addEventListener('click', loadTrend);

// Init
loadTrend();
