"""JSON table directive for zinewire.

Processes /table directives that load data from JSON files and render
as markdown tables before the main markdown conversion.

JSON format (simple):
    {
        "columns": ["Name", "Price", "Weight"],
        "items": [
            {"name": "Sword", "price": "10g", "weight": "3lb"},
            {"name": "Shield", "price": "8g", "weight": "5lb"}
        ],
        "align": ["left", "right", "center"],       // optional
        "display_columns": ["Item", "Cost", "Wt"]   // optional header aliases
    }

JSON format (nested — for grouped tables):
    {
        "units": { "columns": [...], "items": [...] },
        "behavior": { "columns": [...], "items": [...], "title": "..." },
        "special_rule": "...",                        // optional
        "behavior_attacked": { ... }                  // optional
    }

Column lookup: columns are matched to item keys by lowercase name,
then by common display-name-to-key mappings (e.g. "Weapon" → "name",
"d6" → "roll"), then by explicit "keys" array if provided.
"""

import json
import re
from pathlib import Path

# Common display-column-name → item-key mappings.
# Dice columns map to "roll"; descriptive columns map to "name" or "effect".
_KEY_MAPPINGS = {
    # Dice → roll
    "d4": "roll", "d6": "roll", "d8": "roll", "d10": "roll", "d20": "roll",
    "2d4": "roll", "2d6": "roll",
    # Descriptive → name
    "weapon": "name", "armor": "name", "item": "name", "archetype": "name",
    "cybernetic": "name", "power": "name", "protocol": "name",
    "heresy": "name", "blessing": "name", "modifier": "name",
    "type": "name", "layout": "name", "timing": "name",
    "terrain": "name", "complication": "name",
    "contract type": "contract_type",
    # Descriptive → effect
    "rule": "effect", "spawns": "effect", "features": "effect",
    # Explicit keys
    "total": "total", "no los": "no_los", "has los": "has_los",
    "atk los": "atk_los", "atk eng": "atk_eng",
    "finding": "finding", "faction": "faction", "relic reward": "relic_reward",
    "max armor": "max_armor", "result": "result",
    "d3: 1": "d3_1", "d3: 2": "d3_2", "d3: 3": "d3_3",
    # Spanish variants
    "poder": "power", "modificador": "name", "efecto": "effect",
    "tipo": "name", "disposición": "name", "regla": "effect",
    "apariciones": "effect", "características": "effect",
    "terreno": "name", "complicación": "name",
    "atk ldv": "atk_los", "atk trab": "atk_eng",
}


def _render_simple_table(columns, items, display=None, align=None):
    """Render a simple table from columns and items to markdown syntax."""
    headers = display if display else columns
    header = "| " + " | ".join(headers) + " |"

    # Separator with alignment
    sep_parts = []
    for i in range(len(columns)):
        a = align[i] if align and i < len(align) else "left"
        if a == "center":
            sep_parts.append(":---:")
        elif a == "right":
            sep_parts.append("---:")
        else:
            sep_parts.append(":---")
    separator = "|" + "|".join(sep_parts) + "|"

    # Data rows
    rows = []
    for item in items:
        values = []
        for col in columns:
            col_lower = col.lower()
            # Exact match first (skip non-displayable values like lists/dicts)
            if col_lower in item and isinstance(item[col_lower], (str, int, float)):
                value = item[col_lower]
            else:
                # Fall back to common mappings
                key = _KEY_MAPPINGS.get(col_lower, col_lower.replace(" ", "_"))
                value = item.get(key, item.get(col, ""))
            values.append(str(value) if value is not None else "")
        rows.append("| " + " | ".join(values) + " |")

    return "\n".join([header, separator] + rows)


def render_table(data: dict) -> str:
    """Render a JSON table definition to markdown table syntax.

    Supports both simple format (columns/items at root) and nested
    format (units/behavior groups for faction tables).
    """
    # Nested format: units + behavior tables
    if "units" in data and "behavior" in data:
        result = []
        units = data["units"]
        result.append(_render_simple_table(
            units["columns"], units["items"],
            units.get("display_columns"), units.get("align"),
        ))
        if "special_rule" in data:
            result.append("")
            result.append(data["special_rule"])
            result.append("")
        behavior = data["behavior"]
        title = behavior.get("title", "Behavior")
        result.append("")
        result.append(f"**{title}**")
        result.append("")
        result.append(_render_simple_table(
            behavior["columns"], behavior["items"],
            behavior.get("display_columns"), behavior.get("align"),
        ))
        if "behavior_attacked" in data:
            atk = data["behavior_attacked"]
            atk_title = atk.get("title", "Attacked")
            result.append("")
            result.append(f"**{atk_title}**")
            result.append("")
            result.append(_render_simple_table(
                atk["columns"], atk["items"],
                atk.get("display_columns"), atk.get("align"),
            ))
        return "\n".join(result)

    # Simple format
    return _render_simple_table(
        data["columns"], data["items"],
        data.get("display_columns"), data.get("align"),
    )


def process_tables(md_text: str, base_dir: Path | None = None) -> str:
    """Replace /table directives with rendered markdown tables.

    Args:
        md_text: Raw markdown text.
        base_dir: Directory to resolve relative JSON paths from.

    Returns:
        Markdown text with /table directives replaced by table markup.
    """
    if base_dir is None:
        base_dir = Path(".")

    def _replace(match):
        json_path = base_dir / match.group(1)
        if not json_path.exists():
            return f"<!-- ERROR: Table file not found: {match.group(1)} -->"
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            return "\n" + render_table(data) + "\n"
        except json.JSONDecodeError as e:
            return f"<!-- ERROR: Invalid JSON in {match.group(1)}: {e} -->"
        except KeyError as e:
            return f"<!-- ERROR: Missing key {e} in {match.group(1)} -->"

    return re.sub(r"^/table\s+(\S+)\s*$", _replace, md_text, flags=re.MULTILINE)
