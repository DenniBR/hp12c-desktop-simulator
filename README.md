# HP-12C Classic — Simulador Desktop (não oficial)

Simulador funcional da calculadora financeira **HP-12C Classic**, implementado em
Python (motor RPN + financeiro) com interface desktop Tkinter, empacotado como
`.exe` standalone via PyInstaller.

Este projeto **não é afiliado à HP**. Não usa firmware, ROM, imagens ou ativos
proprietários da HP — a lógica foi reconstruída a partir do manual oficial
público (*hp 12c user's guide*, Edition 4) e o visual foi desenhado
originalmente.

## Rodando o executável

```
dist\HP12C-Simulator.exe
```

Standalone, offline, sem instalação. Se `dist/` não existir, veja
[Build](#build) abaixo.

## Estrutura

```
src/hp12c/        motor: pilha RPN, financeiro, calendário, estatística,
                  memória, display, erros (sem UI, 100% testável isolado)
src/ui/           interface Tkinter (teclado + LCD em 7 segmentos)
src/main.py       ponto de entrada
tests/            suíte de referência (JSON) + test runner
docs/             análise pré-implementação, compatibilidade, referências
assets/           ícone do aplicativo (original, não é o logo da HP)
scripts/          geração do ícone
```

## Testes

```
python tests/run_tests.py
```

Imprime EXPECTED/ACTUAL/MATCH por caso e um resumo por categoria (A–L).
Estado atual: **112/112 casos passando** — ver [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)
para o que isso significa (e não significa) em termos de aferição contra
hardware real.

## Requisitos de desenvolvimento

- Python 3.11+ (só biblioteca padrão: `tkinter`, `decimal`, `datetime`, etc. —
  o app em si não tem dependências externas).
- `pyinstaller` (`pip install pyinstaller`) para gerar o `.exe`.
- `Pillow` (`pip install pillow`) **somente** se for regenerar `assets/icon.ico`
  via `scripts/make_icon.py` — não é usado pelo app.
- [Inno Setup](https://jrsoftware.org/isinfo.php) **somente** se for gerar o
  instalador opcional (`Setup.exe`) — não é necessário para o `.exe` em si.

## Build

```
python scripts/make_icon.py    # gera assets/icon.ico (se ainda não existir)
python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "HP12C-Simulator" --icon "assets/icon.ico" ^
  --add-data "assets/icon.ico;assets" --paths "src" "src/main.py"
```

Gera `dist/HP12C-Simulator.exe` (~13 MB, standalone, sem dependências externas).
A receita exata também está em `HP12C-Simulator.spec` (`pyinstaller HP12C-Simulator.spec`
funciona de forma equivalente).

### Instalador (opcional)

Com o [Inno Setup](https://jrsoftware.org/isinfo.php) instalado:

```
ISCC installer\setup.iss
```

Gera `installer/Output/HP12C-Simulator-Setup.exe`. Requer que `dist/HP12C-Simulator.exe`
já exista (rode o Build acima primeiro).

## Documentação

- [docs/ANALYSIS.md](docs/ANALYSIS.md) — inventário de teclas/funções/estados
  extraído do manual oficial, feito antes da implementação.
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — o que está implementado,
  o que não está, e o que é "verificado contra o manual" vs "verificado
  contra hardware real" (ainda não há a segunda categoria).
- [docs/REFERENCE.md](docs/REFERENCE.md) — fonte primária usada e como cada
  categoria de função foi derivada dela.

## Licença / propriedade intelectual

- Este projeto é licenciado sob a [Licença MIT](LICENSE) — Copyright (c) 2026 DenniBR.
- Código e visual originais deste repositório.
- `assets/icon.ico`: gerado originalmente por `scripts/make_icon.py` (formas
  desenhadas via Pillow) — não é o logo da HP nem de terceiros.
- Fontes usadas na interface (`Segoe UI`) são fontes do sistema operacional,
  não embutidas no repositório.
- Ferramentas de build usadas mas não distribuídas neste repositório:
  [PyInstaller](https://pyinstaller.org/) (licença GPL com exceção para o
  bootloader, permitindo distribuir o `.exe` gerado sob qualquer licença) e
  [Inno Setup](https://jrsoftware.org/isinfo.php) (uso livre, inclusive
  comercial). Nenhum binário dessas ferramentas é versionado neste repositório.
- HP-12C é marca registrada da HP Inc.; este projeto não reivindica afiliação
  nem reproduz firmware, ROM ou ativos proprietários da HP.
