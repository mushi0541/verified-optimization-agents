"""Tests for the TSP parser-rule labels (devlog entry 14)."""

from scripts.tsp_parser_rules import label


def test_the_formula_range_decides_the_label():
    assert label("Subtour elimination (MTZ): for all i ≠ j, u[i] - u[j] + N·x[i,j] ≤ N - 1.") == "keeps the start city"
    assert label("MTZ: for all i ≠ j, i,j ∈ {2,…,N}, u_i - u_j + N·x_ij ≤ N - 1.") == "leaves the start city out"
    assert label("MTZ: for all i≠j, i≠Alpha, j≠Alpha, u[i] - u[j] + n·x[i,j] ≤ n - 1") == "leaves the start city out"


def test_bounds_in_another_clause_do_not_count():
    # The start city is left out of the bounds of u, but the formula itself still runs over every pair.
    rule = "MTZ: for all i≠1, 2 ≤ u[i] ≤ N, u[1]=1, and for all i≠j, u[i] - u[j] + N·x[i,j] ≤ N-1."
    assert label(rule) == "keeps the start city"


def test_a_rule_without_a_formula():
    assert label("Subtour elimination constraints (e.g., Miller-Tucker-Zemlin) must be enforced.") == "no formula"
    assert label("") == "no subtour requirement"
