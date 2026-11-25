"""Validate storyboard.json against schema/storyboard.schema.json plus a few sanity rules."""
import sys
from common import load_storyboard

try:
    sb = load_storyboard()
except Exception as e:
    sys.exit(f"INVALID storyboard: {str(e)[:600]}")

ids = [s["id"] for s in sb["shots"]]
assert len(ids) == len(set(ids)), "duplicate shot ids"
total = sum(s["duration_s"] for s in sb["shots"])
assert 55 <= total <= 95, f"planned runtime {total}s should be near 60-90s"
print(f"storyboard OK: {len(ids)} shots, planned {total}s")
