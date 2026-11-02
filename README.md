# CalcudokuPress

Build print-ready **calcudoku (mathdoku) puzzle books for Amazon KDP** where every puzzle is *proven* to have exactly one solution.

## Why

A calcudoku puzzle is only as good as its cages. Generate a grid, scribble cage borders, compute targets loosely — and half your book has two solutions or none, which readers find long before you do. CalcudokuPress does it in the order that can't lie:

1. A complete Latin square is generated.
2. The grid is partitioned into contiguous cages (1–4 cells), and each cage's operation and target are computed **from the true values** — so every target is reachable by construction.
3. An **independent solver** (MRV backtracking with cage sum/product pruning, written separately from the generator) counts the puzzle's solutions. If the count is not exactly one, the partition is discarded and redrawn — a puzzle is printed only when the count is exactly one and the found solution equals the generated grid.

## Use

**App (Windows):** launch `CalcudokuPress.exe`, choose the puzzle count, difficulty (Easy 4×4 / Medium 5×5 / Hard 6×6, or Mixed rotating all three) and a seed, click **Build the book**. Output: `calcudoku_book.pdf` in a `calcudokupress_out` folder — title page, one puzzle per page with heavy cage borders and cage labels (e.g. `12+`, `3-`, `2÷`), then full solutions. 8.5×11in (612×792pt).

**Command line:** `python calcudoku_press.py out/ --puzzles=100 --difficulty=Mixed --seed=42`

A 6-puzzle sample book is included (`sample_book.pdf`).

Operations: addition and multiplication on all cage sizes; subtraction and division on 2-cell cages (Medium/Hard), where the target is always exact. Single-cell cages print their value as the target.

## Verified

Acceptance test (7/7 PASS, `test/acceptance_results.txt`): a 6-puzzle mixed book (4×4/5×5/6×6) re-verified by an independent checker that rebuilds the constraints from the printed cage data alone, searching cage-by-cage instead of cell-by-cell — every puzzle exactly one solution, equal to the printed grid; cages partition the grid and are all contiguous; every cage target arithmetically true of its solution; PDF exactly 14 pages at 612×792pt; whole book in about half a second; deterministic for a fixed seed.

## Scope

Classic calcudoku on 4×4–6×6 grids. This tool makes calcudoku/mathdoku puzzles — generic descriptive names for a public-domain puzzle form; it is not affiliated with any branded puzzle franchise. Deterministic seeds make series production repeatable. 100% local — no uploads, no accounts, no per-book fees.

## Build from source

`pip install pyinstaller reportlab`, then `pyinstaller calcudokupress.spec`. Or push to GitHub and let the included Actions workflow build the Windows package.
