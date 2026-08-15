(() => {
  "use strict";

  const FORM_STATE_KEY = "brainai_detect_state_v1";

  const statusEl = document.getElementById("appStatus");
  const fileEl = document.getElementById("fileInputMain");
  const fileHintEl = document.getElementById("fileHintText");
  const uploadZone = document.getElementById("uploadZone");
  const selectFileBtn = document.getElementById("selectFileBtn");
  const patientEl = document.getElementById("patientSelectMain");
  const notesEl = document.getElementById("notesInputMain");
  const modelEl = document.getElementById("modelChoiceMain");
  const modelLabelText = document.getElementById("modelLabelText");
  const analyzeBtn = document.getElementById("analyzeBtnMain");
  const logoutBtn = document.getElementById("logoutBtn");
  const sourceImg = document.getElementById("sourcePreview");
  const processedImg = document.getElementById("processedPreview");
  const demoDetectOverlay = document.getElementById("demoDetectOverlay");
  const metricBar = document.getElementById("confidenceBar");
  const confidenceText = document.getElementById("confidenceText");
  const resultBadge = document.getElementById("resultBadge");
  const patientSnapshot = document.getElementById("patientSnapshot");
  const scanDate = document.getElementById("scanDate");
  const topUserName = document.getElementById("topUserName");
  const topUserRole = document.getElementById("topUserRole");
  const saveDiagnosisBtn = document.getElementById("saveDiagnosisBtn");
  const selectedRecordText = document.getElementById("selectedRecordText");
  const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
  const historyList = document.getElementById("historyList");
  const historyCountText = document.getElementById("historyCountText");
  const heightInput = document.getElementById("heightInputMain");
  const weightInput = document.getElementById("weightInputMain");
  const saveProfileBtn = document.getElementById("saveProfileBtn");
  const sidebarEl = document.querySelector("aside");

  if (!fileEl || !patientEl || !notesEl || !modelEl || !analyzeBtn) return;

  const hasToken = !!API.getToken();

  const patientsById = new Map();
  let currentUser = null;
  let selectedFile = null;
  let sourceObjectUrl = null;
  let currentRecordId = null;

  const setStatus = (text, isError = false) => {
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.style.color = isError ? "#dc2626" : "#64748b";
  };

  if (!hasToken) {
    if (sidebarEl) sidebarEl.style.visibility = "visible";
    if (topUserName) topUserName.textContent = "Guest Preview";
    if (topUserRole) topUserRole.textContent = "Please login to use features";
    if (logoutBtn) {
      logoutBtn.textContent = "Login";
      logoutBtn.onclick = () => (window.location.href = "login.html");
    }
    [fileEl, patientEl, notesEl, modelEl, analyzeBtn, saveDiagnosisBtn, refreshHistoryBtn, saveProfileBtn].forEach((el) => {
      if (el) el.disabled = true;
    });
    setStatus("Preview mode: login required for detect/history/profile actions.");
    return;
  }

  const roleLabel = (role) => {
    if (role === "doctor") return "Doctor";
    if (role === "patient") return "Patient";
    return "Medical Staff";
  };

  const displayName = (user) => user.full_name || user.username || `User #${user.id}`;

  const setTopUser = (user) => {
    if (topUserName) {
      topUserName.textContent = user.role === "doctor" ? `Dr. ${displayName(user)}` : displayName(user);
    }
    if (topUserRole) {
      topUserRole.textContent = roleLabel(user.role);
    }
    if (window.AppCommon?.initSidebar) {
      window.AppCommon.initSidebar(user);
    } else if (sidebarEl) {
      sidebarEl.style.visibility = "visible";
    }
  };

  const updateConfidence = (confidence) => {
    const safe = Math.max(0, Math.min(100, Number(confidence || 0)));
    if (metricBar) metricBar.style.width = `${safe}%`;
    if (confidenceText) confidenceText.textContent = `${safe.toFixed(1)}%`;
  };

  const updateModelLabel = () => {
    if (!modelLabelText || !modelEl) return;
    const map = {
      ensemble: "YOLO11 + EfficientNet-B0 (Ensemble)",
      yolo: "YOLO11",
      cnn: "EfficientNet-B0"
    };
    modelLabelText.textContent = `Model: ${map[modelEl.value] || "YOLO11 + EfficientNet-B0 (Ensemble)"}`;
  };

  const saveDetectState = () => {
    const payload = {
      patientId: patientEl.value || "",
      modelChoice: modelEl.value || "ensemble",
      notes: notesEl.value || ""
    };
    localStorage.setItem(FORM_STATE_KEY, JSON.stringify(payload));
  };

  const restoreDetectState = () => {
    try {
      const raw = localStorage.getItem(FORM_STATE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data.modelChoice) modelEl.value = data.modelChoice;
      if (typeof data.notes === "string") notesEl.value = data.notes;
      if (data.patientId && patientEl.querySelector(`option[value="${data.patientId}"]`)) {
        patientEl.value = data.patientId;
      }
    } catch (_) {}
  };

  const updatePatientSnapshot = () => {
    const pid = patientEl.value;
    const user = patientsById.get(pid);
    if (patientSnapshot) {
      patientSnapshot.textContent = user ? `Patient: ${displayName(user)} (#${user.id})` : `Patient: #${pid || "N/A"}`;
    }
  };

  const setSelectedFile = (file) => {
    selectedFile = file || null;
    if (!selectedFile) return;
    if (sourceObjectUrl) URL.revokeObjectURL(sourceObjectUrl);
    sourceObjectUrl = URL.createObjectURL(selectedFile);
    if (sourceImg) sourceImg.src = sourceObjectUrl;
    if (processedImg) processedImg.src = sourceObjectUrl;
    if (demoDetectOverlay) demoDetectOverlay.style.display = "flex";
    if (fileHintEl) fileHintEl.textContent = `Selected: ${selectedFile.name}`;
    setStatus(`Selected file: ${selectedFile.name}`);
  };

  const fillPatientSelect = (users, selfUser) => {
    patientEl.innerHTML = "";
    patientsById.clear();

    if (selfUser.role === "doctor") {
      users.forEach((u) => {
        patientsById.set(String(u.id), u);
        const opt = document.createElement("option");
        opt.value = String(u.id);
        opt.textContent = `${displayName(u)} (#${u.id})`;
        patientEl.appendChild(opt);
      });
      return;
    }

    patientsById.set(String(selfUser.id), selfUser);
    const opt = document.createElement("option");
    opt.value = String(selfUser.id);
    opt.textContent = `${displayName(selfUser)} (#${selfUser.id})`;
    patientEl.appendChild(opt);
    patientEl.disabled = true;
  };

  const hydrateProfileInputs = () => {
    const pid = patientEl.value;
    const target = currentUser?.role === "doctor" ? patientsById.get(pid) : currentUser;
    if (!target) return;
    if (heightInput) heightInput.value = target.height ?? 0;
    if (weightInput) weightInput.value = target.weight ?? 0;
  };

  const renderHistory = (records) => {
    if (!historyList) return;
    historyList.innerHTML = "";
    if (historyCountText) historyCountText.textContent = `${records.length} records`;

    if (!records.length) {
      const empty = document.createElement("p");
      empty.className = "text-xs text-slate-500";
      empty.textContent = "No diagnosis history yet.";
      historyList.appendChild(empty);
      return;
    }

    records.forEach((rec) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "w-full text-left px-3 py-2 rounded-lg border border-slate-200 hover:bg-slate-50";
      item.innerHTML = `
        <p class="text-xs font-bold text-slate-700">${rec.prediction_result} (${Number(rec.confidence || 0).toFixed(1)}%)</p>
        <p class="text-[11px] text-slate-500">${new Date(rec.created_at).toLocaleString()}</p>
      `;
      item.addEventListener("click", () => {
        currentRecordId = rec.id;
        if (selectedRecordText) selectedRecordText.textContent = `Selected Record #${rec.id}`;
        if (processedImg && rec.image_path) processedImg.src = API.getUploadUrl(rec.image_path);
        if (demoDetectOverlay) demoDetectOverlay.style.display = "none";
        if (notesEl && typeof rec.notes === "string") notesEl.value = rec.notes;
        if (resultBadge) resultBadge.textContent = rec.prediction_result || "UPDATED";
        if (scanDate) scanDate.textContent = `Scan Date: ${new Date(rec.created_at).toLocaleString()}`;
        updateConfidence(rec.confidence);
        saveDetectState();
      });
      historyList.appendChild(item);
    });
  };

  const loadHistory = async () => {
    try {
      const pid = currentUser?.role === "doctor" ? (parseInt(patientEl.value || "0", 10) || null) : null;
      const records = await API.getRecords(pid || null);
      renderHistory(records);
    } catch (e) {
      setStatus(`History error: ${e.message}`, true);
    }
  };

  if (selectFileBtn) {
    selectFileBtn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      fileEl.click();
    });
  }

  if (uploadZone) {
    uploadZone.addEventListener("click", (e) => {
      if (e.target && e.target.closest && e.target.closest("#selectFileBtn")) return;
      fileEl.click();
    });
    uploadZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadZone.classList.add("ring-2", "ring-primary/40");
    });
    uploadZone.addEventListener("dragleave", () => {
      uploadZone.classList.remove("ring-2", "ring-primary/40");
    });
    uploadZone.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadZone.classList.remove("ring-2", "ring-primary/40");
      const file = e.dataTransfer?.files?.[0];
      if (file) setSelectedFile(file);
    });
  }

  fileEl.addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  });

  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => API.logout());
  }

  patientEl.addEventListener("change", async () => {
    updatePatientSnapshot();
    hydrateProfileInputs();
    saveDetectState();
    await loadHistory();
  });
  modelEl.addEventListener("change", () => {
    updateModelLabel();
    saveDetectState();
  });
  notesEl.addEventListener("input", saveDetectState);

  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return setStatus("Please choose an image file first.", true);
    const patientId = parseInt(patientEl.value || "0", 10);
    if (!patientId) return setStatus("Please choose patient.", true);

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
    setStatus("Running AI prediction...");

    try {
      const rec = await API.predict(selectedFile, patientId, notesEl.value.trim(), modelEl.value);
      currentRecordId = rec.id || null;
      if (selectedRecordText && currentRecordId) selectedRecordText.textContent = `Selected Record #${currentRecordId}`;
      if (processedImg && rec.image_path) processedImg.src = API.getUploadUrl(rec.image_path);
      if (demoDetectOverlay) demoDetectOverlay.style.display = "none";
      updateConfidence(rec.confidence);
      if (resultBadge) resultBadge.textContent = rec.prediction_result || "UPDATED";
      if (scanDate) scanDate.textContent = `Scan Date: ${new Date().toLocaleString()}`;
      updatePatientSnapshot();
      setStatus(`Done: ${rec.prediction_result} (${Number(rec.confidence || 0).toFixed(1)}%)`);
      await loadHistory();
    } catch (e) {
      setStatus(`Predict error: ${e.message}`, true);
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = "Analyze";
    }
  });

  if (saveDiagnosisBtn) {
    saveDiagnosisBtn.addEventListener("click", async () => {
      if (!currentRecordId) {
        setStatus("Please run Analyze first to create a diagnosis record.", true);
        return;
      }
      try {
        await API.updateRecord(currentRecordId, { notes: notesEl.value.trim() });
        setStatus(`Saved diagnosis note for record #${currentRecordId}`);
        await loadHistory();
      } catch (e) {
        setStatus(`Save diagnosis error: ${e.message}`, true);
      }
    });
  }

  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", async () => {
      const height = parseFloat(heightInput?.value || "0") || 0;
      const weight = parseFloat(weightInput?.value || "0") || 0;
      try {
        if (currentUser?.role === "doctor") {
          await API.updatePatientProfile(patientEl.value, height, weight);
          const selected = patientsById.get(patientEl.value);
          if (selected) {
            selected.height = height;
            selected.weight = weight;
          }
        } else {
          currentUser = await API.updateProfile(height, weight);
          patientsById.set(String(currentUser.id), currentUser);
        }
        hydrateProfileInputs();
        setStatus("Profile saved.");
      } catch (e) {
        setStatus(`Save profile error: ${e.message}`, true);
      }
    });
  }

  if (refreshHistoryBtn) {
    refreshHistoryBtn.addEventListener("click", loadHistory);
  }

  (async () => {
    try {
      API.warmup().catch(() => {});
      currentUser = await API.getMe();
      setTopUser(currentUser);
      if (currentUser.role === "doctor") {
        fillPatientSelect(await API.getPatients(), currentUser);
      } else {
        fillPatientSelect([], currentUser);
        if (saveDiagnosisBtn) saveDiagnosisBtn.disabled = true;
      }
      restoreDetectState();
      updateModelLabel();
      updatePatientSnapshot();
      hydrateProfileInputs();
      await loadHistory();
      setStatus("Ready");
    } catch (e) {
      setStatus(`Init error: ${e.message}`, true);
    }
  })();
})();
