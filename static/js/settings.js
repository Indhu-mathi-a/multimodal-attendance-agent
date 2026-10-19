/**
 * settings.js – Settings & Privacy page logic
 */

async function loadSettings() {
  const data = await apiFetch('/api/settings');
  if (!data) return;

  document.getElementById('sInstitution').value = data.institution_name || '';
  document.getElementById('sLate').value        = data.late_threshold_minutes || 15;
  document.getElementById('sPassPct').value     = data.attendance_pass_pct || 75;
  document.getElementById('sRetention').value   = data.data_retention_days || 7;
  document.getElementById('sVideoEnabled').checked = data.video_analysis_enabled === 'true';
  document.getElementById('sAudioEnabled').checked = data.audio_analysis_enabled === 'true';
  document.getElementById('consentCheck').checked  = data.consent_obtained === 'true';
}

document.getElementById('settingsForm').addEventListener('submit', async e => {
  e.preventDefault();
  const payload = {
    institution_name:        document.getElementById('sInstitution').value,
    late_threshold_minutes:  document.getElementById('sLate').value,
    attendance_pass_pct:     document.getElementById('sPassPct').value,
    data_retention_days:     document.getElementById('sRetention').value,
    video_analysis_enabled:  document.getElementById('sVideoEnabled').checked.toString(),
    audio_analysis_enabled:  document.getElementById('sAudioEnabled').checked.toString(),
  };
  const res = await apiFetch('/api/settings', { method: 'POST', body: JSON.stringify(payload) });
  if (res) showToast('Settings saved.', 'success');
});

document.getElementById('saveConsentBtn').addEventListener('click', async () => {
  const consent = document.getElementById('consentCheck').checked;
  const res = await apiFetch('/api/settings', {
    method: 'POST',
    body: JSON.stringify({ consent_obtained: consent.toString() })
  });
  if (res) showToast(consent ? 'Consent recorded.' : 'Consent withdrawn.', consent ? 'success' : 'warning');
});

// Health check
async function checkHealth() {
  const data = await apiFetch('/api/settings/health');
  const panel = document.getElementById('healthPanel');
  if (data && data.status === 'ok') {
    panel.innerHTML = `
      <div class="d-flex align-items-center gap-3">
        <i class="bi bi-check-circle-fill text-success fs-4"></i>
        <div>
          <div class="fw-semibold">System OK</div>
          <div class="text-muted small">Database: ${data.database}</div>
        </div>
      </div>`;
  } else {
    panel.innerHTML = `<div class="text-danger"><i class="bi bi-x-circle-fill me-2"></i>System issue detected.</div>`;
  }
}

loadSettings();
checkHealth();
