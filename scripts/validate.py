from pathlib import Path
import csv, subprocess, sys
root = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(root / "model" / "run_valuation.py")], check=True)
with (root / "model" / "ev_sensitivity_proxy.csv").open(encoding="utf-8-sig") as f:
    output = {r["scenario"]: r for r in csv.DictReader(f)}
with (root / "model" / "assumptions.csv").open(encoding="utf-8-sig") as f:
    inputs = {r["driver"]: r for r in csv.DictReader(f)}
values = {case: float(row["ev_proxy_krw_bn"]) for case, row in output.items()}
assert set(output) == {"bear", "base", "bull"}, output.keys()
assert values["bear"] < values["base"] < values["bull"], values
assert all(v > 0 for v in values.values()), values
# Guard against assumptions.csv drifting away from the values actually used in the model.
for case, result in output.items():
    assert float(result["revenue_growth_y1"]) == float(inputs["revenue_growth_y1"][case])
    assert float(result["revenue_growth_y2_y5"]) == float(inputs["revenue_growth_y2_y5"][case])
    assert float(result["normalized_ebit_margin"]) == float(inputs["EBIT_margin_y1_to_y5"][case])
    assert float(result["normalized_roic"]) == float(inputs["normalized_ROIC"][case])
    assert float(result["wacc"]) == float(inputs["WACC"][case])
print("Validation passed: assumptions.csv drives positive, monotonic EV proxies; outputs are not fair value.")
