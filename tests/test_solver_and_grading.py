from optverify.grading import is_correct, same_optimum
from optverify.solver_tool import extract_code, run_model_code
from tests.fake_llm import TOY_CODE, TOY_OPTIMUM


def test_grading_uses_base_paper_tolerance():
    assert is_correct(570.0, 570.0)
    assert is_correct(571.0, 570.0)  # 0.18% off, inside the 0.2% rule
    assert not is_correct(572.0, 570.0)  # 0.35% off
    assert not is_correct(None, 570.0)
    assert same_optimum(100.0, 100.1)


def test_extract_code_takes_the_full_script():
    text = "Use `x`:\n```python\nx = 1\n```\nFull script:\n" + TOY_CODE
    assert extract_code(text).startswith("import pulp")
    assert extract_code("no code here") is None


def test_solver_returns_optimum():
    result = run_model_code(extract_code(TOY_CODE))
    assert result.status == "optimal"
    assert is_correct(result.objective, TOY_OPTIMUM)


def test_solver_reports_errors_and_infeasibility():
    assert run_model_code("this is not python").status == "error"
    assert run_model_code(None).status == "no_code"
    infeasible = (
        "import pulp\nmodel = pulp.LpProblem('m', pulp.LpMinimize)\n"
        "x = pulp.LpVariable('x', lowBound=5)\nmodel += x\nmodel += x <= 2\nmodel.solve(pulp.HiGHS(msg=False))"
    )
    result = run_model_code(infeasible)
    assert result.status == "infeasible" and result.objective is None


def test_generated_code_cannot_see_api_keys(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret-value")
    result = run_model_code("import os\nprint('KEY=' + str(os.environ.get('LLM_API_KEY')))")
    assert "KEY=None" in result.stdout
