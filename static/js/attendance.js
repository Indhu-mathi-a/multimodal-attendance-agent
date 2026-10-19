/**
 * attendance.js – Attendance register page logic
 */

let currentSessionId = null;

// ── Populate session dropdown ────────────────────────────────────────────────
async function loadSessionOptions() {
  const sessions = await apiFetch('/api/sessions') || [];
  const sel = document.getElementById('sessionSelect');
  sel.innerHTML = '<option value="">Choose a session…</option>' +
    sessions.map(s =>
      `<option value="${s.id}">${s.session_date} – ${s.session_name} (${s.subject})</option>`
    ).join('');

  // Pre-select from URL param
  const urlSession = getQueryParam('session');
  if (urlSession) {
    sel.value = urlSession;
    await loadAttendance(parseInt(urlSession));
  }
}

// ── Load attendance for a session ────────────────────────────────────────────
async function loadAttendance(sessionId) {
  currentSessionId = sessionId;
  if (!sessionId) {
    document.getElementById('attBody').innerHTML =
      '<tr><td colspan="8" class="text-center py-5 text-muted">Select a session to load attendance.</td></tr>';
    document.getElementById('summaryRow').style.setProperty('display', 'none', 'important');
    return;
  }

  const data = await apiFetch('/api/attendance/session/' + sessionId);
  if (!data) return;

  const { records, summary } = data;

  // Update summary cards
  document.getElementById('summaryRow').style.removeProperty('display');
  document.getElementById('sumTotal').textContent   = summary.total;
  document.getElementById('sumPresent').textContent = summary.present;
  document.getElementById('sumLate').textContent    = summary.late;
  document.getElementById('sumAbsent').textContent  = summary.absent;
  document.getElementById('sessionAttPct').textContent = summary.attendance_pct + '%';

  renderAttTable(records);
}

function renderAttTable(records) {
  const tbody = document.getElementById('attBody');
  if (!records.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted">
      No students enrolled. Use Bulk Init to add all students.
      <button class="btn btn-sm btn-outline-primary ms-2" onclick="bulkInit()">Bulk Init</button>
    </td></tr>`;
    return;
  }
  tbody.innerHTML = records.map((r, i) => `
    <tr class="fade-in">
      <td>${i + 1}</td>
      <td><span class="badge bg-secondary">${r.student_code}</span></td>
      <td><strong>${r.name}</strong></td>
      <td>${r.department || '–'}</td>
      <td>${attendanceBadge(r.status)}</td>
      <td>${r.check_in_time ? fmtDateTime(r.check_in_time) : '–'}</td>
      <td><span class="badge bg-light text-dark border">${r.source}</span>
          ${r.corrected_by ? '<i class="bi bi-pencil-fill text-warning ms-1" title="Manually corrected"></i>' : ''}</td>
      <td>
        <div class="d-flex gap-1">
          ${r.status !== 'present' ?
            `<button class="btn btn-xs btn-success" onclick="quickPresent(${r.student_id})">
               <i class="bi bi-check-lg"></i>
             </button>` : ''}
          ${r.status !== 'absent' ?
            `<button class="btn btn-xs btn-danger" onclick="quickAbsent(${r.student_id})">
               <i class="bi bi-x-lg"></i>
             </button>` : ''}
          <button class="btn btn-xs btn-outline-secondary" onclick="openCorrect(${r.id}, '${r.name.replace(/'/g,"\\'")}', '${r.status}')">
            <i class="bi bi-pencil"></i>
          </button>
        </div>
      </td>
    </tr>`).join('');
}

// ── Quick actions ────────────────────────────────────────────────────────────
async function quickPresent(studentDbId) {
  if (!currentSessionId) return;
  const res = await apiFetch('/api/attendance/checkin', {
    method: 'POST',
    body: JSON.stringify({ session_id: currentSessionId, student_db_id: studentDbId, source: 'manual' })
  });
  if (res) { showToast('Marked present.', 'success'); loadAttendance(currentSessionId); }
}

async function quickAbsent(studentDbId) {
  if (!currentSessionId) return;
  const res = await apiFetch('/api/attendance/absent', {
    method: 'POST',
    body: JSON.stringify({ session_id: currentSessionId, student_db_id: studentDbId })
  });
  if (res) { showToast('Marked absent.', 'success'); loadAttendance(currentSessionId); }
}

// ── Mark all present / absent ────────────────────────────────────────────────
document.getElementById('markAllPresentBtn').addEventListener('click', async () => {
  if (!currentSessionId || !confirm('Mark ALL students as present?')) return;
  const data = await apiFetch('/api/attendance/session/' + currentSessionId);
  if (!data) return;
  for (const r of data.records) {
    if (r.status !== 'present') {
      await apiFetch('/api/attendance/checkin', {
        method: 'POST',
        body: JSON.stringify({ session_id: currentSessionId, student_db_id: r.student_id, source: 'manual' })
      });
    }
  }
  showToast('All students marked present.', 'success');
  loadAttendance(currentSessionId);
});

document.getElementById('markAllAbsentBtn').addEventListener('click', async () => {
  if (!currentSessionId || !confirm('Mark ALL students as absent?')) return;
  const data = await apiFetch('/api/attendance/session/' + currentSessionId);
  if (!data) return;
  for (const r of data.records) {
    await apiFetch('/api/attendance/absent', {
      method: 'POST',
      body: JSON.stringify({ session_id: currentSessionId, student_db_id: r.student_id })
    });
  }
  showToast('All students marked absent.', 'success');
  loadAttendance(currentSessionId);
});

// ── QR / Student ID check-in ─────────────────────────────────────────────────
async function qrCheckin() {
  if (!currentSessionId) { showToast('Select a session first.', 'warning'); return; }
  const code = document.getElementById('qrInput').value.trim();
  if (!code) return;
  const res = await apiFetch('/api/attendance/checkin/qr', {
    method: 'POST',
    body: JSON.stringify({ session_id: currentSessionId, student_code: code })
  });
  if (res) {
    showToast(`${res.student_name} marked ${res.status}.`, 'success');
    document.getElementById('qrInput').value = '';
    loadAttendance(currentSessionId);
  }
}

document.getElementById('qrBtn').addEventListener('click', qrCheckin);
document.getElementById('qrInput').addEventListener('keydown', e => { if (e.key === 'Enter') qrCheckin(); });

// ── Bulk init ────────────────────────────────────────────────────────────────
async function bulkInit() {
  if (!currentSessionId) return;
  const res = await apiFetch('/api/attendance/bulk-init', {
    method: 'POST', body: JSON.stringify({ session_id: currentSessionId })
  });
  if (res) { showToast(`Initialized ${res.initialized} records.`, 'success'); loadAttendance(currentSessionId); }
}

// ── Correct modal ────────────────────────────────────────────────────────────
function openCorrect(recordId, studentName, currentStatus) {
  document.getElementById('correctRecordId').value = recordId;
  document.getElementById('correctStudentName').textContent = studentName;
  document.getElementById('correctStatus').value = currentStatus;
  document.getElementById('correctNotes').value = '';
  new bootstrap.Modal(document.getElementById('correctModal')).show();
}

document.getElementById('saveCorrectBtn').addEventListener('click', async () => {
  const id     = document.getElementById('correctRecordId').value;
  const status = document.getElementById('correctStatus').value;
  const notes  = document.getElementById('correctNotes').value;
  const res = await apiFetch('/api/attendance/correct/' + id, {
    method: 'PATCH', body: JSON.stringify({ status, corrected_by: 'educator', notes })
  });
  if (res) {
    showToast('Attendance corrected.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('correctModal'))?.hide();
    loadAttendance(currentSessionId);
  }
});

// ── Session select listener ───────────────────────────────────────────────────
document.getElementById('sessionSelect').addEventListener('change', function() {
  loadAttendance(this.value ? parseInt(this.value) : null);
});

// Init
loadSessionOptions();
