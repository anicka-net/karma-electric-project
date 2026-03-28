import importlib.util
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path("/home/anicka/playground/karma-electric-project")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


init_db = _load_module(REPO_ROOT / "scripts" / "init_training_db.py", "init_training_db")
training_db = _load_module(REPO_ROOT / "scripts" / "training_db.py", "training_db")


def test_create_schema_creates_examples_table_and_fts():
    conn = sqlite3.connect(":memory:")
    init_db.create_schema(conn)

    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'trigger')"
        )
    }
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(examples)")
    }

    assert "examples" in tables
    assert "reasoning" in columns
    assert "examples_fts" in tables
    assert "examples_ai" in tables


def test_detect_template_flags_known_formula():
    text = "You're reifying this relationship as a solid permanent thing."
    assert init_db.detect_template(text) == "reification-template"


def test_export_respects_template_and_score_filters(tmp_path, monkeypatch):
    db_path = tmp_path / "training.db"
    conn = sqlite3.connect(str(db_path))
    init_db.create_schema(conn)
    now = "2026-03-28T12:00:00"

    rows = [
        (
            "keep-1",
            "accepted",
            "unit",
            "ethics",
            json.dumps([{"role": "assistant", "content": "ok"}]),
            35,
            "",
            None,
            None,
            now,
            None,
            None,
        ),
        (
            "tmpl-1",
            "accepted",
            "unit",
            "ethics",
            json.dumps([{"role": "assistant", "content": "template"}]),
            35,
            "",
            None,
            "reification-template",
            now,
            None,
            None,
        ),
        (
            "low-1",
            "accepted",
            "unit",
            "ethics",
            json.dumps([{"role": "assistant", "content": "low"}]),
            27,
            "",
            None,
            None,
            now,
            None,
            None,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO examples
        (id, status, source, category, conversations, hermes_score,
         hermes_evaluation, rejection_reason, template_flag, added_at, scored_at, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(training_db, "DB_PATH", db_path)
    out_path = tmp_path / "export.jsonl"
    args = type(
        "Args",
        (),
        {"output": str(out_path), "exclude_templates": True, "min_score": 28, "system_prompt": None, "category_prompt": None, "reasoning": False},
    )()

    training_db.cmd_export(args)

    exported = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert [ex["id"] for ex in exported] == ["keep-1"]
