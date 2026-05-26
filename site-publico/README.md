# Site Publico

Esta pasta contem a interface estatica de consulta do portfolio.

Quando servida pelo app local, a interface usa:

- `/shared-data/dados.js`
- `/shared-data/edicoes.json`
- `/shared-data/ocultos.json`
- `/shared-data/categorias.json`
- `/shared-data/config.json`
- `/Documentos/`

Quando publicada, esses arquivos devem estar no pacote publico gerado pelo Admin.

## Publicacao

Use o botao **Gerar pacote publico** no Admin. Publique a pasta gerada em um servico de arquivos estaticos, como:

- GitHub Pages;
- Netlify;
- Vercel;
- Cloudflare Pages.

Nao publique a pasta `admin/` nem o servidor Flask.
