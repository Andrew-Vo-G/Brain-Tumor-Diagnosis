(async function () {
  const me = await AppCommon.initPage({ requireRole: 'patient' });
  if (!me) return;

  const recordList = document.getElementById('patientRecords');
  const symptomName = document.getElementById('symptomName');
  const symptomSeverity = document.getElementById('symptomSeverity');
  const symptomNotes = document.getElementById('symptomNotes');
  const symptomList = document.getElementById('symptomList');
  const patientStatus = document.getElementById('patientStatus');

  function renderStatus(msg, isError = false) {
    if (!patientStatus) return;
    patientStatus.textContent = msg;
    patientStatus.className = isError 
      ? "font-bold text-sm text-red-600 mt-2" 
      : "font-bold text-sm text-primary mt-2";
  }

  async function loadRecords() {
    if (!recordList) return;
    try {
      const records = await API.getRecords();
      if (!records.length) {
        recordList.innerHTML = '<p class="text-sm text-slate-500">No diagnostic results yet.</p>';
      } else {
        recordList.innerHTML = records.map(r => `
          <div class="border border-outline-variant/30 rounded-xl p-4 bg-white shadow-sm flex flex-col md:flex-row gap-4">
            <div class="flex-1">
              <div class="flex justify-between items-start mb-2">
                <span class="bg-primary/10 text-primary font-bold text-xs px-2 py-1 rounded-md uppercase tracking-wide">AI Predict</span>
                <span class="text-xs font-semibold text-slate-500">${new Date(r.created_at).toLocaleDateString()}</span>
              </div>
              <p class="font-bold text-lg text-on-surface mb-1">${r.prediction_result}</p>
              <p class="text-sm font-semibold text-slate-600 mb-2">Confidence: <span class="${r.confidence > 80 ? 'text-green-600' : 'text-amber-600'}">${Number(r.confidence || 0).toFixed(1)}%</span></p>
              <p class="text-sm text-slate-700 bg-surface-container-low p-2 rounded-lg italic">Notes: ${r.notes || 'No notes available'}</p>
            </div>
            
            <div class="flex-shrink-0 cursor-pointer group rounded-xl overflow-hidden relative border border-slate-200">
              ${r.image_path ? `
                <a href="${API.getUploadUrl(r.image_path)}" target="_blank" class="block w-full h-full">
                  <img src="${API.getUploadUrl(r.image_path)}" class="w-full md:w-32 h-32 object-cover transition duration-300 group-hover:scale-110" />
                  <div class="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center transition">
                    <span class="material-symbols-outlined text-white mb-1">zoom_in</span>
                  </div>
                </a>` : ''}
            </div>
          </div>
        `).join('');
      }
    } catch (e) {
      renderStatus(`Error loading records: ${e.message}`, true);
    }
  }

  async function loadSymptoms() {
    if (!symptomList) return;
    try {
      const symptoms = await API.getSymptoms();
      if (!symptoms.length) {
        symptomList.innerHTML = '<p class="text-sm text-slate-500">No symptoms recorded yet.</p>';
      } else {
        symptomList.innerHTML = symptoms.map(s => `
          <div class="border border-outline-variant/20 rounded-lg p-3 bg-white shadow-sm flex flex-col gap-1">
            <div class="flex justify-between items-center">
              <p class="text-sm font-bold text-on-surface">${s.symptom_name}</p>
              <span class="${s.severity > 7 ? 'bg-red-100 text-red-700' : (s.severity > 4 ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700')} text-[10px] font-bold px-2 py-0.5 rounded-full">
                Severity ${s.severity}/10
              </span>
            </div>
            <p class="text-xs text-slate-500">${new Date(s.logged_at).toLocaleString()}</p>
            ${s.notes ? `<p class="text-xs text-slate-600 mt-1">${s.notes}</p>` : ''}
          </div>
        `).join('');
      }
    } catch (e) {
      renderStatus(`Error loading symptoms: ${e.message}`, true);
    }
  }

  async function addSymptom() {
    try {
      if (!symptomName.value.trim()) return;
      await API.logSymptom(symptomName.value.trim(), parseInt(symptomSeverity.value || '5', 10), symptomNotes.value.trim());
      symptomName.value = '';
      symptomNotes.value = '';
      await loadSymptoms();
      renderStatus('Symptom logged successfully.');
    } catch (e) {
      renderStatus(`Error logging symptom: ${e.message}`, true);
    }
  }

  if (document.getElementById('logSymptomBtn')) {
    document.getElementById('logSymptomBtn').addEventListener('click', addSymptom);
  }
  
  await loadRecords();
  await loadSymptoms();
})();
