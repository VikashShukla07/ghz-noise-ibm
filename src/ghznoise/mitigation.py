"""Readout-error mitigation (pure NumPy, no Qiskit needed).

The problem: measurement itself is imperfect. A qubit that is really in |1>
is sometimes READ as 0, and vice versa. That makes every result look worse
than the quantum state really was.

The fix, in three steps:
  1. Calibrate: run two tiny circuits, "all qubits in |0>" and "all qubits in
     |1>", and count how often each qubit is misread.
  2. Build each qubit's 2x2 "confusion matrix"
         A_q = [[P(read 0 | was 0), P(read 0 | was 1)],
                [P(read 1 | was 0), P(read 1 | was 1)]]
     and combine them into one 2^n x 2^n matrix with Kronecker products.
     (This assumes each qubit's readout errors are independent.)
  3. Measured probabilities = A @ true probabilities, so
     true probabilities ~= A^-1 @ measured probabilities.
     Inverting can give small negative numbers, so clip them to 0 and
     renormalise.

Bit-order convention (Qiskit's): in a result string like "011", the RIGHTMOST
character is qubit 0. So qubit q is key[-1 - q].
"""

from __future__ import annotations

from functools import reduce

import numpy as np


def counts_to_probs(counts: dict, n_qubits: int) -> np.ndarray:
    """{'00': 480, '11': 520} -> array of 2^n probabilities, index = int(bitstring, 2)."""
    probs = np.zeros(2**n_qubits)
    total = sum(counts.values())
    for key, c in counts.items():
        probs[int(key.replace(" ", ""), 2)] += c / total
    return probs


def bit_of(key: str, qubit: int) -> int:
    """Value of `qubit` in a Qiskit result string (rightmost character = qubit 0)."""
    return int(key.replace(" ", "")[-1 - qubit])


def readout_matrices(counts_all0: dict, counts_all1: dict, n_qubits: int) -> list[np.ndarray]:
    """One 2x2 confusion matrix per qubit, from the two calibration runs."""
    shots0, shots1 = sum(counts_all0.values()), sum(counts_all1.values())
    mats = []
    for q in range(n_qubits):
        p1_given0 = sum(c for k, c in counts_all0.items() if bit_of(k, q) == 1) / shots0
        p0_given1 = sum(c for k, c in counts_all1.items() if bit_of(k, q) == 0) / shots1
        mats.append(np.array([[1 - p1_given0, p0_given1],
                              [p1_given0, 1 - p0_given1]]))
    return mats


def full_matrix(mats: list[np.ndarray]) -> np.ndarray:
    """Kronecker product A_{n-1} (x) ... (x) A_0, matching Qiskit's bit order."""
    return reduce(np.kron, list(reversed(mats)))


def mitigate(probs: np.ndarray, mats: list[np.ndarray]) -> np.ndarray:
    """Undo readout errors: solve A @ p_true = p_measured, clip negatives, renormalise."""
    p_true = np.linalg.solve(full_matrix(mats), probs)
    p_true = np.clip(p_true, 0.0, None)
    return p_true / p_true.sum()


def readout_error_rates(mats: list[np.ndarray]) -> list[float]:
    """Average misread probability per qubit: (P(1|0) + P(0|1)) / 2."""
    return [float((m[1, 0] + m[0, 1]) / 2) for m in mats]
