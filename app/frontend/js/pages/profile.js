(async function () {
  const me = await AppCommon.initPage();
  if (!me) return;

  const patientSelect = document.getElementById('patientSelect');
  const heightEl = document.getElementById('heightInput');
  const weightEl = document.getElementById('weightInput');
  const saveBtn = document.getElementById('saveBtn');

  async function loadPatients() {
    if (me.role !== 'doctor') {
      patientSelect.innerHTML = `<option value="${me.id}">${me.full_name || me.username}</option>`;
      patientSelect.disabled = true;
      heightEl.value = me.height || 0;
      weightEl.value = me.weight || 0;
      return;
    }
    const pts = await API.getPatients();
    patientSelect.innerHTML = pts.map(p => `<option value="${p.id}" data-h="${p.height || 0}" data-w="${p.weight || 0}">${p.full_name || p.username} (#${p.id})</option>`).join('');
    loadSelectedProfile();
  }

  function loadSelectedProfile() {
    const opt = patientSelect.options[patientSelect.selectedIndex];
    heightEl.value = opt?.dataset?.h || 0;
    weightEl.value = opt?.dataset?.w || 0;
  }

  async function saveProfile() {
    try {
      AppCommon.setStatus('profileStatus', 'Saving profile...');
      const h = parseFloat(heightEl.value || '0') || 0;
      const w = parseFloat(weightEl.value || '0') || 0;
      if (me.role === 'doctor') {
        await API.updatePatientProfile(patientSelect.value, h, w);
      } else {
        await API.updateProfile(h, w);
      }
      AppCommon.setStatus('profileStatus', 'Profile saved successfully.');
    } catch (e) {
      AppCommon.setStatus('profileStatus', `Profile error: ${e.message}`, true);
    }
  }

  await loadPatients();
  patientSelect.addEventListener('change', loadSelectedProfile);
  saveBtn.addEventListener('click', saveProfile);
})();
