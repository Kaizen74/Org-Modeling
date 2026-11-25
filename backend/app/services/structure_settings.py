"""
The designer's structural settings and inputs, in one place.

- App-wide settings (Settings page): the span range for each manager type and
  the words in a job title that mark a supervisory role.
- Per-upload inputs: manager types set on screen.

`calculator_inputs` is what every metrics calculation receives, so the current
state and every scenario are judged with the same rules; `signature` tells the
metrics cache when those rules changed.
"""

import hashlib
import json
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import OrgAnalysis, Setting, StructureInputs
from ..resources.benchmarks_reference import DEFAULT_SUPERVISORY_WORDS, MANAGER_TYPES

SETTINGS_KEY = "structure_settings"
MAX_WORDS = 30


def default_settings() -> Dict:
    return {"type_ranges": {k: list(v["range"]) for k, v in MANAGER_TYPES.items()},
            "supervisory_words": list(DEFAULT_SUPERVISORY_WORDS)}


def validate_settings(data: Dict) -> List[str]:
    """Plain-language problems with a settings change (empty list = fine)."""
    problems = []
    for key, rng in (data.get("type_ranges") or {}).items():
        label = MANAGER_TYPES.get(key, {}).get("label")
        if not label:
            problems.append(f"'{key}' is not a manager type")
            continue
        try:
            lo, hi = int(rng[0]), int(rng[1])
        except (TypeError, ValueError, IndexError):
            problems.append(f"{label}: give the range as two whole numbers")
            continue
        if lo < 1 or hi < lo or hi > 200:
            problems.append(f"{label}: the range must run from at least 1 up to a number no smaller than the first, at most 200")
    words = data.get("supervisory_words")
    if words is not None:
        if not isinstance(words, list) or len(words) > MAX_WORDS:
            problems.append(f"Give at most {MAX_WORDS} supervisory words")
        elif any(not isinstance(w, str) or not w.strip() or len(w.strip()) > 40 for w in words):
            problems.append("Each supervisory word must be 1 to 40 characters")
    return problems


async def load_settings(db: AsyncSession) -> Dict:
    row = (await db.execute(select(Setting).where(Setting.key == SETTINGS_KEY))).scalar_one_or_none()
    stored = json.loads(row.value) if row and row.value else {}
    settings = default_settings()
    settings["type_ranges"].update({k: list(v) for k, v in (stored.get("type_ranges") or {}).items() if k in MANAGER_TYPES})
    if stored.get("supervisory_words") is not None:
        settings["supervisory_words"] = list(stored["supervisory_words"])
    return settings


async def save_settings(db: AsyncSession, data: Dict) -> Dict:
    current = await load_settings(db)
    if data.get("type_ranges"):
        current["type_ranges"].update({k: [int(v[0]), int(v[1])] for k, v in data["type_ranges"].items()})
    if data.get("supervisory_words") is not None:
        current["supervisory_words"] = list(dict.fromkeys(w.strip() for w in data["supervisory_words"] if w.strip()))
    row = (await db.execute(select(Setting).where(Setting.key == SETTINGS_KEY))).scalar_one_or_none()
    if not row:
        row = Setting(key=SETTINGS_KEY)
        db.add(row)
    row.value = json.dumps(current)
    await db.commit()
    return current


async def reset_settings(db: AsyncSession) -> Dict:
    row = (await db.execute(select(Setting).where(Setting.key == SETTINGS_KEY))).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return default_settings()


async def load_inputs(analysis: OrgAnalysis, db: AsyncSession, create: bool = False) -> Optional[StructureInputs]:
    row = (await db.execute(select(StructureInputs).where(StructureInputs.analysis_id == analysis.id))).scalar_one_or_none()
    if not row and create:
        row = StructureInputs(analysis_id=analysis.id, manager_types={}, families=[], family_seq=0, family_reasons={})
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def calculator_inputs(analysis: OrgAnalysis, db: AsyncSession) -> Dict:
    """What MetricsCalculator needs beyond the employees: the same for the current state and scenarios."""
    settings = await load_settings(db)
    inputs = await load_inputs(analysis, db)
    return {
        "manager_types": dict((inputs.manager_types if inputs else None) or {}),
        "type_ranges": settings["type_ranges"],
        "supervisory_words": settings["supervisory_words"],
    }


def signature(inputs: Dict) -> str:
    """Changes whenever the rules or the designer's inputs change, so cached metrics recalculate."""
    return hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
