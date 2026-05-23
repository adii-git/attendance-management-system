// ===================================================
// QR SMART ATTENDANCE SYSTEM — Main JS
// ===================================================

document.addEventListener('DOMContentLoaded', function () {

    // ---- Sidebar mobile toggle ----
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebarToggle');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && !sidebar.contains(e.target)) {
                sidebar.classList.remove('open');
            }
        });
    }

    // ---- Auto-dismiss alerts ----
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 4000);
    });

    // ---- Set current date dynamically on page header ----
    document.querySelectorAll('.date-badge').forEach(el => {
        if (el.textContent.trim().startsWith('📅')) return;
        const d = new Date();
        el.innerHTML = `<i class="fas fa-calendar"></i> ${d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
    });

    // ---- Active nav highlighting fallback ----
    const path = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(link => {
        if (link.getAttribute('href') && path.startsWith(link.getAttribute('href'))) {
            link.classList.add('active');
        }
    });
});
