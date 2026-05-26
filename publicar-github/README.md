# myPortfolio

Conteudo pronto para publicar no GitHub Pages do repositorio `myPortfolio`.

## Antes de subir

Gere o instalador Windows e copie para:

```text
downloads/PortfolioProfissionalSetup.exe
```

No projeto principal, o fluxo e:

```powershell
packaging\build_windows.ps1
```

Depois compile `packaging\installer.iss` no Inno Setup e rode:

```powershell
packaging\prepare_landing_download.ps1
```

Esse script copia o instalador para `landing\downloads` e para `publicar-github\downloads`.

## GitHub Pages

Publique o conteudo desta pasta na raiz do repositorio `myPortfolio`.

Nao copie `Documentos`, `site`, `config`, `dist`, `dist-publico` ou `build` para o repositorio publico.
