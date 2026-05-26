# Build Windows

Este diretorio contem os arquivos para gerar o EXE e o instalador Windows.

## Pre-requisitos na maquina de build

- Python instalado e disponivel como `python`.
- Inno Setup instalado para compilar `installer.iss`.

O instalador e por usuario: ele instala em `%LOCALAPPDATA%\Programs\Portfolio Profissional`
e grava os dados mutaveis em `%LOCALAPPDATA%\Portfolio Profissional`.

## Gerar EXE

No PowerShell, a partir da raiz do projeto:

```powershell
packaging\build_windows.ps1
```

O executavel sera gerado em:

```text
dist\PortfolioProfissional\
```

## Gerar instalador

1. Abra o Inno Setup.
2. Compile `packaging\installer.iss`.
3. O instalador sera gerado em `dist-installer\PortfolioProfissionalSetup.exe`.

## Preparar download da landing

Depois de gerar o instalador, copie o arquivo para o caminho usado pelo botao da landing:

```powershell
packaging\prepare_landing_download.ps1
```

Isso cria/atualiza:

```text
landing\downloads\PortfolioProfissionalSetup.exe
publicar-github\downloads\PortfolioProfissionalSetup.exe
```

Ao publicar a landing no GitHub Pages, use somente o conteudo de `publicar-github`.
Nao publique `Documentos`, `site`, `config`, `dist`, `dist-publico` ou `build`.

Durante a instalacao, o assistente pede o nome exibido, subtitulo e titulo do site. Esses valores sao gravados em:

```text
%LOCALAPPDATA%\Portfolio Profissional\config\app.json
```

## Teste recomendado

Teste o instalador em um usuario Windows limpo antes de publicar:

1. Instale o app.
2. Abra pelo atalho.
3. Confirme que o navegador abre o Admin.
4. Clique em Abrir pasta Documentos.
5. Copie alguns PDFs.
6. Clique em Sincronizar.
7. Gere o pacote publico.
