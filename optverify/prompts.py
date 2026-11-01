"""Prompt templates.

BASELINE_FORMALIZE adapts the base paper's zero-shot "question to model code" prompt
(OPT-Engine, Prompts/benchmark_prompt_utils.py, "zeroshot_q2mc_en"): the instructions are kept,
but Gurobi is replaced by the open-source PuLP + HiGHS stack and the output format is fixed.
"""

_CODE_RULES = """Write ONE complete Python script that solves it with PuLP and the HiGHS solver:
- Start with `import pulp`.
- Name the problem variable `model`, for example `model = pulp.LpProblem("plan", pulp.LpMinimize)`.
- Solve with `model.solve(pulp.HiGHS(msg=False, timeLimit=120))`.
- Use only <=, >= and == in constraints.
- Write every number from the question into the script; do not read files or the internet.
Return the script in a single ```python code block."""

BASELINE_FORMALIZE = (
    """You are an operations research and optimization modeling expert. Below is an operations research question:
{question}

Carefully analyze the problem to identify the core elements such as decision variables, objective function and constraints,
and determine whether each variable is integer, binary or continuous.
Build a mathematical model and the corresponding Python code. Think step by step to ensure a flawless translation from math to code.
"""
    + _CODE_RULES
)

REPAIR = (
    """Your script for the optimization problem below failed.

Problem:
{question}

Your script:
```python
{code}
```

What went wrong:
{error}

Fix the script so it models the problem correctly and runs.{note}
"""
    + _CODE_RULES
)

PARSE = """You are the parser in an optimization modeling team. Read the problem and list what the model must contain.
Do not solve it and do not write code.

Problem:
{question}

Return only a JSON object with these keys:
- "objective_sense": "minimize" or "maximize"
- "objective": one sentence describing what is optimized
- "decision_variables": list of {{"name": str, "meaning": str, "type": "continuous" | "integer" | "binary"}}
- "parameters": list of {{"name": str, "value": number or list, "unit": str}} for every number in the problem
- "requirements": list of short strings, one per rule the solution must respect (one constraint each). Do not list
  variable types or the objective here; they belong in "decision_variables" and "objective"."""

FORMALIZE_FROM_SPEC = (
    """You are the formalizer in an optimization modeling team. The parser has listed what the model must contain.
Every requirement in the list must appear as one or more constraints in your model.
Each requirement has an ID (R1, R2, ...). Name every constraint so the name starts with the ID of the requirement
it implements, for example `model += x + y <= 10, "R3_capacity"`. When a requirement needs many constraints, add an
index after the ID, for example f"R2_demand_{{t}}". Write a requirement as a named constraint even when it is a
simple bound such as x >= 3, because a variable bound has no name.

Problem:
{question}

Parser output:
{spec}
"""
    + _CODE_RULES
)

# Added to the repair prompt in the pipeline, so a repaired model keeps its requirement links.
KEEP_CONSTRAINT_NAMES = " Keep the constraint names, each starting with its requirement ID (R1, R2, ...)."

PARAPHRASE ="""Rewrite the optimization problem below in different words, as a different operations manager might describe it.
Keep every number, unit, objective and rule exactly the same. Do not add or remove information. Do not solve it.
Return only the rewritten problem text.

Problem:
{question}"""
