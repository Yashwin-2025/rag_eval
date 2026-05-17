import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.openrouter import get_chat_llm

_JUDGE_SYSTEM = """You evaluate RAG answers. Reply with JSON only, no markdown:
{"correctness": <0.0-1.0>, "groundedness": <0.0-1.0>, "reasoning": "<short explanation>"}

- correctness: how well the model answer matches the reference answer (semantic match OK).
- groundedness: how well the model answer is supported by the retrieved context only (penalize hallucination).
"""


def _parse_judge_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise
        return json.loads(match.group(0))


def judge_answer(
    *,
    question: str,
    reference_answer: str,
    context: str,
    model_answer: str,
) -> tuple[float, float, str]:
    llm = get_chat_llm()
    user = f"""Question: {question}

Reference answer: {reference_answer}

Retrieved context:
{context}

Model answer: {model_answer}
"""
    msg = llm.invoke(
        [
            SystemMessage(content=_JUDGE_SYSTEM),
            HumanMessage(content=user),
        ]
    )
    raw = msg.content if isinstance(msg.content, str) else str(msg.content)
    data = _parse_judge_json(raw)
    correctness = float(max(0.0, min(1.0, data["correctness"])))
    groundedness = float(max(0.0, min(1.0, data["groundedness"])))
    reasoning = str(data.get("reasoning", ""))
    return correctness, groundedness, reasoning
