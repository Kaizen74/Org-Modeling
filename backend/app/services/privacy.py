"""Remove personal names from text that leaves the app (AI prompts, exported packs)."""

import re
from typing import Dict, List


def name_map(employees: List[Dict]) -> Dict[str, str]:
    """Personal name → job title, for everyone in the upload."""
    return {e.get("name", ""): e.get("job_title", "") for e in employees if e.get("name")}


def without_names(text: str, name_to_title: Dict[str, str]) -> str:
    """Replace personal names with job titles (longest names first, whole words only)."""
    for name in sorted(name_to_title, key=len, reverse=True):
        if name:
            text = re.sub(rf"\b{re.escape(name)}\b", f"the {name_to_title[name] or 'role'}", text)
    return text
