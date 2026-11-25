import json, sys
from pathlib import Path
import jsonschema, pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

sb = json.loads((ROOT / "storyboard.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "schema" / "storyboard.schema.json").read_text())


def test_valid():
    jsonschema.validate(sb, schema)


def test_runtime_and_shot_count():
    assert 8 <= len(sb["shots"]) <= 12
    assert 60 <= sum(s["duration_s"] for s in sb["shots"]) <= 90


def test_every_shot_has_a_reason_and_unique_seed():
    assert all(len(s["reason"]) >= 10 for s in sb["shots"])
    seeds = [s["seed"] for s in sb["shots"]]
    assert len(seeds) == len(set(seeds))


def test_bad_storyboard_is_rejected():
    bad = json.loads(json.dumps(sb)); del bad["shots"][0]["reason"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_cache_key_changes_with_text():
    from common import sha
    assert sha("m", "v", "a") != sha("m", "v", "b")
    assert sha("m", "v", "a") == sha("m", "v", "a")
