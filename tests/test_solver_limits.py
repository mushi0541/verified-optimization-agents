from optverify.solver_tool import extract_code, run_model_code


def test_solver_stops_scripts_at_the_time_limit():
    result = run_model_code("import time\ntime.sleep(30)", timeout_s=1)
    assert result.status == "timeout" and result.objective is None and "1 s" in result.error


def test_script_without_a_model_is_an_error_with_a_reason():
    result = run_model_code("x = 1\nprint(x)")
    assert result.status == "error" and "model" in result.error


def test_runtime_errors_return_the_error_text():
    result = run_model_code("raise ValueError('bad data')")
    assert result.status == "error" and "bad data" in result.error


def test_extract_code_accepts_py_and_plain_fences():
    assert extract_code("```py\nx = 1\n```") == "x = 1"
    assert extract_code("```\nimport pulp\n```") == "import pulp"
