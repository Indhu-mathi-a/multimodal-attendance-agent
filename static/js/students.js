/**
 * students.js – Student management page logic
 */

let allStudents = [];
let deleteTargetId = null;

// ── Load & Render ────────────────────────────────────────────────────────────
async function loadStudents() {
  const q    = document.getElementById('searchInput').value;
  const dept = document.getElementById('deptFilter').value;
  const qs   = new URLSearchParams({ q, department: dept, active: 'true' });
  allStudents = await apiFetch('/api/students?' + qs) || [];
  renderTable(allStudents);
}

function renderTable(students) {
  const tbody = document.getElementById('studentsBody');
  if (!students.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-5 text-muted">
      <i class="bi bi-people fs-1 d-block mb-2 opacity-25"></i>No students found.
      <a href="#" onclick="document.getElementById('addStudentBtn').click()">Add one →</a></td></tr>`;
    return;
  }
  tbody.innerHTML = students.map(s => `
    <tr class="fade-in">
      <td><span class="badge bg-primary">${s.student_id}</span></td>
      <td><strong>${s.name}</strong></td>
      <td>${s.department || '–'}</td>
      <td>${s.email || '–'}</td>
      <td>${s.enrolled_at ? s.enrolled_at.split('T')[0] : '–'}</td>
      <td>
        <button class="btn btn-sm btn-outline-primary me-1" onclick="openEdit(${s.id})">
          <i class="bi bi-pencil"></i>
        </button>
        <button class="btn btn-sm btn-outline-danger" onclick="openDelete(${s.id}, '${s.name.replace(/'/g,"\\'")}')">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    </tr>`).join('');
}

// ── Load Departments ─────────────────────────────────────────────────────────
async function loadDepts() {
  const depts = await apiFetch('/api/students/departments') || [];
  const sel = document.getElementById('deptFilter');
  sel.innerHTML = '<option value="">All Departments</option>' +
    depts.map(d => `<option value="${d}">${d}</option>`).join('');
}

// ── Add/Edit Modal ────────────────────────────────────────────────────────────
function openAdd() {
  document.getElementById('editStudentId').value = '';
  document.getElementById('studentModalLabel').textContent = 'Add Student';
  document.getElementById('studentForm').reset();
  document.getElementById('fieldStudentId').removeAttribute('readonly');
  document.getElementById('formError').classList.add('d-none');
}

async function openEdit(id) {
  const s = await apiFetch('/api/students/' + id);
  if (!s) return;
  document.getElementById('editStudentId').value  = s.id;
  document.getElementById('fieldStudentId').value = s.student_id;
  document.getElementById('fieldName').value       = s.name;
  document.getElementById('fieldDept').value       = s.department;
  document.getElementById('fieldEmail').value      = s.email;
  document.getElementById('fieldPhone').value      = s.phone;
  document.getElementById('fieldNotes').value      = s.notes;
  document.getElementById('fieldStudentId').setAttribute('readonly', true);
  document.getElementById('studentModalLabel').textContent = 'Edit Student';
  document.getElementById('formError').classList.add('d-none');
  new bootstrap.Modal(document.getElementById('studentModal')).show();
}

document.getElementById('saveStudentBtn').addEventListener('click', async () => {
  const id = document.getElementById('editStudentId').value;
  const payload = {
    student_id: document.getElementById('fieldStudentId').value.trim(),
    name:       document.getElementById('fieldName').value.trim(),
    department: document.getElementById('fieldDept').value.trim(),
    email:      document.getElementById('fieldEmail').value.trim(),
    phone:      document.getElementById('fieldPhone').value.trim(),
    notes:      document.getElementById('fieldNotes').value.trim(),
  };

  const url    = id ? `/api/students/${id}` : '/api/students';
  const method = id ? 'PUT' : 'POST';
  const result = await apiFetch(url, { method, body: JSON.stringify(payload) });

  if (result) {
    showToast(id ? 'Student updated.' : 'Student added.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('studentModal'))?.hide();
    loadStudents();
    loadDepts();
  }
});

// ── Delete ───────────────────────────────────────────────────────────────────
function openDelete(id, name) {
  deleteTargetId = id;
  document.getElementById('deleteStudentName').textContent = name;
  new bootstrap.Modal(document.getElementById('deleteModal')).show();
}

document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
  if (!deleteTargetId) return;
  const res = await apiFetch('/api/students/' + deleteTargetId, { method: 'DELETE' });
  if (res) {
    showToast('Student deactivated.', 'success');
    bootstrap.Modal.getInstance(document.getElementById('deleteModal'))?.hide();
    loadStudents();
  }
});

// ── CSV Import ───────────────────────────────────────────────────────────────
document.getElementById('csvImport').addEventListener('change', async function() {
  if (!this.files.length) return;
  const formData = new FormData();
  formData.append('file', this.files[0]);
  const resp = await fetch('/api/students/import/csv', { method: 'POST', body: formData });
  const data = await resp.json();
  if (resp.ok) {
    showToast(`Imported ${data.imported} students, skipped ${data.skipped}.`, 'success');
    loadStudents();
  } else {
    showToast(data.error || 'Import failed.', 'danger');
  }
  this.value = '';
});

// ── Listeners ────────────────────────────────────────────────────────────────
document.getElementById('addStudentBtn').addEventListener('click', openAdd);
document.getElementById('searchInput').addEventListener('input', () => loadStudents());
document.getElementById('deptFilter').addEventListener('change', () => loadStudents());

// Init
loadDepts();
loadStudents();
