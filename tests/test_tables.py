"""Tests for /table JSON directive."""

import json
import pytest
from pathlib import Path

from zinewire.tables import render_table, process_tables


def test_render_table_basic():
    data = {
        "columns": ["Name", "Price"],
        "items": [
            {"name": "Sword", "price": "10g"},
            {"name": "Shield", "price": "8g"},
        ],
    }
    result = render_table(data)
    assert "| Name | Price |" in result
    assert "| Sword | 10g |" in result
    assert "| Shield | 8g |" in result


def test_render_table_alignment():
    data = {
        "columns": ["Name", "Value", "Notes"],
        "items": [{"name": "A", "value": "1", "notes": "ok"}],
        "align": ["left", "right", "center"],
    }
    result = render_table(data)
    assert "|:---|---:|:---:|" in result


def test_render_table_display_columns():
    data = {
        "columns": ["Name", "Qty"],
        "display_columns": ["Item", "Quantity"],
        "items": [{"name": "Bolt", "qty": "12"}],
    }
    result = render_table(data)
    assert "| Item | Quantity |" in result
    assert "| Bolt | 12 |" in result


def test_render_table_underscore_keys():
    """Column names with spaces map to underscore keys."""
    data = {
        "columns": ["Full Name", "Home Town"],
        "items": [{"full_name": "Alice", "home_town": "Portland"}],
    }
    result = render_table(data)
    assert "| Alice | Portland |" in result


def test_render_table_missing_key():
    """Missing keys render as empty string."""
    data = {
        "columns": ["Name", "Missing"],
        "items": [{"name": "Test"}],
    }
    result = render_table(data)
    assert "| Test |  |" in result


def test_process_tables_replaces_directive(tmp_path):
    json_file = tmp_path / "items.json"
    json_file.write_text(json.dumps({
        "columns": ["Name", "Price"],
        "items": [{"name": "Potion", "price": "5g"}],
    }))

    md = "Some text\n/table items.json\nMore text"
    result = process_tables(md, base_dir=tmp_path)

    assert "/table" not in result
    assert "| Name | Price |" in result
    assert "| Potion | 5g |" in result
    assert "Some text" in result
    assert "More text" in result


def test_process_tables_file_not_found(tmp_path):
    md = "/table missing.json"
    result = process_tables(md, base_dir=tmp_path)
    assert "ERROR: Table file not found" in result


def test_process_tables_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ not valid json")

    md = "/table bad.json"
    result = process_tables(md, base_dir=tmp_path)
    assert "ERROR: Invalid JSON" in result


def test_process_tables_missing_columns_key(tmp_path):
    json_file = tmp_path / "nokey.json"
    json_file.write_text(json.dumps({"items": []}))

    md = "/table nokey.json"
    result = process_tables(md, base_dir=tmp_path)
    assert "ERROR: Missing key" in result


def test_process_tables_multiple_directives(tmp_path):
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps({
            "columns": ["X"],
            "items": [{"x": name}],
        }))

    md = "/table a.json\n\n/table b.json"
    result = process_tables(md, base_dir=tmp_path)
    assert "a.json" in result
    assert "b.json" in result
    assert "/table" not in result


def test_table_integration_build(tmp_path):
    """End-to-end: markdown with /table → HTML with rendered table."""
    from zinewire import build

    # Create JSON data
    data_file = tmp_path / "gear.json"
    data_file.write_text(json.dumps({
        "columns": ["Item", "Weight"],
        "items": [
            {"item": "Rope", "weight": "2kg"},
            {"item": "Lamp", "weight": "1kg"},
        ],
    }))

    # Create markdown
    md_file = tmp_path / "test.md"
    md_file.write_text("# Gear List\n\n/table gear.json\n")

    html = build(str(md_file), config=None)
    assert "<table>" in html or "<table" in html
    assert "Rope" in html
    assert "2kg" in html
    assert "Lamp" in html
