/**
 * sessions.js – Session management page logic
 */

async function loadSessions() {
  const status   = document.getElementById('statusFilter').value;
  const dateFrom = document.getElementById('dateFrom').value;
  const dateTo   = document.getElementById('dateTo').value;
  const qs = new URLSearchParams({ status, date_from: dateFrom, date_to: dateTo });
  const sessions = await apiFetch('/api/sessions?' + qs) || [];
  renderSessions(sessions);
}

function renderSessions(sessions) {
  const tbody = document.getElementById('sessionsBody');
  if (!sessions.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted">
      <i class="bi bi-calendar2-x fs-1 d-block mb-2 opacity-25"></i>
      No sessions found. <button class="btn btn-link p-0" data-bs-toggle="modal"
        data-bs-target="#sessionModal">Create one →</button></td></tr>`;
    return;
  }
  tbody.innerHTML = sessions.map(s => `
    <tr class="fade-in">
      <td><strong>${s.session_name}</strong></td>
      <td>${s.subject}</td>
      <td>${s.department || '–'}</td>
      <td>${s.session_date}</td>
      <td>${s.start_time} – ${s.end_time}</td>
      <td>${statusBadge(s.status)}</td>
      <td>
        <div class="d-flex gap-1 flex-wrap">
          <a href="/attendance?session=${s.id}" class="btn btn-xs btn-outline-primary">
            <i class="bi bi-clipboard2-check"></i>
          </a>
          <button class="btn btn-xs btn-outline-secondary" onclick="editSession(${s.id})">
            <i class="bi bi-pencil"></i>
          </button>
          <button class="btn btn-xs btn-outline-${s.status === 'active' ? 'success' : 'warning'}"
            onclick="changeStatus(${s.id}, '${s.status}')">
            <i class="bi bi-${s.status === 'active' ? 'stop-circle' : 'play-circle'}"></i>
          </button>
          <button class="btn btn-xs btn-outline-danger" onclick="deleteSession(${s.id})">
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </td>
    </tr>`).join('');
}

// ── Load students into the checkbox list ──────────────────────────────────────
async function loadStudentCheckboxes() {
  const students = await apiFetch('/api/students') || [];
  const container = document.getElementById('studentCheckboxes');
  if (!students.length) {
    container.innerHTML = '<p class="text-muted small mb-0">No students registered yet.</p>';
    return;
  }
  container.innerHTML = students.map(s => `
    <div class="form-check">
      <input class="form-check-input stu-check" type="checkbox"
             value="${s.id}" id="stu_${s.id}" />
      <label class="form-check-label small" for="stu_${s.id}">
        [${s.student_id}] ${s.name} – ${s.department}
      </label>
    </div>`).join('');
}

// ── Save session ─────────────────────────────────────────────────────────────
document.getElementById('saveSessionBtn').addEventListener('click', async () => {
  const id = document.getElementById('editSessionId').value;
  const studentIds = [...document.querySelectorAll('.stu-check:checked')].map(c => +c.value);

  const payload = {
    session_name: document.getElementById('sName').value.trim(),
    subject:      document.getElementById('sSubject').value.trim(),
    department:   document.getElementById('sDept').value.trim(),
    session_date: document.getElementById('sDate').value,
    start_time:   document.getElementById('sStart').value,
    end_time:     document.getElementById('sEnd').value,
    notes:        document.getElementById('sNotes').value.trim(),
    student_ids:  studentIds,
  };

  const url = id ? `/api/sessions/${id}` : '/api/sessions';
  const method = id ? 'PUT' : 'POST';
  const result = await apiFetch(url, { method, body: JSON.stringify(payload) });

  if (result) {
    showToast(id ? 'Session updated.' : 'Session created.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('sessionModal'))?.hide();
    loadSessions();
  }
});

// ── Edit ─────────────────────────────────────────────────────────────────────
async function editSession(id) {
  const s = await apiFetch('/api/sessions/' + id);
  if (!s) return;
  document.getElementById('editSessionId').value = s.id;
  document.getElementById('sName').value         = s.session_name;
  document.getElementById('sSubject').value      = s.subject;
  document.getElementById('sDept').value         = s.department;
  document.getElementById('sDate').value         = s.session_date;
  document.getElementById('sStart').value        = s.start_time;
  document.getElementById('sEnd').value          = s.end_time;
  document.getElementById('sNotes').value        = s.notes;
  document.getElementById('sessionModalLabel').textContent = 'Edit Session';
  new bootstrap.Modal(document.getElementById('sessionModal')).show();
}

// ── Status change ─────────────────────────────────────────────────────────────
async function changeStatus(id, currentStatus) {
  const next = currentStatus === 'active' ? 'completed' : 'active';
  const res = await apiFetch(`/api/sessions/${id}/status`, {
    method: 'PATCH', body: JSON.stringify({ status: next })
  });
  if (res) { showToast(`Session marked ${next}.`, 'success'); loadSessions(); }
}

// ── Delete ────────────────────────────────────────────────────────────────────
async function deleteSession(id) {
  if (!confirm('Delete this session and ALL related attendance records? This cannot be undone.')) return;
  const res = await apiFetch('/api/sessions/' + id, { method: 'DELETE' });
  if (res) { showToast('Session deleted.', 'success'); loadSessions(); }
}

// ── Init ─────────────────────────────────────────────────────────────────────
document.getElementById('addSessionBtn').addEventListener('click', () => {
  document.getElementById('editSessionId').value = '';
  document.getElementById('sessionModalLabel').textContent = 'New Session';
  document.getElementById('sessionForm').reset();
  loadStudentCheckboxes();
});

document.getElementById('sessionModal').addEventListener('show.bs.modal', () => {
  if (!document.getElementById('editSessionId').value) loadStudentCheckboxes();
});

document.getElementById('filterBtn').addEventListener('click', loadSessions);

// Set today's date as default
document.getElementById('sDate').valueAsDate = new Date();
loadSessions();
