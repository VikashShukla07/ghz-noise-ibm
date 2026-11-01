import numpy as np

from ghznoise.mitigation import bit_of, counts_to_probs, full_matrix, mitigate, readout_matrices


def test_counts_to_probs_uses_binary_index():
    p = counts_to_probs({"00": 30, "11": 70}, 2)
    assert np.allclose(p, [0.3, 0, 0, 0.7])


def test_rightmost_character_is_qubit_0():
    assert bit_of("01", 0) == 1 and bit_of("01", 1) == 0


def test_perfect_readout_gives_identity():
    mats = readout_matrices({"000": 100}, {"111": 100}, 3)
    assert np.allclose(full_matrix(mats), np.eye(8))


def test_readout_matrix_picks_out_the_noisy_qubit():
    # qubit 0 misread 10% of the time in both directions, qubit 1 perfect
    mats = readout_matrices({"00": 90, "01": 10}, {"11": 90, "10": 10}, 2)
    assert np.allclose(mats[0], [[0.9, 0.1], [0.1, 0.9]])
    assert np.allclose(mats[1], np.eye(2))


def test_mitigation_recovers_the_true_distribution():
    true = np.array([0.5, 0, 0, 0.5])                     # ideal Bell state
    mats = [np.array([[0.95, 0.08], [0.05, 0.92]]), np.array([[0.97, 0.04], [0.03, 0.96]])]
    measured = full_matrix(mats) @ true
    assert measured[0] + measured[3] < 0.95               # noise hides the Bell state
    assert np.allclose(mitigate(measured, mats), true, atol=1e-9)


def test_mitigated_probs_are_valid():
    mats = [np.array([[0.9, 0.1], [0.1, 0.9]])]
    out = mitigate(np.array([0.99, 0.01]), mats)          # would give a negative entry before clipping
    assert np.all(out >= 0) and np.isclose(out.sum(), 1)
