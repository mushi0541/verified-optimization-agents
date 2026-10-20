"""Tests for capturing decision variable values from solver runs and explaining them."""

from optverify.contracts import Decision, VerifierReport
from optverify.roles import explain
from optverify.solver_tool import run_model_code


def test_two_variables_produce_var_lines_and_dict():
    code = (
        "import pulp\n"
        "model = pulp.LpProblem('two_vars', pulp.LpMinimize)\n"
        "x = pulp.LpVariable('x', lowBound=0)\n"
        "y = pulp.LpVariable('y', lowBound=0)\n"
        "model += x + 2 * y >= 10\n"
        "model += 2 * x + y >= 8\n"
        "model += x + y\n"
        "model.solve(pulp.HiGHS(msg=False))\n"
    )
    result = run_model_code(code)
    assert result.status == "optimal"
    assert "x" in result.variables
    assert "y" in result.variables
    assert result.variables == {"x": 2.0, "y": 4.0}


def test_more_than_100_variables_capped_and_omitted_line_printed():
    lines = [
        "import pulp",
        "model = pulp.LpProblem('many_vars', pulp.LpMinimize)",
        "vars_list = []",
        "for i in range(150):",
        "    v = pulp.LpVariable(f'v_{i:03d}', lowBound=1)",
        "    vars_list.append(v)",
        "model += pulp.lpSum(vars_list)",
        "model.solve(pulp.HiGHS(msg=False))",
    ]
    result = run_model_code("\n".join(lines))
    assert result.status == "optimal"
    assert len(result.variables) == 100
    expected_names = [f"v_{i:03d}" for i in range(100)]
    assert list(result.variables.keys()) == expected_names
    assert all(value == 1.0 for value in result.variables.values())
    assert "VARS_OMITTED: 50" in result.stdout


def test_near_zero_variables_are_not_reported():
    code = (
        "import pulp\n"
        "model = pulp.LpProblem('near_zero', pulp.LpMinimize)\n"
        "x = pulp.LpVariable('x', lowBound=0)\n"
        "y = pulp.LpVariable('y', lowBound=0)\n"
        "model += x >= 5\n"
        "model += y >= 0\n"
        "model += x + y\n"
        "model.solve(pulp.HiGHS(msg=False))\n"
    )
    result = run_model_code(code)
    assert result.status == "optimal"
    assert "x" in result.variables
    assert "y" not in result.variables


def test_code_without_model_gives_empty_variables_and_same_error():
    result = run_model_code("x = 1\nprint('no model here')")
    assert result.variables == {}
    assert result.status == "error"
    assert "model" in result.error
    assert result.objective is None


def test_variable_name_with_parentheses_and_commas():
    # PuLP allows parentheses and commas in variable names.
    code = (
        "import pulp\n"
        "model = pulp.LpProblem('paren_comma', pulp.LpMinimize)\n"
        "v = pulp.LpVariable('x_(1,2)', lowBound=0)\n"
        "model += v >= 3.5\n"
        "model += v\n"
        "model.solve(pulp.HiGHS(msg=False))\n"
    )
    result = run_model_code(code)
    assert result.status == "optimal"
    assert "x_(1,2)" in result.variables
    assert result.variables["x_(1,2)"] == 3.5


def test_explainer_lists_values_for_answer_and_not_for_escalate_or_abstain():
    report = VerifierReport(True, 1.0, [], 1.0, [570.0, 570.0], 1.0)
    vars_dict = {"x": 2.0, "y": 4.0}

    # Answer case with variables lists values.
    ans_dec = Decision("answer", 6.0, ["All checks passed."])
    ans_text = explain(ans_dec, report, vars_dict)
    assert "Recommended plan found. Optimal objective value: 6." in ans_text
    assert "x: 2" in ans_text
    assert "y: 4" in ans_text
    assert ans_text.splitlines()[-2:] == ["x: 2", "y: 4"]

    # Answer case without variables leaves text unchanged.
    ans_no_vars = explain(ans_dec, report, {})
    assert "\n" not in ans_no_vars

    # Escalate case does not list variables.
    esc_dec = Decision("escalate", 6.0, ["Coverage low."])
    esc_text = explain(esc_dec, report, vars_dict)
    assert "x: 2" not in esc_text
    assert "y: 4" not in esc_text
    assert "\n" not in esc_text

    # Abstain case does not list variables.
    abst_dec = Decision("abstain", None, ["No model."])
    abst_text = explain(abst_dec, report, vars_dict)
    assert "x: 2" not in abst_text
    assert "y: 4" not in abst_text
    assert "\n" not in abst_text
