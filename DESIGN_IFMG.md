---
name: IFMG - Identidade Visual Institucional
description: Sistema de design oficial do Instituto Federal de Minas Gerais (IFMG). Garante consistência visual em interfaces digitais, materiais institucionais e gerações de UI por IA, alinhado ao Manual de Identidade Visual 2016 e à marca dos Institutos Federais.
version: alpha
colors:
  primary-verde: "#2F9E41"      # Harmonia, integração e rede de conhecimento
  accent-vermelho: "#CD191E"    # Pensamento, força, energia e destaque
  neutral-preto: "#000000"
  neutral-branco: "#FFFFFF"
  text-primary: "{colors.neutral-preto}"
  text-secondary: "#1A1A1A"
  background-light: "{colors.neutral-branco}"
  background-dark: "{colors.neutral-preto}"
typography:
  heading-principal:
    fontFamily: "Open Sans"
    fontWeight: 700
    fontSize: 2.5rem
    lineHeight: 1.2
    letterSpacing: -0.02em
  heading-secundario:
    fontFamily: "Open Sans"
    fontWeight: 700
    fontSize: 1.75rem
    lineHeight: 1.3
  body-text:
    fontFamily: "Open Sans"
    fontWeight: 400
    fontSize: 1rem
    lineHeight: 1.6
  label-caps:
    fontFamily: "Open Sans"
    fontWeight: 700
    fontSize: 0.875rem
    letterSpacing: 0.05em
rounded:
  sm: 4px
  md: 8px
  lg: 12px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
components:
  button-primary:
    backgroundColor: "{colors.primary-verde}"
    textColor: "{colors.neutral-branco}"
    rounded: "{rounded.md}"
    padding: "12px 24px"
  button-secondary:
    backgroundColor: "{colors.accent-vermelho}"
    textColor: "{colors.neutral-branco}"
    rounded: "{rounded.md}"
    padding: "12px 24px"
  header-institucional:
    backgroundColor: "{colors.neutral-branco}"
    textColor: "{colors.neutral-preto}"
    borderColor: "{colors.primary-verde}"
  card-institucional:
    backgroundColor: "{colors.neutral-branco}"
    borderColor: "{colors.primary-verde}"
    rounded: "{rounded.md}"
    shadow: "0 2px 8px rgba(0,0,0,0.1)"
---
## Visão Geral
O sistema de design do IFMG foi construído sobre a ideia do ser humano integrado e funcional, representado pela rede de quadrados que formam a marca institucional. Reflete os valores de excelência em educação, ciência e tecnologia, promovendo harmonia, integração entre campi e uma imagem institucional unificada e de alta qualidade. A identidade visual deve transmitir profissionalismo, acessibilidade e coesão em todos os materiais impressos e digitais.

## Cores
- **Verde IFMG (#2F9E41)**: Cor primária. Representa harmonia, integração e a rede de conhecimento entre os campi. Deve ser usada em elementos principais, botões de ação e destaques institucionais.
- **Vermelho IFMG (#CD191E)**: Cor de destaque (accent). Simboliza pensamento expresso, força e energia. Recomendada para chamadas de ação secundárias, alertas e ênfases.
- **Preto (#000000)** e **Branco (#FFFFFF)**: Cores neutras para textos, fundos e contraste máximo. Versões monocromáticas ou em escala de cinza são permitidas quando necessário para harmonia visual.

Todas as combinações de cores devem respeitar o contraste WCAG AA (mínimo 4.5:1) para garantir acessibilidade.

## Tipografia
A tipografia oficial é baseada exclusivamente na família **Open Sans**, conforme o Manual de Identidade Visual:
- **Open Sans Bold (700)**: Títulos, cabeçalhos institucionais e destaques.
- **Open Sans Regular (400)**: Textos correntes, legendas e conteúdo geral.

O uso de outras fontes (ex.: Arial em apresentações) é permitido apenas em casos específicos previstos no manual, mas Open Sans é a preferencial para consistência digital.

## Layout e Espaçamento
- Sistema de espaçamento modular baseado em múltiplos de 8px (escala 4-8-16-24-32px).
- Área de influência da marca: mínimo 1X (módulo base da grade de construção do logo) de espaço livre ao redor da logomarca.
- Alinhamento: textos devem respeitar a base alinhada aos quadrados verdes da marca.

## Formas e Arredondamentos
- Arredondamentos suaves (4px a 12px) para elementos digitais, mantendo a sensação de rede organizada e funcional.
- A logomarca utiliza quadrados com cantos arredondados em 10% do módulo X, conforme grade de construção.

## Componentes
- **Botão Primário**: Fundo verde institucional, texto branco, arredondamento médio. Representa ações principais.
- **Botão Secundário**: Fundo vermelho institucional, texto branco, arredondamento médio. Usado em ações complementares.
- **Cabeçalho Institucional**: Fundo branco, texto preto, borda verde sutil.
- **Card Institucional**: Fundo branco, borda verde fina, sombra leve para profundidade.

## Regras de Uso (Do's and Don'ts)
**Do's:**
- Sempre utilizar as versões oficiais da logomarca (horizontal ou vertical) baixadas do portal institucional.
- Manter proporções e área de influência da marca.
- Priorizar contraste e acessibilidade em interfaces digitais.
- Usar o DESIGN.md como fonte de verdade para ferramentas de IA (Stitch, agentes de código etc.).

**Don'ts:**
- Alterar cores, distorcer ou rotacionar a logomarca.
- Separar o símbolo (quadrados) do texto da marca.
- Utilizar fundos instáveis sem fundo branco de proteção.
- Aplicar a marca como marca-d'água ou com transparência excessiva.

**Referência oficial**: Manual de Identidade Visual do IFMG (disponível em ifmg.edu.br).  
Qualquer dúvida ou variação por campus deve ser validada com a Comissão de Comunicação do IFMG.

---

**Como usar este arquivo**  
1. Salve como `DESIGN.md` na raiz do projeto.  
2. Importe no Stitch (Google) ou em qualquer agente compatível com o formato open-source.  
3. O arquivo garante que todas as telas e componentes gerados respeitem a identidade visual institucional do IFMG.