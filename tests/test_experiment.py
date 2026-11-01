"""Tests that need Qiskit + Qiskit Aer."""

import pytest

pytest.importorskip("qiskit")
AerSimulator = pytest.importorskip("qiskit_aer").AerSimulator

from ghznoise.experiment import (  # noqa: E402
    analyse,
    calibration_circuits,
    compile_for_device,
    ghz_circuit,
    run_circuits,
    two_qubit_gate_count,
)


def test_ghz_circuit_has_n_minus_1_cnots():
    for n in (2, 3, 5):
        assert ghz_circuit(n).count_ops()["cx"] == n - 1


def test_ideal_ghz_only_gives_all_zeros_or_all_ones():
    sim = AerSimulator()
    c = compile_for_device(4, sim)
    counts = run_circuits(sim, [c["ghz"], c["cal0"], c["cal1"]], shots=2000, hardware=False)
    assert set(counts[0]) <= {"0000", "1111"}
    assert 0.4 < counts[0].get("0000", 0) / 2000 < 0.6
    assert counts[1] == {"0000": 2000} and counts[2] == {"1111": 2000}
    row = analyse(c, *counts, shots=2000)
    assert row["ghz_population_raw"] == 1.0 and row["ghz_population_mitigated"] == 1.0


def test_calibration_circuits_prepare_all_zeros_and_all_ones():
    zeros, ones = calibration_circuits(3)
    assert "x" not in zeros.count_ops() and ones.count_ops()["x"] == 3


def test_two_qubit_count_ignores_barriers_and_measurements():
    assert two_qubit_gate_count(ghz_circuit(2)) == 1
