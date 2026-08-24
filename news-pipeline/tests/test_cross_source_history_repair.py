import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "source" / "news" / "data"


def _js_payload(path):
    raw = path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\});\s*$", raw, re.S)
    assert match
    return json.loads(match.group(1))


def test_august_3_deepseek_restatement_is_only_in_raw_archives():
    daily = _js_payload(DATA / "daily" / "2026-08-03.js")
    assert daily["stats"]["pick_count"] == 23
    assert all(item.get("id") != "pick-193" for item in daily["items"])
    assert all("pick-193" not in theme.get("member_ids", [])
               for theme in daily["themes"])
    assert daily["quality"]["enrichment_audited_events"] == 24
    assert "cross_source_restatements" not in daily["quality"]

    registry = json.loads((DATA / "events.json").read_text(encoding="utf-8"))
    line = next(event for event in registry["events"]
                if event.get("event_id") == "evt-20260801-f55954")
    assert line["last_seen"] == "2026-08-01"
    assert [row["date"] for row in line["history"]] == ["2026-08-01"]

    score_history = json.loads(
        (DATA / "score_history.json").read_text(encoding="utf-8"))
    assert score_history["days"]["2026-08-03"]["eligible_scores"].count(69) == 1

    # source_health.json intentionally retains only the latest 14 production
    # days, so durable repair evidence must come from the archives below.
    cls_url = "https://www.cls.cn/detail/2443548"
    all_payload = _js_payload(DATA / "all" / "2026-08-03.js")
    all_row = next(row for row in all_payload["items"] if row.get("u") == cls_url)
    assert all_row["score"] == 69
    seen_payload = json.loads(
        (DATA / "news-seen" / "2026-08-03.json").read_text(encoding="utf-8"))
    assert any(row.get("url") == cls_url for row in seen_payload["items"])

    public_refs = ((DATA / "feed.xml").read_text(encoding="utf-8")
                   + (DATA / "search_index.js").read_text(encoding="utf-8"))
    assert "2026-08-03:pick-193" not in public_refs
    weekly = (DATA / "weekly" / "2026-W31.js").read_text(encoding="utf-8")
    assert "2026-08-01:pick-46" in weekly
    assert "2026-08-03:pick-193" not in weekly


def test_august_3_quality_health_remains_original_run_telemetry():
    health = json.loads(
        (DATA / "quality-health.json").read_text(encoding="utf-8"))
    row = next(record for record in health["records"]
               if record.get("date") == "2026-08-03")
    assert row["enrichment_audited_events"] == 24
    assert row["removed_fields"] == 51
    assert "cross_source_restatements" not in row
