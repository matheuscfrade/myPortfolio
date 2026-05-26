const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const mainJs = fs.readFileSync(path.join(__dirname, 'main.js'), 'utf8');

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

assert.ok(context.__portfolioPublicTest, 'public test helpers should be exposed');

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioPublicTest.mergeAppConfig({ displayName: 'Ana' }))),
  {
    displayName: 'Ana',
    subtitle: 'Portfolio Profissional',
    portfolioTitle: 'Portfolio Documental',
    organization: ''
  },
  'public config merge should keep defaults for missing values'
);

const docs = [
  { categoria: 'Comissão', ano: 2026, nome: 'PDI', assunto: 'Monitoramento' },
  { categoria: 'Comissão', ano: 2025, nome: 'Licitação', assunto: 'Pregão' },
  { categoria: 'Comissão', ano: 2025, nome: 'PDI antigo', assunto: 'Monitoramento' },
  { categoria: 'Grupo de Trabalho', ano: 2026, nome: 'PDI', assunto: 'PDLS' },
  { categoria: 'Outro', ano: 0, nome: 'Sem data', assunto: 'PDI' }
];

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioPublicTest.getCategoryCountsForFilters(docs, {
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
  'category counts should follow search and year filters, preserving unknown years'
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioPublicTest.getCategoryCountsForFilters(docs, {
    query: 'pdi',
    yearMin: 2026,
    yearMax: 2026,
    activeCategories: new Set(['Comissão'])
  }))),
  {
    'Comissão': 1
  },
  'category counts should follow the active category filter too'
);

assert.deepEqual(
  JSON.parse(JSON.stringify(context.__portfolioPublicTest.buildExportPayload(docs.map((doc, index) => ({
    ...doc,
    arquivo: `doc-${index}.pdf`,
    data: '2026-01-01',
    numero: String(index + 1)
  })), new Set(['doc-1.pdf'])))),
  [
    {
      nome: 'Licitação',
      assunto: 'Pregão',
      categoria: 'Comissão',
      ano: 2025,
      data: '2026-01-01',
      numero: '2',
      arquivo: 'doc-1.pdf'
    }
  ],
  'public export payload should include only selected documents with metadata'
);
