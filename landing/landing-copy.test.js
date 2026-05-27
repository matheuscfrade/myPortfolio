const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');

assert.match(html, /Portfolio Profissional para organizar seus documentos/, 'landing should use the updated hero headline');
assert.match(html, /href="https:\/\/github\.com\/matheuscfrade\/myPortfolio\/releases\/latest\/download\/PortfolioProfissionalSetup\.exe"/, 'installer button should point to the GitHub Release artifact');
assert.match(html, /Baixe sempre a versão mais recente do instalador/, 'landing should tell users the button gets the latest installer');
assert.match(html, /Não Categorizado/, 'landing should mention the triage category used for loose PDFs');
assert.match(html, /Documentos\/_Excluidos/, 'landing should mention the recovery folder for deleted documents');
assert.match(html, /Copiar PDFs para Documentos não finaliza o cadastro\./, 'bulk upload warning should keep the required accented copy');
assert.match(html, /<h2>Publicação na Web<\/h2>/, 'publication section should use the requested title');
assert.match(html, /clique em Gerar pacote público no Admin e envie apenas os arquivos estáticos da pasta dist-publico para Cloudflare Pages, Netlify, GitHub Pages ou Vercel\./, 'publishing warning should reflect the current Admin button flow');
assert.doesNotMatch(html, /Ver como publicar|Publicação realmente pública/, 'landing should not include removed publishing copy');
assert.doesNotMatch(html, /Melhor para upload direto|Mais simples para arrastar|Bom para manter histórico|Bom para projetos/, 'hosting cards should not include subjective interpretations');
assert.match(html, /<div class="hosting-item"><strong>Cloudflare Pages<\/strong><\/div>/, 'Cloudflare hosting card should show only the service name');
assert.match(html, /<div class="hosting-item"><strong>Netlify<\/strong><\/div>/, 'Netlify hosting card should show only the service name');
assert.match(html, /grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/, 'hosting suggestions should use two balanced columns on wide layouts');
assert.match(html, /Developed by Matheus Costa Frade/, 'landing should use the required footer credit');
assert.doesNotMatch(html, /Visualização Pública/, 'landing should not show the public badge');
assert.doesNotMatch(html, /Administração do Portfólio/, 'landing should not show the admin preview section');
assert.doesNotMatch(html, /O que vem no instalador|Para quem é/, 'landing should not include removed sections');
assert.doesNotMatch(html, /Gerar_Pasta_Publica\.bat|Abrir pasta Documentos/, 'landing should not tell users to run local scripts or unrelated admin buttons');
assert.doesNotMatch(html, /Feito com base no projeto original|O app instalado usa o nome informado pelo usuário/, 'landing should not use the old footer credit');
assert.match(html, /--bg:\s*#0F1110/i, 'landing should default to the same dark background as the app');
assert.match(html, /--surface:\s*#1C1F1D/i, 'landing should default to dark app surfaces');
assert.doesNotMatch(html, /Navegacao|Visualizacao|Publicacao|Configuracoes|Portifolio|Portfolio documental para publicar com seguranca/i, 'landing should avoid unaccented legacy copy');
assert.doesNotMatch(html, /Ã|Â|â€|ðŸ|ï¼|â€¦/, 'landing should not contain mojibake text');
