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


# ====================================================================================================================
# Arrhenius continuous-flow reactor on a physical temperature path (both rate constants Arrhenius; psi and epsilon vary with T)
# ====================================================================================================================
from scipy.optimize import brentq as _brentq


def _k1(T_C):
    return A1 * np.exp(-EA1 / (R_GAS * (T_C + 273.15)))


def _k2(T_C):
    return A2 * np.exp(-EA2 / (R_GAS * (T_C + 273.15)))


def arr_flow_curve(tau_res, vt, dtad, n=1.5, N=4000):
    """Steady states of dalpha/dt = (k1 + k2 alpha)(1-alpha)^n - alpha/tau_res,  dT/dt = dtad (rate) - (T - Tinf)(1/tau_th + 1/tau_res)  (tau_th = vt tau_res).
    Parametrized by the conversion alpha: T solves the conversion balance, Tinf = T - dtad alpha vt/(1+vt). Returns alpha, T, Tinf."""
    al = np.geomspace(1e-7, 0.995, N)
    T = np.empty(N)
    for i, a in enumerate(al):
        f = lambda TT: (_k1(TT) + _k2(TT) * a) * (1 - a) ** n * tau_res - a
        T[i] = _brentq(f, -100.0, 3000.0, xtol=1e-10)
    return al, T, T - dtad * al * vt / (1 + vt)


def arr_flow_jacobian(a, T, Tinf, tau_res, vt, dtad, n=1.5):
    tau_th = vt * tau_res

    def F(y):
        TT, aa = y
        r = (_k1(TT) + _k2(TT) * aa) * (1 - aa) ** n
        return np.array([dtad * r - (TT - Tinf) * (1 / tau_th + 1 / tau_res), r - aa / tau_res])
    y0 = np.array([T, a])
    J = np.zeros((2, 2))
    for j in range(2):
        h = 1e-6 * max(abs(y0[j]), 1.0)
        e = np.zeros(2)
        e[j] = h
        J[:, j] = (F(y0 + e) - F(y0 - e)) / (2 * h)
    return J


def arr_flow_analysis(tau_res, vt, dtad, n=1.5, N=4000):
    """Folds, stability change points and the window of two stable states on the Arrhenius temperature path."""
    al, T, Tinf = arr_flow_curve(tau_res, vt, dtad, n, N)
    d = np.diff(Tinf)
    idx = np.where(np.sign(d[1:]) != np.sign(d[:-1]))[0] + 1
    if len(idx) < 2:
        return dict(bistable=False, folds=[])
    ev = np.array([np.linalg.eigvals(arr_flow_jacobian(al[i], T[i], Tinf[i], tau_res, vt, dtad, n)) for i in range(len(al))])
    maxre = ev.real.max(axis=1)
    stable = maxre < 0
    i_lo, i_hi = idx[0], idx[1]                      # lower (ignition) and upper fold indices
    upper = np.where(stable & (np.arange(len(al)) > i_hi))[0]
    k = int(upper[0]) if len(upper) else None
    kind = "fold" if (k is not None and k - i_hi <= 2) else "hopf"
    T_ext = float(Tinf[k]) if k is not None else None
    T_ign = float(Tinf[i_lo])
    win = None if (T_ext is None or T_ext >= T_ign) else dict(T_ext=T_ext, T_ign=T_ign, width_K=T_ign - T_ext, alpha_ext=float(al[k]), kind=kind)
    # local dimensionless numbers at the folds
    def psi_eps(i):
        Tk = T[i] + 273.15
        return dict(T=float(T[i]), psi=float(dtad * EA2 / (R_GAS * Tk ** 2)), eps=float(_k1(T[i]) / _k2(T[i])), D=float(_k2(T[i]) * tau_res), Ar=float(EA2 / (R_GAS * Tk)))
    return dict(bistable=win is not None, window=win, fold_lower=dict(alpha=float(al[i_lo]), Tinf=float(Tinf[i_lo]), **psi_eps(i_lo)),
                fold_upper=dict(alpha=float(al[i_hi]), Tinf=float(Tinf[i_hi]), **psi_eps(i_hi)),
                trace_upper_fold=float(np.trace(arr_flow_jacobian(al[i_hi], T[i_hi], Tinf[i_hi], tau_res, vt, dtad, n))))


def arr_flow_sweep(rate, T_lo, T_hi, tau_res, vt, dtad, n=1.5, dwell=20.0, dt_out=0.05, rtol=1e-8, atol=1e-10):
    """Up-then-down ramp of the wall temperature Tinf at `rate` K per residence time, Arrhenius kinetics (time in residence times).
    Returns loop area (alpha dTinf, K) and Tinf at which alpha crosses 0.5 on the up and down legs."""
    tau_th = vt * tau_res
    T_leg = abs(T_hi - T_lo) / rate
    t1, t2, t3, t4, t_end = dwell, dwell + T_leg, 2 * dwell + T_leg, 2 * dwell + 2 * T_leg, 3 * dwell + 2 * T_leg

    def Tinf_of(t):
        return T_lo if t <= t1 else T_lo + rate * (t - t1) if t <= t2 else T_hi if t <= t3 else T_hi - rate * (t - t3) if t <= t4 else T_lo

    def f(t, y):
        TT, a = y
        a = min(max(a, 0.0), 1.0)
        r = (_k1(TT) + _k2(TT) * a) * (1 - a) ** n
        return [(dtad * r - (TT - Tinf_of(t)) * (1 / tau_th + 1 / tau_res)) * tau_res, (r - a / tau_res) * tau_res]        # time in units of tau_res
    ts = np.arange(0.0, t_end, dt_out)
    sol = solve_ivp(f, [0, t_end], [T_lo, 0.0], method="LSODA", rtol=rtol, atol=atol, t_eval=ts, max_step=min(0.5, 0.5 / max(rate, 1e-6)))
    al = sol.y[1]
    Ti = np.array([Tinf_of(t) for t in sol.t])
    up = (sol.t >= t1) & (sol.t <= t2)
    dn = (sol.t >= t3) & (sol.t <= t4)
    area = float(np.trapezoid(al[up], Ti[up]) - np.trapezoid(al[dn][::-1], Ti[dn][::-1]))
    return abs(area), float(Ti[up][np.argmax(al[up] > 0.5)]), float(Ti[dn][np.argmax(al[dn] < 0.5)])


def flow_collapse_radius(lnD, psi, vt, direction, n=1.5, eps=3e-3, t_end=2500.0, steps=26):
    """Smallest perturbation of the upper steady state, along `direction` = (d theta, d alpha), after which the trajectory collapses to the lower state
    (alpha < 0.5 at t_end): the radius of the basin of the upper state along that direction (None if no collapse up to 0.5). Requires theory.branches_at."""
    import theory as _T
    D = float(np.exp(lnD))
    kap = _T.kappa(psi, vt)
    up = _T.branches_at(D, eps, n, kap)[-1]
    th0 = up * vt / (1 + vt)
    f = _flow_rhs(D, psi, vt, n, eps)

    def collapses(delta):
        sol = solve_ivp(f, [0, t_end], [th0 + direction[0] * delta, up + direction[1] * delta], method="LSODA", rtol=1e-10, atol=1e-13, max_step=0.5, dense_output=True)
        return sol.sol(t_end)[1] < 0.5
    lo, hi = 1e-6, 0.5
    if not collapses(hi):
        return None
    for _ in range(steps):
        m = float(np.sqrt(lo * hi))
        if collapses(m):
            hi = m
        else:
            lo = m
    return float(hi)
