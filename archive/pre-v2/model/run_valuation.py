#!/usr/bin/env python3
"""Scenario EV proxy from assumptions.csv; this is not a completed FCFF DCF."""
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data" / "actuals.csv"
ASSUMPTIONS = ROOT / "assumptions.csv"
OUT = ROOT / "ev_sensitivity_proxy.csv"

with DATA.open(encoding="utf-8-sig") as f:
    actuals = list(csv.DictReader(f))
with ASSUMPTIONS.open(encoding="utf-8-sig") as f:
    assumption_rows = list(csv.DictReader(f))
base_actual = next(r for r in actuals if r["period"] == "2025")
rev0 = float(base_actual["revenue_bn_krw"])
by_driver = {r["driver"]: r for r in assumption_rows}
required = ["revenue_growth_y1", "revenue_growth_y2_y5", "terminal_growth", "WACC", "normalized_tax", "EBIT_margin_y1_to_y5", "normalized_ROIC"]
missing = [k for k in required if k not in by_driver]
if missing:
    raise ValueError(f"Missing assumption drivers: {missing}")
scenarios = ["bear", "base", "bull"]
out = []
for name in scenarios:
    p = {k: float(by_driver[k][name]) for k in required}
    if p["WACC"] <= p["terminal_growth"]:
        raise ValueError(f"WACC must exceed terminal growth for {name}")
    revenue, pv = rev0, 0.0
    for year in range(1, 6):
        growth = p["revenue_growth_y1"] if year == 1 else p["revenue_growth_y2_y5"]
        revenue *= 1 + growth
        nopat = revenue * p["EBIT_margin_y1_to_y5"] * (1 - p["normalized_tax"])
        # Steady-state reinvestment identity. ROIC is an analyst assumption, not audited ROIC.
        proxy_fcff = nopat * (1 - growth / p["normalized_ROIC"])
        pv += proxy_fcff / (1 + p["WACC"]) ** year
    terminal_nopat = nopat * (1 + p["terminal_growth"])
    terminal_fcff = terminal_nopat * (1 - p["terminal_growth"] / p["normalized_ROIC"])
    terminal = terminal_fcff / (p["WACC"] - p["terminal_growth"])
    ev = pv + terminal / (1 + p["WACC"]) ** 5
    out.append({
        "scenario": name,
        "revenue_growth_y1": p["revenue_growth_y1"],
        "revenue_growth_y2_y5": p["revenue_growth_y2_y5"],
        "normalized_ebit_margin": p["EBIT_margin_y1_to_y5"],
        "normalized_roic": p["normalized_ROIC"],
        "wacc": p["WACC"],
        "terminal_growth": p["terminal_growth"],
        "ev_proxy_krw_bn": round(ev, 1),
        "status": "exploratory EV proxy from assumptions.csv; not fair value; analyst ROIC/WACC and audited FCFF/equity bridge inputs pending",
    })
with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=out[0].keys())
    w.writeheader()
    w.writerows(out)
for row in out:
    print(f"{row['scenario']}: EV proxy KRW {row['ev_proxy_krw_bn']:,.1f}bn")
print(f"Wrote {OUT}")
