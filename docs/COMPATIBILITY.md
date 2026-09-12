# Compatibilidade — HP-12C Classic Simulator

Modelo alvo: **HP-12C Classic** (não Platinum). Fonte primária:
*hp 12c financial calculator user's guide*, Edition 4, HP Part Number
0012C-90001 (manual oficial linkado pelo usuário no briefing original).

## Como ler este documento

- **VERIFICADO (manual)** = o comportamento/fórmula foi confirmado no texto
  do manual (citado em `docs/ANALYSIS.md`) e coberto por caso(s) de teste em
  `tests/hp12c-reference.json`.
- **NOT VERIFIED (hardware)** = ainda não há nenhum caso de teste com saída
  de uma HP-12C física real. Todo o projeto está nesta categoria até que o
  usuário forneça resultados de um aparelho real — nesse momento esses
  resultados tornam-se fixtures prioritárias (ver política em
  `docs/ANALYSIS.md` §12 e no briefing original).
- **NOT IMPLEMENTED** = função do manual que a calculadora real tem e este
  simulador não reproduz ainda.
- **SIMPLIFICAÇÃO DOCUMENTADA** = implementado, mas com uma escolha de
  design explícita onde o manual era ambíguo ou onde a posição física exata
  de uma tecla não pôde ser confirmada.

Suíte atual: **72/72 casos passando** (`python tests/run_tests.py`), cobrindo
categorias A–K. Nenhuma divergência conhecida e não resolvida está sendo
escondida — o que segue é a lista completa de lacunas conhecidas.

**2026-09-12 — auditoria de fidelidade**: uma auditoria completa comparando
cada função contra o texto do manual (não contra a implementação) encontrou e
corrigiu **7 divergências reais** entre o comportamento anterior e o manual —
não apenas nomenclatura. Lista completa e evidência de cada uma em
`docs/ANALYSIS.md` §5; resumo:
1. Juros simples (`INT`) tratava `n` como anos e não dividia por 360/365 —
   corrigido, validado contra exemplo do manual ($450/60 dias/7% → 5,25/5,18).
2. Amortização usava arredondamento de 10 dígitos em vez do arredondamento
   pelas casas decimais do display (o `_RND` da fórmula) — corrigido,
   validado contra o exemplo de 25 anos do manual.
3. Amortização decrementava `n` de um prazo pré-definido; o manual mostra que
   `n` ACUMULA períodos amortizados a partir de 0 — corrigido.
4. Depreciação lia SBV/SAL/vida da pilha RPN; o manual usa PV/FV/n — corrigido.
5. YTM de bonds lia o preço-alvo do registrador FV; o manual usa PV —
   corrigido.
6. Registradores de saída de AMORT/INT/depreciação/bond-PRICE seguiam um
   "lift" genérico da pilha; a tabela do Apêndice A exige um mapeamento
   T/Z/Y/X específico e diferente — corrigido para as 4 funções.
7. Média ponderada dividia por Σy; o exemplo do manual (item ENTER peso Σ+)
   mostra que o peso vai para X, logo a divisão correta é por Σx — corrigido.

Todas as 7 correções foram validadas bit-a-bit (ou arredondado ao display,
quando é isso que o próprio manual mostra) contra exemplos numéricos REAIS do
manual — não apenas contra a fórmula. Isso é aferição documental da mais alta
confiança disponível sem um aparelho físico.

## Implementado e verificado contra o manual

- Pilha RPN completa (X,Y,Z,T,LAST X), regras de stack lift/drop exatas
  (Apêndice A), incluindo a supressão de lift pelas 6 teclas específicas do
  12C (ENTER, CLx, Σ+, Σ-, 12×, 12÷) e por STO em registrador financeiro.
- Aritmética, 1/x, √x, y^x, LN, e^x, n!, RND, INTG, FRAC.
- %, Δ%, %T (com o comportamento de pilha diferenciado — não dropa/lifta).
- TVM sem período fracionário (n, i, PV, PMT, FV), com n sempre arredondado
  para cima; solução de i por bisseção (não é o algoritmo do firmware, ver
  seção "Aproximações" abaixo).
- Amortização (`f n`): recursão período a período do Apêndice D com
  arredondamento pelas casas decimais do display, `n` acumulando períodos
  amortizados, registradores de saída T/Z/Y/X exatos — bit-a-bit igual ao
  exemplo do manual (hipoteca 25 anos/13.25%/$50.000, 2 anos).
- Juros simples (`f i`): bases 360 e 365, `n` em dias, `i` anual — bit-a-bit
  igual ao exemplo do manual ($450/60 dias/7%).
- NPV / IRR com até 20 fluxos de caixa distintos e repetições (Nj).
- Depreciação SL/SOYD/DB (fórmulas de tecla, sem período parcial), entradas
  via PV/FV/n/i (não pilha), RBV persistido em PV entre chamadas de DB —
  bit-a-bit igual ao exemplo do manual (custo 10.000/salvamento 500/vida 5
  anos/200%, 3 anos).
- Bonds (PRICE/YTM) pelo método SIA citado no próprio manual, entradas via
  PMT(cupom)/i(yield)/PV(preço-alvo do YTM), resultado de PRICE também
  gravado em PV — bit-a-bit (arredondado ao display) igual aos dois exemplos
  do manual, além da identidade "par bond" (cupom=yield ⇒ preço=100)
  verificada por cálculo independente.
- Calendário: ΔDYS actual-basis (via `datetime` do Python, não a fórmula
  polinomial do manual — ver justificativa em `calendar_fns.py`) e 30/360
  (fórmula exata do Apêndice D). DATE (soma de dias). Formatos D.MY/M.DY.
- Estatística completa: Σ+/Σ-, média, média ponderada (Σxy/Σx — peso em X,
  item em Y, bit-a-bit igual ao exemplo do manual dos 4 postos de gasolina),
  desvio padrão amostral, regressão linear (ŷ,r e x̂,r).
- Registradores R0–R9/R.0–R.9, STO/RCL, aritmética de registrador restrita a
  R0–R4 (Erro 4 fora disso — confirmado no Apêndice C, não é suposição).
- Modelo de memória de programa: 8 linhas base + 20 registradores, expansão
  em blocos de 7 linhas consumindo registradores na ordem R.9→R.0→R9→...,
  limite de 99 linhas (consumindo exatamente 13 registradores) — replica o
  exemplo numérico do próprio manual.
- Programação: gravação de teclas (1 tecla física = 1 linha, igual ao
  hardware), GTO, rótulos A–E, R/S, testes condicionais (x=0/x≠0/x>0/x<0/
  x≥0/x≤0 e x=y/x≠y/x>y/x<y/x≥y/x≤y).
- Display: Standard (FIX 0–9) e Científico (mantissa de 7 dígitos
  significativos), arredondamento round-half-up, overflow (clamp em
  ±9.999999999×10^99) e underflow (→0) exatamente como descrito na p.73.
- Erros 0–9 completos (Apêndice C) com as condições exatas listadas no
  manual, não uma lista genérica de "erro matemático".

## NOT IMPLEMENTED (por design, não por omissão)

- **Modo ENG (engenharia)**: não existe no HP-12C Classic. Busca no texto
  completo do manual (211 páginas) não encontrou nenhuma ocorrência de "ENG"
  como modo de display. Implementá-lo seria inventar um comportamento que o
  hardware alvo não tem.
- **TVM com período fracionário (odd period)**: o manual documenta duas
  variantes (juros simples ou compostos no período fracionário) mas não
  deixa claro qual a tecla usa por padrão sem período explícito. Em vez de
  adivinhar, apenas o caminho sem período fracionário está implementado.
- **Bonds com cupom não-semestral / base 30/360 para bonds**: só o caso
  semestral actual/actual está implementado.
- **Separador decimal vírgula/ponto configurável** (recurso de hardware via
  segurar `.` ao ligar): não implementado, baixa prioridade funcional.
- **`f CLx` segurado mostrando a mantissa completa**: reconhecido como tecla
  mas não implementado (é um recurso de UI, não de cálculo).
- **Edição de um fluxo de caixa específico por índice** (armazenar `j` em
  `n` depois `g Nj` para corrigir a repetição de um CFj já lançado, sem
  refazer a lista inteira — descrito na p.61-62): não implementado; o
  simulador só grava CFo/CFj sequencialmente. Encontrado durante a auditoria,
  registrado aqui em vez de ser deixado de fora silenciosamente.
- **`g` + tecla = MEM** (mapa de memória: linhas de programa usadas vs.
  registradores disponíveis): reconhecido (Programming Key Index, p.206) mas
  não implementado — só consulta informativa, não afeta cálculo.

## SIMPLIFICAÇÕES DOCUMENTADAS

- **Layout físico do teclado**: o teclado "core" (n/i/PV/PMT/FV, dígitos,
  aritmética, ENTER, CHS, EEX, STO, RCL, GTO, f, g, x≷y, R↓, Σ+, %/Δ%/%T,
  CLx) segue a disposição real do 12C. As atribuições `f`/`g` da linha
  financeira (`f n`=AMORT, `f i`=INT, `f PV`=NPV, `f PMT`=RND, `f FV`=IRR;
  `g n`=12×, `g i`=12÷, `g PV`=CFo, `g PMT`=CFj, `g FV`=Nj, `g CHS`=DATE,
  `g 7`=BEG, `g 8`=END) foram confirmadas contra uma foto de referência
  fornecida pelo usuário (não uma imagem proprietária da HP redistribuída —
  apenas usada para conferência de posição/rótulo, como qualquer referência
  de manual). Funções ainda sem posição física confirmada (matemática
  avançada, estatística, depreciação, bonds, calendário D.MY/M.DY, `g 9`=MEM
  — não implementado, programação, CLEAR REG/FIN/Σ/PRGM) continuam num
  painel "Funções Adicionais" separado — mais honesto do que arriscar uma
  posição física não verificada para essas teclas no corpo principal.
  Paleta de cores (corpo bege/creme, teclas quase pretas, dourado/azul)
  também ajustada para a referência.

  **2026-09-12 — auditoria de posição física (SL/SOYD/DB/PRICE/YTM):** o
  manual documenta (p.91) um "keycode" de 2 dígitos (linha, posição) exibido
  para cada tecla gravada em um programa. Isso permite confirmar posição
  **sem depender da foto**, cruzando citações independentes do próprio texto:
  - **DB (`f #`) — CONFIRMADA**: duas listagens de programa (p.68-69, p.141)
    mostram `f# ... 42 25`; separadamente, o texto da p.91 afirma
    explicitamente que a tecla `%` (glifo `b`) tem keycode `25` (linha2,
    posição5). As duas citações batem exatamente na mesma tecla — **DB é
    `f` + a tecla `%`**, independente da foto.
  - **SL (`f V`) e SOYD (`f Ý`) — POSIÇÃO CONFIRMADA, TECLA-BASE NÃO
    CONFIRMADA**: as mesmas listagens mostram `fV...42 23` e `fÝ...42 24`
    (linha2, posições 3 e 4 — adjacentes à posição 5 da tecla `%`, batendo
    com o agrupamento visual "%T Δ% %" da foto). Mas nenhuma listagem do
    manual usa `%T` ou `Δ%` isoladamente para confirmar de forma
    independente QUAL rótulo sem shift ocupa essas duas posições — a
    identificação desses dois rótulos continua apoiada na foto, não em
    citação textual cruzada.
  - **PRICE (`f E`) e YTM (`f S`) — NÃO CONFIRMADAS**: nenhuma listagem de
    programa no manual usa as teclas nativas `E`/`S` (o programa de bonds
    30/360 da p.163-166 reimplementa tudo do zero com rótulo de usuário, sem
    tocar nessas teclas). Sem keycode para cruzar, e sem poder reabrir a foto
    para conferência pixel a pixel, a posição física permanece **NÃO
    CONFIRMADA**. Layout não alterado a pedido explícito do usuário.
- **Registro de `i`**: digitado/exibido como percentual (ex.: `10` para 10%),
  convertido para decimal internamente antes de entrar nas fórmulas do
  Apêndice D (que definem i "expressa como decimal"). Comportamento
  confirmado pela nota de rodapé da p.172 sobre `100000 PV` vs `100000 PV FV`.
- ~~Bonds — convenção de registradores~~: **não é mais uma simplificação**.
  Confirmado no texto do manual (p.66-67): cupom via `PMT`, yield via `i`,
  liquidação=Y, vencimento=X; preço-alvo do YTM via `PV` (não `FV` — um
  engano inicial desta implementação, corrigido na auditoria). O que
  permanece não confirmado é apenas a POSIÇÃO FÍSICA da tecla `f`+`E`/`f`+`S`
  no teclado (ver "Layout físico do teclado" acima).
- **Solução iterativa de `i` e de YTM**: por bisseção, não o algoritmo do
  firmware (não documentado publicamente). Convergem ao mesmo resultado com
  10 dígitos significativos nos casos testados, mas não são bit-exatos ao
  hardware.
- **ΔDYS actual-basis**: calculado com `datetime.date` do Python em vez de
  reimplementar a fórmula polinomial do Apêndice D, cuja correção de "anos
  de século não são bissextos" não vem com a aritmética exata no texto
  extraído. `datetime` já implementa o calendário gregoriano correto (o
  mesmo alvo que a correção do manual busca), então é usado diretamente.
- **Precisão interna**: `Decimal` de 40 dígitos de working precision por
  operação, com arredondamento explícito para 10 dígitos significativos após
  cada operação (mimetizando o registrador BCD de 10 dígitos do hardware,
  não IEEE-754 binário). Isso reproduz overflow/underflow/arredondamento
  observáveis, mas não é uma emulação bit-exata da BCD real.

## Aferição

Todos os 72 casos de teste são aferidos **contra o manual** (fórmulas do
Apêndice D, exemplos do próprio texto, ou identidades matematicamente
verificáveis como o par-bond). **Nenhum caso foi aferido contra uma HP-12C
física.** Não declaro "100% compatível" — apenas "consistente com a
especificação documental do fabricante nos pontos testados". Se/quando o
usuário fornecer saídas de um aparelho real, essas se tornam a referência
prioritária (ver política de divergência em `docs/ANALYSIS.md`).

## Divergências conhecidas e não resolvidas

Nenhuma no momento — toda discrepância encontrada durante o desenvolvimento
(ver histórico de commits/checkpoints) foi investigada e corrigida na
implementação, nunca "resolvida" ajustando o valor esperado sem justificativa
documental.
