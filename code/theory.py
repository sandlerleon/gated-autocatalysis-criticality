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


def sharpness_exact_n1(a, b):
    """Exact n = 1 sharpness: S = ln[9 (a + 0.9 b) / (a + 0.1 b)] / ln[(a + 0.1 b) / (0.9 a)]."""
    return float(np.log(9.0 * (a + 0.9 * b) / (a + 0.1 * b)) / np.log((a + 0.1 * b) / (0.9 * a)))


def sharpness_law(a, b):
    """Leading-order sharpness S = (t90 - t10)/t10 = 2 ln 9 / ln(b / 9a)  (b >> a)."""
    return 2.0 * np.log(9.0) / np.log(b / (9.0 * a))


# ------------------------------------------------------------------ Proposition 1: availability clock
def clock(t, kr, f=1.0):
    """Integrated availability s(t) = int_0^t C(u) du for C(u) = f (1 - exp(-kr u))."""
    return f * (t - (1.0 - np.exp(-kr * t)) / kr)


def gate_delay(t_gated, kr):
    """Delay of a fully open population relative to the ungated resin, as a function of the gated time: tau_rel [1 - exp(-t_gated / tau_rel)]."""
    return (1.0 - np.exp(-kr * t_gated)) / kr


def t_gated(alpha, a, b, n, kr, f=1.0):
    """Time to conversion alpha at constant T with relaxing availability: the isothermal time evaluated on the availability clock."""
    target = t_iso(alpha, a, b, n)
    hi = target / f + 10.0 / kr + 10.0
    return brentq(lambda t: clock(t, kr, f) - target, 0.0, hi)


# ------------------------------------------------------------------ Proposition 3: storage leakage of a capsule population
def f_active(Delta, sigma, w0=0.5):
    """Fraction of capsules whose gate is open a margin Delta below the mean melting temperature (Gaussian spread sigma, logistic width w0)."""
    return float(norm.cdf(-Delta / np.sqrt(sigma ** 2 + np.pi ** 2 * w0 ** 2 / 3.0)))


def t_eff(kr, t):
    """Effective open time of a fully open population started at zero availability: t - (1 - exp(-kr t)) / kr."""
    return t - (1.0 - np.exp(-kr * t)) / kr


def leak(f, a, b, kr, t):
    """Storage conversion in the small-conversion (linearized) limit, closed form: alpha_s = (a/b) [exp(b f t_eff) - 1]."""
    return float((a / b) * np.expm1(b * f * t_eff(kr, t)))


def leak_quad(f, a, b, kr, t):
    """The same quantity from the defining integral alpha_s = a int_0^t <C>(s) exp(b int_s^t <C>) ds (used to test the closed form)."""
    return quad(lambda s: a * f * (1 - np.exp(-kr * s)) * np.exp(b * (clock(t, kr, f) - clock(s, kr, f))), 0.0, t, limit=300)[0]


def f_star(eta, a, b, kr, t):
    """Largest open fraction compatible with a storage conversion eta (exact inversion of the linearized closed form)."""
    return float(np.log1p(eta * b / a) / (b * t_eff(kr, t)))


def sigma_star(eta, Delta, a, b, kr, t, w0=0.5):
    """Largest melting-temperature spread that keeps the storage conversion below eta at a margin Delta below the mean melting temperature:
    sigma* = sqrt[(Delta / z*)^2 - pi^2 w0^2 / 3], z* = -Phi^-1(f*).  Returns inf when f* >= 1/2 (no finite bound) and nan when the radicand is negative
    (the logistic activation width alone already exceeds the tolerance)."""
    fs = f_star(eta, a, b, kr, t)
    if fs >= 0.5:
        return float("inf")
    z = -norm.ppf(fs)
    s2 = (Delta / z) ** 2 - np.pi ** 2 * w0 ** 2 / 3.0
    return float(np.sqrt(s2)) if s2 >= 0 else float("nan")


# ------------------------------------------------------------------ Proposition 4: thermal-feedback criticality
def r_max(n, eps=0.0):
    """Maximum of the isothermal rate r(x) = (eps + x)(1 - x)^n over 0 <= x <= 1 (units of b), closed form for n eps < 1:
    x* = (1 - n eps)/(1 + n),  r_max = n^n (1 + eps)^(n+1) / (1 + n)^(n+1)."""
    if n * eps >= 1.0:
        return float(eps)
    return float(n ** n * (1.0 + eps) ** (n + 1.0) / (1.0 + n) ** (n + 1.0))


def Pi_c0(n, eps=0.0):
    """Critical thermal-feedback number of the frozen-conversion quasi-steady manifold, Pi_c = 1/(e r_max) = (1+n)^(1+n) / [e n^n (1+eps)^(1+n)].
    For eps -> 0:  e^-1 (1+n)^(1+n) / n^n."""
    return 1.0 / (np.e * r_max(n, eps))


def arrhenius_fold_y(Ar):
    """Small root of y = (1 + y/Ar)^2: the frozen-conversion fold of exp[y / (1 + y/Ar)] (a single Arrhenius source)."""
    return float(brentq(lambda y: y - (1.0 + y / Ar) ** 2, 0.5, 0.5 * Ar))


def arrhenius_fold_factor(Ar):
    """Ratio of the frozen-conversion critical number for a single Arrhenius source to its exponential limit: e * y_f * exp(-y_f / (1 + y_f/Ar)).
    Its large-Ar expansion is exp(1/Ar) (first order)."""
    y = arrhenius_fold_y(Ar)
    return float(np.e * y * np.exp(-y / (1.0 + y / Ar)))


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
    """First-order (large-Ar) correction of the critical number for Arrhenius rather than exponential temperature dependence: exp(1/Ar)."""
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


def qfun(alpha, eps, n):
    return alpha / (eps + alpha) - n * alpha / (1.0 - alpha)


def jacobian(alpha, eps, n, psi, vt):
    """Jacobian of (d alpha/dt', d theta/dt') at the steady state with conversion alpha:  [[q - 1, psi alpha], [q, psi alpha - 1 - 1/vt]]."""
    q = qfun(alpha, eps, n)
    return np.array([[q - 1.0, psi * alpha], [q, psi * alpha - 1.0 - 1.0 / vt]])


def trace_det(alpha, eps, n, psi, vt):
    q = qfun(alpha, eps, n)
    return float(q + psi * alpha - 2.0 - 1.0 / vt), float((1.0 + 1.0 / vt) * (1.0 - q) - psi * alpha)


def upper_stable_from(eps, n, psi, vt):
    """Conversion above which the upper steady branch is stable (trace < 0, det > 0), and the way it is lost: 'fold' when the trace is negative at the
    upper fold (saddle-node) or 'hopf' when the trace vanishes at a larger conversion (a Hopf-type point, where det > 0)."""
    kap = kappa(psi, vt)
    fl = folds(eps, n, kap)
    if fl is None:
        return None
    hi = fl[1]
    tr_hi, _ = trace_det(hi, eps, n, psi, vt)
    if tr_hi <= 0:
        return hi, "fold"
    aH = brentq(lambda x: trace_det(x, eps, n, psi, vt)[0], hi, 1 - 1e-9)
    return aH, "hopf"


def bistable_window(eps, n, psi, vt):
    """Window of D in which the lower and the upper steady branch are both stable (two attractors), or None."""
    kap = kappa(psi, vt)
    fl = folds(eps, n, kap)
    if fl is None:
        return None
    a_ext, kind = upper_stable_from(eps, n, psi, vt)
    D_ext = float(g_curve(a_ext, eps, n, kap))
    D_ign = float(g_curve(fl[0], eps, n, kap))
    if D_ext >= D_ign:
        return None
    return dict(alpha_ext=float(a_ext), kind=kind, D_ext=D_ext, D_ign=D_ign, lnD_ext=float(np.log(D_ext)), lnD_ign=float(np.log(D_ign)),
                D_fold_hi=float(g_curve(fl[1], eps, n, kap)), alpha_fold_lo=float(fl[0]), alpha_fold_hi=float(fl[1]))


def attractor_loop_area(eps, n, psi, vt, N=3000):
    """Area of the static loop of the two stable branches in the (ln D, alpha) plane: integral of (alpha_upper - alpha_lower) d ln D over the bistable window."""
    w = bistable_window(eps, n, psi, vt)
    if w is None:
        return 0.0, None
    kap = kappa(psi, vt)
    xs = np.linspace(w["lnD_ext"], w["lnD_ign"], N + 2)[1:-1]
    vals = []
    for lnD in xs:
        r = branches_at(np.exp(lnD), eps, n, kap)
        vals.append(r[-1] - r[0] if len(r) == 3 else 0.0)
    return float(np.trapezoid(vals, xs)), w


def static_loop_area(eps, n, kap):
    """Area between the outermost steady branches over the full multiplicity window (fold to fold), i.e. the equilibrium-multiplicity loop. This is NOT
    the hysteresis loop when the upper branch is unstable near its fold; use attractor_loop_area for that."""
    fl = folds(eps, n, kap)
    if fl is None:
        return 0.0, None, None
    a_lo, a_hi = fl
    D1, D2 = g_curve(a_lo, eps, n, kap), g_curve(a_hi, eps, n, kap)
    d_up, d_dn = max(D1, D2), min(D1, D2)
    xs = np.geomspace(d_dn * 1.0000001, d_up * 0.9999999, 4000)
    vals = np.array([(lambda r: (r[-1] - r[0]) if len(r) == 3 else 0.0)(branches_at(D, eps, n, kap)) for D in xs])
    return float(np.trapezoid(vals, np.log(xs))), d_dn, d_up
