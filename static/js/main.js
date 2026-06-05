/* ============================================
   KAZIM — Public Research Notebook
   Core JavaScript v0.1
   ============================================ */

(function() {
  'use strict';

  /* --- Dark/Light Mode Toggle --- */
  const THEME_KEY = 'kazim-theme';

  function getPreferredTheme() {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored) return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    const btn = document.querySelector('.theme-toggle');
    if (btn) {
      btn.textContent = theme === 'dark' ? 'light mode' : 'dark mode';
    }
  }

  // Apply theme immediately (before DOM fully loads to prevent flash)
  setTheme(getPreferredTheme());

  document.addEventListener('DOMContentLoaded', function() {
    // Theme toggle button
    const toggleBtn = document.querySelector('.theme-toggle');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function() {
        const current = document.documentElement.getAttribute('data-theme');
        setTheme(current === 'dark' ? 'light' : 'dark');
      });
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
      if (!localStorage.getItem(THEME_KEY)) {
        setTheme(e.matches ? 'dark' : 'light');
      }
    });

    /* --- Footnote Hover Previews --- */
    const footnoteRefs = document.querySelectorAll('.footnote-ref, a[href^="#fn"]');
    let activePopup = null;

    footnoteRefs.forEach(function(ref) {
      ref.addEventListener('mouseenter', function(e) {
        const href = ref.getAttribute('href');
        if (!href) return;
        const id = href.replace('#', '');
        const footnote = document.getElementById(id);
        if (!footnote) return;

        // Remove existing popup
        if (activePopup) activePopup.remove();

        // Create popup
        const popup = document.createElement('div');
        popup.className = 'footnote-popup';
        popup.innerHTML = footnote.innerHTML;

        // Remove backref from popup
        const backref = popup.querySelector('.footnote-backref');
        if (backref) backref.remove();

        document.body.appendChild(popup);
        activePopup = popup;

        // Position popup
        const rect = ref.getBoundingClientRect();
        const popupRect = popup.getBoundingClientRect();

        let top = rect.top - popupRect.height - 8;
        let left = rect.left + (rect.width / 2) - (popupRect.width / 2);

        // Keep within viewport
        if (top < 10) top = rect.bottom + 8;
        if (left < 10) left = 10;
        if (left + popupRect.width > window.innerWidth - 10) {
          left = window.innerWidth - popupRect.width - 10;
        }

        popup.style.top = (top + window.scrollY) + 'px';
        popup.style.left = left + 'px';
        popup.style.opacity = '1';
      });

      ref.addEventListener('mouseleave', function() {
        setTimeout(function() {
          if (activePopup && !activePopup.matches(':hover')) {
            activePopup.remove();
            activePopup = null;
          }
        }, 200);
      });
    });

    // Remove popup when leaving it
    document.addEventListener('mouseover', function(e) {
      if (activePopup && !activePopup.contains(e.target) &&
          !e.target.classList.contains('footnote-ref') &&
          !e.target.closest('a[href^="#fn"]')) {
        activePopup.remove();
        activePopup = null;
      }
    });

    /* --- Active nav highlighting --- */
    const currentPath = window.location.pathname;
    document.querySelectorAll('.site-nav a').forEach(function(link) {
      const href = link.getAttribute('href');
      if (href === '/' && currentPath === '/') {
        link.classList.add('active');
      } else if (href !== '/' && currentPath.startsWith(href)) {
        link.classList.add('active');
      }
    });
  });
})();
