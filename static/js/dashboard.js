// Dashboard Document Search, Filter, Sort, and Delete Management
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('search-docs-input');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const sortSelect = document.getElementById('sort-docs-select');
  const docsGrid = document.getElementById('documents-grid');
  const emptyState = document.getElementById('dashboard-empty-state');
  const noMatchesState = document.getElementById('no-matches-state');

  let activeFilter = 'ALL';
  let activeQuery = '';
  let activeSort = 'newest';

  let docToDeleteId = null;
  let docToDeleteCard = null;

  function filterAndSortDocs() {
    if (!docsGrid) return;
    const cards = Array.from(docsGrid.querySelectorAll('.doc-card'));
    let visibleCount = 0;

    cards.forEach(card => {
      const title = (card.getAttribute('data-filename') || '').toLowerCase();
      const summary = (card.getAttribute('data-summary') || '').toLowerCase();
      const type = (card.getAttribute('data-type') || '').toUpperCase();

      const matchesQuery = !activeQuery || title.includes(activeQuery) || summary.includes(activeQuery);
      let matchesType = true;
      if (activeFilter === 'IMAGES') {
        matchesType = type === 'IMAGE';
      } else if (activeFilter !== 'ALL') {
        matchesType = type === activeFilter;
      }

      if (matchesQuery && matchesType) {
        card.style.display = 'flex';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    // Sorting visible cards
    cards.sort((a, b) => {
      if (activeSort === 'name_asc') {
        return a.getAttribute('data-filename').localeCompare(b.getAttribute('data-filename'));
      } else if (activeSort === 'name_desc') {
        return b.getAttribute('data-filename').localeCompare(a.getAttribute('data-filename'));
      } else if (activeSort === 'oldest') {
        return (a.getAttribute('data-date') || '').localeCompare(b.getAttribute('data-date') || '');
      } else { // newest
        return (b.getAttribute('data-date') || '').localeCompare(a.getAttribute('data-date') || '');
      }
    });

    cards.forEach(c => docsGrid.appendChild(c));

    if (noMatchesState) {
      noMatchesState.style.display = (visibleCount === 0 && cards.length > 0) ? 'block' : 'none';
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      activeQuery = e.target.value.trim().toLowerCase();
      filterAndSortDocs();
    });
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.getAttribute('data-filter') || 'ALL';
      filterAndSortDocs();
    });
  });

  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      activeSort = e.target.value;
      filterAndSortDocs();
    });
  }

  // Delete modal handling
  const deleteModal = document.getElementById('delete-modal');
  const deleteDocNameSpan = document.getElementById('delete-doc-name');
  const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
  const cancelDeleteBtn = document.getElementById('cancel-delete-btn');

  document.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.delete-doc-trigger');
    if (delBtn) {
      e.preventDefault();
      docToDeleteId = delBtn.getAttribute('data-id');
      const docName = delBtn.getAttribute('data-name');
      docToDeleteCard = delBtn.closest('.doc-card');

      if (deleteDocNameSpan) deleteDocNameSpan.innerText = docName || 'this document';
      AIDoc.openModal('delete-modal');
    }
  });

  if (cancelDeleteBtn) {
    cancelDeleteBtn.addEventListener('click', () => {
      AIDoc.closeModal('delete-modal');
      docToDeleteId = null;
      docToDeleteCard = null;
    });
  }

  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener('click', async () => {
      if (!docToDeleteId) return;

      confirmDeleteBtn.disabled = true;
      confirmDeleteBtn.innerHTML = '<span class="spinner"></span> Deleting...';

      try {
        const resp = await fetch(`/api/documents/${docToDeleteId}`, {
          method: 'DELETE',
          headers: { 'Accept': 'application/json' }
        });
        const resData = await resp.json();

        if (resp.ok && resData.success) {
          AIDoc.showToast(resData.message || 'Document deleted.', 'success');
          if (docToDeleteCard) {
            docToDeleteCard.remove();
          }
          AIDoc.closeModal('delete-modal');

          // Check if grid is now empty
          const remaining = document.querySelectorAll('.doc-card');
          if (remaining.length === 0 && emptyState) {
            emptyState.style.display = 'block';
          }
        } else {
          AIDoc.showToast(resData.error ? resData.error.message : 'Failed to delete document.', 'error');
        }
      } catch (err) {
        console.error('Delete error:', err);
        AIDoc.showToast('Network error while deleting document.', 'error');
      } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.innerHTML = 'Delete Permanently';
        docToDeleteId = null;
        docToDeleteCard = null;
      }
    });
  }
});
