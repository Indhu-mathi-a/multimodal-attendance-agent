/**
 * app.js - Shared utilities for Multimodal Attendance & Engagement Agent
 * Provides: apiFetch, toast notifications, shared helpers
 */

// ── API fetch helper ─────────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
  try {
    const resp = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: resp.statusText }));
      showToast(Array.isArray(err.error) ? err.error.join(', ') : (err.error || 'Request failed'), 'danger');
      return null;
    }
    return await resp.json();
  } catch (e) {
    showToast('Network error: ' + e.message, 'danger');
    return null;
  }
}

// ── Toast notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'success', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const iconMap = {
    success: 'bi-check-circle-fill',
    danger:  'bi-exclamation-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info:    'bi-info-circle-fill',
  };

  const id = 'toast-' + Date.now();
  const html = `
    <div id="${id}" class="toast align-items-center text-white bg-${type} border-0 show mb-2" role="alert">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${iconMap[type] || 'bi-info-circle-fill'}"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                onclick="document.getElementById('${id}').remove()"></button>
      </div>
    </div>`;
  container.insertAdjacentHTML('beforeend', html);
  setTimeout(() => {
    const el = document.getElementById(id);
    if (el) el.remove();
  }, duration);
}

// ── Status badge helper ──────────────────────────────────────────────────────
function statusBadge(s) {
  const map = {
    scheduled: 'secondary',
    active:    'success',
    completed: 'primary',
    cancelled: 'danger',
  };
  return `<span class="badge bg-${map[s] || 'secondary'}">${s}</span>`;
}

function attendanceBadge(s) {
  const map = { present: 'success', late: 'warning', absent: 'danger' };
  return `<span class="badge bg-${map[s] || 'secondary'}">${s}</span>`;
}

// ── Populate a <select> from an array of sessions ────────────────────────────
async function populateSessionSelect(selectId, placeholder = 'Choose session…') {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const sessions = await apiFetch('/api/sessions');
  if (!sessions) return;
  sel.innerHTML = `<option value="">${placeholder}</option>` +
    sessions.map(s =>
      `<option value="${s.id}">${s.session_date} – ${s.session_name} (${s.subject})</option>`
    ).join('');
}

// ── URL query param helper ───────────────────────────────────────────────────
function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// ── Format date/time ─────────────────────────────────────────────────────────
function fmtDateTime(iso) {
  if (!iso) return '–';
  return new Date(iso).toLocaleString();
}

// ── Chart colour palette ─────────────────────────────────────────────────────
const CHART_COLORS = {
  blue:   '#3b82f6',
  purple: '#8b5cf6',
  green:  '#22c55e',
  amber:  '#f59e0b',
  red:    '#f43f5e',
  teal:   '#14b8a6',
};
