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

# Version 2 (#95), designed on development problems only. Version 1 above stays the default, so every earlier run
# reproduces. The failure analysis found that the parser wrote textbook formulas as requirements (for TSP, a
# subtour constraint over every pair of cities, the start city included) and that the formalizer copied them, and
# that rules lost their timing (storage capacity "at any moment" became a check at the end of the day). Version 2
# changes three templates; use_version swaps them in, and roles.py and systems.py read them at call time.
_V2 = {
    "PARSE": PARSE.replace(
        """- "requirements": list of short strings, one per rule the solution must respect (one constraint each). Do not list
  variable types or the objective here; they belong in "decision_variables" and "objective".""",
        """- "requirements": list of short strings, one per rule the solution must respect. State each rule in plain words, as
  the problem states it, with its exact scope and timing (for example "for every city except the start city", "at
  any moment", "at the end of each day"). Do not write formulas or standard modelling constructs such as subtour
  elimination or big-M constraints; the formalizer chooses how to model each rule. Do not list variable types or the
  objective here; they belong in "decision_variables" and "objective".""",
    ),
    "FORMALIZE_FROM_SPEC": FORMALIZE_FROM_SPEC.replace(
        "Every requirement in the list must appear as one or more constraints in your model.\n",
        "Every requirement in the list must appear as one or more constraints in your model. The requirements are a\n"
        "checklist, not a model: write each one with the constraints the problem text implies, and when a requirement\n"
        "disagrees with the problem text, follow the problem text.\n",
    ),
    "REPAIR": REPAIR.replace(
        "Fix the script so it models the problem correctly and runs.{note}",
        "If the solver found the model infeasible, look for a rule written more strictly than the problem states: a\n"
        "constraint applied to an index the problem leaves out (such as the start city of a tour or the first period),\n"
        "bounds that are too tight, or an equality where the problem allows less or more.\n\n"
        "Fix the script so it models the problem correctly and runs.{note}",
    ),
}
_V1 = {name: globals()[name] for name in _V2}
# Version 3 (#95, second dev iteration): v2 lost accuracy on the dev sample because the parser, told not to write
# standard constructs, left subtour elimination out of TSP models. v3 keeps the v1 parser and keeps v2's formalizer
# and repair changes, which fixed models that v1 left infeasible.
_V3 = {**_V2, "PARSE": _V1["PARSE"]}
_TEMPLATES = {"v1": _V1, "v2": _V2, "v3": _V3}
VERSIONS = tuple(_TEMPLATES)


def use_version(version: str) -> None:
    """Make the templates of a prompt version the active ones (v1, the Phase 1 prompts, is the default)."""
    if version not in _TEMPLATES:
        raise ValueError(f"unknown prompt version {version!r}; known: {', '.join(VERSIONS)}")
    globals().update(_TEMPLATES[version])
