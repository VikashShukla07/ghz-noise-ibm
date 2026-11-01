# How Entanglement Degrades on Real Quantum Hardware (Qiskit, IBM Quantum)

Prepare GHZ states, (|00…0⟩ + |11…1⟩)/√2, on 2 to 8 qubits and measure how much of the ideal state survives on a perfect simulator, on a simulator with the noise of a real IBM chip, and on real IBM quantum hardware, before and after readout-error mitigation.

> **Status:** Step 1 (simulators) ready. Step 2 (real IBM hardware) next.

## The experiment

1. **Circuit.** Hadamard on qubit 0, then a chain of CNOTs 0→1→2→… Ideally, every measurement gives all zeros or all ones, 50/50.
2. **Score.** GHZ population = P(0…0) + P(1…1): 1.0 for a perfect device, lower when noise flips qubits. It upper-bounds the true GHZ fidelity, because it checks populations but not the phase between the two branches.
3. **Compile for the device.** Qiskit's transpiler maps the circuit onto the chip's native gates and qubit connections; the script records the resulting two-qubit gate count and depth.
4. **Readout-error mitigation.** Two calibration circuits (all qubits in |0⟩, all in |1⟩) on the *same physical qubits* give each qubit's misread probabilities. Inverting the resulting confusion matrix removes measurement errors from the GHZ result, leaving the errors from the gates and decoherence.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
pytest -v                          # 10 tests
```

## Step 1: Simulators

```bash
python scripts/run_study.py --backend ideal    # sanity check: everything 1.000
python scripts/run_study.py --backend fake     # noise model of IBM Brisbane, offline
python scripts/plot_results.py                 # results/ghz_population.png
```

## Repository layout

```
├── src/ghznoise/
│   ├── experiment.py     # GHZ + calibration circuits, compiling, running, scoring
│   └── mitigation.py     # readout confusion matrices and their inversion (NumPy only)
├── scripts/
│   ├── run_study.py      # one backend -> results/ghz_<backend>.json
│   └── plot_results.py   # all backends -> results/ghz_population.png
└── tests/
```

## Tech stack

Python, Qiskit, Qiskit Aer, Qiskit IBM Runtime, NumPy, Matplotlib, pytest
