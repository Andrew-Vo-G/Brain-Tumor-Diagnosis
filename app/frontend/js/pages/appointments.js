(async function () {
  const me = await AppCommon.initPage();
  if (!me) return;

  const statusEl = document.getElementById('appointmentStatus');
  const bookingWrap = document.getElementById('bookingWrap');
  const doctorListEl = document.getElementById('doctorList');
  const historyListEl = document.getElementById('appointmentHistoryList');
  const dateInput = document.getElementById('appointmentDate');
  const timeBtns = document.querySelectorAll('.time-slot-btn');
  const bookBtn = document.getElementById('bookConfirmBtn');
  const notesInput = document.getElementById('appointmentNotes');
  
  const nextApptCard = document.getElementById('nextAppointmentCard');
  const nextApptDate = document.getElementById('nextApptDate');
  const nextApptDoctor = document.getElementById('nextApptDoctor');

  let selectedDoctorId = null;
  let selectedTime = null;

  // Set default date to today
  if (dateInput) {
    const today = new Date();
    dateInput.value = today.toISOString().split('T')[0];
    dateInput.min = today.toISOString().split('T')[0];
  }

  function renderStatus(msg, isError = false) {
    if (!statusEl) return;
    statusEl.textContent = msg;
    statusEl.className = isError ? "mt-2 text-sm text-red-600 font-semibold" : "mt-2 text-sm text-green-600 font-semibold";
  }

  // Handle Role displaying
  if (me.role === 'doctor') {
    if (bookingWrap) {
        // Hide the left column entirely and right column booking
        const leftCol = bookingWrap.querySelector('.lg\\:col-span-7');
        const rightCol = bookingWrap.querySelector('.lg\\:col-span-5');
        if (rightCol) rightCol.style.display = 'none';
        if (leftCol) leftCol.className = 'col-span-1 lg:col-span-12 space-y-8';
        
        // Hide doctor list UI for doctors
        const docSection = doctorListEl?.closest('section');
        if (docSection) docSection.style.display = 'none';
    }
  }

  // Load doctors for Booking
  async function loadDoctors() {
    if (me.role === 'doctor' || !doctorListEl) return;
    try {
      const doctors = await API.getDoctors();
      if (!doctors.length) {
        doctorListEl.innerHTML = '<p class="text-sm text-slate-500">No doctors available.</p>';
        return;
      }
      
      doctorListEl.innerHTML = doctors.map(d => `
        <div class="doctor-card bg-surface-container-low p-5 rounded-xl border border-outline-variant/10 hover:bg-surface-container-lowest transition-colors cursor-pointer" data-id="${d.id}">
          <div class="flex items-start gap-4">
            <div class="relative w-16 h-16 rounded-full overflow-hidden bg-primary/10 flex items-center justify-center text-primary font-bold text-xl ring-2 ring-transparent transition">
              ${(d.full_name || d.username).charAt(0).toUpperCase()}
            </div>
            <div class="flex-1">
              <h4 class="font-headline font-bold text-on-surface">Dr. ${d.full_name || d.username}</h4>
              <p class="text-xs text-primary font-semibold mb-2">Neurology Specialist</p>
            </div>
          </div>
        </div>
      `).join('');

      // Add click events to doctor cards
      document.querySelectorAll('.doctor-card').forEach(card => {
        card.addEventListener('click', function() {
          // Deselect others
          document.querySelectorAll('.doctor-card').forEach(c => {
            c.classList.remove('border-l-4', 'border-l-primary', 'bg-surface-container-lowest');
            c.classList.add('bg-surface-container-low');
          });
          // Select this one
          this.classList.remove('bg-surface-container-low');
          this.classList.add('border-l-4', 'border-l-primary', 'bg-surface-container-lowest');
          selectedDoctorId = this.getAttribute('data-id');
        });
      });
      
      // Auto select first doctor
      const firstDoc = document.querySelector('.doctor-card');
      if (firstDoc) firstDoc.click();

    } catch (e) {
      renderStatus(`Error loading doctors: ${e.message}`, true);
    }
  }

  // Time Slot Selection
  if (timeBtns) {
    timeBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        if (this.classList.contains('cursor-not-allowed')) return;
        
        // Deselect others
        timeBtns.forEach(b => {
          b.classList.remove('bg-primary-fixed', 'text-on-primary-fixed', 'border-primary', 'border-2');
          b.classList.add('bg-surface-container-low', 'text-on-surface');
        });
        
        // Select this
        this.classList.remove('bg-surface-container-low', 'text-on-surface');
        this.classList.add('bg-primary-fixed', 'text-on-primary-fixed', 'border-primary', 'border-2');
        selectedTime = this.getAttribute('data-time');
      });
    });
  }

  // Load Appointments
  async function loadAppointments() {
    if (!historyListEl) return;
    try {
      const data = await API.getAppointments();
      if (!data.length) {
        historyListEl.innerHTML = '<p class="text-sm text-slate-500">No appointments scheduled.</p>';
        if (nextApptCard) nextApptCard.style.display = 'none';
      } else {
        historyListEl.innerHTML = data.map(a => {
          const dt = new Date(a.appointment_date);
          const timeStr = dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          const dateStr = dt.toLocaleDateString('en-US', { day: '2-digit', month: 'short' });
          const otherPerson = me.role === 'doctor' ? (a.patient_name || 'Patient') : (a.doctor_name || 'Doctor');
          const isPending = a.status === 'pending';
          
          const icon = isPending ? 'pending_actions' : 'check_circle';
          const iconColor = isPending ? 'text-amber-500' : 'text-primary';
          const iconBg = isPending ? 'bg-amber-100' : 'bg-primary-fixed/50';
          const statusText = isPending ? 'Pending' : 'Confirmed';

          return `
            <div class="flex items-center justify-between p-4 bg-surface-container-lowest rounded-xl border border-outline-variant/10">
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-full ${iconBg} flex items-center justify-center ${iconColor}">
                  <span class="material-symbols-outlined" data-icon="${icon}" style="${!isPending ? "font-variation-settings: 'FILL' 1;" : ""}">${icon}</span>
                </div>
                <div>
                  <p class="font-bold text-sm">Meeting with ${otherPerson}</p>
                  <p class="text-xs text-on-surface-variant">${statusText} • ${timeStr}</p>
                </div>
              </div>
              <span class="text-xs font-bold text-on-surface-variant bg-surface-container px-3 py-1 rounded-full">${dateStr}</span>
            </div>
          `;
        }).join('');
        
        // Find next upcoming appointment
        const upcoming = data.filter(a => new Date(a.appointment_date) > new Date()).sort((a,b) => new Date(a.appointment_date) - new Date(b.appointment_date));
        if (upcoming.length > 0 && nextApptCard) {
            nextApptCard.style.display = 'flex';
            const nextOne = upcoming[0];
            const dt = new Date(nextOne.appointment_date);
            nextApptDate.textContent = dt.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) + " at " + dt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            nextApptDoctor.textContent = (me.role === 'doctor' ? nextOne.patient_name : nextOne.doctor_name) || "N/A";
        } else if (nextApptCard) {
            nextApptCard.style.display = 'none';
        }
      }
    } catch (e) {
      if ((e.message || '').includes('public.appointments')) {
        historyListEl.innerHTML = '<p class="text-sm text-amber-700">Feature not initialized (SQL missing).</p>';
      } else {
        renderStatus(`Error loading history: ${e.message}`, true);
      }
    }
  }

  async function book() {
    try {
      if (!selectedDoctorId) {
          alert('Please select a doctor.');
          return;
      }
      if (!dateInput.value) {
          alert('Please select an appointment date.');
          return;
      }
      
      let timeValue = selectedTime;
      if (!timeValue) {
          // fallback
          timeValue = "08:00";
      }

      // Combine date and time
      const datetimeStr = `${dateInput.value}T${timeValue}:00`;
      
      renderStatus('Sending booking request...', false);
      bookBtn.disabled = true;

      await API.bookAppointment(
          parseInt(selectedDoctorId, 10), 
          datetimeStr, 
          notesInput ? notesInput.value.trim() : ''
      );
      
      if (notesInput) notesInput.value = '';
      renderStatus('Appointment booked successfully!', false);
      await loadAppointments();
      
    } catch (e) {
      const msg = e.message || '';
      renderStatus(`Booking error: ${msg}`, true);
    } finally {
      if (bookBtn) bookBtn.disabled = false;
    }
  }

  // Init
  await loadDoctors();
  await loadAppointments();
  
  if (bookBtn) {
      bookBtn.addEventListener('click', book);
  }
})();
