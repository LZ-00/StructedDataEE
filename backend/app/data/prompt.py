"""激光焊接实验记录结构化抽取 Prompt。"""

from __future__ import annotations

from app.schemas.extraction import SCHEMA_FIELDS

_DEFAULT_EXTRACTION_TASK = (
    "Identify each laser welding experimental record in the following passage. "
    "For each record, extract the welding process parameters, including welding power (W), "
    "welding speed (m/min), defocusing distance (mm), shielding gas, and shielding gas flow rate(L/min), "
    "together with the corresponding mechanical performance metrics, including tensile strength, "
    "yield strength, and elongation rate (%). "
    "Only extract information explicitly stated in the passage."
)

_SCHEMA_EXAMPLE = ",\n    ".join(f'"{field}": null' for field in SCHEMA_FIELDS)

EXTRACTION_PROMPT_TEMPLATE = f"""You are a domain-specific information extraction assistant for laser welding experimental literature.

Given the following passage, identify each laser welding experimental record and extract structured fields for welding process parameters and mechanical performance metrics.

Paragraph:
\"\"\"
{{paragraph}}
\"\"\"

Requirements:
1. Extract only information explicitly stated in the passage.
2. Do not infer or generate values that are not present.
3. Keep all numerical values together with their units (e.g., W, m/min, mm, L/min, %).
4. Use null for missing fields.
5. If multiple experimental records are present, return one JSON object per record in a JSON array.
6. Output valid JSON only.

Field definitions:
- welding_power: welding power (W)
- welding_speed: welding speed (m/min)
- defocusing_distance: defocusing distance (mm)
- shielding_gas: shielding gas type or composition
- shielding_gas_flow_rate: shielding gas flow rate (L/min)
- tensile_strength: tensile strength with unit if stated
- yield_strength: yield strength with unit if stated
- elongation_rate: elongation rate (%)

Schema:
[
  {{
    {_SCHEMA_EXAMPLE}
  }}
]"""


RELEVANCE_PROMPT_TEMPLATE = """You are a document relevance classifier for domain-specific information extraction.

Task description (what to extract from the document):
\"\"\"
{task_description}
\"\"\"

Text chunk:
\"\"\"
{chunk}
\"\"\"

Determine whether this chunk contains information that is relevant to the task description and may contain extractable target content.

Requirements:
1. Output valid JSON only, no markdown.
2. Use is_relevant=true only when the chunk likely contains information related to the task.
3. Provide a brief reason in the same language as the task description when possible.

Output schema:
{{"is_relevant": true, "reason": "brief explanation"}}"""


def build_extraction_prompt(paragraph: str, task_description: str = "") -> str:
    """将段落文本与任务描述填入抽取 Prompt 模板。"""
    base = EXTRACTION_PROMPT_TEMPLATE.replace("{paragraph}", (paragraph or "").strip())
    task = (task_description or "").strip()
    if not task or task == _DEFAULT_EXTRACTION_TASK:
        return base
    task_block = (
        "\n\nAdditional extraction focus (from user task description):\n"
        f"\"\"\"\n{task}\n\"\"\"\n"
        "Prioritize fields and values that match this focus while still following the schema."
    )
    return base + task_block


def build_relevance_prompt(chunk: str, task_description: str) -> str:
    """构建文本块相关性判断 Prompt。"""
    task = (task_description or "").strip() or _DEFAULT_EXTRACTION_TASK
    return RELEVANCE_PROMPT_TEMPLATE.format(
        task_description=task,
        chunk=(chunk or "").strip(),
    )
