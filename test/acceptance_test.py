#!/usr/bin/env python3
"""CalcudokuPress acceptance test.

Seeded-proof method: build a real book (2 puzzles per difficulty,
4x4/5x5/6x6), then re-verify every puzzle with a checker written
independently of the engine: it rebuilds cage constraints FROM THE
PRINTED DATA ALONE (cells/op/target tuples) using a plain exhaustive
search over cage-consistent assignments, and confirms exactly one
solution equal to the printed grid. Also audits every cage target
against the solution (op arithmetic), cage coverage (partition of the
grid, all cages contiguous), counts, PDF geometry, timing, determinism.
"""
import os
import sys
import time
from itertools import permutations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from calcudoku_press import run_calcudokupress  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "out")
results = []

def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")

def cage_target_ok(vals, op, target):
    if op == "":
        return len(vals) == 1 and vals[0] == target
    if op == "+":
        return sum(vals) == target
    if op == "x":
        p = 1
        for v in vals:
            p *= v
        return p == target
    if op == "-":
        return len(vals) == 2 and abs(vals[0] - vals[1]) == target
    if op == "/":
        return len(vals) == 2 and max(vals) % min(vals) == 0 and max(vals) // min(vals) == target
    return False

def count_from_printed(n, cages, limit=2):
    """Independent recount: assign whole cages at a time via permutations
    of candidate tuples -- a different search shape from the engine's
    cell-MRV solver."""
    grid = [[0] * n for _ in range(n)]
    sols = []

    def cage_candidates(cells, op, target):
        dom = list(range(1, n + 1))
        out = []
        def rec(idx, cur):
            if len(sols) >= limit:
                return
            if idx == len(cells):
                if cage_target_ok(cur, op, target):
                    out.append(tuple(cur))
                return
            r, c = cells[idx]
            for v in dom:
                if v in [grid[r][i] for i in range(n) if grid[r][i]] or \
                   v in [grid[i][c] for i in range(n) if grid[i][c]]:
                    continue
                if cells.index((r, c)) > 0:
                    prev_same_row = [cur[j] for j, (rr, cc) in enumerate(cells[:idx]) if rr == r]
                    prev_same_col = [cur[j] for j, (rr, cc) in enumerate(cells[:idx]) if cc == c]
                    if v in prev_same_row or v in prev_same_col:
                        continue
                cur.append(v)
                rec(idx + 1, cur)
                cur.pop()
        rec(0, [])
        return out

    order = sorted(range(len(cages)), key=lambda i: len(cages[i][0]))

    def rec(k):
        if len(sols) >= limit:
            return
        if k == len(order):
            sols.append([row[:] for row in grid])
            return
        cells, op, target = cages[order[k]]
        for tup in cage_candidates(cells, op, target):
            placed = []
            ok = True
            for (r, c), v in zip(cells, tup):
                if grid[r][c] not in (0, v):
                    ok = False
                    break
                if grid[r][c] == 0:
                    row_used = {grid[r][i] for i in range(n)} - {0}
                    col_used = {grid[i][c] for i in range(n)} - {0}
                    if v in row_used or v in col_used:
                        ok = False
                        break
                placed.append((r, c, grid[r][c]))
                grid[r][c] = v
            if ok:
                rec(k + 1)
            for r, c, old in placed:
                grid[r][c] = old
            if len(sols) >= limit:
                return

    rec(0)
    return sols

def main():
    t0 = time.time()
    s = run_calcudokupress(6, OUT, seed=42, difficulty="Mixed")
    dt = time.time() - t0
    ps = s["puzzles"]
    check("counts: 6 puzzles, sizes 4/5/6", len(ps) == 6 and [p["n"] for p in ps] == [4, 5, 6, 4, 5, 6],
          f"({[p['n'] for p in ps]})")

    coverage_ok, targets_ok, unique_ok = True, True, True
    for p in ps:
        n = p["n"]
        flat = [cell for cells, _, _ in p["cages"] for cell in cells]
        if sorted(flat) != [(r, c) for r in range(n) for c in range(n)]:
            coverage_ok = False
        for cells, op, target in p["cages"]:
            # contiguity
            seen, stack = set(), [cells[0]]
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                for nb in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]),
                           (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
                    if nb in cells and nb not in seen:
                        stack.append(nb)
            if seen != set(cells):
                coverage_ok = False
            vals = [p["solution"][r][c] for r, c in cells]
            if not cage_target_ok(vals, op, target):
                targets_ok = False
        sols = count_from_printed(n, p["cages"], limit=2)
        if len(sols) != 1 or sols[0] != p["solution"]:
            unique_ok = False
    check("cages partition the grid and are all contiguous", coverage_ok, "")
    check("every cage target is arithmetically true of the solution", targets_ok, "")
    check("every puzzle: exactly one solution (independent cage-wise recount), "
          "equal to printed solution", unique_ok, "")

    with open(s["pdf_path"], "rb") as fh:
        data = fh.read()
    pages = data.count(b"/Type /Page") - data.count(b"/Type /Pages")
    check("PDF 612x792pt, 14 pages", b"612 792" in data and pages == 14, f"({pages})")
    check("6-puzzle mixed book builds in under 180s", dt < 180, f"({dt:.1f}s)")

    s2 = run_calcudokupress(6, OUT, seed=42, difficulty="Mixed")
    same = [p["cages"] for p in s2["puzzles"]] == [p["cages"] for p in ps]
    check("deterministic for fixed seed", same, "")

    npass = sum(1 for _, ok, _ in results if ok)
    print(f"\n{npass}/{len(results)} PASS")
    with open(os.path.join(os.path.dirname(__file__), "acceptance_results.txt"), "w") as fh:
        for name, ok, detail in results:
            fh.write(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}\n")
        fh.write(f"\n{npass}/{len(results)} PASS\n")
    return 0 if npass == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
