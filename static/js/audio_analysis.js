/**
 * audio_analysis.js – Audio upload and analysis page logic
 */

let audioChart = null;

populateSessionSelect('audioSessionSelect');
populateSessionSelect('pastAudioSession');

// ── Dropzone ─────────────────────────────────────────────────────────────────
const zone = document.getElementById('audioDropzone');
const fileInput = document.getElementById('audioFile');

zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
zone.addEventListener('drop', e => {
  e.preventDefault(); zone.classList.remove('drag-over');
  if (e.dataTransfer.files.length) { fileInput.files = e.dataTransfer.files; handleSelect(); }
});
fileInput.addEventListener('change', handleSelect);

function handleSelect() {
  const f = fileInput.files[0];
  if (!f) return;
  zone.innerHTML = `<i class="bi bi-file-music-fill fs-1 text-success mb-2"></i>
    <p class="mb-0 fw-semibold">${f.name}</p>
    <p class="text-muted small">${(f.size / 1024 / 1024).toFixed(2)} MB</p>`;
  document.getElementById('uploadAudioBtn').disabled = false;
}

// ── Upload & analyse ──────────────────────────────────────────────────────────
document.getElementById('uploadAudioBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('audioSessionSelect').value;
  if (!sessionId) { showToast('Select a session first.', 'warning'); return; }
  if (!fileInput.files.length) { showToast('Select an audio file.', 'warning'); return; }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);

  document.getElementById('audioProcessing').style.removeProperty('display');
  document.getElementById('uploadAudioBtn').disabled = true;

  const resp = await fetch(`/api/analysis/audio/upload/${sessionId}`, { method: 'POST', body: formData });
  const data = await resp.json();

  document.getElementById('audioProcessing').style.setProperty('display','none','important');
  document.getElementById('uploadAudioBtn').disabled = false;

  if (!resp.ok) { showToast(data.error || 'Analysis failed.', 'danger'); return; }

  showToast('Audio analysis complete.', 'success');
  renderAudioResults(data);
});

function renderAudioResults(data) {
  document.getElementById('audioActivityPct').textContent   = (data.audio_activity_pct || 0) + '%';
  document.getElementById('audioActivePeriods').textContent = data.active_periods || 0;
  document.getElementById('audioQuietPeriods').textContent  = data.quiet_periods  || 0;
  document.getElementById('audioResultsCard').style.removeProperty('display');

  if (audioChart) audioChart.destroy();
  const timeline = data.activity_timeline || [];
  const labels   = timeline.map(p => p.t + 's');
  const scores   = timeline.map(p => p.s);
  const bgColors = timeline.map(p => p.active ? 'rgba(34,197,94,.7)' : 'rgba(239,68,68,.4)');

  audioChart = new Chart(document.getElementById('audioTimeline'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Audio Activity',
        data: scores,
        backgroundColor: bgColors,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      scales: { y: { min: 0, max: 100, title: { display: true, text: 'Activity Level' } } },
      plugins: { legend: { display: false } }
    }
  });
}

// ── Load past ─────────────────────────────────────────────────────────────────
document.getElementById('loadAudioPastBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('pastAudioSession').value;
  if (!sessionId) { showToast('Select a session.', 'warning'); return; }
  const data = await apiFetch(`/api/analysis/audio/result/${sessionId}`);
  if (data) renderAudioResults(data);
});
