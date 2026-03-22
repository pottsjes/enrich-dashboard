"""EvalAgent — evaluates recommendation quality using Haiku (cheap + fast)."""

from __future__ import annotations

from models.schemas import EvalResult, RecommendationReport
from agents.llm_client import call, HAIKU

SYSTEM_PROMPT = """\
You are a quality evaluator for short-term rental revenue management \
recommendations. Evaluate the provided recommendations on three criteria:

1. SPECIFICITY: Are they actionable with concrete numbers? \
("adjust pricing" = BAD, "reduce weekday rate by $15-20" = GOOD)
2. CONSISTENCY: Do any recommendations contradict each other?
3. GROUNDING: Are they supported by the data metrics provided?

Score from 0.0 to 1.0. Pass threshold is 0.7.
If the score is below 0.7, provide specific feedback about what to improve.
If the score is 0.7 or above, set passed to true.

Return your response as a JSON object matching the provided schema."""


class EvalAgent:
    """Evaluates recommendation quality."""

    def evaluate(self, report: RecommendationReport) -> EvalResult:
        recs_data = [r.model_dump() for r in report.recommendations]
        user_msg = (
            f"Recommendations to evaluate:\n{recs_data}\n\n"
            f"Summary: {report.summary}\n\n"
            "Evaluate specificity, consistency, and grounding. "
            "Return your structured evaluation."
        )
        return call(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
            model=HAIKU,
            output_schema=EvalResult,
        )
