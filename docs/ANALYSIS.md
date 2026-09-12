# Análise pré-implementação — HP-12C Classic

Fonte primária: *hp 12c financial calculator user's guide*, Edition 4, HP Part Number
0012C-90001 (manual oficial linkado pelo usuário, extraído e lido página a página).
Todas as regras abaixo foram confirmadas no texto do manual, não em memória genérica de
"calculadora financeira". Onde o manual é omisso, isso é declarado explicitamente.

## 1. Inventário de teclas (mapa físico → função)

| Tecla física | Direto | `f` (dourado) | `g` (azul) |
|---|---|---|---|
| `n` | n (períodos) | — | 12× (n = 12·x, vai para reg. n) |
| `i` | i (taxa) | — | 12÷ (i = x/12, vai para reg. i) |
| `PV` | PV | — | CFo (fluxo de caixa inicial) |
| `PMT` | PMT | — | CFj (fluxo de caixa j) |
| `FV` | FV | — | Nj (nº de repetições do fluxo) |
| `CHS` | troca sinal | — | — |
| `7` | 7 | CLEAR REG | — |
| `8` | 8 | CLEAR FIN | — |
| `9` | 9 | CLEAR PRGM | — |
| `÷` | ÷ | — | x≤y / testes condicionais (programação) |
| `4` `5` `6` | dígitos | — | — |
| `×` | × | — | — |
| `1` | 1 | AMORT | INT (juros simples) |
| `2` | 2 | %T | %Δ |
| `3` | 3 | NPV | IRR |
| `-` `+` | aritmética | — | — |
| `RCL` | RCL | — | — |
| `STO` | STO | — | — |
| `EEX` | EEX | — | — |
| `CLx` | Clear X | — | — |
| `÷ family` (Σ+, R↓, x≷y, ENTER) | conforme legenda | ver abaixo | ver abaixo |
| `ENTER` | ENTER↑ | — | LSTx |
| `x≷y` | troca X/Y | — | — |
| `R↓` | roll down | — | — |
| `Σ+` | acumula estatística | — | Σ- (remove) |
| `1/x` | recíproco | — | — |
| `√x` | raiz | — | — |
| `y^x` | potência | — | — |
| `%` | x% de y | — | — |
| `.` | ponto decimal | FIX (casas decimais) | — |
| `Σ+`..`E` (labels A-E) | rótulos de programa | — | GTO destino |
| `R/S` | run/stop programa | — | P/R (programa/execução) |
| `GTO` | vai para linha | — | mapa de memória (`g MEM`) |
| `f` | prefixo dourado | — | — |
| `g` | prefixo azul | — | — |
| `ON` | liga/desliga | — | — |

Funções `f`/`g` adicionais relevantes: `f 0-9` = casas decimais fixas (FIX);
`f .` = notação científica (SCI); `f CLx` (mantido pressionado) = mostra mantissa
completa de 10 dígitos; `g D.MY` / `g M.DY` = formato de data; `g BEG` / `f END`
(nomes reais: `g 7`=BEG, `f 8` na verdade é END — confirmado via Function Key Index,
ver `E`/BEG glyphs) = modo de pagamento antecipado/postecipado.

## 2. Estados da máquina

- **Ligado/Desligado**: memória contínua preserva stack, registradores, programa,
  formato de display, formato de data, modo de pagamento.
- **Reset de memória contínua**: (a) automático se energia interrompida — mostra
  `Pr Error` ao ligar; (b) manual: desligado, segurar `-`, pressionar `ON`.
  Resultado: todos os registradores zerados; programa = 8 linhas `GTO 00`;
  display = padrão 2 casas; data = M.DY; pagamento = End.
- **Run mode vs Program mode**: `f P/R` alterna. Ao voltar para Run, ponteiro de
  programa volta para linha 00.
- **Erro**: qualquer tecla limpa a mensagem de erro e restaura o estado anterior à
  operação (não executa a função da tecla que limpou o erro).
- **CLEAR x / CLEAR REG / CLEAR FIN / CLEAR Σ / CLEAR PRGM / CLEAR PREFIX**: são
  operações independentes, cada uma limpando um subconjunto diferente — **nunca
  assumir que uma limpa as outras** (requisito explícito do usuário, confirmado
  pelo manual: CLEAR REG não apaga o programa; CLx não apaga registradores).

## 3. Pilha RPN (Appendix A — fonte primária, não paráfrase)

Registradores: X (display), Y, Z, T, mais LAST X (não é pilha, é retenção).

Regras exatas:
1. `ENTER↑`: copia X→Y (stack lift), termina entrada de dígitos. Pilha sempre sobe.
2. **Stack lift é suprimido** (o próximo número digitado substitui X em vez de
   empurrar a pilha) se a última tecla pressionada foi uma destas 6: `ENTER↑`,
   `CLx`, `Σ+`, `Σ-`, `12×`, `12÷`. (As duas últimas são específicas do 12C —
   ambas armazenam diretamente em registrador financeiro, mesma razão pela qual
   armazenar em registrador financeiro via `STO n/i/PV/PMT/FV` também suprime o
   próximo lift.)
3. **Funções de 1 número** (1/x, √x, LN, e^x, n!, RND, INTG, FRAC, CHS): operam só
   em X, resultado vai para X, X anterior vai para LAST X, pilha **não** dropa
   (Y/Z/T inalterados).
4. **Funções de 2 números** (+, −, ×, ÷, y^x): usam X e Y, resultado em X, X
   anterior → LAST X, pilha **dropa** (Z→Y, T→Z e T permanece — permite constante).
5. **Funções de porcentagem** (%, Δ%, %T): resultado em X, X anterior → LAST X,
   pilha **não dropa nem sobe** — Y/Z/T inalterados. Isso é diferente de uma função
   binária normal.
6. **Funções financeiras/calendário quando calculam** (n, i, PV, PMT, FV, NPV, IRR,
   DATE, ΔDYS, INT, PRICE, YTM, DEP): cada uma tem efeito próprio documentado numa
   tabela específica (ver Appendix A) — não seguem a regra binária genérica.
7. `x≷y`: troca X↔Y, não mexe em Z/T, não é lift nem drop.
8. `R↓`: rotaciona X→T, T→Z, Z→Y, Y→X (para baixo circular).
9. `LSTx` (`g` + ENTER): lift da pilha (a menos que a tecla anterior suprima lift),
   copia LAST X para X.

## 4. Formatos de display

- Padrão de fábrica / após reset: **Standard**, 2 casas decimais.
- `f 0`–`f 9`: Standard com N casas decimais (arredondamento *display-only*,
  **o valor interno de 10 dígitos não muda**, exceto quando a própria tecla é
  uma das que arredondam de fato o valor interno: `f RND`, `AMORT`, `SL`, `SOYD`,
  `DB`).
- Regra de arredondamento: dígito seguinte 5–9 arredonda para cima; 0–4 trunca
  (round-half-up, não banker's rounding).
- `f .`: notação científica — mantissa de 7 dígitos significativos + expoente de
  2 dígitos com sinal (espaço = positivo, `-` = negativo).
- **Não existe modo ENG (engenharia) no 12C Classic** — busquei "ENG" no manual
  completo (211 páginas) e não há nenhuma ocorrência. Isso é uma feature de
  outras calculadoras HP (15C/16C) ou de suítes financeiras genéricas, não do
  12C. **Marcarei como NOT IMPLEMENTED** em vez de inventar um modo que não existe
  no hardware alvo.
- Overflow: |resultado| > 9.999999999×10^99 → cálculo é interrompido e mostra
  ±9.999999999 99 (não é "Error", é clamp).
- Underflow: |resultado| < 10^-99 (≠0) → valor tratado como 0, cálculo continua
  normalmente (sem interrupção).
- `f CLx` mantido pressionado: mostra mantissa completa (10 dígitos) enquanto
  pressionado.
- Separador decimal ponto/vírgula: alternável (recurso documentado de hardware via
  segurar `.` ao ligar) — baixa prioridade, implementar se sobrar tempo.

## 5. Funções financeiras (Appendix D — fórmulas oficiais)

- **TVM sem período fracionário**:
  `PV·(1+i)^n + PMT·(1+i·S)·[(1+i)^n − 1]/i + FV = 0`, S=1 (Begin) ou 0 (End).
- **TVM com período fracionário (odd period)**: duas variantes documentadas —
  juros simples no período fracionário, ou juros compostos no período fracionário
  — fórmulas distintas envolvendo INTG(n)/FRAC(n). O 12C físico decide qual usar
  conforme o contexto (não fica 100% explícito no manual qual é o padrão da tecla
  simples `n`/`i`/`PV`/`PMT`/`FV`; vou implementar a versão sem período
  fracionário como caminho principal, testado, e marcar odd-period como
  **NOT VERIFIED** até haver fixtures de hardware real).
- **Solução iterativa de `i`**: o manual não publica o algoritmo exato de
  convergência do firmware. Implementarei Newton-Raphson com fallback de bisseção,
  documentado como **não bit-exato ao firmware**, mas convergente ao mesmo
  resultado (10 dígitos significativos) nos casos testáveis.
- **n é sempre arredondado para cima** para o próximo inteiro (documentado
  explicitamente).
- **Amortização** (`f n` = AMORT, CONFIRMADO p.54-55): `INT₁ = |PV₀·i|_RND ·
  sinal(PMT)` (ou 0 se j=1 e Begin), `PRN = PMT − INT`, `PV_novo = PV + PRN`.
  **O arredondamento `_RND` é para as CASAS DECIMAIS DO DISPLAY ATUAL (ex.: 2),
  não para 10 dígitos significativos** — validado bit-a-bit contra o exemplo
  do manual (hipoteca de 25 anos, 13.25%, $50.000, PMT=-573.35: ano 1 =
  -6.608,89/-271,31; ano 2 = -6.570,72/-309,48). O registrador `n`
  **ACUMULA** períodos amortizados (começa em 0 após CLEAR FIN, soma a cada
  chamada) — confirmado pelo próprio manual (":n 12.00 Total number of
  payments amortized" após amortizar 12 períodos, não um termo decrescente).
  Registradores de saída: X=INT, Y=PRN, Z=X-anterior(contagem), T=Y-anterior
  (Apêndice A p.175, não é um lift genérico).
- **Juros simples** (`f i` = INT, CONFIRMADO p.33-34): `n` é NÚMERO DE DIAS
  (não anos), `i` é a taxa ANUAL. `I360 = n·(−PV)·i/360`, `I365 =
  n·(−PV)·i/365` — o `−PV` (não `PV`) é necessário porque o principal é
  guardado negativo (convenção de sinal) mas o juro exibido é positivo;
  validado bit-a-bit contra o exemplo do manual ($450, 60 dias, 7% →
  5,25/5,18). Registradores de saída: X=INT360, Y=−PV, Z=INT365, T=X-anterior
  — confirmado tanto pela tabela do Apêndice A quanto pela sequência real
  "f INT R↓ x≷y" do manual para ver a base de 365 dias.
- **NPV**: soma de CFj/(1+i)^j, j=0..n, suporta Nj (repetições) até 20 fluxos
  distintos armazenados.
- **IRR**: raiz de NPV(i)=0. Erro 3 = não converge; Erro 7 = não há mudança de
  sinal nos fluxos (sem solução).
- **Bonds** (`f` + tecla não identificada = PRICE/YTM, shift CONFIRMADO
  p.66-67, tecla física NÃO CONFIRMADA): yield via `i`, cupom via `PMT`,
  liquidação=Y, vencimento=X. PRICE grava o resultado também no registrador
  `PV` (confirmado: "shown in the display and also is stored in the PV
  register"); juros acumulados ficam em Y (via x≷y). YTM lê o preço-alvo do
  registrador `PV` (não `FV` — corrigido de um engano inicial) e grava o
  resultado em `i`. Validado bit-a-bit/display contra os dois exemplos do
  manual (yield 8.25%→preço 87.62/90.31; preço 88.375→yield 8.15%).
- **Depreciação** (`f` + tecla não identificada = SL/SOYD/DB, shift
  CONFIRMADO p.68 "fV"/"fÝ"/"f#", tecla física NÃO CONFIRMADA): custo via
  `PV`, valor residual via `FV`, vida útil via `n`, fator (DB) via `i`
  (percentual); só o número do ano é digitado direto em X. Fórmulas de tecla,
  sem período parcial: SL: `DPN=(SBV−SAL)/L`. SOYD: `DPN=(L−j+1)/SOYD·(SBV−SAL)`,
  `SOYD=W(W+1)/2+WF`. DB: `DPNⱼ=RBVⱼ₋₁·FACT/100/L`, com `RBV` persistido no
  registrador `PV` entre chamadas (mesmo padrão da amortização). Saída:
  X=DPN, Y=RDV (valor residual **menos** valor de salvamento, não o valor
  contábil puro). Validado bit-a-bit contra o exemplo do manual de
  declining-balance (custo 10.000/salvamento 500/vida 5/fator 200%: anos 1-3
  = 4.000/2.400/1.440, RDV = 5.500/3.100/1.660).
- **Conversão de taxas**: `EFF=(1+NOM/C)^C−1` (composição finita),
  `EFF=e^NOM−1` (contínua) — presentes no apêndice, teclas dedicadas não
  claramente identificadas no Function Key Index; implementar como utilitário,
  marcar acesso via tecla como NOT VERIFIED.

## 6. Calendário

- **Base Actual**: `ΔDYS = f(DT2) − f(DT1)`, onde
  `f(DT) = 365·ano + 31·(mês−1) + dia + INTG(z/4) − x`, com regra de ano
  bissexto por século (século múltiplo de 100 não é bissexto, exceto múltiplo de
  400 — nota do manual: "century (but not millennium) years are not considered
  leap years", ou seja, replica o calendário Gregoriano padrão).
- **Base 30/360**: fórmula própria com regras de dia 31 tratado como 30 —
  documentada exatamente no Appendix D.
- Formatos D.MY / M.DY selecionáveis via `g` shift, não programável.
- Erro 8: formato de data inválido, ou (para DATE) ultrapassa capacidade da
  calculadora, ou (bonds) mais de 500 anos entre datas / vencimento antes de
  liquidação / vencimento sem cupom correspondente 6 meses antes (regra especial
  para dia 29/30/31 de certos meses).

## 7. Estatística

Registradores R1..R6 = n, Σx, Σy, Σx², Σy², Σxy (confirmado pela condição de
Erro 2, que referencia exatamente essas somas).
- Média: `x̄=Σx/n`, `ȳ=Σy/n`.
- Média ponderada: `x̄w = Σ(peso·item)/Σpeso`. Convenção CONFIRMADA pelo
  exemplo do manual (p.81-82, "item ENTER peso Σ+"): X=peso, Y=item no
  momento do Σ+, logo `Σx=Σpeso`, `Σy=Σitem`, `Σxy=Σ(peso·item)`, e
  `x̄w=Σxy/Σx` (não `/Σy` — uma versão anterior desta análise tinha a
  convenção invertida; corrigido e validado bit-a-bit contra o exemplo dos
  4 postos de gasolina, resultado 1.19/galão).
- Desvio padrão amostral: `sx=√[(nΣx²−(Σx)²)/(n(n−1))]` (mesmo para y). Requer
  n≥2 (Erro 2 se n≤1 ou termo negativo por cancelamento numérico).
- Regressão linear: `ŷ=A+Bx`, `B=(nΣxy−ΣxΣy)/(nΣx²−(Σx)²)`, `A=ȳ−Bx̄`;
  inverso `x̂=(y−A)/B`; coeficiente de correlação `r` com fórmula própria
  (raiz de produto de variâncias).

## 8. Memória e registradores

- Registradores de dados: `R0`–`R9` e `R.0`–`R.9` (20 no total, default).
- `STO`/`RCL` aceitam registrador direto, aritmética de registrador
  (`STO +/-/×/÷ n`), e registradores financeiros como destino.
- Erro 4/6: aritmética de registrador não é permitida em `R5`-`R9`/`R.0`-`R.9`
  quando parte deles foi convertida em linhas de programa; registrador
  inexistente ou convertido → Erro 6.
- `CLEAR REG`: zera X,Y,Z,T + todos storage + estatística + financeiros (mas
  **não** programa).
- `CLEAR FIN`: zera apenas registradores financeiros (n,i,PV,PMT,FV).
- `CLEAR Σ`: zera R1-R6 + stack.
- `CLEAR PRGM`: reseta memória de programa a 8 linhas `GTO 00`, não mexe em dados.

## 9. Programação

- Memória total combinável: **8 linhas de programa fixas** + **20 registradores
  de dados**, com conversão dinâmica: a cada bloco de 7 instruções além da 8ª, o
  **último registrador de dados disponível** (começando por `R.9`) é convertido
  em 7 novas linhas de programa (perdendo o dado nele armazenado).
- Máximo: **99 linhas de programa**, consumindo 13 registradores
  (`8 + 13×7 = 99`), sobrando `R0`-`R6` (7 registradores) para dados.
- Linha 00 contém instrução oculta de "halt"; linhas vazias contêm `GTO 00`.
- `f P/R`: alterna Program↔Run; ao voltar a Run, ponteiro vai para linha 00.
- `R/S`: roda/pausa a partir da linha atual.
- `GTO nn`: desvia para linha; rótulos `0`-`9`, `.0`-`.9`, `A`-`E` também servem
  como destino de `GTO`/chamada implícita.
- Testes condicionais (`x≤y`,`x=0`, etc. sob tecla dedicada com sufixo 0-9):
  pula a próxima linha se falso — implementarei o conjunto completo (`x=0`,
  `x≠0`, `x>0`, `x<0`, `x≥0`, `x≤0`, `x=y`, `x≠y`, `x>y`, `x<y`, `x≥y`, `x≤y`).
- Erro 4: mais de 99 linhas, ou `GTO` para linha inexistente.

## 10. Erros (Appendix C — completo, 10 categorias)

Erro 0 Matemática (÷0, ln(x≤0), √(x<0), y^x inválido, x! não-inteiro/negativo,
etc.) · Erro 1 Overflow de registrador de armazenamento (aritmética STO
resultando em |valor|>9.999999999e99) · Erro 2 Estatística (n=0, Σx=0 onde
necessário, termo de variância negativo, n≤1 para desvio padrão) · Erro 3 IRR
sem convergência · Erro 4 Memória (>99 linhas, GTO inválido, aritmética de
registrador inválida) · Erro 5 Juros compostos (condições sem solução —
PMT≤−PV·i, i≤−100%, etc.) · Erro 6 Registradores de armazenamento inexistentes/
convertidos · Erro 7 IRR sem mudança de sinal nos fluxos · Erro 8 Calendário
(data/formato inválido, excede capacidade, regras de cupom) · Erro 9 Serviço
(falha de hardware/autoteste — não aplicável a um simulador; vou mapear para
uma condição informativa apenas).

## 11. Plano de testes (`tests/hp12c-reference.json`)

Categorias obrigatórias A–J do briefing, com casos derivados diretamente dos
exemplos do próprio manual sempre que disponíveis (essas sequências e resultados
JÁ SÃO a referência oficial — quando o usuário fornecer resultados de hardware
físico, estes serão tratados como fixtures adicionais e terão prioridade sobre
qualquer suposição minha em caso de divergência).

## 12. Escopo desta primeira entrega (transparência, não é "100% compatível")

Implementado e testado nesta rodada: pilha RPN completa, aritmética, percentuais,
TVM (caso sem período fracionário), amortização, juros simples, NPV/IRR,
depreciação (fórmulas de tecla), calendário (actual + 30/360), estatística
completa, registradores/STO/RCL, programação básica (GTO, R/S, rótulos, testes
condicionais, expansão de memória).

Explicitamente **NOT IMPLEMENTED**: modo ENG (não existe no hardware alvo),
bonds com cupom não-semestral, MIRR (não é tecla nativa do 12C, é exemplo de
"solutions"), separador decimal vírgula/ponto configurável, `f CLx` segurado
mostrando mantissa (baixa prioridade de UI).

Explicitamente **NOT VERIFIED contra hardware físico**: qualquer resultado
numérico até que o usuário forneça saídas de uma HP-12C real para comparação —
os testes atuais validam contra as fórmulas e exemplos do próprio manual, o que
é uma aferição documental, não uma aferição de hardware.
