# myPortfolio

Conteudo pronto para publicar no GitHub Pages do repositorio `myPortfolio`.

## Antes de subir

Gere o instalador Windows e publique como asset de GitHub Release:

```text
dist-installer/PortfolioProfissionalSetup.exe
```

No projeto principal, o fluxo e:

```powershell
packaging\build_windows.ps1
```

Depois compile `packaging\installer.iss` no Inno Setup e rode:

```powershell
packaging\prepare_landing_download.ps1
```

O link da landing aponta para `releases/latest/download/PortfolioProfissionalSetup.exe`.
Nao versione o instalador no repositorio.

## GitHub Pages

Publique o conteudo desta pasta na branch `gh-pages` do repositorio `myPortfolio`.

Nao copie `Documentos`, `site`, `config`, `dist`, `dist-publico` ou `build` para o repositorio publico.
