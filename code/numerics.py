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


def flow_sweep(v, lnD_a, lnD_b, psi, vartheta, n=1.5, eps=3e-3, dt_out=0.05):
    """Up-then-down sweep of ln D at rate v (per residence time) of the continuous-flow reactor, in units t' = t / tau_res:
        d alpha/dt' = D r - alpha;   d theta/dt' = D r - theta (1 + 1/vartheta);   r = (eps + alpha)(1 - alpha)^n exp(psi theta).
    Returns the loop area  oint alpha d ln D  and the switching values of ln D on the up and down legs (largest jump of alpha)."""
    T_leg = abs(lnD_b - lnD_a) / v

    def lnD_of(t):
        return lnD_a + v * t if t <= T_leg else lnD_b - v * (t - T_leg)

    def f(t, y):
        th, al = y
        D = np.exp(lnD_of(t))
        r = (eps + max(al, 0.0)) * np.exp(min(psi * th, 300.0)) * max(1.0 - al, 0.0) ** n
        return [D * r - th * (1.0 + 1.0 / vartheta), D * r - al]
    # start on the lower (unreacted) branch: slow relaxation at the lowest D
    ts = np.arange(0.0, 2 * T_leg, dt_out)
    sol = solve_ivp(f, [0, 2 * T_leg], [0.0, 0.0], method="LSODA", rtol=1e-8, atol=1e-12, t_eval=ts, max_step=min(0.5, 0.02 / max(v, 1e-6)))
    al = sol.y[1]
    lnD = np.array([lnD_of(t) for t in sol.t])
    area = float(np.trapezoid(al, lnD))
    up = sol.t <= T_leg
    jump_up = lnD[up][np.argmax(np.diff(al[up], prepend=al[up][0]))]
    dn = ~up
    jump_dn = lnD[dn][np.argmin(np.diff(al[dn], prepend=al[dn][0]))]
    return abs(area), float(jump_up), float(jump_dn)
