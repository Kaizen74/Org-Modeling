"""
The single place the app calls Claude.

Model, effort and output limit are configured here (overridable with
environment variables) so every analysis uses the same settings. Calls are
streamed because analyses are long, opt into server-side refusal fallback,
and report refusals and cut-off responses instead of failing silently.
"""

import os
from typing import Dict, Optional, Tuple

from anthropic import Anthropic

MODEL = os.getenv("ORG_ANALYZER_MODEL", "claude-opus-5-5")
# Org design judgement benefits from deeper thinking; Opus 5.5 defaults to "medium"
EFFORT = os.getenv("ORG_ANALYZER_EFFORT", "high")
MAX_OUTPUT_TOKENS = int(os.getenv("ORG_ANALYZER_MAX_TOKENS", "64000"))
# On a policy decline, re-run on Anthropic's recommended fallback model
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnalysisRefused(Exception):
    """The model (and its fallback) declined the request."""


def run_analysis(client: Anthropic, prompt: str, max_tokens: Optional[int] = None) -> Tuple[str, Dict]:
    """
    Send one analysis prompt and return (response text, call metadata).

    Thinking blocks are skipped; only the answer text is returned. Metadata
    records which model served the answer and whether it was cut off.
    """
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=max_tokens or MAX_OUTPUT_TOKENS,
        output_config={"effort": EFFORT},
        betas=[FALLBACK_BETA],
        fallbacks="default",
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        category = getattr(details, "category", None) if details else None
        raise AnalysisRefused(
            "The AI declined this request" + (f" (category: {category})" if category else "")
        )

    text = "".join(block.text for block in message.content if block.type == "text")
    meta = {
        "model_requested": MODEL,
        "model_served": message.model,
        "effort": EFFORT,
        "stop_reason": message.stop_reason,
        "truncated": message.stop_reason == "max_tokens",
    }
    return text, meta
