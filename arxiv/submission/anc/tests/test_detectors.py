"""Fast unit tests for the estimators (run with `pytest -q`)."""
import numpy as np

from shadowdollars.detectors import bunching as B
from shadowdollars.detectors import causal as C
from shadowdollars.detectors import flows as Fl
from shadowdollars.simulate import country_panel


def _amounts(n, med, sig, rng, hassle=0.35, T=50_000):
    z = np.exp(rng.normal(np.log(med), sig, n))
    move = (z >= T) & (z < 1.25 * T) & (rng.random(n) < hassle)
    z[move] = rng.uniform(0.95 * T, 0.999 * T, move.sum())
    return z


def test_bunching_difference_null_and_alternative():
    rng = np.random.default_rng(0)
    usdt = _amounts(200_000, 20_000, 0.9, rng)
    other = _amounts(200_000, 8_000, 1.0, rng)
    null = B.difference_in_bunching(usdt, other, reps=100)
    assert abs(null.delta) < 3 * null.se            # slope-invariant: no false signal
    structured = rng.uniform(40_000, 49_999, 3_000)
    alt = B.difference_in_bunching(np.concatenate([usdt, structured]), other, reps=100)
    assert alt.delta > 0 and alt.p_one_sided < 0.01


def test_direction_matters_for_hubs():
    # 0 = flagged, 1 = layering wallet paying 0 and cashing out at hub 2; hub pays user 3
    edges = np.array([[1, 0], [1, 2], [2, 3]])
    d_dir = Fl.distance_to_flagged(edges, 4, np.array([0]), directed=True)
    d_und = Fl.distance_to_flagged(edges, 4, np.array([0]), directed=False)
    assert d_und[2] == 2 and np.isinf(d_dir[2]) and d_dir[1] == 1


def test_synthetic_control_recovers_effect():
    Y = country_panel(n_donors=19, effect=-0.15, seed=21)
    r = C.synthetic_control(Y, treated=0, t0=104)
    assert abs(r.att + 0.15) < 0.03 and r.p_value <= 0.05
    assert abs(r.weights.sum() - 1) < 1e-8 and (r.weights >= 0).all()


def test_displacement_keeps_total_constant():
    # quadratic costs c_j = a_j q^2 / 2 with a tax tau on channel E = 0
    a = np.array([2.0, 1.0, 4.0]); M = 10.0

    def solve(tau):
        lam = (M + tau / a[0]) / np.sum(1 / a)
        q = lam / a
        q[0] -= tau / a[0]
        return q

    q0, q1 = solve(0.0), solve(0.5)
    assert q1[0] < q0[0] and (q1[1:] > q0[1:]).all() and np.isclose(q1.sum(), q0.sum())
