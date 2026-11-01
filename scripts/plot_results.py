"""Plot every results/ghz_*.json on one figure.

Run after one or more run_study.py runs:
    python scripts/plot_results.py
Output: results/ghz_population.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd"]


def main() -> None:
    files = sorted(Path("results").glob("ghz_*.json"))
    if not files:
        raise SystemExit("No results yet: run scripts/run_study.py first.")

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for color, f in zip(COLORS, files):
        data = json.loads(f.read_text())
        rows = sorted(data["rows"], key=lambda r: r["n"])
        n = [r["n"] for r in rows]
        raw = [r["ghz_population_raw"] for r in rows]
        err = [r["ghz_population_raw_se"] for r in rows]
        fixed = [r["ghz_population_mitigated"] for r in rows]
        ax.errorbar(n, raw, yerr=err, fmt="o-", color=color, capsize=3, label=f"{data['backend']} (raw)")
        if "ideal" not in data["backend"]:
            ax.plot(n, fixed, "s--", color=color, alpha=0.7, label=f"{data['backend']} (readout-mitigated)")

    ax.axhline(1.0, color="gray", ls=":", lw=1)
    ax.set_xlabel("number of qubits in the GHZ state")
    ax.set_ylabel("GHZ population  P(0...0) + P(1...1)")
    ax.set_title("How entanglement degrades with size")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig("results/ghz_population.png", dpi=150)
    print("Saved results/ghz_population.png")


if __name__ == "__main__":
    main()
