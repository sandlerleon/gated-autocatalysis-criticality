"""Reference numerics for the thermal-feedback and flow-reactor results (adaptive stiff integration)."""
import numpy as np
from scipy.integrate import solve_ivp

R_GAS = 8.314
A1, EA1 = 2.0e3, 5.0e4
A2, EA2 = 2.5e7, 6.5e4


def fk_peak(Pi, Theta, n, eps=3e-3, tmax=40.0):
    """Peak temperature rise (fraction of the adiabatic rise) of the ungated, isothermally started batch problem in the exponential (Frank-Kamenetskii) form.
    tau = k2 t;  d theta/d tau = -theta/Theta + r;  d alpha/d tau = r;  r = (eps + alpha)(1 - alpha)^n exp(psi theta),  psi = Pi / Theta."""
    psi = Pi / Theta

    def f(t, y):
        th, al = y
        r = (eps + max(al, 0.0)) * np.exp(min(psi * th, 300.0)) * max(1.0 - al, 0.0) ** n
        return [-th / Theta + r, r]
    sol = solve_ivp(f, [0, tmax], [0.0, 0.0], method="LSODA", rtol=1e-9, atol=1e-13, max_step=0.02)
    return float(sol.y[0].max())


def fk_critical(Theta, n, eps=3e-3, thr=0.3, iters=30):
    lo, hi = 0.3, 8.0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if fk_peak(mid, Theta, n, eps) > thr:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def arr_peak(Tinf_C, tau_th, dtad, n=1.5, gated_tau_rel=None):
    """Same problem with true Arrhenius rate constants (dimensional). Optional first-order release with time constant gated_tau_rel (availability C starts at 0)."""
    Tk = Tinf_C + 273.15
    k2 = A2 * np.exp(-EA2 / (R_GAS * Tk))
    tmax = 60.0 / k2

    def f(t, y):
        T, al, C = y
        TK = max(T, 200.0)
        a_ = min(max(al, 0.0), 1.0)
        r = C * (A1 * np.exp(-EA1 / (R_GAS * TK)) + A2 * np.exp(-EA2 / (R_GAS * TK)) * max(a_, 1e-9)) * (1 - a_) ** n
        dC = 0.0 if gated_tau_rel is None else (1.0 - C) / gated_tau_rel
        return [(Tk - T) / tau_th + dtad * r, r, dC]
    sol = solve_ivp(f, [0, tmax], [Tk, 0.0, 1.0 if gated_tau_rel is None else 0.0], method="LSODA", rtol=1e-8, atol=1e-12)
    return float((sol.y[0].max() - Tk) / dtad)


def arr_critical(Tinf_C, tau_th, n=1.5, thr=0.3, gated_tau_rel=None, iters=26):
    lo, hi = np.log(3.0), np.log(8000.0)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if arr_peak(Tinf_C, tau_th, np.exp(mid), n, gated_tau_rel) > thr:
            hi = mid
        else:
            lo = mid
    dtad = float(np.exp(0.5 * (lo + hi)))
    Tk = Tinf_C + 273.15
    psi = dtad * EA2 / (R_GAS * Tk ** 2)
    k2 = A2 * np.exp(-EA2 / (R_GAS * Tk))
    Ar = EA2 / (R_GAS * Tk)
    return dict(dtad_c=dtad, psi_c=psi, Theta=tau_th * k2, Pi_c=psi * tau_th * k2, Ar=Ar, eps=A1 * np.exp(-EA1 / (R_GAS * Tk)) / k2)


def _flow_rhs(D, psi, vt, n, eps):
    c = 1.0 + 1.0 / vt

    def f(t, y):
        th, al = y
        r = (eps + max(al, 0.0)) * np.exp(min(psi * th, 300.0)) * max(1.0 - al, 0.0) ** n
        return [D * r - th * c, D * r - al]
    return f


def flow_sweep(v, lnD_a, lnD_b, psi, vt, n=1.5, eps=3e-3, dwell=20.0, dt_out=0.05, rtol=1e-8, atol=1e-12):
    """Up-then-down sweep of ln D at rate v (per residence time) of the continuous-flow reactor, in units t' = t / tau_res:
        d alpha/dt' = D r - alpha;   d theta/dt' = D r - theta (1 + 1/vartheta);   r = (eps + alpha)(1 - alpha)^n exp(psi theta).
    Protocol: start at (theta, alpha) = (0, 0) at ln D = lnD_a, dwell 20 residence times, sweep up to lnD_b at rate v, dwell 20, sweep back, dwell 20.
    Returns the loop area  oint alpha d ln D  (sweep legs only) and the values of ln D at which alpha crosses 0.5 on the up and on the down leg."""
    T_leg = abs(lnD_b - lnD_a) / v
    t1, t2, t3 = dwell, dwell + T_leg, 2 * dwell + T_leg
    t4, t_end = 2 * dwell + 2 * T_leg, 3 * dwell + 2 * T_leg

    def lnD_of(t):
        if t <= t1:
            return lnD_a
        if t <= t2:
            return lnD_a + v * (t - t1)
        if t <= t3:
            return lnD_b
        if t <= t4:
            return lnD_b - v * (t - t3)
        return lnD_a

    c = 1.0 + 1.0 / vt

    def f(t, y):
        th, al = y
        D = np.exp(lnD_of(t))
        r = (eps + max(al, 0.0)) * np.exp(min(psi * th, 300.0)) * max(1.0 - al, 0.0) ** n
        return [D * r - th * c, D * r - al]
    ts = np.arange(0.0, t_end, dt_out)
    sol = solve_ivp(f, [0, t_end], [0.0, 0.0], method="LSODA", rtol=rtol, atol=atol, t_eval=ts, max_step=min(0.5, 0.02 / max(v, 1e-6)))
    al = sol.y[1]
    lnD = np.array([lnD_of(t) for t in sol.t])
    up = (sol.t >= t1) & (sol.t <= t2)
    dn = (sol.t >= t3) & (sol.t <= t4)
    area = float(np.trapezoid(al[up], lnD[up]) - np.trapezoid(al[dn][::-1], lnD[dn][::-1]))
    iu = np.argmax(al[up] > 0.5)
    idn = np.argmax(al[dn] < 0.5)
    return abs(area), float(lnD[up][iu]), float(lnD[dn][idn])


def flow_attractor(lnD, psi, vt, y0, n=1.5, eps=3e-3, t_end=4000.0):
    """Long-time behavior at fixed D from the initial state y0 = (theta, alpha): returns (alpha_min, alpha_max) over the last 10 % of the run."""
    f = _flow_rhs(float(np.exp(lnD)), psi, vt, n, eps)
    sol = solve_ivp(f, [0, t_end], list(y0), method="LSODA", rtol=1e-11, atol=1e-14, max_step=0.5, dense_output=True)
    tt = np.linspace(0.9 * t_end, t_end, 3000)
    y = sol.sol(tt)
    return float(y[1].min()), float(y[1].max())


def const_T_times(T_C, levels, n=1.5, f=1.0, tau_th_free=True):
    """Constant-temperature gated cure (no heating): times to reach the conversion levels, with availability relaxing to f at rate k_rel
    (alpha(0) = C(0) = 0). Independent adaptive integration (RK45, rtol 1e-12)."""
    from scipy.optimize import brentq
    TK = T_C + 273.15
    a = A1 * np.exp(-EA1 / (R_GAS * TK))
    b = A2 * np.exp(-EA2 / (R_GAS * TK))
    kr = 6.4e6 * np.exp(-6.0e4 / (R_GAS * TK))

    def rhs(t, y):
        al, C = y
        al_ = min(max(al, 0.0), 1.0)
        return [C * (a + b * al_) * (1 - al_) ** n, kr * (f - C)]
    sol = solve_ivp(rhs, [0, 2000.0], [0.0, 0.0], method="RK45", rtol=1e-12, atol=1e-15, dense_output=True)
    out = {}
    for lev in levels:
        tt = np.linspace(0, 2000.0, 400001)
        al = sol.sol(tt)[0]
        i = int(np.argmax(al >= lev))
        out[lev] = float(brentq(lambda t: sol.sol(t)[0] - lev, tt[max(i - 1, 0)], tt[i], xtol=1e-12))
    return out
