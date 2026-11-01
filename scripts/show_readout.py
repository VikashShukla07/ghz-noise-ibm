"""Print each physical qubit's readout error from a results file.

Example:
    python scripts/show_readout.py results/ghz_noisy_sim_fake_brisbane_opt1.json
"""

import json
import sys

data = json.loads(open(sys.argv[1]).read())
row = max(data["rows"], key=lambda r: r["n"])  # the largest GHZ state uses every qubit
print(f"{data['backend']}: readout error per physical qubit (n = {row['n']})")
for phys, err in zip(row["physical_qubits"], row["readout_error_per_qubit"]):
    print(f"  qubit {phys:>3}: {err:6.2%}  {'#' * round(err * 200)}")
