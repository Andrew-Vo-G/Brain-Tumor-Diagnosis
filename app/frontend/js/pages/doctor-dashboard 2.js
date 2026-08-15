(async function () {
  const me = await AppCommon.initPage({ requireRole: 'doctor' });
  if (!me) return;

  const statusEl = document.getElementById('dashboardStatus');
  const totalPatientsEl = document.getElementById('statTotalPatients');
  const weeklyCasesEl = document.getElementById('statWeeklyCases');
  const analyzedCasesEl = document.getElementById('statAnalyzedCases');
  const tableBody = document.getElementById('recordsTableBody');

  function setStatus(text, isError) {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.className = isError ? 'text-xs text-red-600' : 'text-xs text-slate-500';
  }

  function formatDate(dateString) {
    if (!dateString) return '--';
    const d = new Date(dateString);
    if (Number.isNaN(d.getTime())) return '--';
    return d.toLocaleDateString('en-US');
  }

  function fmtPrediction(row) {
    if (!row) return 'No data available';
    const conf = Number(row.confidence || 0);
    return `${row.prediction_result || 'Unknown'} (${conf.toFixed(1)}%)`;
  }

  try {
    setStatus('Loading data...');

    const [patients, records] = await Promise.all([
      API.getPatients(),
      API.getRecords()
    ]);

    const byUser = new Map();
    for (const record of records) {
      const uid = record.user_id;
      const prev = byUser.get(uid);
      if (!prev || new Date(record.created_at) > new Date(prev.created_at)) {
        byUser.set(uid, record);
      }
    }

    const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
    const weeklyCount = records.filter((r) => {
      const t = new Date(r.created_at).getTime();
      return !Number.isNaN(t) && t >= oneWeekAgo;
    }).length;

    totalPatientsEl.textContent = String(patients.length);
    weeklyCasesEl.textContent = String(weeklyCount);
    analyzedCasesEl.textContent = String(records.length);

    if (!patients.length) {
      tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">No patients yet.</td></tr>';
      setStatus('No patients found');
      return;
    }

    const rows = patients.slice(0, 10).map((p) => {
      const latest = byUser.get(p.id);
      const latestDate = latest?.created_at ? formatDate(latest.created_at) : '--';
      const prediction = fmtPrediction(latest);
      const aiStatus = latest ? 'Completed' : 'Pending';
      const aiClass = latest ? 'text-green-700' : 'text-slate-500';
      return `
        <tr class="hover:bg-slate-50 transition-colors">
          <td class="px-6 py-4 text-sm font-mono text-blue-700">#PAT-${String(p.id).padStart(4, '0')}</td>
          <td class="px-6 py-4 text-sm font-semibold text-slate-900">${p.full_name || p.username || 'Unknown'}</td>
          <td class="px-6 py-4 text-sm text-slate-600">${latestDate}</td>
          <td class="px-6 py-4 text-sm text-slate-700">${prediction}</td>
          <td class="px-6 py-4 text-sm font-semibold ${aiClass}">${aiStatus}</td>
          <td class="px-6 py-4 text-right">
            <a href="history.html" class="text-blue-700 font-bold text-xs hover:underline">View history</a>
          </td>
        </tr>
      `;
    }).join('');

    tableBody.innerHTML = rows;
    setStatus(`Loaded ${patients.length} patients, ${records.length} records.`);
  } catch (err) {
    tableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-red-600">Failed to load dashboard data.</td></tr>';
    setStatus(`Error: ${err.message}`, true);
  }
})();
