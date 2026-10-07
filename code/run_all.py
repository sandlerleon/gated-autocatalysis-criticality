"""Computes every number and result table of the manuscript -> ../results.json. Figures are drawn by figures.py from results.json.

    python run_all.py        (about 20 minutes; each block prints as it finishes)

Error convention used in every table: difference = closed form / numerical - 1 (relative to the numerical reference).
"""
import json
import os
import sys
import time

import numpy as np
import scipy
from scipy.optimize import brentq, least_squares
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C            # noqa: E402
import numerics as N        # noqa: E402
import theory as T          # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
RES = {"versions": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}}
t0 = time.time()
n_ord, eps_fk = C.N_EXP, 3e-3
K = 801
zq = norm.ppf((np.arange(K) + 0.5) / K)


def rates(T_C):
    return float(T.arrhenius(C.A1, C.EA1, T_C)), float(T.arrhenius(C.A2, C.EA2, T_C)), float(T.arrhenius(C.A_REL, C.EA_REL, T_C))


def log(msg):
    print("[%5.0f s] %s" % (time.time() - t0, msg), flush=True)


# ================================================================== E0  energy conservation
r = C.integrate([140.0], tau_th=1e12, gated=False, T0_off=0.0, dt=0.01, tmax=300.0)
RES["energy"] = dict(rise=float(r["Tmax"][0] - 140.0), dTad_alpha=float(C.DT_AD * r["a_end"][0]), alpha_end=float(r["a_end"][0]))
log("E0 adiabatic energy balance: rise %.6f K vs dT_ad * alpha = %.6f K" % (RES["energy"]["rise"], RES["energy"]["dTad_alpha"]))

# ================================================================== E1  availability clock (Proposition 1)
rows = []
for Tinf in (125.0, 140.0, 155.0):
    a, b, kr = rates(Tinf)
    num = C.integrate([Tinf], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=300.0)
    for al, key in ((0.1, "t10"), (0.5, "t50"), (0.9, "t90")):
        th = T.t_gated(al, a, b, n_ord, kr)
        rows.append(dict(T=Tinf, alpha=al, numeric=float(num[key][0]), clock=float(th), iso=T.t_iso(al, a, b, n_ord), tau_release=1.0 / kr))
RES["clock"] = rows
log("E1 clock (reference RK4): max relative error %.2e" % max(abs(r["clock"] - r["numeric"]) / r["numeric"] for r in rows))

# delay as a function of the conversion level (T = 140 C): the shift is conversion dependent and approaches tau_rel
a, b, kr = rates(140.0)
levels = [0.001, 0.01, 0.1, 0.5, 0.9]
tg = N.const_T_times(140.0, levels, n_ord)
RES["delay_vs_alpha"] = [dict(alpha=l, t_gated=tg[l], t_iso=T.t_iso(l, a, b, n_ord), delay=tg[l] - T.t_iso(l, a, b, n_ord), delay_formula=float(T.gate_delay(tg[l], kr)),
                              ratio=tg[l] * kr, tau_rel=1.0 / kr) for l in levels]
RES["delay_1pct_ratio"] = float(np.log(100.0))
fh = 0.5          # incomplete activation: open fraction f = 0.5
tgf = N.const_T_times(140.0, [0.1, 0.5, 0.9], n_ord, f=fh)
RES["incomplete_activation"] = [dict(alpha=l, f=fh, t_ode=tgf[l], t_clock=float(T.t_gated(l, a, b, n_ord, kr, fh)), t_iso=T.t_iso(l, a, b, n_ord), t_full_open=tg[l]) for l in (0.1, 0.5, 0.9)]
log("E1 delay vs alpha: %s" % [(d["alpha"], round(d["delay"], 3)) for d in RES["delay_vs_alpha"]])

# ================================================================== E2  isothermal closed forms (Proposition 2)
rows = []
for Tinf in (110.0, 125.0, 140.0, 155.0):
    a, b, kr = rates(Tinf)
    for n in (1.0, 1.5):
        r = C.integrate([Tinf], tau_th=1e9, gated=False, p=dict(dtad=0.0, n=n), T0_off=0.0, dt=0.01, tmax=600.0)
        t10, t90 = float(r["t10"][0]), float(r["t90"][0])
        c10, c90 = T.t_iso(0.1, a, b, n), T.t_iso(0.9, a, b, n)
        rows.append(dict(T=Tinf, n=n, a=a, b=b, ratio=b / a, t10_num=t10, t90_num=t90, t10_th=c10, t90_th=c90, S_num=(t90 - t10) / t10, S_th=(c90 - c10) / c10,
                         S_law=float(T.sharpness_law(a, b)), S_exact_n1=float(T.sharpness_exact_n1(a, b)), t10_n1=float(T.t_iso_n1(0.1, a, b))))
RES["isothermal"] = rows
RES["sharpness_endpoints"] = [dict(ratio=ratio, S_exact=float(T.sharpness_exact_n1(1.0, ratio)), S_law=float(T.sharpness_law(1.0, ratio))) for ratio in (159.0, 15900.0)]
log("E2 isothermal: max rel. error of t10, t90 (quadrature vs RK4) %.2e" % max(max(abs(r["t10_th"] - r["t10_num"]) / r["t10_num"], abs(r["t90_th"] - r["t90_num"]) / r["t90_num"]) for r in rows))

# ================================================================== E3  storage leakage and design rule (Proposition 3)
T_STORAGE_MIN = 150.0
rows = []
for margin in (3.0, 6.0, 10.0):
    Ts = 118.0 - margin
    a, b, kr = rates(Ts)
    for sg in (2.0, 4.0, 6.0, 10.0):
        num = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=sg * zq, dt=0.05, T0_off=0.0)["a_end"][0])
        f = T.f_active(margin, sg)
        rows.append(dict(margin=margin, sigma=sg, f=f, numeric=num, closed_form=float(T.leak(f, a, b, kr, T_STORAGE_MIN)), quadrature=float(T.leak_quad(f, a, b, kr, T_STORAGE_MIN))))
RES["leakage"] = rows
RES["leak_closed_vs_quad_max_rel"] = float(max(abs(r["closed_form"] / r["quadrature"] - 1) for r in rows if r["quadrature"] > 0))
log("E3 leakage: median closed/numeric %.3f; closed form vs defining integral max rel. difference %.1e" % (np.median([r["closed_form"] / r["numeric"] for r in rows if r["numeric"] > 1e-5]), RES["leak_closed_vs_quad_max_rel"]))

rows = []
for margin in (3.0, 6.0, 10.0):
    Ts = 118.0 - margin
    a, b, kr = rates(Ts)
    for eta in (0.001, 0.01, 0.05):
        s_an = T.sigma_star(eta, margin, a, b, kr, T_STORAGE_MIN)
        s_an0 = T.sigma_star(eta, margin, a, b, kr, T_STORAGE_MIN, w0=0.0)
        fnum = lambda sg: float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=sg * zq, dt=0.05, T0_off=0.0)["a_end"][0]) - eta
        try:
            s_num = brentq(fnum, 0.3, 40.0, xtol=1e-3) if fnum(40.0) > 0 else None
        except ValueError:
            s_num = None
        fs = T.f_star(eta, a, b, kr, T_STORAGE_MIN)
        rows.append(dict(margin=margin, eta=eta, f_star=fs, z_star=float(-norm.ppf(fs)) if fs < 0.5 else None,
                         sigma_star_closed=s_an if np.isfinite(s_an) else None, sigma_star_closed_w0_zero=s_an0 if np.isfinite(s_an0) else None, sigma_star_ode=s_num))
        log("   margin %.0f eta %.3f: f* %.4f sigma* closed %s (w0 -> 0: %s) ODE %s" % (margin, eta, fs, "no finite bound" if not np.isfinite(s_an) else "%.3f" % s_an,
                                                                                        "none" if not np.isfinite(s_an0) else "%.3f" % s_an0, "n/a" if s_num is None else "%.3f" % s_num))
RES["design_rule"] = rows

# ---- convergence: population size K and RK4 step (storage conversion, margin 6 C)
Ts = 112.0
conv = []
ref = {}
zz3201 = norm.ppf((np.arange(3201) + 0.5) / 3201)
for sg in (2.0, 4.0, 6.0):
    ref[sg] = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=sg * zz3201, dt=0.05, T0_off=0.0)["a_end"][0])
for Kc in (101, 201, 401, 801, 1601):
    zz = norm.ppf((np.arange(Kc) + 0.5) / Kc)
    for sg in (2.0, 4.0, 6.0):
        v = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=sg * zz, dt=0.05, T0_off=0.0)["a_end"][0])
        conv.append(dict(kind="K", K=Kc, dt=0.05, sigma=sg, value=v, reference=ref[sg], rel_diff=v / ref[sg] - 1))
vals_dt = {}
for dt in (0.2, 0.1, 0.05, 0.025, 0.0125):
    for sg in (2.0, 4.0, 6.0):
        vals_dt[(dt, sg)] = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=sg * zq, dt=dt, T0_off=0.0)["a_end"][0])
for (dt, sg), v in vals_dt.items():
    conv.append(dict(kind="dt", K=K, dt=dt, sigma=sg, value=v, reference=vals_dt[(0.0125, sg)], rel_diff=v / vals_dt[(0.0125, sg)] - 1))
RES["convergence"] = conv
log("E3 convergence: K = 801 vs 3201 max |diff| %.2e; dt = 0.05 vs 0.0125 max |diff| %.2e" % (max(abs(c["rel_diff"]) for c in conv if c["kind"] == "K" and c["K"] == 801),
                                                                                         max(abs(c["rel_diff"]) for c in conv if c["kind"] == "dt" and c["dt"] == 0.05)))

# ---- synthetic-data recovery of (T_m, sigma) from isothermal storage curves
rng = np.random.default_rng(20261007)
true_sigma, true_Tm = 5.0, 118.0
times = np.array([30.0, 60.0, 90.0, 120.0, 150.0])
temps = [112.0, 108.0, 105.0]
noise = 0.002


def model_curves(sg, Tm):
    out = []
    for Ts_ in temps:
        a_, b_, kr_ = rates(Ts_)
        f_ = T.f_active(Tm - Ts_, sg)
        out.extend(T.leak(f_, a_, b_, kr_, t) for t in times)
    return np.array(out)


truth = model_curves(true_sigma, true_Tm)
meas0 = []
for Ts_ in temps:
    for t in times:
        meas0.append(float(C.integrate([Ts_], Tmelt=true_Tm, width=0.5, off=true_sigma * zq, dt=0.05, T0_off=0.0, tmax=t)["a_end"][0]))
meas0 = np.array(meas0)
est = []
for k in range(200):
    y = np.clip(meas0 + noise * rng.standard_normal(meas0.size), 0, None)
    fit = least_squares(lambda p: (model_curves(p[0], p[1]) - y) / noise, x0=[3.0, 117.0], bounds=([0.5, 112.0], [15.0, 124.0]))
    est.append(fit.x)
est = np.array(est)
RES["recovery"] = dict(true_sigma=true_sigma, true_Tm=true_Tm, noise=noise, n_trials=len(est), times=times.tolist(), temps=temps, w0=0.5,
                       sigma_mean=float(est[:, 0].mean()), sigma_sd=float(est[:, 0].std()), Tm_mean=float(est[:, 1].mean()), Tm_sd=float(est[:, 1].std()),
                       corr=float(np.corrcoef(est[:, 0], est[:, 1])[0, 1]), estimates=est[::5].tolist(),
                       noiseless_closed_form_vs_ode_max_abs_diff=float(np.max(np.abs(truth - meas0))))
log("E3b recovery: sigma %.2f +/- %.2f (true %.1f); Tm %.2f +/- %.2f (true %.1f); corr %.2f" % (est[:, 0].mean(), est[:, 0].std(), true_sigma, est[:, 1].mean(), est[:, 1].std(), true_Tm, RES["recovery"]["corr"]))
est2 = []
rng2 = np.random.default_rng(20261008)
for k in range(200):
    y = np.clip(meas0 + noise * rng2.standard_normal(meas0.size), 0, None)
    fit = least_squares(lambda p: np.concatenate([(model_curves(p[0], p[1]) - y) / noise, [(p[1] - true_Tm) / 0.5]]), x0=[3.0, 117.0], bounds=([0.5, 112.0], [15.0, 124.0]))
    est2.append(fit.x)
est2 = np.array(est2)
RES["recovery_prior"] = dict(Tm_prior_sd=0.5, sigma_mean=float(est2[:, 0].mean()), sigma_sd=float(est2[:, 0].std()), Tm_mean=float(est2[:, 1].mean()), Tm_sd=float(est2[:, 1].std()))
log("E3c recovery with Tm prior: sigma %.2f +/- %.2f" % (est2[:, 0].mean(), est2[:, 0].std()))

# ================================================================== E4  criticality (Proposition 4)
rows = []
for n in (1.0, 1.5, 2.0):
    for Th in (0.1, 0.03, 0.01, 0.003):
        rows.append(dict(n=n, Theta=Th, Pi_c_numeric=float(N.fk_critical(Th, n, eps_fk)), Pi_c_finite_eps=float(T.Pi_c0(n, eps_fk)), Pi_c_eps0=float(T.Pi_c0(n, 0.0))))
    log("E4 exponential-form n=%.1f done" % n)
RES["critical_fk"] = rows
RES["critical_threshold_sensitivity"] = {str(thr): float(N.fk_critical(0.003, 1.5, eps_fk, thr=thr)) for thr in (0.15, 0.3, 0.6)}
RES["epsilon_dependence"] = {str(e): dict(numeric=float(N.fk_critical(0.01, 1.5, e)), theory=float(T.Pi_c0(1.5, e))) for e in (1e-4, 1e-3, 1e-2)}
log("E4 threshold sensitivity %s" % RES["critical_threshold_sensitivity"])

rows = []
for Th in (0.01, 0.003):
    for Pi in (0.5, 1.0, 1.5, 1.8):
        rows.append(dict(Theta=Th, Pi=Pi, numeric=N.fk_peak(Pi, Th, 1.5, eps_fk), qss=T.theta_peak_qss(Pi, Th, 1.5, eps_fk)))
RES["overshoot_qss"] = rows
rows = []
Pc = T.Pi_c0(1.5, eps_fk)
Th = 0.002
for frac in (0.5, 0.8, 0.9, 0.95, 0.98):
    Pi = frac * Pc
    rows.append(dict(frac=frac, psi_theta_numeric=float(N.fk_peak(Pi, Th, 1.5, eps_fk) * Pi / Th),
                     psi_theta_lambert=float(-1 * T.lambertw(-Pi / (np.e * Pc)).real), normal_form=float(T.exponent_form(Pi, 1.5, eps_fk))))
RES["fold_exponent"] = rows
log("E4 overshoot done")

rows = []
for Tinf in (120.0, 140.0, 160.0):
    a, b, kr = rates(Tinf)
    for Th in (0.01, 0.03, 0.1):
        tau = Th / b
        cr = N.arr_critical(Tinf, tau)
        fk = N.fk_critical(Th, 1.5, a / b)
        gated = N.arr_critical(Tinf, tau, gated_tau_rel=1.0 / kr) if Th == 0.03 else None
        rows.append(dict(T=Tinf, Theta=Th, tau_th=tau, Ar=cr["Ar"], eps=a / b, Pi_c_arrhenius=cr["Pi_c"], Pi_c_fk=float(fk),
                         factor_first_order=T.arrhenius_factor(cr["Ar"]), factor_fold=T.arrhenius_fold_factor(cr["Ar"]),
                         prediction_first_order=float(fk * T.arrhenius_factor(cr["Ar"])), prediction_fold=float(fk * T.arrhenius_fold_factor(cr["Ar"])),
                         Pi_c_gated=None if gated is None else gated["Pi_c"], tau_release=1.0 / kr))
        log("   Arrhenius T=%.0f Theta=%.2f: Pi_c %.3f (FK %.3f x fold factor %.4f = %.3f; x exp(1/Ar) = %.3f)" % (
            Tinf, Th, cr["Pi_c"], fk, T.arrhenius_fold_factor(cr["Ar"]), fk * T.arrhenius_fold_factor(cr["Ar"]), fk * T.arrhenius_factor(cr["Ar"])))
RES["critical_arrhenius"] = rows

# ================================================================== E5  continuous-flow reactor (Proposition 5)
eps, n, vt = eps_fk, 1.5, 1.0
res5 = {"kappa_c": T.kappa_c(eps, n)[0], "n": n, "eps": eps, "vartheta": vt, "RT2_over_E2_K_at_140C": C.R_GAS * (140.0 + 273.15) ** 2 / C.EA2}
stab = []
for psi in (3.0, 4.5, 6.0, 8.0, 12.0, 20.0):
    kap = T.kappa(psi, vt)
    fl = T.folds(eps, n, kap)
    row = dict(psi=psi, kappa=kap, folds=fl is not None)
    if fl is not None:
        tr_hi, det_hi = T.trace_det(fl[1], eps, n, psi, vt)
        tr_lo, det_lo = T.trace_det(fl[0], eps, n, psi, vt)
        A_att, w = T.attractor_loop_area(eps, n, psi, vt)
        A_mult, _, _ = T.static_loop_area(eps, n, kap)
        row.update(alpha_fold_lo=fl[0], alpha_fold_hi=fl[1], lnD_fold_lo=float(np.log(T.g_curve(fl[0], eps, n, kap))), lnD_fold_hi=float(np.log(T.g_curve(fl[1], eps, n, kap))),
                   trace_lower_fold=tr_lo, trace_upper_fold=tr_hi, bistable=w is not None, window=w, attractor_area=A_att, multiplicity_area=A_mult)
    stab.append(row)
res5["stability"] = stab
lo_, hi_ = 3.0, 40.0
for _ in range(50):
    mid = 0.5 * (lo_ + hi_)
    if T.bistable_window(eps, n, mid, vt) is not None:
        hi_ = mid
    else:
        lo_ = mid
res5["psi_bistable"], res5["kappa_bistable"] = hi_, T.kappa(hi_, vt)
lo_, hi_ = 4.0, 40.0
for _ in range(50):
    mid = 0.5 * (lo_ + hi_)
    if T.trace_det(T.folds(eps, n, T.kappa(mid, vt))[1], eps, n, mid, vt)[0] > 0:
        hi_ = mid
    else:
        lo_ = mid
res5["psi_hopf_replaces_fold"] = hi_
log("E5 stability: kappa_c %.4f, bistability threshold psi %.4f (kappa %.4f); upper fold becomes unstable for psi > %.3f" % (res5["kappa_c"], res5["psi_bistable"], res5["kappa_bistable"], res5["psi_hopf_replaces_fold"]))

att = []
for psi in (4.5, 20.0):
    kap = T.kappa(psi, vt)
    w = T.bistable_window(eps, n, psi, vt)
    span = w["lnD_ign"] - w["lnD_ext"]
    for lnD in np.linspace(w["lnD_ext"] - 0.25 * span - 0.02, w["lnD_ign"] + 0.25 * span + 0.02, 9):
        D = float(np.exp(lnD))
        roots = T.branches_at(D, eps, n, kap)
        ics = [(0.0, 0.0), (0.5 * vt / (1 + vt), 0.5)]
        for rt in roots[-1:]:
            ics += [(rt * vt / (1 + vt) * (1 + 0.02), rt * (1 + 0.01)), (rt * vt / (1 + vt) * (1 - 0.02), rt * (1 - 0.01))]
        finals = [N.flow_attractor(lnD, psi, vt, y0, n, eps, t_end=3000.0) for y0 in ics]
        distinct = []
        for mn, mx in finals:
            if not any(abs(mn - d[0]) < 2e-3 and abs(mx - d[1]) < 2e-3 for d in distinct):
                distinct.append((mn, mx))
        att.append(dict(psi=psi, lnD=float(lnD), n_roots=len(roots), in_window=bool(w["lnD_ext"] < lnD < w["lnD_ign"]), attractors=[dict(alpha_min=a_, alpha_max=b_) for a_, b_ in distinct],
                        max_oscillation=float(max(mx - mn for mn, mx in finals))))
    log("E5 attractor scan psi=%.1f done" % psi)
res5["attractors"] = att

cases = []
for psi in (3.0, 4.5, 8.0, 20.0):
    kap = T.kappa(psi, vt)
    w = T.bistable_window(eps, n, psi, vt)
    fl = T.folds(eps, n, kap)
    lo_ = (w["lnD_ext"] if w else (np.log(T.g_curve(fl[1], eps, n, kap)) if fl else -2.0)) - 2.0
    hi_ = (w["lnD_ign"] if w else (np.log(T.g_curve(fl[0], eps, n, kap)) if fl else 0.0)) + 2.0
    pts = []
    for v in (0.02, 0.01, 0.005, 0.002, 0.001, 0.0005, 0.0002):
        a_, ju, jd = N.flow_sweep(v, lo_, hi_, psi, vt, n, eps)
        pts.append(dict(v=v, area=a_, lnD_up=ju, lnD_down=jd))
        log("   sweep psi=%.1f v=%.3f area %.4f up %.3f down %.3f" % (psi, v, a_, ju, jd))
    vv = np.array([p["v"] for p in pts])
    aa = np.array([p["area"] for p in pts])
    try:
        fit = least_squares(lambda q: q[0] + q[1] * vv ** q[2] - aa, x0=[aa[-1], aa[0] - aa[-1], 0.7], bounds=([-1.0, 0.0, 0.1], [20.0, 100.0, 3.0]))
        A0f, cf, pf = [float(x) for x in fit.x]
    except Exception:
        A0f = cf = pf = None
    cases.append(dict(psi=psi, kappa=kap, bistable=w is not None, window=w, attractor_area=T.attractor_loop_area(eps, n, psi, vt)[0], multiplicity_area=T.static_loop_area(eps, n, kap)[0],
                      sweeps=pts, fit_A0=A0f, fit_c=cf, fit_p=pf, sweep_bounds=[float(lo_), float(hi_)]))
res5["cases"] = cases
RES["flow"] = res5

json.dump(RES, open(os.path.join(HERE, "..", "results.json"), "w", encoding="utf-8"), indent=1, default=float)
log("done")
