/**
 * video_analysis.js – Video upload and analysis page logic
 */

let videoTimelineChart = null;

// Populate session selects
populateSessionSelect('videoSessionSelect');

// ── Dropzone ─────────────────────────────────────────────────────────────────
const zone = document.getElementById('videoDropzone');
const fileInput = document.getElementById('videoFile');

zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; handleFileSelect(); }
});
fileInput.addEventListener('change', handleFileSelect);

function handleFileSelect() {
  const f = fileInput.files[0];
  if (!f) return;
  zone.innerHTML = `<i class="bi bi-file-play-fill fs-1 text-success mb-2"></i>
    <p class="mb-0 fw-semibold">${f.name}</p>
    <p class="text-muted small">${(f.size / 1024 / 1024).toFixed(1)} MB</p>`;
  document.getElementById('uploadVideoBtn').disabled = false;
}

// ── Upload & process ──────────────────────────────────────────────────────────
document.getElementById('uploadVideoBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('videoSessionSelect').value;
  if (!sessionId) { showToast('Select a session first.', 'warning'); return; }
  if (!fileInput.files.length) { showToast('Select a video file first.', 'warning'); return; }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  document.getElementById('progressCard').style.removeProperty('display');
  document.getElementById('resultsCard').style.setProperty('display', 'none', 'important');
  document.getElementById('uploadVideoBtn').disabled = true;

  const resp = await fetch(`/api/analysis/video/upload/${sessionId}`, { method: 'POST', body: formData });
  const data = await resp.json();

  if (!resp.ok) { showToast(data.error || 'Upload failed.', 'danger'); return; }

  showToast('Processing started. This may take a while for large videos.', 'info', 8000);
  pollProgress(sessionId);
});

// ── Poll progress ─────────────────────────────────────────────────────────────
function pollProgress(sessionId) {
  const bar  = document.getElementById('videoProgress');
  const text = document.getElementById('progressText');

  const interval = setInterval(async () => {
    const data = await apiFetch(`/api/analysis/video/progress/${sessionId}`);
    if (!data) return;

    bar.style.width = data.progress + '%';
    text.textContent = data.status === 'processing'
      ? `Processing… ${data.progress}%`
      : data.status === 'done' ? 'Processing complete!' : 'Status: ' + data.status;

    if (data.status === 'done' || data.status === 'failed') {
      clearInterval(interval);
      document.getElementById('progressCard').style.setProperty('display', 'none', 'important');
      if (data.status === 'done') { loadResults(sessionId); }
      else { showToast('Video processing failed.', 'danger'); }
    }
  }, 2000);
}

// ── Load results ──────────────────────────────────────────────────────────────
async function loadResults(sessionId) {
  const data = await apiFetch(`/api/analysis/video/result/${sessionId}`);
  if (!data) return;

  document.getElementById('resMovement').textContent = (data.movement_score || 0).toFixed(1) + '/100';
  document.getElementById('resPersons').textContent  = (data.person_count_avg || 0).toFixed(1);
  document.getElementById('resDuration').textContent = data.duration_seconds || '–';

  document.getElementById('resultsCard').style.removeProperty('display');

  if (videoTimelineChart) videoTimelineChart.destroy();
  const labels  = (data.activity_timeline || []).map(p => p.t + 's');
  const scores  = (data.activity_timeline || []).map(p => p.s);

  videoTimelineChart = new Chart(document.getElementById('videoTimeline'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Activity Score',
        data: scores,
        borderColor: CHART_COLORS.blue,
        backgroundColor: 'rgba(59,130,246,.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
      }]
    },
    options: {
      responsive: true,
      scales: { y: { min: 0, max: 100 } },
      plugins: { legend: { display: false } }
    }
  });
}

// ── Load past results ─────────────────────────────────────────────────────────
document.getElementById('loadPastBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('videoSessionSelect').value;
  if (!sessionId) { showToast('Select a session first.', 'warning'); return; }
  loadResults(sessionId);
});
