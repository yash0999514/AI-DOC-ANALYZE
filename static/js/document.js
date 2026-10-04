// Document Analysis View Tab Controller and Interactive Elements
document.addEventListener('DOMContentLoaded', () => {
  const tabBtns = document.querySelectorAll('.analysis-tabs .tab-btn');
  const tabPanes = document.querySelectorAll('.analysis-container-card .tab-pane');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(`tab-${targetId}`);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });

  // Export dropdown toggle
  const exportBtn = document.getElementById('export-menu-btn');
  const exportDropdown = document.getElementById('export-dropdown-menu');

  if (exportBtn && exportDropdown) {
    exportBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      exportDropdown.classList.toggle('active');
    });

    document.addEventListener('click', (e) => {
      if (!exportDropdown.contains(e.target)) {
        exportDropdown.classList.remove('active');
      }
    });
  }

  // Copy Summary button
  const copySummaryBtn = document.getElementById('copy-summary-btn');
  if (copySummaryBtn) {
    copySummaryBtn.addEventListener('click', () => {
      const summaryText = document.getElementById('summary-content-text');
      if (summaryText) {
        navigator.clipboard.writeText(summaryText.innerText).then(() => {
          AIDoc.showToast("Summary copied to clipboard!", "success");
        }).catch(() => {
          AIDoc.showToast("Failed to copy summary to clipboard.", "error");
        });
      }
    });
  }
});
