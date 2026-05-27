/* ==========================================================================
   Admin — Interface administrativa
   Inclui edição de metadados, ocultação e sincronização.
   Usa as mesmas APIs do servidor Flask (/api/*).
   ========================================================================== */

(() => {
  'use strict';

  // --- State ---
  let allDocuments = [];           // base non-hidden documents
  let hiddenDocuments = [];        // documents hidden via admin "ocult" button
  let filteredDocuments = [];
  let activeCategories = new Set();
  let yearMin = null;
  let yearMax = null;
  let searchQuery = '';
  let includeHidden = false;       // only relevant on localhost
  let selectedFiles = new Set();

  let categoryMeta = {};
  let savedCategories = [];

  // --- Path configuration (supports both server and direct file open) ---
  const IS_HTTP = location.protocol.startsWith('http');

  // When served via the admin Flask server, use the shared data routes.
  // When opened directly as file://, fall back to relative paths
  const PDF_BASE = IS_HTTP
    ? '/Documentos/'
    : '../Documentos/';

  const SHARED_DATA_BASE = IS_HTTP
    ? '/shared-data/'
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
  let importModal, importFile, importNome, importAssunto, importCategoria, importAno, importData, importNumero;
  let newCategoryNameInput, newCategoryColorInput, categoryCreateStatus;
  let openDocumentsBtn, publicPackageBtn;

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
    document.title = `Admin - ${merged.portfolioTitle}`;
    const description = document.querySelector('meta[name="description"]');
    if (description) {
      description.setAttribute('content', `Administracao local - ${merged.displayName}`);
    }
    return merged;
  }

  async function openDocumentsFolder() {
    try {
      const response = await fetch('/api/abrir-documentos', { method: 'POST' });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || 'Nao foi possivel abrir a pasta.');
      }
    } catch (e) {
      alert(e.message || 'Nao foi possivel abrir a pasta Documentos.');
    }
  }

  async function createPublicPackage() {
    const originalText = publicPackageBtn ? publicPackageBtn.textContent : 'Gerar pacote público';
    if (publicPackageBtn) {
      publicPackageBtn.disabled = true;
      publicPackageBtn.textContent = 'Gerando...';
    }

    try {
      const response = await fetch('/api/gerar-pacote-publico', { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || 'Nao foi possivel gerar o pacote publico.');
      }
      alert(`Pacote público criado em:\n${data.path}\n\nEnvie essa pasta para GitHub Pages, Netlify, Vercel ou Cloudflare Pages para publicar de verdade. Esta é a versão pública do portfólio.`);
    } catch (e) {
      alert(e.message || 'Nao foi possivel gerar o pacote publico.');
    } finally {
      if (publicPackageBtn) {
        publicPackageBtn.disabled = false;
        publicPackageBtn.textContent = originalText;
      }
    }
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
      alert('Abra o admin pelo servidor local para exportar documentos.');
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
    if (!normalized) return false;
    if (!CATEGORY_CONFIG[normalized]) {
      CATEGORY_CONFIG[normalized] = { icon: '', color: color || '#546E7A' };
    } else if (color && CATEGORY_CONFIG[normalized].color === '#546E7A') {
      CATEGORY_CONFIG[normalized].color = color;
    }
    return true;
  }

  function compareCategories(a, b) {
    const nameA = typeof a === 'string' ? a : a.nome;
    const nameB = typeof b === 'string' ? b : b.nome;
    const orderA = CATEGORY_ORDER.indexOf(nameA);
    const orderB = CATEGORY_ORDER.indexOf(nameB);
    if (orderA !== -1 || orderB !== -1) {
      if (orderA === -1) return 1;
      if (orderB === -1) return -1;
      return orderA - orderB;
    }
    return nameA.localeCompare(nameB, 'pt-BR');
  }

  function getCategoryOptions({ docs = allDocuments.concat(hiddenDocuments), savedCategories: categories = savedCategories } = {}) {
    const seen = new Map();

    Object.keys(CATEGORY_CONFIG).forEach(name => {
      seen.set(name, { nome: name, color: getCategoryColor(name) });
    });

    categories.forEach(item => {
      const name = normalizeCategoryName(item && (item.nome || item.name || item));
      if (!name) return;
      registerCategory(name, item.color);
      seen.set(name, { nome: name, color: getCategoryColor(name) });
    });

    docs.forEach(doc => {
      const name = normalizeCategoryName(doc && doc.categoria);
      if (!name) return;
      registerCategory(name);
      seen.set(name, { nome: name, color: getCategoryColor(name) });
    });

    return Array.from(seen.values()).sort(compareCategories);
  }

  function renderCategorySelect(selectEl, selectedValue = '') {
    if (!selectEl) return;
    const options = getCategoryOptions();
    selectEl.innerHTML = options
      .map(item => `<option value="${escapeHtml(item.nome)}" ${item.nome === selectedValue ? 'selected' : ''}>${escapeHtml(item.nome)}</option>`)
      .join('');
  }

  function refreshCategoryControls() {
    renderCategorySelect(importCategoria, importCategoria ? importCategoria.value : '');
    renderCategoryChips();
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
        console.warn('[admin] Script loaded but DOCUMENTOS global not found after', dadosUrl);
      }
    } catch (e) {
      console.warn('[admin] Failed to load data via script', dadosUrl, e);
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
      console.info('[admin] Could not load override JSONs.');
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
    hiddenDocuments = merged.filter(d => d.oculto);
    getCategoryOptions({ docs: merged, savedCategories });

    console.log('[admin] Loaded documents:', allDocuments.length, 'visible,', hiddenDocuments.length, 'hidden');
    window.__isLocal = isLocal;

    // Visible-only stats (initial chips + year range)
    categoryMeta = {};
    allDocuments.forEach(d => {
      if (!categoryMeta[d.categoria]) categoryMeta[d.categoria] = 0;
      categoryMeta[d.categoria]++;
    });

    const years = allDocuments
      .map(d => d.ano)
      .filter(y => Number.isInteger(y) && y > 1900);
    yearMin = years.length ? Math.min(...years) : 2010;
    yearMax = years.length ? Math.max(...years) : 2026;

    // Remember the original visible-only year range (for when hiding hidden docs again)
    window.__visibleYearMin = yearMin;
    window.__visibleYearMax = yearMax;

    // Full corpus stats (used to expand UI when "Mostrar ocultos" is activated)
    const fullYears = merged
      .map(d => d.ano)
      .filter(y => Number.isInteger(y) && y > 1900);
    window.__fullYearMin = fullYears.length ? Math.min(...fullYears) : yearMin;
    window.__fullYearMax = fullYears.length ? Math.max(...fullYears) : yearMax;

    // Store a combined category count for when showing hidden
    window.__fullCategoryMeta = {};
    merged.forEach(d => {
      if (!window.__fullCategoryMeta[d.categoria]) window.__fullCategoryMeta[d.categoria] = 0;
      window.__fullCategoryMeta[d.categoria]++;
    });

    return allDocuments;
  }

  function getDocumentsToShow() {
    if (window.__isLocal && includeHidden) {
      return [...allDocuments, ...hiddenDocuments];
    }
    return allDocuments;
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
    updateHeroStats();
  }

  function updateResultsCount() {
    if (!resultsCountEl) return;
    const baseTotal = allDocuments.length + hiddenDocuments.length;
    const shown = filteredDocuments.length;

    if (window.__isLocal) {
      const hiddenCount = includeHidden ? hiddenDocuments.length : 0;
      resultsCountEl.textContent = `${shown} documentos`;
      if (hiddenDocuments.length > 0) {
        resultsCountEl.textContent += ` (${hiddenDocuments.length} oculto${hiddenDocuments.length > 1 ? 's' : ''})`;
      }
    } else {
      resultsCountEl.textContent = `${shown} de ${baseTotal} documentos`;
    }
  }

  function updateHeroStats() {
    // Use the already-filtered set so stats reflect current search + categories + year range
    // (including hidden documents when the "Mostrar ocultos" checkbox is active)
    const docs = filteredDocuments;

    const totalEl = document.getElementById('stat-total');
    const catsEl = document.getElementById('stat-cats');
    const yearsEl = document.getElementById('stat-years');

    if (totalEl) {
      totalEl.textContent = docs.length;
    }

    if (catsEl) {
      const uniqueCats = new Set(docs.map(d => d.categoria).filter(Boolean));
      catsEl.textContent = uniqueCats.size;
    }

    if (yearsEl) {
      const years = docs
        .map(d => d.ano)
        .filter(y => Number.isInteger(y) && y > 1900);

      if (years.length > 0) {
        yearsEl.textContent = `${Math.min(...years)}–${Math.max(...years)}`;
      } else {
        yearsEl.textContent = '—';
      }
    }
  }

  // --- Rendering ---
  function renderCategoryChips() {
    if (!chipsContainer) return;
    chipsContainer.innerHTML = '';

    const cats = getCategoryOptions().map(item => item.nome);
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
      ? `<span style="background:#CD191E;color:white;font-size:0.6rem;padding:1px 5px;border-radius:3px;margin-left:6px;font-weight:600;letter-spacing:0.3px;">OCULTO</span>`
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

    // Clicking the card opens the detail view (read-only by default)
    div.addEventListener('click', (e) => {
      if (e.target.closest('a') || e.target.closest('button') || e.target.closest('.card-select')) return;
      openModal(doc, index);   // Opens in view mode
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

  // --- Unified Modal System (one modal, two states: view + edit) ---
  let currentModalDoc = null;
  let currentModalIndex = null;

  function openModal(doc, index) {
    currentModalDoc = doc;
    currentModalIndex = index;
    renderModalContent('view');
  }

  function renderModalContent(mode = 'view') {
    if (!modalEl || !currentModalDoc) return;

    const doc = currentModalDoc;
    const pdfUrl = getPdfUrl(doc);
    const date = formatDate(doc.data);

    if (mode === 'edit') {
      modalTitle.textContent = `Editando: ${doc.nome || 'Documento'}`;
    } else {
      modalTitle.textContent = doc.nome || 'Documento';
    }

    let html = '';

    if (mode === 'edit') {
      const catOptions = getCategoryOptions()
        .map(item => `<option value="${escapeHtml(item.nome)}" ${item.nome === doc.categoria ? 'selected' : ''}>${escapeHtml(item.nome)}</option>`).join('');

      html = `
        <div class="modal-meta">
          <input type="hidden" id="edit-arquivo" value="${doc.arquivo}">

          <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-subtle)">NOME</label>
          <input type="text" id="edit-nome" value="${escapeHtml(doc.nome || '')}" style="width:100%; margin-bottom:12px; padding:8px;">

          <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-subtle)">ASSUNTO</label>
          <textarea id="edit-assunto" style="width:100%; min-height:80px; margin-bottom:12px; padding:8px;">${escapeHtml(doc.assunto || '')}</textarea>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
            <div>
              <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-subtle)">NÚMERO</label>
              <input type="text" id="edit-numero" value="${escapeHtml(doc.numero || '')}" style="width:100%; padding:8px;">
            </div>
            <div>
              <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-subtle)">DATA</label>
              <input type="date" id="edit-data" value="${doc.data || ''}" style="width:100%; padding:8px;">
            </div>
          </div>

          <label style="display:block; margin-bottom:4px; font-size:0.75rem; color:var(--text-subtle)">CATEGORIA</label>
          <select id="edit-categoria" style="width:100%; padding:8px; margin-bottom:16px;">
            ${catOptions}
          </select>

          <div style="display:flex; align-items:center; gap:8px; font-size:0.7rem; color:#CD191E; margin-bottom:16px;">
            <span style="background:#CD191E; color:white; padding:1px 6px; border-radius:3px; font-size:0.65rem;">EDITANDO</span>
            <span>Arquivo: <code style="font-size:0.65rem">${escapeHtml(doc.arquivo)}</code></span>
          </div>

          <div class="modal-actions">
            <button class="btn btn-ghost" id="modal-edit-cancel">Cancelar</button>
            <button class="btn btn-primary" id="modal-edit-save">Salvar Alterações</button>
          </div>
        </div>

        <div class="modal-pdf">
          ${pdfUrl
            ? `<object data="${pdfUrl}" type="application/pdf" style="width:100%; height:100%">
                 <div style="padding:40px; text-align:center; color:#ccc">Não foi possível exibir o PDF embutido.</div>
               </object>`
            : `<div style="color:#888">PDF não disponível</div>`}
        </div>
      `;
    } else {
      // VIEW MODE
      const isHidden = !!doc.oculto;
      const hideText = isHidden ? '👁️ Mostrar' : '🚫 Ocultar';

      html = `
        <div class="modal-meta">
          <div style="display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; border-bottom:1px solid var(--border); padding-bottom:12px;">
            <button class="btn btn-primary" id="modal-edit-btn" style="padding:6px 14px; font-size:0.85rem;">✏️ Editar</button>
            <button class="btn btn-secondary" id="modal-hide-btn" style="padding:6px 14px; font-size:0.85rem;">${hideText}</button>
          </div>

          <div style="margin-bottom:16px">
            <div style="font-size:0.75rem; color:var(--text-subtle); margin-bottom:4px">CATEGORIA</div>
            <div style="font-weight:700; color:${getCategoryColor(doc.categoria)}">${escapeHtml(doc.categoria)}</div>
          </div>

          ${doc.numero ? `<div style="margin-bottom:16px"><div style="font-size:0.75rem; color:var(--text-subtle); margin-bottom:4px">NÚMERO</div><div style="font-weight:600">${escapeHtml(doc.numero)}</div></div>` : ''}

          <div style="margin-bottom:16px">
            <div style="font-size:0.75rem; color:var(--text-subtle); margin-bottom:4px">DATA / VIGÊNCIA</div>
            <div style="font-weight:600">${date || 'Data não informada'}</div>
          </div>

          <div style="margin-bottom:20px">
            <div style="font-size:0.75rem; color:var(--text-subtle); margin-bottom:4px">ASSUNTO</div>
            <div style="line-height:1.5">${escapeHtml(doc.assunto || '—')}</div>
          </div>

          <div>
            <div style="font-size:0.75rem; color:var(--text-subtle); margin-bottom:4px">ARQUIVO ORIGINAL</div>
            <div style="font-family:monospace; font-size:0.72rem; word-break:break-all; color:var(--text-muted)">${escapeHtml(doc.arquivo || '')}</div>
          </div>
        </div>

        <div class="modal-pdf">
          ${pdfUrl
            ? `<object data="${pdfUrl}" type="application/pdf" style="width:100%; height:100%">
                 <div style="padding:40px; text-align:center; color:#ccc">Não foi possível exibir o PDF embutido.</div>
               </object>`
            : `<div style="color:#888">PDF não disponível</div>`}
        </div>
      `;
    }

    modalBody.innerHTML = html;
    modalEl.classList.add('open');

    // Wire buttons depending on current mode
    if (mode === 'edit') {
      const cancel = document.getElementById('modal-edit-cancel');
      const save = document.getElementById('modal-edit-save');
      if (cancel) cancel.addEventListener('click', () => renderModalContent('view'), { once: true });
      if (save) save.addEventListener('click', saveEdit, { once: true });
    } else {
      const editBtn = document.getElementById('modal-edit-btn');
      const hideBtn = document.getElementById('modal-hide-btn');
      if (editBtn) editBtn.addEventListener('click', () => renderModalContent('edit'), { once: true });
      if (hideBtn) {
        hideBtn.addEventListener('click', async () => {
          await toggleHidden(currentModalDoc);
          renderModalContent('view');
        }, { once: true });
      }
    }

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

  // --- Import PDF ---
  function openImportModal() {
    if (!importModal) return;
    importModal.classList.add('open');
  }

  function closeImportModal() {
    if (!importModal) return;
    importModal.classList.remove('open');

    // clear fields
    [importFile, importNome, importAssunto, importAno, importData, importNumero].forEach(el => {
      if (el) el.value = '';
    });

    // reset filename display
    const filenameEl = document.getElementById('import-filename');
    if (filenameEl) {
      filenameEl.textContent = 'Nenhum arquivo selecionado';
      filenameEl.classList.remove('has-file');
    }
  }

  function setupImportListeners() {
    if (!importFile) return;

    // Auto-fill name and date when file is selected + show filename
    importFile.addEventListener('change', () => {
      const file = importFile.files[0];
      const filenameEl = document.getElementById('import-filename');

      if (!file) {
        if (filenameEl) {
          filenameEl.textContent = 'Nenhum arquivo selecionado';
          filenameEl.classList.remove('has-file');
        }
        return;
      }

      if (filenameEl) {
        filenameEl.textContent = file.name;
        filenameEl.classList.add('has-file');
      }

      const baseName = file.name.replace(/\.pdf$/i, '');
      if (!importNome.value) {
        importNome.value = baseName;
      }

      // Try to extract date from filename (Portuguese format)
      const dateMatch = baseName.match(/de\s+(\d{1,2})\s+de\s+([a-zçã]+)\s+de\s+(\d{4})/i);
      if (dateMatch) {
        const monthMap = {
          janeiro: '01', fevereiro: '02', março: '03', marco: '03',
          abril: '04', maio: '05', junho: '06', julho: '07',
          agosto: '08', setembro: '09', outubro: '10', novembro: '11', dezembro: '12'
        };
        const m = monthMap[dateMatch[2].toLowerCase()];
        if (m) {
          const isoDate = `${dateMatch[3]}-${m}-${dateMatch[1].padStart(2, '0')}`;
          if (importData) importData.value = isoDate;
          if (importAno) importAno.value = dateMatch[3];
        }
      }
    });

    // Wire buttons (will be called from init)
  }

  async function confirmImport() {
    const file = importFile && importFile.files[0];
    if (!file) {
      alert('Selecione um arquivo PDF.');
      return;
    }

    const nome = (importNome && importNome.value || '').trim();
    const assunto = (importAssunto && importAssunto.value || '').trim();
    const categoria = importCategoria ? importCategoria.value : 'Outro';
    const ano = importAno ? parseInt(importAno.value) || 0 : 0;
    const dataVal = (importData && importData.value) || `${ano}-01-01`;
    const numero = (importNumero && importNumero.value || '').trim();

    if (!nome) { alert('Preencha o nome do documento.'); return; }
    if (!ano) { alert('Preencha o ano.'); return; }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('nome', nome);
    formData.append('assunto', assunto);
    formData.append('categoria', categoria);
    formData.append('ano', ano);
    formData.append('data', dataVal);
    if (numero) formData.append('numero', numero);

    const btn = document.getElementById('btn-confirm-import');
    const originalText = btn ? btn.textContent : 'Importar';
    if (btn) { btn.disabled = true; btn.textContent = 'Enviando...'; }

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const res = await response.json();
        const novoArquivo = res.novo_arquivo;

        // Optimistic add to local data
        const newDoc = {
          nome,
          assunto,
          categoria,
          ano,
          data: dataVal,
          numero,
          arquivo: novoArquivo
        };

        // Add to visible list (it won't be hidden by default)
        allDocuments.push(newDoc);

        // Rebuild category meta and year bounds
        if (!categoryMeta[categoria]) categoryMeta[categoria] = 0;
        categoryMeta[categoria]++;

        const years = allDocuments.map(d => d.ano).filter(y => Number.isInteger(y) && y > 1900);
        if (years.length) {
          yearMin = Math.min(...years);
          yearMax = Math.max(...years);
        }

        applyFilters();
        updateHeroStats();
        closeImportModal();

        alert('PDF importado com sucesso!\n\nO documento já aparece nesta tela.\n\nClique em "Sincronizar" quando terminar para aplicar as mudanças no site público.');
      } else {
        const err = await response.json().catch(() => ({}));
        alert('Erro ao importar: ' + (err.error || 'Erro desconhecido'));
      }
    } catch (e) {
      console.error(e);
      alert('Erro de conexão ao importar o arquivo.');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    }
  }

  async function createCategory() {
    const name = normalizeCategoryName(newCategoryNameInput && newCategoryNameInput.value);
    const color = (newCategoryColorInput && newCategoryColorInput.value) || '#546E7A';

    if (!name) {
      if (categoryCreateStatus) categoryCreateStatus.textContent = 'Informe o nome da categoria.';
      return;
    }

    const alreadyExists = getCategoryOptions().some(item => item.nome.toLowerCase() === name.toLowerCase());
    if (alreadyExists) {
      if (categoryCreateStatus) categoryCreateStatus.textContent = 'Essa categoria já existe.';
      return;
    }

    const btn = document.getElementById('btn-create-category');
    const originalText = btn ? btn.textContent : 'Criar categoria';
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Salvando...';
    }

    try {
      if (IS_HTTP) {
        const response = await fetch('/api/categorias', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nome: name, color })
        });

        if (!response.ok) {
          const err = await response.json().catch(() => ({}));
          throw new Error(err.error || 'Erro ao salvar categoria.');
        }

        savedCategories = await response.json();
      } else {
        savedCategories = [...savedCategories, { nome: name, color }];
      }

      registerCategory(name, color);
      if (newCategoryNameInput) newCategoryNameInput.value = '';
      if (categoryCreateStatus) categoryCreateStatus.textContent = `Categoria "${name}" criada.`;
      refreshCategoryControls();
    } catch (e) {
      if (categoryCreateStatus) categoryCreateStatus.textContent = e.message || 'Erro ao criar categoria.';
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    }
  }

  async function toggleHidden(doc, cardElement = null) {
    const newState = !doc.oculto;

    try {
      const res = await fetch('/api/ocultar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arquivo: doc.arquivo, oculto: newState })
      });

      if (res.ok) {
        doc.oculto = newState;

        // Refresh data lists
        allDocuments = allDocuments.filter(d => !d.oculto);
        hiddenDocuments = hiddenDocuments.filter(d => d.oculto);

        if (newState) {
          hiddenDocuments.push(doc);
        } else {
          allDocuments.push(doc);
        }

        applyFilters();
        renderGrid();
      } else {
        alert('Erro ao alterar visibilidade do documento.');
      }
    } catch (e) {
      alert('Erro de conexão ao ocultar/mostrar o documento.');
    }
  }

  async function saveEdit() {
    const idx = parseInt(document.getElementById('edit-idx').value);
    const doc = [...allDocuments, ...hiddenDocuments][idx]; // fallback lookup

    if (!doc) {
      alert("Documento não encontrado.");
      return;
    }

    const payload = {
      arquivo: document.getElementById('edit-arquivo').value,
      nome: document.getElementById('edit-nome').value.trim(),
      assunto: document.getElementById('edit-assunto').value.trim(),
      numero: document.getElementById('edit-numero').value.trim(),
      data: document.getElementById('edit-data').value.trim(),
      categoria: document.getElementById('edit-categoria').value
    };

    if (!payload.nome) {
      alert("O campo Nome é obrigatório.");
      return;
    }

    const saveBtn = document.querySelector('#modal-body .btn-primary');
    const originalText = saveBtn ? saveBtn.textContent : 'Salvar';
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = 'Salvando...';
    }

    try {
      const res = await fetch('/api/editar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const responseData = await res.json();

        // Optimistic update in local data
        Object.assign(doc, payload);
        if (responseData.novo_arquivo) {
          doc.arquivo = responseData.novo_arquivo;
        }

        closeModal();
        applyFilters();
        renderGrid();
        alert('Documento atualizado com sucesso!');
      } else {
        const err = await res.json().catch(() => ({}));
        alert('Erro ao salvar: ' + (err.error || 'Erro desconhecido'));
      }
    } catch (e) {
      alert('Erro de conexão ao salvar as alterações.');
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = originalText;
      }
    }
  }

  // --- Filter Controls ---
  function clearAllFilters() {
    searchInput.value = '';
    activeCategories.clear();
    yearMin = null;
    yearMax = null;
    includeHidden = false;

    const toggle = document.getElementById('show-hidden-toggle');
    if (toggle) toggle.checked = false;

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
      if (e.key.toLowerCase() === 'escape' && importModal && importModal.classList.contains('open')) {
        closeImportModal();
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInput.focus();
      }
    });

    // Hint in console for power users
    console.info('%c[admin] Dica: pressione / para focar na busca', 'color:#888');
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

    // Import modal refs
    importModal = document.getElementById('modal-import');
    importFile = document.getElementById('import-file');
    importNome = document.getElementById('import-nome');
    importAssunto = document.getElementById('import-assunto');
    importCategoria = document.getElementById('import-categoria');
    importAno = document.getElementById('import-ano');
    importData = document.getElementById('import-data');
    importNumero = document.getElementById('import-numero');
    newCategoryNameInput = document.getElementById('new-category-name');
    newCategoryColorInput = document.getElementById('new-category-color');
    categoryCreateStatus = document.getElementById('category-create-status');
    openDocumentsBtn = document.getElementById('btn-open-documents');
    publicPackageBtn = document.getElementById('btn-public-package');

    if (openDocumentsBtn) openDocumentsBtn.addEventListener('click', openDocumentsFolder);
    if (publicPackageBtn) publicPackageBtn.addEventListener('click', createPublicPackage);

    // Close modal handlers
    document.getElementById('modal-close').addEventListener('click', closeModal);
    modalEl.addEventListener('click', (e) => {
      if (e.target === modalEl) closeModal();
    });

    // Load data (respects existing ocultos/edicoes)
    const loadingEl = document.getElementById('loading');
    try {
      await loadData();

      // Show "Mostrar ocultos" toggle only for the owner on localhost
      const showHiddenWrapper = document.getElementById('show-hidden-wrapper');
      const showHiddenToggle = document.getElementById('show-hidden-toggle');

      if (window.__isLocal && hiddenDocuments.length > 0 && showHiddenWrapper && showHiddenToggle) {
        showHiddenWrapper.style.display = 'flex';

        showHiddenToggle.addEventListener('change', () => {
          includeHidden = showHiddenToggle.checked;
          console.log('[admin] Mostrar ocultos toggled to:', includeHidden);
          console.log('[admin] hiddenDocuments count:', hiddenDocuments.length);

          if (includeHidden) {
            // Expand year range to cover hidden documents too
            if (window.__fullYearMin != null && window.__fullYearMax != null) {
              yearMin = Math.min(yearMin || window.__fullYearMin, window.__fullYearMin);
              yearMax = Math.max(yearMax || window.__fullYearMax, window.__fullYearMax);

              if (yearMinInput) yearMinInput.value = yearMin;
              if (yearMaxInput) yearMaxInput.value = yearMax;
            }

            // Use full category counts while showing hidden
            if (window.__fullCategoryMeta) {
              categoryMeta = { ...window.__fullCategoryMeta };
            }
          } else {
            // Restore visible-only stats when hiding the hidden ones again
            if (window.__visibleYearMin != null && window.__visibleYearMax != null) {
              yearMin = window.__visibleYearMin;
              yearMax = window.__visibleYearMax;
              if (yearMinInput) yearMinInput.value = yearMin;
              if (yearMaxInput) yearMaxInput.value = yearMax;
            }

            categoryMeta = {};
            allDocuments.forEach(d => {
              if (!categoryMeta[d.categoria]) categoryMeta[d.categoria] = 0;
              categoryMeta[d.categoria]++;
            });
          }

          // Re-apply everything (applyFilters already updates grid, results count and hero stats)
          renderCategoryChips();
          applyFilters();
          updateSelectionToolbar();
        });
      }

      // Initial UI
      renderCategorySelect(importCategoria);
      renderCategoryChips();
      renderYearInputs();

      // First render (respect current includeHidden state, which starts as false)
      filteredDocuments = getDocumentsToShow();
      renderGrid();
      updateResultsCount();
      updateHeroStats();

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

      // Admin actions
      const btnSync = document.getElementById('btn-sync');
      if (btnSync) {
        btnSync.addEventListener('click', async () => {
          if (!confirm('Sincronizar os dados agora? Isso vai aplicar todas as edições no Admin.')) return;

          btnSync.disabled = true;
          const originalText = btnSync.innerHTML;
          btnSync.innerHTML = '⏳ Sincronizando...';

          try {
            const resp = await fetch('/api/sync', { method: 'POST' });
            if (resp.ok) {
              alert('Sincronização concluída com sucesso!\n\nOs dados foram regenerados. Se você copiou PDFs em massa para Documentos, revise nome, assunto, data, categoria e visibilidade dos novos cards. Quando estiver tudo certo, clique em "Gerar pacote público" para criar a versão que será hospedada.\n\nRecarregando os dados nesta tela...');
              
              // Reload data in current admin UI so changes are visible immediately
              await loadData();
              renderCategoryChips();
              applyFilters();
              updateHeroStats();
            } else {
              let message = 'Erro ao sincronizar.';
              try {
                const data = await resp.json();
                const details = data.details || data.error;
                if (resp.status === 403) {
                  message += '\n\nO servidor ainda está rodando uma versão antiga com bloqueio de acesso. Feche e abra novamente o Portfolio Profissional.';
                } else if (details) {
                  message += `\n\n${details}`;
                }
              } catch (e) {
                // Keep the generic message if the server did not return JSON.
              }
              alert(message);
            }
          } catch (e) {
            alert('Erro de conexão com o servidor.');
          } finally {
            btnSync.disabled = false;
            btnSync.innerHTML = originalText;
          }
        });
      }

      const btnImport = document.getElementById('btn-importar');
      if (btnImport) {
        btnImport.addEventListener('click', openImportModal);
      }

      const btnCreateCategory = document.getElementById('btn-create-category');
      if (btnCreateCategory) btnCreateCategory.addEventListener('click', createCategory);
      if (newCategoryNameInput) {
        newCategoryNameInput.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') createCategory();
        });
      }

      // Import modal wiring
      setupImportListeners();
      const importCloseBtn = document.getElementById('import-modal-close');
      const btnCancelImport = document.getElementById('btn-cancel-import');
      const btnConfirmImport = document.getElementById('btn-confirm-import');

      if (importCloseBtn) importCloseBtn.addEventListener('click', closeImportModal);
      if (importModal) importModal.addEventListener('click', (e) => {
        if (e.target === importModal) closeImportModal();
      });
      if (btnCancelImport) btnCancelImport.addEventListener('click', closeImportModal);
      if (btnConfirmImport) btnConfirmImport.addEventListener('click', confirmImport);

      // Stats (will reflect current visible + hidden state)
      updateHeroStats();

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

  window.__portfolioAdminTest = {
    getCategoryOptions,
    getCategoryCountsForFilters,
    normalizeCategoryName,
    registerCategory,
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
