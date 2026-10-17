from pathlib import Path
import csv, subprocess, sys
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / "model" / "run_valuation.py")], check=True)
with (root / "model" / "ev_sensitivity_proxy.csv").open(encoding="utf-8-sig") as f:
    values = {r["scenario"]: float(r["ev_proxy_krw_bn"]) for r in csv.DictReader(f)}
assert values["bear"] < values["base"] < values["bull"], values
assert all(v > 0 for v in values.values()), values
print("Validation passed: positive, monotonic scenario EV proxies (not fair value).")
