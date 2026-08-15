(function () {
  function toGuest() {
    return { id: 0, username: 'guest', full_name: 'Guest', role: 'guest' };
  }

  // ─── SYNCHRONOUS: hide sidebar immediately when script loads ───
  // This runs BEFORE any async API call, so user never sees duplicate links
  (function hideSidebarBeforeLoad() {
    const aside = document.querySelector('aside');
    if (aside) aside.style.visibility = 'hidden';
  })();
  // ──────────────────────────────────────────────────────────────

  window.AppCommon = {

    async initPage(opts = {}) {
      const topName = document.getElementById('topUserName');
      const topRole = document.getElementById('topUserRole');
      const logoutBtn = document.getElementById('logoutBtn');

      const hasToken = !!API.getToken();
      if (!hasToken) {
        if (!opts.allowGuest) {
          window.location.href = 'login.html';
          return null;
        }
        if (topName) topName.textContent = 'Guest Preview';
        if (topRole) topRole.textContent = 'Please login';
        if (logoutBtn) {
          logoutBtn.textContent = 'Login';
          logoutBtn.onclick = () => { window.location.href = 'login.html'; };
        }
        return toGuest();
      }

      const me = await API.getMe();
      if (topName) topName.textContent = me.role === 'doctor' ? `Dr. ${me.full_name || me.username}` : (me.full_name || me.username);
      if (topRole) topRole.textContent = me.role || 'user';
      if (logoutBtn) {
        logoutBtn.onclick = () => API.logout();
        const pwdBtn = document.createElement('button');
        pwdBtn.className = "px-3 py-1.5 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 text-xs font-semibold ml-2 mr-2";
        pwdBtn.textContent = "Change Password";
        pwdBtn.onclick = async () => {
          const newPwd = prompt("Enter new password (leaves blank to cancel):");
          if (newPwd) {
            try {
              await API.changePassword(newPwd.trim());
              alert("Password changed successfully!");
            } catch (e) {
              alert("Error: " + e.message);
            }
          }
        };
        logoutBtn.parentNode.insertBefore(pwdBtn, logoutBtn);
      }

      if (opts.requireRole && me.role !== opts.requireRole) {
        window.location.href = API.getHomePage(me.role);
        return null;
      }
      
      // Init sidebar UI logic
      this.initSidebar(me);
      
      return me;
    },

    setStatus(id, text, isError = false) {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent = text;
      el.style.color = isError ? '#dc2626' : '#64748b';
    },

    initSidebar(me) {
      const currentPath = window.location.pathname.split('/').pop() || window.location.href.split('/').pop().split('?')[0];
      
      const isDoctorFiles = ['doctor-dashboard.html', 'analysis.html', 'profiles.html', 'history.html'];
      const isPatientFiles = ['patient.html'];

      // Determine correct dashboard page for this user
      const dashboardPage = me.role === 'doctor' ? 'doctor-dashboard.html' : 'patient.html';
      
      const navLinks = document.querySelectorAll('.nav-btn');
      navLinks.forEach(link => {
        const href = link.getAttribute('href');

        // ── Single Dashboard Link ──────────────────────────────────────
        // Convert doctor-dashboard.html link → correct dashboard for this role
        if (href === 'doctor-dashboard.html') {
          link.setAttribute('href', dashboardPage);
          link.innerHTML = `<span class="material-symbols-outlined" data-icon="dashboard">dashboard</span> Dashboard`;
        }
        // Always permanently hide the patient.html duplicate link
        if (href === 'patient.html') {
          link.style.display = 'none';
          return; // skip further processing for this link
        }
        // ──────────────────────────────────────────────────────────────

        // Get the (possibly updated) href
        const resolvedHref = link.getAttribute('href');

        // Handle Active State
        if (resolvedHref === currentPath || (resolvedHref === dashboardPage && (currentPath === 'doctor-dashboard.html' || currentPath === 'patient.html'))) {
          link.classList.remove('text-slate-600', 'hover:bg-slate-100');
          link.classList.add('bg-primary-fixed', 'text-on-primary-fixed', 'font-bold');
        }

        // Hide doctor-only links for patients
        if (me.role === 'patient' && isDoctorFiles.includes(resolvedHref)) {
          link.style.display = 'none';
        }
      });

      // Reveal sidebar after processing
      const aside = document.querySelector('aside');
      if (aside) aside.style.visibility = 'visible';
      
      // Hide doctor-only mobile nav for patients
      if (me.role === 'patient') {
        document.querySelectorAll('.hide-patient').forEach(el => {
          el.style.display = 'none'; 
        });
      }
    }
  };
})();
