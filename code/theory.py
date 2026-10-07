"""Closed-form results (Propositions 1-5 of the manuscript). Pure functions; no simulation is run here.

Rate law (Kamal-Sourour, m = 1):   d alpha / dt = C(t) (k1 + k2 alpha) (1 - alpha)^n
a = k1(T), b = k2(T) are the isothermal rate constants, eps = a / b, kr = release rate constant, C = capsule-averaged availability.
"""
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar
from scipy.special import lambertw
from scipy.stats import norm

R_GAS = 8.314


def arrhenius(A, Ea, T_C):
    return A * np.exp(-Ea / (R_GAS * (np.asarray(T_C, dtype=float) + 273.15)))


# ------------------------------------------------------------------ Proposition 2: isothermal cure, no gate
def t_iso_n1(alpha, a, b):
    """Exact time to conversion alpha for n = 1:  t = ln[(a + b alpha) / (a (1 - alpha))] / (a + b)."""
    return np.log((a + b * alpha) / (a * (1.0 - alpha))) / (a + b)


def t_iso(alpha, a, b, n):
    """Exact time to conversion alpha for any n (m = 1), by one quadrature."""
    if n == 1.0:
        return float(t_iso_n1(alpha, a, b))
    return quad(lambda x: 1.0 / ((a + b * x) * (1.0 - x) ** n), 0.0, alpha, limit=200)[0]


def sharpness_iso_n1(a, b):
    t10, t90 = t_iso_n1(0.1, a, b), t_iso_n1(0.9, a, b)
    return (t90 - t10) / t10


def sharpness_law(a, b):
    """Leading-order sharpness S = (t90 - t10)/t10 = 2 ln 9 / ln(b / 9a)  (b >> a)."""
    return 2.0 * np.log(9.0) / np.log(b / (9.0 * a))


# ------------------------------------------------------------------ Proposition 1: availability clock
def clock(t, kr, f=1.0):
    """Integrated availability s(t) = int_0^t C(u) du for C(u) = f (1 - exp(-kr u))."""
    return f * (t - (1.0 - np.exp(-kr * t)) / kr)


def t_gated(alpha, a, b, n, kr, f=1.0):
    """Time to conversion alpha at constant T with relaxing availability: the isothermal time evaluated on the availability clock."""
    target = t_iso(alpha, a, b, n)
    hi = target / f + 10.0 / kr + 10.0
    return brentq(lambda t: clock(t, kr, f) - target, 0.0, hi)


# ------------------------------------------------------------------ Proposition 3: storage leakage of a capsule population
def f_active(Delta, sigma, w0=0.5):
    """Fraction of capsules whose gate is open a margin Delta below the mean melting temperature (Gaussian spread sigma, logistic width w0)."""
    return float(norm.cdf(-Delta / np.sqrt(sigma ** 2 + np.pi ** 2 * w0 ** 2 / 3.0)))


def leak(f, a, b, kr, t):
    """Storage conversion, small-alpha limit: alpha(t) = a int_0^t C(s) exp(b int_s^t C) ds  with C(s) = f (1 - exp(-kr s))."""
    return quad(lambda s: a * f * (1 - np.exp(-kr * s)) * np.exp(b * (clock(t, kr, f) - clock(s, kr, f))), 0.0, t, limit=300)[0]


def f_star(eps, a, b, kr, t):
    """Largest open fraction compatible with a storage conversion eps."""
    return brentq(lambda f: leak(f, a, b, kr, t) - eps, 1e-9, 1.0)


def sigma_star(eps, Delta, a, b, kr, t, w0=0.5):
    """Largest melting-temperature spread that keeps the storage conversion below eps at a margin Delta below the mean melting temperature."""
    if leak(1.0, a, b, kr, t) <= eps:          # even a fully open population stays below the tolerance: no limit on the spread
        return float("inf")
    z = -norm.ppf(f_star(eps, a, b, kr, t))
    s2 = (Delta / z) ** 2 - np.pi ** 2 * w0 ** 2 / 3.0
    return float(np.sqrt(max(s2, 0.0)))


# ------------------------------------------------------------------ Proposition 4: thermal-feedback criticality
def r_max(n, eps=0.0):
    """Maximum of the isothermal rate r(x) = (eps + x)(1 - x)^n over 0 <= x <= 1 (units of b)."""
    res = minimize_scalar(lambda x: -(eps + x) * (1 - x) ** n, bounds=(0, 1), method="bounded", options={"xatol": 1e-12})
    return float(-res.fun)


def Pi_c0(n, eps=0.0):
    """Critical thermal-feedback number Pi = psi * Theta in the limit Theta -> 0:  1 / (e r_max).  For eps = 0: e^-1 (1+n)^(1+n) / n^n."""
    return 1.0 / (np.e * r_max(n, eps))


def theta_peak_qss(Pi, Theta, n, eps=0.0):
    """Quasi-steady peak temperature rise (fraction of the adiabatic rise) below criticality: psi*theta = -W0(-Pi/(e Pi_c)) with psi = Pi/Theta."""
    Pc = Pi_c0(n, eps)
    if Pi > Pc:
        return np.nan
    return float(-lambertw(-Pi / (np.e * Pc), 0).real * Theta / Pi)


def exponent_form(Pi, n, eps=0.0):
    """psi * theta_peak just below criticality: 1 - sqrt(2 (1 - Pi/Pi_c)) (fold normal form)."""
    return 1.0 - np.sqrt(2.0 * (1.0 - Pi / Pi_c0(n, eps)))


def arrhenius_factor(Ar):
    """Multiplicative correction of the critical number for Arrhenius (rather than exponential) temperature dependence: exp(1/Ar)."""
    return float(np.exp(1.0 / Ar))


# ------------------------------------------------------------------ Proposition 5: continuous-flow reactor
def kappa(psi, vartheta):
    return psi * vartheta / (1.0 + vartheta)


def g_curve(alpha, eps, n, kap):
    """Steady-state curve D(alpha) of the flow reactor: D = alpha / [(eps + alpha)(1 - alpha)^n exp(kap alpha)]."""
    return alpha / ((eps + alpha) * (1.0 - alpha) ** n * np.exp(kap * alpha))


def h_fold(alpha, eps, n):
    return n / (1.0 - alpha) + eps / (alpha * (eps + alpha))


def kappa_c(eps, n):
    """Bistability threshold: smallest kappa for which the steady-state curve is S-shaped = min over alpha of h_fold."""
    res = minimize_scalar(lambda x: h_fold(x, eps, n), bounds=(1e-6, 0.9), method="bounded", options={"xatol": 1e-12})
    return float(res.fun), float(res.x)


def folds(eps, n, kap):
    """Two fold conversions (alpha_lo < alpha_hi) where h_fold = kappa, or None when kappa < kappa_c."""
    kc, am = kappa_c(eps, n)
    if kap <= kc:
        return None
    lo = brentq(lambda x: h_fold(x, eps, n) - kap, 1e-9, am)
    hi = brentq(lambda x: h_fold(x, eps, n) - kap, am, 1 - 1e-9)
    return lo, hi


def branches_at(D, eps, n, kap):
    """All steady conversions at a given D (1 or 3 roots)."""
    fl = folds(eps, n, kap)
    edges = [1e-9] + (list(fl) if fl else []) + [1 - 1e-9]
    roots = []
    for x0, x1 in zip(edges[:-1], edges[1:]):
        f0, f1 = g_curve(x0, eps, n, kap) - D, g_curve(x1, eps, n, kap) - D
        if f0 * f1 < 0:
            roots.append(brentq(lambda x: g_curve(x, eps, n, kap) - D, x0, x1, xtol=1e-14))
    return roots


def static_loop_area(eps, n, kap):
    """Area of the static hysteresis loop in the (ln D, alpha) plane and the two switching values of D."""
    fl = folds(eps, n, kap)
    if fl is None:
        return 0.0, None, None
    a_lo, a_hi = fl
    D1, D2 = g_curve(a_lo, eps, n, kap), g_curve(a_hi, eps, n, kap)     # D at the two folds; g has a local max at a_lo and a local min at a_hi
    d_up, d_dn = max(D1, D2), min(D1, D2)                                # up-sweep switching value (upper), down-sweep (lower)
    xs = np.geomspace(d_dn * 1.0000001, d_up * 0.9999999, 4000)
    area = 0.0
    prev = None
    vals = []
    for D in xs:
        r = branches_at(D, eps, n, kap)
        vals.append((r[-1] - r[0]) if len(r) == 3 else 0.0)
    vals = np.array(vals)
    area = float(np.trapezoid(vals, np.log(xs)))
    return area, d_dn, d_up
