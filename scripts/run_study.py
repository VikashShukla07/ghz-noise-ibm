"""Run the GHZ noise study on one backend.

Backends:
    ideal  -- perfect simulator (sanity check: everything should be 1.0)
    fake   -- simulator with the noise and wiring of a real IBM chip (offline)
    ibm    -- a real IBM quantum computer (needs a saved IBM Quantum account)

Examples:
    python scripts/run_study.py --backend ideal
    python scripts/run_study.py --backend fake
    python scripts/run_study.py --backend fake --opt-level 3      # noise-aware qubit choice
    python scripts/run_study.py --backend fake --fake-name FakeTorino
    python scripts/run_study.py --backend ibm --qubits 2 3 4 5 --shots 2000
Output: results/ghz_<backend name>_opt<level>.json
"""

import argparse
import json
from pathlib import Path

from ghznoise.experiment import analyse, compile_for_device, run_circuits


def get_backend(kind: str, fake_name: str):
    if kind == "ideal":
        from qiskit_aer import AerSimulator
        return AerSimulator(), "ideal_simulator", False
    if kind == "fake":
        from qiskit_aer import AerSimulator
        import qiskit_ibm_runtime.fake_provider as fakes
        device = getattr(fakes, fake_name)()
        # same noise model + same qubit wiring as the real chip, simulated locally
        return AerSimulator.from_backend(device), f"noisy_sim_{device.name}", False
    if kind == "ibm":
        from qiskit_ibm_runtime import QiskitRuntimeService
        service = QiskitRuntimeService()  # uses the account saved with save_account(...)
        device = service.least_busy(operational=True, simulator=False)
        return device, f"hardware_{device.name}", True
    raise ValueError(kind)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["ideal", "fake", "ibm"], default="fake")
    parser.add_argument("--fake-name", default="FakeBrisbane", help="any class in qiskit_ibm_runtime.fake_provider")
    parser.add_argument("--qubits", type=int, nargs="+", default=[2, 3, 4, 5, 6, 7, 8])
    parser.add_argument("--shots", type=int, default=4000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--opt-level", type=int, default=1, choices=[0, 1, 2, 3],
                        help="transpiler optimisation level; 3 = noise-aware choice of physical qubits")
    args = parser.parse_args()

    backend, label, hardware = get_backend(args.backend, args.fake_name)
    label = f"{label}_opt{args.opt_level}"
    print(f"Backend: {label}")

    # 1. compile every circuit for this device
    compiled = [compile_for_device(n, backend, seed=args.seed, opt_level=args.opt_level) for n in args.qubits]
    circuits = [c[key] for c in compiled for key in ("ghz", "cal0", "cal1")]

    # 2. run them all in one job
    if hardware:
        print(f"Submitting {len(circuits)} circuits x {args.shots} shots to {backend.name} (may queue)...")
    counts = run_circuits(backend, circuits, args.shots, hardware)

    # 3. score each qubit count
    rows = []
    for i, c in enumerate(compiled):
        rows.append(analyse(c, counts[3 * i], counts[3 * i + 1], counts[3 * i + 2], args.shots))

    out = Path("results")
    out.mkdir(exist_ok=True)
    path = out / f"ghz_{label}.json"
    path.write_text(json.dumps({"backend": label, "shots": args.shots, "rows": rows}, indent=2))

    print(f"\n{'n':>3} {'2q gates':>9} {'depth':>6} {'raw':>8} {'+/-':>7} {'mitigated':>10}  physical qubits")
    for r in rows:
        print(f"{r['n']:>3} {r['two_qubit_gates']:>9} {r['depth']:>6} {r['ghz_population_raw']:>8.3f} "
              f"{r['ghz_population_raw_se']:>7.3f} {r['ghz_population_mitigated']:>10.3f}  {r['physical_qubits']}")
    print(f"\nSaved {path}")


if __name__ == "__main__":
    main()
