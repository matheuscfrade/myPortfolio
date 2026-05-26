/* ==========================================================================
   Portfólio Profissional — Public read-only explorer
   Loads data via /shared-data/ (when served by admin server) or relative paths (file://)
   Uses /Documentos/ for PDF serving.
   ========================================================================== */

(() => {
  'use strict';

  // --- State ---
  let allDocuments = [];           // base non-hidden documents
  let filteredDocuments = [];
  let activeCategories = new Set();
  let yearMin = null;
  let yearMax = null;
  let searchQuery = '';
  let selectedFiles = new Set();

  let categoryMeta = {};
  let savedCategories = [];

  // --- Path configuration (supports both server and direct file open) ---
  const IS_HTTP = location.protocol.startsWith('http');
  const IS_LOCAL_SERVER = location.hostname === 'localhost' || location.hostname === '127.0.0.1';

  // When served via the admin Flask server, use the shared data routes.
  // When opened directly as file://, fall back to relative paths
  const PDF_BASE = IS_HTTP
    ? (IS_LOCAL_SERVER ? '/Documentos/' : './Documentos/')
    : '../Documentos/';

  const SHARED_DATA_BASE = IS_HTTP
    ? (IS_LOCAL_SERVER ? '/shared-data/' : './shared-data/')
    : '../site/';   // fallback only for direct file:// opening

  const DEFAULT_APP_CONFIG = {
    displayName: 'Seu Nome',
    subtitle: 'Portfolio Profissional',
    portfolioTitle: 'Portfolio Documental',
    organization: ''
  };

  // --- DOM References ---
  let searchInput, chipsContainer, yearMinInput, yearMaxInput;
  let resultsCountEl, gridEl, modalEl, modalBody, modalTitle;
  let selectionBarEl, selectionCountEl, selectionExportBtn, selectionSelectVisibleBtn, selectionClearBtn;

  // --- Category Configuration (harmonized with existing system) ---
  const CATEGORY_CONFIG = {
    'Comissão':               { icon: '👥', color: '#2F9E41' },
    'Cargo/Função':           { icon: '📋', color: '#1565C0' },
    'Progressão':             { icon: '📈', color: '#E65100' },
    'Fiscal de Contrato':     { icon: '📑', color: '#6A1B9A' },
    'Conselho Superior':      { icon: '🏛️', color: '#00838F' },
    'Grupo de Trabalho':      { icon: '🔧', color: '#F57F17' },
    'Colegiado':              { icon: '🎓', color: '#AD1457' },
    'Outro':                  { icon: '📄', color: '#546E7A' }
  };

  const CATEGORY_ORDER = ['Cargo/Função', 'Conselho Superior', 'Colegiado', 'Comissão', 'Grupo de Trabalho', 'Fiscal de Contrato', 'Progressão', 'Outro'];

  // --- Utilities ---
  function escapeHtml(str = '') {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function mergeAppConfig(config = {}) {
    const merged = { ...DEFAULT_APP_CONFIG };
    Object.keys(DEFAULT_APP_CONFIG).forEach(key => {
      if (config[key] != null && String(config[key]).trim()) {
        merged[key] = String(config[key]).trim();
      }
    });
    return merged;
  }

  async function loadAppConfig() {
    try {
      const response = await fetch(`${SHARED_DATA_BASE}config.json`, { cache: 'no-store' });
      if (!response.ok) return mergeAppConfig();
      return mergeAppConfig(await response.json());
    } catch (e) {
      return mergeAppConfig();
    }
  }

  function applyAppConfig(config) {
    const merged = mergeAppConfig(config);
    document.querySelectorAll('[data-config]').forEach(el => {
      const key = el.dataset.config;
      if (merged[key]) el.textContent = merged[key];
    });
    document.title = merged.portfolioTitle;
    const description = document.querySelector('meta[name="description"]');
    if (description) {
      description.setAttribute('content', `${merged.portfolioTitle} - ${merged.displayName}`);
    }
    return merged;
  }

  function formatDate(dateStr) {
    if (!dateStr || dateStr.includes('Desconhecido')) return '';
    const parts = dateStr.split('-');
    if (parts.length < 3) return dateStr;
    const [y, m, d] = parts;
    const months = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
    const month = months[parseInt(m, 10) - 1] || m;
    return `${d} ${month} ${y}`;
  }

  function getPdfUrl(doc) {
    if (!doc.arquivo) return '';
    return PDF_BASE + encodeURI(doc.arquivo);
  }

  function toExportDocument(doc) {
    return {
      nome: doc.nome || '',
      assunto: doc.assunto || '',
      categoria: doc.categoria || '',
      ano: doc.ano || '',
      data: doc.data || '',
      numero: doc.numero || '',
      arquivo: doc.arquivo || ''
    };
  }

  function buildExportPayload(docs, selected = selectedFiles) {
    const selectedLookup = new Set(Array.from(selected));
    return docs
      .filter(doc => doc && doc.arquivo && selectedLookup.has(doc.arquivo))
      .map(toExportDocument);
  }

  function getSelectedDocuments() {
    return buildExportPayload(getDocumentsToShow(), selectedFiles);
  }

  function updateSelectionToolbar() {
    const selectedCount = getSelectedDocuments().length;
    if (selectionCountEl) {
      selectionCountEl.textContent = `${selectedCount} selecionado${selectedCount === 1 ? '' : 's'}`;
    }
    if (selectionBarEl) {
      selectionBarEl.classList.toggle('has-selection', selectedCount > 0);
    }
    if (selectionExportBtn) {
      selectionExportBtn.disabled = selectedCount === 0 || !IS_HTTP;
      selectionExportBtn.title = IS_HTTP
        ? 'Exportar documentos selecionados'
        : 'Abra pelo servidor local para exportar';
    }
  }

  function syncSelectionState() {
    document.querySelectorAll('.card-select-input').forEach(input => {
      input.checked = selectedFiles.has(input.value);
    });
    updateSelectionToolbar();
  }

  function toggleSelection(doc, selected) {
    if (!doc || !doc.arquivo) return;
    if (selected) {
      selectedFiles.add(doc.arquivo);
    } else {
      selectedFiles.delete(doc.arquivo);
    }
    syncSelectionState();
  }

  function selectVisibleDocuments() {
    filteredDocuments.forEach(doc => {
      if (doc.arquivo) selectedFiles.add(doc.arquivo);
    });
    syncSelectionState();
  }

  function clearSelection() {
    selectedFiles.clear();
    syncSelectionState();
  }

  async function exportSelectedDocuments() {
    const documentos = getSelectedDocuments();
    if (!IS_HTTP) {
      alert('Abra o portfólio pelo servidor local para exportar documentos.');
      return;
    }
    if (documentos.length === 0) {
      alert('Selecione pelo menos um documento para exportar.');
      return;
    }

    const originalText = selectionExportBtn ? selectionExportBtn.textContent : '';
    if (selectionExportBtn) {
      selectionExportBtn.disabled = true;
      selectionExportBtn.textContent = 'Exportando...';
    }

    try {
      const response = await fetch('/api/exportar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documentos })
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        if (response.status === 404) {
          throw new Error('Servidor sem endpoint de exportação. Feche e abra novamente o iniciar_admin.bat.');
        }
        throw new Error(error.error || 'Erro ao exportar documentos.');
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = getDownloadFilename(response) || 'portfolio-documentos-selecionados.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e.message || 'Erro ao exportar documentos.');
    } finally {
      if (selectionExportBtn) {
        selectionExportBtn.disabled = false;
        selectionExportBtn.textContent = originalText;
      }
      updateSelectionToolbar();
    }
  }

  function getDownloadFilename(response) {
    const disposition = response.headers.get('Content-Disposition') || '';
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) return decodeURIComponent(utf8Match[1]);
    const asciiMatch = disposition.match(/filename="?([^";]+)"?/i);
    return asciiMatch ? asciiMatch[1] : '';
  }

  function getCategoryColor(cat) {
    return (CATEGORY_CONFIG[cat] && CATEGORY_CONFIG[cat].color) || '#546E7A';
  }

  function normalizeCategoryName(name) {
    return String(name || '').trim().replace(/\s+/g, ' ');
  }

  function registerCategory(name, color = '#546E7A') {
    const normalized = normalizeCategoryName(name);
    if (!normalized || CATEGORY_CONFIG[normalized]) return;
    CATEGORY_CONFIG[normalized] = { icon: '', color: color || '#546E7A' };
  }

  function compareCategories(a, b) {
    const orderA = CATEGORY_ORDER.indexOf(a);
    const orderB = CATEGORY_ORDER.indexOf(b);
    if (orderA !== -1 || orderB !== -1) {
      if (orderA === -1) return 1;
      if (orderB === -1) return -1;
      return orderA - orderB;
    }
    return a.localeCompare(b, 'pt-BR');
  }

  function documentMatchesFilters(doc, { query = '', activeCategories: categories = activeCategories, minYear, maxYear, yearMin: filterYearMin, yearMax: filterYearMax } = {}) {
    const lowerYear = minYear !== undefined ? minYear : (filterYearMin !== undefined ? filterYearMin : yearMin);
    const upperYear = maxYear !== undefined ? maxYear : (filterYearMax !== undefined ? filterYearMax : yearMax);
    const docYear = doc.ano || 0;
    const hasUnknownYear = docYear <= 0;

    const inYearRange = hasUnknownYear ||
      ((!lowerYear || docYear >= lowerYear) && (!upperYear || docYear <= upperYear));

    const catMatch = categories.size === 0 || categories.has(doc.categoria);

    let textMatch = true;
    if (query) {
      const hay = `${doc.nome || ''} ${doc.assunto || ''} ${doc.numero || ''} ${doc.categoria || ''}`.toLowerCase();
      textMatch = hay.includes(query);
    }

    return inYearRange && catMatch && textMatch;
  }

  function getCategoryCountsForFilters(docs, filters = {}) {
    return docs.reduce((counts, doc) => {
      if (documentMatchesFilters(doc, filters)) {
        counts[doc.categoria] = (counts[doc.categoria] || 0) + 1;
      }
      return counts;
    }, {});
  }

  function getCurrentCategoryCounts() {
    return getCategoryCountsForFilters(getDocumentsToShow(), {
      query: searchQuery,
      activeCategories,
      minYear: yearMin,
      maxYear: yearMax
    });
  }

  // Load a classic script dynamically. This is the most reliable way to load
  // the DOCUMENTOS definition from dados.js in BOTH http:// (served) and file:// (direct open)
  // environments.
  function loadDataScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('Falha ao carregar ' + src));
      document.head.appendChild(s);
    });
  }

  // --- Data Loading & Merging (respects existing edicoes + ocultos) ---
  async function loadData() {
    let baseDocs = [];
    const dadosUrl = `${SHARED_DATA_BASE}dados.js`;

    // Always use dynamic script injection for DOCUMENTOS. This guarantees that
    // Load documents from direct file:// or from the admin server.
    try {
      await loadDataScript(dadosUrl);
      if (typeof DOCUMENTOS !== 'undefined') {
        baseDocs = DOCUMENTOS;
      } else {
        console.warn('[portfolio] Script loaded but DOCUMENTOS global not found after', dadosUrl);
      }
    } catch (e) {
      console.warn('[portfolio] Failed to load data via script', dadosUrl, e);
      // Last-resort (rare): a static tag was manually added to the HTML
      if (typeof DOCUMENTOS !== 'undefined') {
        baseDocs = DOCUMENTOS;
      } else if (typeof window !== 'undefined' && typeof window.DOCUMENTOS !== 'undefined') {
        baseDocs = window.DOCUMENTOS;
      }
    }

    // 2. Fetch overrides (edicoes.json + ocultos.json)
    let edicoes = {};
    let ocultos = [];

    try {
      const [edRes, ocRes, catRes] = await Promise.allSettled([
        fetch(`${SHARED_DATA_BASE}edicoes.json`),
        fetch(`${SHARED_DATA_BASE}ocultos.json`),
        fetch(`${SHARED_DATA_BASE}categorias.json`)
      ]);

      if (edRes.status === 'fulfilled' && edRes.value.ok) {
        edicoes = await edRes.value.json();
      }
      if (ocRes.status === 'fulfilled' && ocRes.value.ok) {
        ocultos = await ocRes.value.json();
      }
      if (catRes.status === 'fulfilled' && catRes.value.ok) {
        savedCategories = await catRes.value.json();
      }
    } catch (e) {
      console.info('[portfolio] Could not load override JSONs.');
    }

    // Merge exactly like the existing logic
    const merged = baseDocs.map(doc => {
      const override = edicoes[doc.arquivo];
      let d = { ...doc };
      if (override) {
        d = { ...d, ...override };
      }
      if (ocultos.includes(doc.arquivo)) {
        d.oculto = true;
      }
      return d;
    });

    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';

    allDocuments = merged.filter(d => !d.oculto);
    savedCategories.forEach(item => {
      if (item && typeof item === 'object') registerCategory(item.nome, item.color);
    });
    allDocuments.forEach(doc => registerCategory(doc.categoria));

    window.__isLocal = isLocal;

    // Build category metadata
    categoryMeta = {};
    allDocuments.forEach(d => {
      if (!categoryMeta[d.categoria]) categoryMeta[d.categoria] = 0;
      categoryMeta[d.categoria]++;
    });

    // Determine global year bounds
    const years = allDocuments
      .map(d => d.ano)
      .filter(y => Number.isInteger(y) && y > 1900);
    yearMin = years.length ? Math.min(...years) : 2010;
    yearMax = years.length ? Math.max(...years) : 2026;

    return allDocuments;
  }

  function getDocumentsToShow() {
    // Public version: never shows hidden documents via UI
    return allDocuments;
  }

  // --- Filtering ---
  function applyFilters() {
    const q = (searchInput.value || '').trim().toLowerCase();
    searchQuery = q;

    const docsToFilter = getDocumentsToShow();

    filteredDocuments = docsToFilter.filter(doc => {
      return documentMatchesFilters(doc, {
        query: q,
        activeCategories,
        minYear: yearMin,
        maxYear: yearMax
      });
    });

    // Default sort: newest first
    filteredDocuments.sort((a, b) => {
      if (a.data && b.data) return b.data.localeCompare(a.data);
      return (b.ano || 0) - (a.ano || 0);
    });

    renderCategoryChips();
    renderGrid();
    updateResultsCount();
  }

  function updateResultsCount() {
    if (!resultsCountEl) return;
    const shown = filteredDocuments.length;
    resultsCountEl.textContent = `${shown} documentos`;
  }

  // --- Rendering ---
  function renderCategoryChips() {
    if (!chipsContainer) return;
    chipsContainer.innerHTML = '';

    const cats = Object.keys(categoryMeta).sort(compareCategories);
    const counts = getCurrentCategoryCounts();

    cats.forEach(cat => {
      const chip = document.createElement('button');
      chip.className = 'chip';
      chip.dataset.category = cat;
      chip.innerHTML = `
        <span class="dot" style="background:${getCategoryColor(cat)}"></span>
        <span>${escapeHtml(cat)}</span>
        <span style="opacity:0.6;font-size:0.75em">(${counts[cat] || 0})</span>
      `;

      if (activeCategories.has(cat)) chip.classList.add('active');

      chip.addEventListener('click', () => {
        if (activeCategories.has(cat)) {
          activeCategories.delete(cat);
        } else {
          activeCategories.add(cat);
        }
        chip.classList.toggle('active', activeCategories.has(cat));
        applyFilters();
      });

      chipsContainer.appendChild(chip);
    });
  }

  function renderYearInputs() {
    if (!yearMinInput || !yearMaxInput) return;
    yearMinInput.value = yearMin || '';
    yearMaxInput.value = yearMax || '';

    const handler = () => {
      const min = parseInt(yearMinInput.value, 10);
      const max = parseInt(yearMaxInput.value, 10);
      yearMin = Number.isNaN(min) ? null : min;
      yearMax = Number.isNaN(max) ? null : max;
      applyFilters();
    };

    yearMinInput.addEventListener('input', handler);
    yearMaxInput.addEventListener('input', handler);
  }

  function createCard(doc, index) {
    const div = document.createElement('article');
    div.className = 'card';
    div.dataset.index = index;

    const color = getCategoryColor(doc.categoria);
    div.style.setProperty('--cat-color', color);

    const date = formatDate(doc.data);
    const pdfUrl = getPdfUrl(doc);

    const isHidden = !!doc.oculto;
    if (isHidden) {
      div.classList.add('card-hidden');
    }

    const hiddenBadge = isHidden 
      ? `<span style="background:#CD191E;color:white;font-size:0.65rem;padding:1px 6px;border-radius:3px;margin-left:6px;">OCULTO</span>` 
      : '';

    div.innerHTML = `
      <label class="card-select" title="Selecionar para exportação">
        <input class="card-select-input" type="checkbox" value="${escapeHtml(doc.arquivo || '')}" ${selectedFiles.has(doc.arquivo) ? 'checked' : ''} aria-label="Selecionar documento para exportação">
        <span></span>
      </label>
      <div class="card-header">
        <div class="card-title">${escapeHtml(doc.nome || 'Sem título')}${hiddenBadge}</div>
        ${doc.ano ? `<div class="card-year">${doc.ano}</div>` : ''}
      </div>
      <div class="card-subject">${escapeHtml(doc.assunto || 'Sem assunto registrado')}</div>
      <div class="card-meta">
        <div class="card-category" style="border:1px solid ${color}33; color:${color}">
          ${escapeHtml(doc.categoria)}
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          ${date ? `<span>${date}</span>` : ''}
          <div class="card-actions">
            ${pdfUrl ? `<a href="${pdfUrl}" target="_blank" rel="noopener" title="Abrir PDF original">PDF</a>` : ''}
          </div>
        </div>
      </div>
    `;

    // Click anywhere on card opens modal (except links)
    div.addEventListener('click', (e) => {
      if (e.target.closest('a') || e.target.closest('button') || e.target.closest('.card-select')) return;
      openModal(doc, index);
    });

    const checkbox = div.querySelector('.card-select-input');
    if (checkbox) {
      checkbox.addEventListener('change', (e) => {
        toggleSelection(doc, e.target.checked);
      });
    }

    return div;
  }

  function renderGrid() {
    if (!gridEl) return;
    gridEl.innerHTML = '';

    if (filteredDocuments.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-state';

      const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';

      if (allDocuments.length === 0) {
        empty.innerHTML = `
          <p>Nenhum documento foi carregado.</p>
          <p style="font-size:0.85rem">Verifique se o arquivo <code>site/dados.js</code> existe e tem conteúdo.</p>
        `;
      } else {
        empty.innerHTML = `
          <p>Nenhum documento encontrado com os filtros atuais.</p>
          <button class="btn btn-secondary" id="clear-all-btn">Limpar todos os filtros</button>
        `;
      }
      gridEl.appendChild(empty);

      const clearBtn = empty.querySelector('#clear-all-btn');
      if (clearBtn) clearBtn.addEventListener('click', clearAllFilters);

      return;
    }

    const fragment = document.createDocumentFragment();
    filteredDocuments.forEach((doc, i) => {
      fragment.appendChild(createCard(doc, i));
    });
    gridEl.appendChild(fragment);
    syncSelectionState();
  }

  // --- Modal ---
  function openModal(doc, index) {
    if (!modalEl) return;

    const pdfUrl = getPdfUrl(doc);
    const date = formatDate(doc.data);

    modalTitle.textContent = doc.nome || 'Documento';

    modalBody.innerHTML = `
      <div class="modal-meta">
        <div style="margin-bottom:16px">
          <div style="font-size:0.75rem;color:var(--text-subtle);margin-bottom:4px">CATEGORIA</div>
          <div style="font-weight:700;color:${getCategoryColor(doc.categoria)}">${escapeHtml(doc.categoria)}</div>
        </div>

        ${doc.numero ? `
        <div style="margin-bottom:16px">
          <div style="font-size:0.75rem;color:var(--text-subtle);margin-bottom:4px">NÚMERO</div>
          <div style="font-weight:600">${escapeHtml(doc.numero)}</div>
        </div>` : ''}

        <div style="margin-bottom:16px">
          <div style="font-size:0.75rem;color:var(--text-subtle);margin-bottom:4px">DATA / VIGÊNCIA</div>
          <div style="font-weight:600">${date || 'Data não informada'}</div>
        </div>

        <div style="margin-bottom:20px">
          <div style="font-size:0.75rem;color:var(--text-subtle);margin-bottom:4px">ASSUNTO</div>
          <div style="line-height:1.5">${escapeHtml(doc.assunto || '—')}</div>
        </div>

        <div>
          <div style="font-size:0.75rem;color:var(--text-subtle);margin-bottom:4px">ARQUIVO ORIGINAL</div>
          <div style="font-family:monospace;font-size:0.72rem;word-break:break-all;color:var(--text-muted)">${escapeHtml(doc.arquivo || '')}</div>
        </div>
      </div>

      <div class="modal-pdf">
        ${pdfUrl
          ? `<object data="${pdfUrl}" type="application/pdf" style="width:100%;height:100%">
               <div style="padding:40px;text-align:center;color:#ccc">
                 <p>Não foi possível exibir o PDF embutido.</p>
                 <a href="${pdfUrl}" target="_blank" style="color:#8cf">Abrir PDF em nova aba →</a>
               </div>
             </object>`
          : `<div style="color:#888">PDF não disponível</div>`}
      </div>
    `;

    modalEl.classList.add('open');

    // Keyboard escape handling
    const onKey = (e) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', onKey);
      }
    };
    document.addEventListener('keydown', onKey, { once: true });
  }

  function closeModal() {
    if (modalEl) modalEl.classList.remove('open');
  }

  // --- Filter Controls ---
  function clearAllFilters() {
    searchInput.value = '';
    activeCategories.clear();
    yearMin = null;
    yearMax = null;

    // Reset chips
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));

    // Reset year inputs
    if (yearMinInput) yearMinInput.value = '';
    if (yearMaxInput) yearMaxInput.value = '';

    applyFilters();
  }

  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement.tagName === 'BODY') {
        e.preventDefault();
        searchInput.focus();
        searchInput.select();
      }
      if (e.key.toLowerCase() === 'escape' && modalEl.classList.contains('open')) {
        closeModal();
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInput.focus();
      }
    });

    // Hint in console for power users
    console.info('%c[portfolio] Dica: pressione / para focar na busca', 'color:#888');
  }

  function setupFilterListeners() {
    // Search (debounced)
    let t;
    searchInput.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(applyFilters, 140);
    });

    // Clear button next to search (we add it dynamically)
    const clearBtn = document.createElement('button');
    clearBtn.textContent = '✕';
    clearBtn.className = 'btn btn-ghost';
    clearBtn.style.position = 'absolute';
    clearBtn.style.right = '6px';
    clearBtn.style.top = '50%';
    clearBtn.style.transform = 'translateY(-50%)';
    clearBtn.style.padding = '2px 8px';
    clearBtn.style.fontSize = '0.8rem';
    clearBtn.style.display = 'none';

    searchInput.parentElement.style.position = 'relative';
    searchInput.parentElement.appendChild(clearBtn);

    searchInput.addEventListener('input', () => {
      clearBtn.style.display = searchInput.value ? 'inline-flex' : 'none';
    });
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearBtn.style.display = 'none';
      applyFilters();
      searchInput.focus();
    });
  }

  // --- Initialization ---
  async function init() {
    const appConfig = await loadAppConfig();
    applyAppConfig(appConfig);

    // Cache DOM
    searchInput = document.getElementById('search');
    chipsContainer = document.getElementById('category-chips');
    yearMinInput = document.getElementById('year-min');
    yearMaxInput = document.getElementById('year-max');
    resultsCountEl = document.getElementById('results-count');
    gridEl = document.getElementById('cards-grid');
    modalEl = document.getElementById('modal');
    modalTitle = document.getElementById('modal-title');
    modalBody = document.getElementById('modal-body');
    selectionBarEl = document.getElementById('selection-bar');
    selectionCountEl = document.getElementById('selection-count');
    selectionExportBtn = document.getElementById('selection-export');
    selectionSelectVisibleBtn = document.getElementById('selection-select-visible');
    selectionClearBtn = document.getElementById('selection-clear');

    // Close modal handlers
    document.getElementById('modal-close').addEventListener('click', closeModal);
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) closeModal();
    });

    // Load data (respects existing ocultos/edicoes)
    const loadingEl = document.getElementById('loading');
    try {
      await loadData();

      // Initial UI (public version has no "mostrar ocultos" toggle)
      renderCategoryChips();
      renderYearInputs();

      // First render
      filteredDocuments = [...allDocuments];
      renderGrid();
      updateResultsCount();

      // Wire controls
      setupFilterListeners();
      setupKeyboardShortcuts();

      // Global clear button
      const clearAll = document.getElementById('clear-filters');
      if (clearAll) clearAll.addEventListener('click', clearAllFilters);
      if (selectionSelectVisibleBtn) selectionSelectVisibleBtn.addEventListener('click', selectVisibleDocuments);
      if (selectionClearBtn) selectionClearBtn.addEventListener('click', clearSelection);
      if (selectionExportBtn) selectionExportBtn.addEventListener('click', exportSelectedDocuments);
      updateSelectionToolbar();
      // Stats
      const totalEl = document.getElementById('stat-total');
      const catsEl = document.getElementById('stat-cats');
      const yearsEl = document.getElementById('stat-years');

      if (totalEl) totalEl.textContent = allDocuments.length;
      if (catsEl) catsEl.textContent = Object.keys(categoryMeta).length;
      if (yearsEl) yearsEl.textContent = `${yearMin}–${yearMax}`;

      loadingEl.style.display = 'none';

    } catch (err) {
      console.error(err);
      loadingEl.innerHTML = `<p style="color:#c33">Erro ao carregar os dados. Verifique se você está abrindo o arquivo dentro da pasta do projeto.</p>`;
    }

    // Make sure pressing Enter in year fields applies immediately
    [yearMinInput, yearMaxInput].forEach(el => {
      if (el) el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyFilters();
      });
    });
  }

  window.__portfolioPublicTest = {
    documentMatchesFilters,
    getCategoryCountsForFilters,
    buildExportPayload,
    mergeAppConfig
  };

  // Boot
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
