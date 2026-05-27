const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const mainJs = fs.readFileSync(path.join(__dirname, 'main.js'), 'utf8');
const indexHtml = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const stylesCss = fs.readFileSync(path.join(__dirname, 'styles.css'), 'utf8');

assert.doesNotMatch(indexHtml, /config-display-name|config-subtitle|config-portfolio-title|btn-save-config/, 'admin should not expose installer identity settings');
assert.doesNotMatch(indexHtml, /Configura(?:c|ç)(?:o|õ)es do portfolio|Nome exibido|Titulo do site|Salvar configura/, 'admin should not show configuration copy');
assert.match(indexHtml, /btn-open-documents/, 'admin should keep operational document-folder action');
assert.match(indexHtml, /btn-public-package/, 'admin should keep public package action');
assert.doesNotMatch(stylesCss, /prefers-color-scheme:\s*dark/, 'admin should not depend on the OS/browser theme to use dark mode');
assert.match(stylesCss, /--bg:\s*#0F1110/i, 'admin should default to the dark theme background');
assert.match(mainJs, /Não Categorizado/, 'admin should expose the triage category for manually copied PDFs');
assert.match(mainJs, /modal-delete-btn/, 'document detail modal should expose a delete action');

const context = {
  console,
  location: { protocol: 'http:', hostname: '127.0.0.1' },
  window: {},
  document: {
    readyState: 'loading',
    addEventListener() {},
    createElement() {
      return {};
    },
    head: {
      appendChild() {}
    }
  }
};

context.window = context;
vm.createContext(context);
vm.runInContext(mainJs, context);

assert.ok(context.__portfolioAdminTest, 'admin test helpers should be exposed');

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioAdminTest.mergeAppConfig({ displayName: 'Ana' }))),
  {
    displayName: 'Ana',
    subtitle: 'Portfolio Profissional',
    portfolioTitle: 'Portfolio Documental',
    organization: ''
  },
  'admin config merge should keep defaults for missing values'
);

const options = context.__portfolioAdminTest.getCategoryOptions({
  docs: [
    { categoria: 'Comissão' },
    { categoria: 'Banca Examinadora' }
  ],
  savedCategories: [
    { nome: 'Comitê' },
    { nome: 'Banca Examinadora' }
  ]
});

assert.deepEqual(
  JSON.parse(JSON.stringify(options.filter(item => item.nome === 'Banca Examinadora'))),
  [{ nome: 'Banca Examinadora', color: '#546E7A' }],
  'custom categories from saved data and documents should be deduplicated'
);

assert.ok(
  options.some(item => item.nome === 'Comissão' && item.color === '#2F9E41'),
  'default categories should keep their configured colors'
);

assert.ok(
  options.some(item => item.nome === 'Comitê' && item.color === '#546E7A'),
  'saved custom categories should appear in the options list'
);

assert.ok(
  options.some(item => item.nome === 'Não Categorizado' && item.color === '#546E7A'),
  'triage category should appear in the options list'
);

const docs = [
  { categoria: 'Comissão', ano: 2026, nome: 'PDI', assunto: 'Monitoramento' },
  { categoria: 'Comissão', ano: 2025, nome: 'PDI antigo', assunto: 'Monitoramento' },
  { categoria: 'Grupo de Trabalho', ano: 2026, nome: 'PDI', assunto: 'PDLS' },
  { categoria: 'Outro', ano: 0, nome: 'Sem data', assunto: 'PDI' }
];

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioAdminTest.getCategoryCountsForFilters(docs, {
    query: 'pdi',
    yearMin: 2026,
    yearMax: 2026,
    activeCategories: new Set()
  }))),
  {
    'Comissão': 1,
    'Grupo de Trabalho': 1,
    Outro: 1
  },
  'admin category counts should follow search and year filters'
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioAdminTest.buildExportPayload([
    {
      nome: 'VisÃ­vel',
      assunto: 'Selecionado',
      categoria: 'ComissÃ£o',
      ano: 2026,
      data: '2026-01-01',
      numero: '1',
      arquivo: 'visivel.pdf'
    },
    {
      nome: 'Oculto',
      assunto: 'Fora da tela',
      categoria: 'Outro',
      ano: 2025,
      data: '2025-01-01',
      numero: '2',
      arquivo: 'oculto.pdf'
    }
  ], new Set(['visivel.pdf', 'oculto-inexistente.pdf'])))),
  [
    {
      nome: 'VisÃ­vel',
      assunto: 'Selecionado',
      categoria: 'ComissÃ£o',
      ano: 2026,
      data: '2026-01-01',
      numero: '1',
      arquivo: 'visivel.pdf'
    }
  ],
  'admin export payload should include only selected documents from the provided visible set'
);
