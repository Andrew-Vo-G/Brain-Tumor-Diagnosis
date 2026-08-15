(async function () {
  const me = await AppCommon.initPage();
  if (!me) return;

  const patientSelect = document.getElementById('patientSelect');
  const list = document.getElementById('historyList');
  const statusId = 'historyStatus';

  async function loadPatients() {
    if (me.role !== 'doctor') {
      patientSelect.innerHTML = `<option value="${me.id}">${me.full_name || me.username}</option>`;
      patientSelect.disabled = true;
      return;
    }
    const pts = await API.getPatients();
    patientSelect.innerHTML = pts.map(p => `<option value="${p.id}">${p.full_name || p.username} (#${p.id})</option>`).join('');
  }

  async function loadHistory() {
    try {
      AppCommon.setStatus(statusId, 'Loading history...');
      const pid = me.role === 'doctor' ? (patientSelect.value || null) : null;
      const records = await API.getRecords(pid);
      if (!records.length) {
        list.innerHTML = '<p class="text-sm text-slate-500">No records found.</p>';
      } else {
        list.innerHTML = records.map(r => `
          <div class="rounded-lg border border-slate-200 p-3 bg-white">
            <div class="flex justify-between items-center mb-1">
              <p class="font-semibold text-sm">${r.prediction_result}</p>
              <p class="text-xs text-slate-500">${Number(r.confidence || 0).toFixed(1)}%</p>
            </div>
            <p class="text-xs text-slate-500 mb-2">${new Date(r.created_at).toLocaleString()} - ${r.patient_name || 'Unknown'}</p>
            <p class="text-sm text-slate-700">${r.notes || 'No notes'}</p>
            ${r.image_path ? `<a class="text-xs text-blue-600 mt-2 inline-block" href="/uploads/${r.image_path}" target="_blank">Open image</a>` : ''}
          </div>
        `).join('');
      }
      AppCommon.setStatus(statusId, `Loaded ${records.length} records`);
    } catch (e) {
      AppCommon.setStatus(statusId, `History error: ${e.message}`, true);
    }
  }

  await loadPatients();
  await loadHistory();
  patientSelect.addEventListener('change', loadHistory);
  document.getElementById('refreshBtn').addEventListener('click', loadHistory);
})();
