"""GHZ experiment: build circuits, compile them for a device, run them, score them.

GHZ state on n qubits:  (|00...0> + |11...1>) / sqrt(2)
  * the n-qubit generalisation of a Bell state (n = 2 IS a Bell state);
  * made by a Hadamard on qubit 0, then a chain of CNOTs 0->1, 1->2, ...;
  * ideally, measuring gives ONLY all-zeros or all-ones, 50/50.

Score ("GHZ population") = P(all zeros) + P(all ones).
  * 1.0 for a perfect device; anything else means noise flipped some qubits.
  * It is an UPPER BOUND on the true GHZ fidelity: it checks the populations
    but not the phase coherence between |00..0> and |11..1>. A full fidelity
    measurement would add parity measurements in other bases.

Why it drops with n: more qubits -> more CNOTs (n - 1) and more qubits that can
decay or be misread, and if the chip's wiring doesn't link the chosen qubits,
the compiler adds SWAPs (3 CNOTs each).
"""

from __future__ import annotations

import math

from qiskit import QuantumCircuit, transpile

from ghznoise.mitigation import counts_to_probs, mitigate, readout_error_rates, readout_matrices


# ---------------------------------------------------------------- circuits
def ghz_circuit(n: int) -> QuantumCircuit:
    qc = QuantumCircuit(n, name=f"ghz_{n}")
    qc.h(0)
    for q in range(n - 1):
        qc.cx(q, q + 1)
    qc.measure_all()  # adds a classical register called "meas"
    return qc


def calibration_circuits(n: int) -> tuple[QuantumCircuit, QuantumCircuit]:
    """'Prepare all |0>, measure' and 'prepare all |1>, measure': for readout mitigation."""
    zeros = QuantumCircuit(n, name=f"cal0_{n}")
    zeros.measure_all()
    ones = QuantumCircuit(n, name=f"cal1_{n}")
    ones.x(range(n))
    ones.measure_all()
    return zeros, ones


# ---------------------------------------------------------------- compiling
def compile_for_device(n: int, backend, seed: int = 0, opt_level: int = 1) -> dict:
    """Transpile the GHZ circuit for the device, then put the calibration
    circuits on the SAME physical qubits (readout errors differ per qubit).

    opt_level 1: takes the first set of connected qubits that fits (often 0, 1, 2, ...).
    opt_level 3: also scores candidate qubit sets by their reported error rates
                 and picks the best ones ("noise-aware layout").
    """
    ghz = transpile(ghz_circuit(n), backend=backend, optimization_level=opt_level, seed_transpiler=seed)
    layout = ghz.layout.final_index_layout() if ghz.layout is not None else list(range(n))
    cal0, cal1 = (
        transpile(c, backend=backend, initial_layout=layout, optimization_level=opt_level, seed_transpiler=seed)
        for c in calibration_circuits(n)
    )
    return {"n": n, "ghz": ghz, "cal0": cal0, "cal1": cal1, "physical_qubits": list(layout)}


def two_qubit_gate_count(circuit: QuantumCircuit) -> int:
    """Number of two-qubit gates after compilation (CNOT/ECR/CZ; SWAPs appear as 3 of these)."""
    return sum(
        1 for inst in circuit.data
        if inst.operation.num_qubits == 2 and inst.operation.name not in ("barrier", "measure")
    )


# ---------------------------------------------------------------- running
def run_circuits(backend, circuits: list, shots: int, hardware: bool) -> list[dict]:
    """Run compiled circuits; return one counts dict per circuit.

    Simulators: backend.run(...).
    Real IBM hardware: the Sampler primitive (the current IBM interface).
    All circuits go in ONE job, which saves queue time and free-plan minutes.
    """
    if hardware:
        from qiskit_ibm_runtime import SamplerV2

        result = SamplerV2(mode=backend).run(circuits, shots=shots).result()
        return [pub.data.meas.get_counts() for pub in result]
    result = backend.run(circuits, shots=shots).result()
    return [result.get_counts(i) for i in range(len(circuits))]


# ---------------------------------------------------------------- scoring
def ghz_population(probs) -> float:
    return float(probs[0] + probs[-1])


def standard_error(p: float, shots: int) -> float:
    """Shot-noise error bar of a measured probability: sqrt(p(1-p)/shots)."""
    return math.sqrt(max(p * (1 - p), 0.0) / shots)


def analyse(compiled: dict, counts_ghz: dict, counts_cal0: dict, counts_cal1: dict, shots: int) -> dict:
    n = compiled["n"]
    raw = counts_to_probs(counts_ghz, n)
    mats = readout_matrices(counts_cal0, counts_cal1, n)
    fixed = mitigate(raw, mats)
    raw_pop = ghz_population(raw)
    return {
        "n": n,
        "physical_qubits": compiled["physical_qubits"],
        "two_qubit_gates": two_qubit_gate_count(compiled["ghz"]),
        "depth": compiled["ghz"].depth(),
        "ghz_population_raw": raw_pop,
        "ghz_population_raw_se": standard_error(raw_pop, shots),
        "ghz_population_mitigated": ghz_population(fixed),
        "readout_error_per_qubit": readout_error_rates(mats),
        "p_all_zeros": float(raw[0]),
        "p_all_ones": float(raw[-1]),
    }
