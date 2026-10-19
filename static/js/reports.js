/**
 * reports.js – Reports page logic
 */

populateSessionSelect('reportSession');

function buildParams() {
  const session  = document.getElementById('reportSession').value;
  const dateFrom = document.getElementById('reportDateFrom').value;
  const dateTo   = document.getElementById('reportDateTo').value;
  const qs = new URLSearchParams();
  if (session)  qs.append('session_id', session);
  if (dateFrom) qs.append('date_from', dateFrom);
  if (dateTo)   qs.append('date_to', dateTo);
  return qs.toString();
}

document.getElementById('dlAttendanceCSV').addEventListener('click', () => {
  window.open('/api/reports/attendance/csv?' + buildParams());
});

document.getElementById('dlStudentCSV').addEventListener('click', () => {
  window.open('/api/reports/students/csv?' + buildParams());
});

document.getElementById('dlActivityCSV').addEventListener('click', () => {
  window.open('/api/reports/activity/csv?' + buildParams());
});

document.getElementById('dlRecsCSV').addEventListener('click', () => {
  window.open('/api/reports/recommendations/csv?' + buildParams());
});

document.getElementById('printAttendance').addEventListener('click', () => {
  const session = document.getElementById('reportSession').value;
  if (!session) { showToast('Select a session to print its attendance report.', 'warning'); return; }
  document.getElementById('previewCard').style.removeProperty('display');
  document.getElementById('reportIframe').src = `/api/reports/attendance/html/${session}`;
});

document.getElementById('closePreviewBtn').addEventListener('click', () => {
  document.getElementById('previewCard').style.setProperty('display','none','important');
});
