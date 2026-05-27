# Portfolio Profissional

Aplicativo Windows para organizar documentos profissionais localmente e publicar uma versao estatica do portfolio.

## Para usuarios

### Instalar no Windows

1. Baixe o instalador `PortfolioProfissionalSetup.exe`.
2. Execute o instalador.
3. Informe o nome que deve aparecer no portfolio.
4. Abra o app pelo atalho **Portfolio Profissional**.

O app abre um servidor local e mostra o painel Admin no navegador. Nao e necessario instalar Python, pip ou usar terminal na maquina do usuario final.

## Primeiro uso

No painel Admin voce pode:

- importar PDFs individualmente;
- editar nome, assunto, numero, data, categoria e visibilidade;
- criar categorias;
- abrir a pasta `Documentos`;
- sincronizar dados;
- gerar a pasta publica para hospedagem estatica pelo botao **Gerar pacote publico**.

## Carga inicial em massa

Use este fluxo quando ja houver muitos PDFs:

1. No Admin, clique em **Abrir pasta Documentos**.
2. Copie varios PDFs para essa pasta.
3. Se quiser, organize como `Documentos/Categoria/Ano/arquivo.pdf`.
4. Volte ao Admin e clique em **Sincronizar**.
5. Revise os metadados dos novos cards.

Copiar PDFs para `Documentos` nao finaliza o cadastro. Depois de sincronizar, revise nome, assunto, data, categoria e visibilidade no painel Admin.

## Publicar de verdade

O painel Admin fica apenas no computador local. Para publicar:

1. Revise documentos e visibilidade.
2. No Admin, clique em **Gerar pacote publico**.
3. Envie a pasta `dist-publico` para GitHub Pages, Netlify, Vercel, Cloudflare Pages ou outro servico de hospedagem estatica.

O pacote publico nao deve incluir o Admin nem o servidor Flask.

## Publicar a landing de download

A landing para baixar o instalador fica em `publicar-github`.
Ela deve conter apenas `index.html` e `README.md`; o instalador deve ser publicado
como asset de GitHub Release.
Nao suba `Documentos`, `site`, `config`, `dist`, `dist-publico` ou `build` para o repositorio publico.

## Desenvolvimento

Para rodar a partir do codigo-fonte:

```powershell
python -m pip install -r requirements.txt
python scripts\servidor_admin.py
```

Acesse:

- Admin: `http://127.0.0.1:5000/admin/`
O app instalado abre apenas o Admin local. A visualizacao publica e gerada dentro da pasta `dist-publico` quando voce cria o pacote publico.

## Build Windows

Os arquivos de empacotamento ficam em `packaging/`.

```powershell
packaging\build_windows.ps1
```

Depois compile `packaging\installer.iss` no Inno Setup.

Para o botao de download da landing funcionar, copie o instalador gerado para a pasta publica da landing:

```powershell
packaging\prepare_landing_download.ps1
```

## Testes

```powershell
python scripts\app_runtime.test.py
python scripts\export_zip.test.py
python scripts\create_public_package.test.py
python scripts\create_starter_kit.test.py
node site-publico\category-counts.test.js
node admin\category-options.test.js
```
