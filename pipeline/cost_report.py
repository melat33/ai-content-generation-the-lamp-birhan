"""Summarise runs.jsonl per stage -> markdown table for COSTS.md (calls, latency, GPU minutes, list-price equivalent).
   Fill pipeline/prices.json from the providers' pricing pages first.   python pipeline/cost_report.py"""
import json
from collections import defaultdict
from common import RUNS, ROOT

prices = json.loads((ROOT / "pipeline" / "prices.json").read_text())
agg = defaultdict(lambda: dict(calls=0, errors=0, lat=0.0, gpu=0.0, models=set()))
for line in RUNS.read_text(encoding="utf-8").splitlines() if RUNS.exists() else []:
    r = json.loads(line); st = r.get("stage")
    if st in (None, "smoke"): continue
    a = agg[st]
    if r.get("status") == "error" or r.get("ok") is False: a["errors"] += 1; continue
    a["calls"] += 1; a["lat"] += r.get("latency_s", 0) or 0; a["gpu"] += r.get("gpu_minutes", 0) or 0
    if r.get("model"): a["models"].add(str(r["model"]))
print("| stage | models | ok calls | errors | total latency (s) | mean (s) | GPU min | list-price equiv (USD) |\n|---|---|---|---|---|---|---|---|")
for st, a in agg.items():
    pr = prices.get(st, {}); eq = None
    if pr.get("usd_per_call") is not None: eq = a["calls"] * pr["usd_per_call"]
    if pr.get("usd_per_gpu_minute") is not None: eq = a["gpu"] * pr["usd_per_gpu_minute"]
    mean = a["lat"] / a["calls"] if a["calls"] else 0
    print(f"| {st} | {', '.join(sorted(a['models'])) or '-'} | {a['calls']} | {a['errors']} | {a['lat']:.1f} | {mean:.2f} | {a['gpu']:.1f} | {'n/a (fill prices.json)' if eq is None else f'{eq:.2f}'} |")
