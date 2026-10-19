/**
 * recommendations.js – Teaching recommendations page logic
 */

populateSessionSelect('recSessionSelect');

document.getElementById('genRecsBtn').addEventListener('click', async () => {
  const sessionId = document.getElementById('recSessionSelect').value;
  if (!sessionId) { showToast('Select a session.', 'warning'); return; }

  const btn = document.getElementById('genRecsBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Generating…';

  const recs = await apiFetch(`/api/engagement/recommendations/${sessionId}?refresh=true`);

  btn.disabled = false;
  btn.innerHTML = '<i class="bi bi-arrow-repeat me-1"></i>Generate';

  if (!recs) return;
  renderRecs(recs);
});

function renderRecs(recs) {
  const placeholder = document.getElementById('recsPlaceholder');
  const grid = document.getElementById('recsGrid');

  if (!recs.length) {
    placeholder.style.removeProperty('display');
    placeholder.innerHTML = `
      <i class="bi bi-info-circle fs-1 opacity-25"></i>
      <p class="mt-3 text-muted">No recommendations generated. Make sure the session has activity data
        (upload a video or audio file, or log participation events).</p>`;
    grid.style.setProperty('display','none','important');
    return;
  }

  placeholder.style.setProperty('display','none','important');
  grid.style.removeProperty('display');

  const catIcons = {
    break:      'bi-pause-circle-fill',
    activity:   'bi-lightning-fill',
    quiz:       'bi-patch-question-fill',
    pacing:     'bi-speedometer',
    discussion: 'bi-chat-dots-fill',
    revision:   'bi-book-fill',
  };

  grid.innerHTML = recs.map(r => `
    <div class="col-md-6 col-xl-4 fade-in">
      <div class="rec-card rec--${r.category}" id="rec-${r.id}">
        <div class="rec-card-header">
          <div><i class="bi ${catIcons[r.category] || 'bi-lightbulb-fill'} me-2"></i>${r.category.toUpperCase()}</div>
          <span class="badge ${r.priority === 1 ? 'bg-danger' : r.priority === 2 ? 'bg-warning text-dark' : 'bg-secondary'}">
            ${r.priority === 1 ? 'High' : r.priority === 2 ? 'Medium' : 'Low'}
          </span>
        </div>
        <div class="rec-card-body">
          <p class="mb-2 fw-semibold">${r.recommendation}</p>
          <div class="rec-card-reason">${r.reason}</div>
          <div class="mt-3 d-flex justify-content-end">
            <button class="btn btn-sm btn-outline-secondary" onclick="dismiss(${r.id})">
              <i class="bi bi-x-circle me-1"></i>Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>`).join('');
}

async function dismiss(recId) {
  const res = await apiFetch('/api/engagement/recommendations/dismiss/' + recId, { method: 'PATCH' });
  if (res) {
    const el = document.getElementById('rec-' + recId);
    if (el) el.closest('.col-md-6').remove();
    showToast('Recommendation dismissed.', 'success');
  }
}

// Auto-load if session param in URL
const urlSession = getQueryParam('session');
if (urlSession) {
  (async () => {
    await populateSessionSelect('recSessionSelect');
    document.getElementById('recSessionSelect').value = urlSession;
    document.getElementById('genRecsBtn').click();
  })();
}
