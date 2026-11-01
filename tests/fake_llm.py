"""A scripted stand-in for an LLM so the tests run offline and cost nothing."""

from optverify.contracts import LLMReply, TokenUsage

TOY_QUESTION = (
    "A workshop makes chairs and tables. Each chair earns 30 dollars of profit and each table earns 50 dollars. "
    "A chair needs 2 hours of work and a table needs 4 hours. There are 40 hours available. "
    "At least 3 tables must be made. How many of each should be made to maximize profit?"
)
TOY_OPTIMUM = 570.0

TOY_CODE = """```python
import pulp
model = pulp.LpProblem("workshop", pulp.LpMaximize)
chairs = pulp.LpVariable("chairs", lowBound=0, cat="Integer")
tables = pulp.LpVariable("tables", lowBound=0, cat="Integer")
model += 30 * chairs + 50 * tables
model += 2 * chairs + 4 * tables <= 40, "R1_work_hours"
model += tables >= 3, "R2_min_tables"
model.solve(pulp.HiGHS(msg=False, timeLimit=120))
```"""

TOY_SPEC = """{"objective_sense": "maximize", "objective": "total profit",
 "decision_variables": [{"name": "chairs", "meaning": "chairs made", "type": "integer"},
                        {"name": "tables", "meaning": "tables made", "type": "integer"}],
 "parameters": [{"name": "chair_profit", "value": 30, "unit": "dollars"}],
 "requirements": ["work hours <= 40", "tables >= 3"]}"""


class FakeLLM:
    name = "fake-llm"

    def __init__(self, code_reply: str = TOY_CODE):
        self.code_reply = code_reply
        self.prompts: list[str] = []

    def complete(self, prompt: str, max_tokens: int = 4096) -> LLMReply:
        self.prompts.append(prompt)
        if "Return only a JSON object" in prompt:
            text = TOY_SPEC
        elif "Rewrite the optimization problem" in prompt:
            text = TOY_QUESTION.replace("A workshop makes", "A small factory produces")
        else:
            text = self.code_reply
        return LLMReply(text, TokenUsage(input_tokens=len(prompt) // 4, output_tokens=len(text) // 4, calls=1), 0.0)
