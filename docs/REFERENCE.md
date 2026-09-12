# Fonte de referência

**Documento único, primário, oficial**: *hp 12c financial calculator user's
guide*, Edition 4, HP Part Number 0012C-90001 — o manual linkado pelo usuário
no briefing (`h10032.www1.hp.com/ctg/Manual/c00363319.pdf`). 211 páginas,
extraídas e lidas integralmente (texto, não apenas índice) durante a análise
em `docs/ANALYSIS.md`.

Nenhuma outra "calculadora financeira genérica" foi usada como referência de
comportamento. Onde este simulador usa uma biblioteca padrão (`datetime` do
Python para diferença de dias em base "actual"), isso está documentado
explicitamente em `docs/COMPATIBILITY.md` com a justificativa de por que
substitui, sem perda de fidelidade, a fórmula do manual naquele ponto
específico.

## Mapa: seção do manual → módulo do código

| Assunto | Seção/Apêndice do manual | Módulo |
|---|---|---|
| Pilha RPN, LAST X, stack lift/drop | Apêndice A | `src/hp12c/stack.py` |
| Erros 0–9 | Apêndice C | `src/hp12c/errors.py`, disparados em todo `engine.py` |
| TVM, amortização, juros simples, NPV/IRR, bonds, depreciação | Apêndice D | `src/hp12c/financial.py` |
| Calendário (actual e 30/360) | Apêndice D | `src/hp12c/calendar_fns.py` |
| Estatística (fórmulas) | Apêndice D + Seção 6 | `src/hp12c/statistics_fns.py` |
| Memória de programa (8+20, expansão, limite 99) | Seção 8 | `src/hp12c/memory.py` |
| Display (Standard/Científico, arredondamento, overflow/underflow) | Seção 5 | `src/hp12c/display.py` |
| Nomes/descrições de cada tecla | Function Key Index / Programming Key Index | `src/hp12c/engine.py` (dispatcher) |

## Por que não há aferição de hardware ainda

O briefing original pede aferição contra uma HP-12C física quando disponível,
e trata isso como prioritário sobre qualquer suposição da implementação. Até
o momento, nenhum resultado de hardware real foi fornecido — os 58 casos em
`tests/hp12c-reference.json` são todos derivados do próprio manual (fórmulas
do Apêndice D ou exemplos numéricos já resolvidos no texto) ou de identidades
matemáticas independentemente verificáveis (ex.: bond ao par ⇒ preço = 100).
Isso é uma aferição **documental**, não uma aferição de **hardware** — a
distinção é feita explicitamente em `docs/COMPATIBILITY.md` para não
apresentar precisão que ainda não foi conquistada.
