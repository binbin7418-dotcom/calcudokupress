#!/usr/bin/env python3
"""CalcudokuPress engine: Calcudoku (Mathdoku) puzzle books (PDF) where
every puzzle is PROVEN to have exactly one solution.

How a puzzle is made: a complete Latin square is generated, partitioned
into cages, and each cage gets an operation whose target is computed
FROM the true values (so the target is always reachable). An independent
solver -- MRV backtracking with cage partial-sum/product pruning,
written separately from the generator -- then counts solutions. If the
count is not exactly one, the partition is discarded and redrawn; a
puzzle is never printed until the count is exactly one and the found
solution equals the generated grid.

Note: this tool generates calcudoku puzzles (also called mathdoku). It
is not affiliated with any branded puzzle franchise.

Deterministic for a fixed seed. 100% local. Requires: reportlab.

Usage:
    python calcudoku_press.py out/ [--puzzles 20] [--difficulty Mixed]
                              [--seed 42]
"""
import os
import random
import sys

PAGE_W, PAGE_H = 612, 792
SIZES = {"Easy": 4, "Medium": 5, "Hard": 6}
MAX_PARTITION_TRIES = 60

# ------------------------------------------------------------ Latin fill

def fill_latin(rng, n):
    g = [[0] * n for _ in range(n)]

    def rec(pos):
        if pos == n * n:
            return True
        r, c = divmod(pos, n)
        opts = [v for v in range(1, n + 1)
                if v not in g[r] and v not in [g[i][c] for i in range(n)]]
        rng.shuffle(opts)
        for v in opts:
            g[r][c] = v
            if rec(pos + 1):
                return True
            g[r][c] = 0
        return False

    rec(0)
    return g

# --------------------------------------------------------- cage partition

def partition(rng, n):
    """Random contiguous cages of size 1..4 covering the grid."""
    owner = [[-1] * n for _ in range(n)]
    cages = []
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    for r, c in cells:
        if owner[r][c] != -1:
            continue
        size = rng.choices([1, 2, 3, 4], weights=[12, 40, 30, 18])[0]
        cage = [(r, c)]
        owner[r][c] = len(cages)
        frontier = [(r, c)]
        while len(cage) < size and frontier:
            cr, cc = rng.choice(frontier)
            nbrs = [(cr + dr, cc + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= cr + dr < n and 0 <= cc + dc < n
                    and owner[cr + dr][cc + dc] == -1]
            if not nbrs:
                frontier.remove((cr, cc))
                continue
            nr, nc = rng.choice(nbrs)
            owner[nr][nc] = len(cages)
            cage.append((nr, nc))
            frontier.append((nr, nc))
        cages.append(cage)
    return cages, owner

def assign_ops(rng, sol, cages, allow_div):
    """Each cage: (cells, op, target) with target computed from truth."""
    out = []
    for cage in cages:
        vals = [sol[r][c] for r, c in cage]
        if len(vals) == 1:
            out.append((cage, "", vals[0]))
            continue
        ops = ["+", "x"]
        if len(vals) == 2:
            ops.append("-")
            if allow_div and max(vals) % min(vals) == 0:
                ops.append("/")
        op = rng.choice(ops)
        if op == "+":
            t = sum(vals)
        elif op == "x":
            t = 1
            for v in vals:
                t *= v
        elif op == "-":
            t = abs(vals[0] - vals[1])
        else:
            t = max(vals) // min(vals)
        out.append((cage, op, t))
    return out

# ---------------------------------------------------------------- solver

def count_solutions(n, cage_of, cages, limit=2):
    """Count solutions given cage structure [(cells, op, target), ...].
    Independent of generator internals: works only from the puzzle."""
    grid = [[0] * n for _ in range(n)]
    found = []
    cage_cells = [ [tuple(cell) for cell in cage] for cage, _, _ in cages ]

    def cage_ok(ci):
        cells, op, target = cages[ci]
        vals = [grid[r][c] for r, c in cells]
        filled = [v for v in vals if v]
        if op == "+":
            s = sum(filled)
            if len(filled) == len(vals):
                return s == target
            # remaining cells contribute at least 1 each, and at most n each
            rem = len(vals) - len(filled)
            return s + rem * 1 <= target <= s + rem * n
        if op == "x":
            p = 1
            for v in filled:
                p *= v
            if len(filled) == len(vals):
                return p == target
            return target % p == 0
        if op == "-":
            if len(filled) == 2:
                return abs(filled[0] - filled[1]) == target
            return True
        if op == "/":
            if len(filled) == 2:
                return max(filled) % min(filled) == 0 and max(filled) // min(filled) == target
            return True
        return filled[0] == target if filled else True

    def rec():
        if len(found) >= limit:
            return
        best, best_opts = None, None
        for r in range(n):
            for c in range(n):
                if grid[r][c] == 0:
                    used = set(grid[r]) | {grid[i][c] for i in range(n)}
                    opts = [v for v in range(1, n + 1) if v not in used]
                    if best_opts is None or len(opts) < len(best_opts):
                        best, best_opts = (r, c), opts
                        if len(opts) <= 1:
                            break
            if best_opts is not None and len(best_opts) <= 1:
                break
        if best is None:
            found.append([row[:] for row in grid])
            return
        if not best_opts:
            return
        r, c = best
        ci = cage_of[r][c]
        for v in best_opts:
            grid[r][c] = v
            if cage_ok(ci):
                rec()
            grid[r][c] = 0
            if len(found) >= limit:
                return

    rec()
    return len(found), (found[0] if found else None)

# -------------------------------------------------------------- generator

def make_puzzle(rng, n, difficulty):
    allow_div = difficulty in ("Medium", "Hard")
    sol = fill_latin(rng, n)
    for _ in range(MAX_PARTITION_TRIES):
        cages, owner = partition(rng, n)
        cages = assign_ops(rng, sol, cages, allow_div)
        cnt, found = count_solutions(n, owner, cages, limit=2)
        if cnt == 1 and found == sol:
            return {"n": n, "solution": sol, "cages": cages, "owner": owner,
                    "difficulty": difficulty, "cage_count": len(cages)}
    raise RuntimeError(f"no unique partition found in {MAX_PARTITION_TRIES} tries "
                       f"for {n}x{n}; refusing to print an unproven puzzle")

# -------------------------------------------------------------------- PDF

OP_GLYPH = {"+": "+", "-": "-", "x": "\u00d7", "/": "\u00f7", "": ""}

def _draw_grid(c, p, x0, y_top, cell, solved=False):
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    light = HexColor("#aaaaaa")
    n = p["n"]
    owner = p["owner"]
    c.setStrokeColor(light)
    c.setLineWidth(0.5)
    for i in range(n + 1):
        c.line(x0, y_top - i * cell, x0 + n * cell, y_top - i * cell)
        c.line(x0 + i * cell, y_top, x0 + i * cell, y_top - n * cell)
    c.setStrokeColor(ink)
    c.setLineWidth(2.2)
    for r in range(n):
        for cc in range(n):
            x, y = x0 + cc * cell, y_top - r * cell
            if r == 0 or owner[r - 1][cc] != owner[r][cc]:
                c.line(x, y, x + cell, y)
            if r == n - 1 or owner[r + 1][cc] != owner[r][cc]:
                c.line(x, y - cell, x + cell, y - cell)
            if cc == 0 or owner[r][cc - 1] != owner[r][cc]:
                c.line(x, y, x, y - cell)
            if cc == n - 1 or owner[r][cc + 1] != owner[r][cc]:
                c.line(x + cell, y, x + cell, y - cell)
    c.setFillColor(ink)
    if solved:
        for r in range(n):
            for cc in range(n):
                c.setFont("Helvetica", cell * 0.4)
                c.drawCentredString(x0 + cc * cell + cell / 2,
                                    y_top - r * cell - cell * 0.62,
                                    str(p["solution"][r][cc]))
    else:
        for cells, op, target in p["cages"]:
            ar, ac = min(cells)
            label = f"{target}{OP_GLYPH[op]}"
            c.setFont("Helvetica-Bold", max(9, cell * 0.21))
            c.drawString(x0 + ac * cell + 3, y_top - ar * cell - max(11, cell * 0.24), label)

def render_pdf(path, puzzles):
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.colors import HexColor
    ink = HexColor("#1a1a1a")
    accent = HexColor("#2050a0")
    c = rl_canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(72, 640, "CalcudokuPress")
    c.setFont("Helvetica", 15)
    c.drawString(72, 606, "Calcudoku books with proven unique solutions.")
    c.setFont("Helvetica", 11.5)
    lines = [
        "Fill the grid so every row and column holds 1..N once, and the",
        "numbers in each outlined cage combine (with the printed operation)",
        "to make the cage target. Every puzzle here was verified by an",
        "independent solver: exactly one solution exists, and it is the",
        "one printed at the back.",
        "",
        f"{len(puzzles)} puzzles with full solutions at the back.",
    ]
    y = 540
    for ln in lines:
        c.drawString(72, y, ln)
        y -= 20
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(84, 430 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(54, 748, f"Puzzle {i} -- {p['difficulty']} ({n}x{n})")
        c.setFont("Helvetica", 10.5)
        c.setFillColor(accent)
        c.drawString(54, 730, f"{p['cage_count']} cages -- one solution, proven")
        _draw_grid(c, p, x0, 700, cell)
        c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(ink)
    c.drawString(54, 748, "Solutions")
    c.showPage()
    for i, p in enumerate(puzzles, 1):
        n = p["n"]
        cell = min(66, 430 // n)
        x0 = (PAGE_W - n * cell) // 2
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(54, 748, f"Solution {i}")
        _draw_grid(c, p, x0, 716, cell, solved=True)
        c.showPage()
    c.save()
    with open(path, "rb") as fh:
        data = fh.read()
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")

# -------------------------------------------------------------------- run

def run_calcudokupress(count, outdir, seed=42, difficulty="Mixed", **kw):
    if difficulty not in ("Easy", "Medium", "Hard", "Mixed"):
        raise ValueError("difficulty must be Easy, Medium, Hard or Mixed")
    os.makedirs(outdir, exist_ok=True)
    rng = random.Random(seed)
    puzzles = []
    diffs = ["Easy", "Medium", "Hard"]
    for i in range(count):
        d = diffs[i % 3] if difficulty == "Mixed" else difficulty
        puzzles.append(make_puzzle(rng, SIZES[d], d))
    pdf_path = os.path.join(outdir, "calcudoku_book.pdf")
    pages = render_pdf(pdf_path, puzzles)
    return {"puzzles": puzzles, "pages": pages, "pdf_path": pdf_path,
            "count": len(puzzles)}

def main(argv):
    outdir = argv[1] if len(argv) > 1 else "out"
    opts = {"puzzles": 20, "difficulty": "Mixed", "seed": 42}
    for a in argv[2:]:
        if a.startswith("--") and "=" in a:
            k, v = a[2:].split("=", 1)
            if k in ("puzzles", "seed"):
                v = int(v)
            opts[k] = v
    s = run_calcudokupress(opts["puzzles"], outdir, seed=opts["seed"],
                           difficulty=opts["difficulty"])
    for i, p in enumerate(s["puzzles"], 1):
        print(f"Puzzle {i}: {p['difficulty']} {p['n']}x{p['n']}, "
              f"{p['cage_count']} cages, unique solution proven")
    print(f"Pages: {s['pages']}")
    print(f"PDF: {s['pdf_path']}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
