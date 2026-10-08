"""Fast checks of the closed forms against the numerical reference model (about 1-2 minutes). run_all.py produces the full tables."""
import os
import sys

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C        # noqa: E402
import numerics as N    # noqa: E402
import theory as T      # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
    if not ok:
        FAILS.append(name)


def rates(T_C):
    return (float(T.arrhenius(C.A1, C.EA1, T_C)), float(T.arrhenius(C.A2, C.EA2, T_C)), float(T.arrhenius(C.A_REL, C.EA_REL, T_C)))


# Energy ---------------------------------------------------------------------------------------------------------------
r = C.integrate([140.0], tau_th=1e12, gated=False, T0_off=0.0, dt=0.01, tmax=300.0)
check("adiabatic energy balance: temperature rise equals dT_ad times the final conversion", abs(r["Tmax"][0] - 140.0 - C.DT_AD * r["a_end"][0]) < 1e-6, "rise %.6f K" % (r["Tmax"][0] - 140.0))

# Proposition 1 and 2 -------------------------------------------------------------------------------------------------
a, b, kr = rates(140.0)
num = C.integrate([140.0], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=300.0)
err = max(abs(T.t_gated(al, a, b, 1.5, kr) - float(num[k][0])) / float(num[k][0]) for al, k in ((0.1, "t10"), (0.5, "t50"), (0.9, "t90")))
check("availability clock reproduces the gated cure times (n = 1.5, T = 140 C, reference RK4) to 0.05 %", err < 5e-4, "max rel. error %.2e" % err)
ex = N.const_T_times(140.0, [0.001, 0.01, 0.1, 0.9])
check("gate delay equals tau_rel [1 - exp(-t_gated/tau_rel)] (independent adaptive integration), also at alpha = 0.001",
      all(abs((ex[l] - T.t_iso(l, a, b, 1.5)) - T.gate_delay(ex[l], kr)) < 1e-6 for l in ex), "delay at alpha = 0.001: %.3f min of tau_rel = %.3f" % (ex[0.001] - T.t_iso(0.001, a, b, 1.5), 1 / kr))
exf = N.const_T_times(140.0, [0.5], f=0.5)
check("incomplete activation f = 0.5: clock with f reproduces the integrated time", abs(T.t_gated(0.5, a, b, 1.5, kr, 0.5) - exf[0.5]) < 1e-6)
check("fractional deficit of the delay is below 1 % once t_gated / tau_rel exceeds ln 100", T.gate_delay(np.log(100.0) / kr, kr) / (1 / kr) >= 0.99 - 1e-12)
iso = C.integrate([140.0], tau_th=1e9, gated=False, p=dict(dtad=0.0, n=1.0), T0_off=0.0, dt=0.01, tmax=300.0)
check("n = 1 closed form equals the integrator (t10, t90) to 0.05 %", abs(T.t_iso_n1(0.1, a, b) - float(iso["t10"][0])) / float(iso["t10"][0]) < 5e-4 and abs(T.t_iso_n1(0.9, a, b) - float(iso["t90"][0])) / float(iso["t90"][0]) < 5e-4)
check("quadrature for n = 1 equals the closed form", abs(T.t_iso(0.9, a, b, 1.0) - T.t_iso_n1(0.9, a, b)) < 1e-12)
check("exact n = 1 sharpness formula equals the quadrature", abs(T.sharpness_exact_n1(a, b) - T.sharpness_iso_n1(a, b)) < 1e-12)
check("sharpness law within 5 % of the exact n = 1 sharpness at 140 C", abs(T.sharpness_law(a, b) / T.sharpness_exact_n1(a, b) - 1) < 0.05, "law %.3f exact %.3f" % (T.sharpness_law(a, b), T.sharpness_exact_n1(a, b)))
check("a hundredfold change of b/a (159 to 15,900) changes the exact S by a factor of about 2.6", abs(T.sharpness_exact_n1(1.0, 159.0) / T.sharpness_exact_n1(1.0, 15900.0) - 2.6) < 0.1,
      "S = %.3f and %.3f" % (T.sharpness_exact_n1(1.0, 159.0), T.sharpness_exact_n1(1.0, 15900.0)))

# Proposition 3 -------------------------------------------------------------------------------------------------------
K = 801
zq = norm.ppf((np.arange(K) + 0.5) / K)
Ts = 112.0
a, b, kr = rates(Ts)
numl = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=6.0 * zq, dt=0.05, T0_off=0.0)["a_end"][0])
anl = T.leak(T.f_active(6.0, 6.0), a, b, kr, 150.0)
check("closed-form storage conversion within 3 % of the population ODE (margin 6 C, sigma 6 C)", abs(anl / numl - 1) < 0.03, "numeric %.5f closed form %.5f" % (numl, anl))
check("closed form (a/b)[exp(b f t_eff) - 1] equals the defining integral", abs(T.leak(0.1, a, b, kr, 150.0) / T.leak_quad(0.1, a, b, kr, 150.0) - 1) < 1e-8)
ss = T.sigma_star(0.01, 6.0, a, b, kr, 150.0)
chk = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=ss * zq, dt=0.05, T0_off=0.0)["a_end"][0])
check("population ODE at the closed-form sigma* gives a storage conversion within 5 % of the tolerance", abs(chk / 0.01 - 1) < 0.05, "sigma* %.2f gives %.5f" % (ss, chk))
check("f* inverts the closed form exactly", abs(T.leak(T.f_star(0.01, a, b, kr, 150.0), a, b, kr, 150.0) - 0.01) < 1e-14)
check("sigma*: no finite bound when f* >= 1/2, and nan when the logistic width alone exceeds the tolerance",
      np.isinf(T.sigma_star(0.5, 6.0, a, b, kr, 150.0)) and np.isnan(T.sigma_star(0.001, 6.0, a, b, kr, 150.0, w0=8.0)))

# Proposition 4 -------------------------------------------------------------------------------------------------------
for n in (1.0, 1.5, 2.0):
    check("Pi_c(eps = 0) equals e^-1 (1+n)^(1+n) / n^n for n = %.1f" % n, abs(T.Pi_c0(n, 0.0) - np.exp(-1) * (1 + n) ** (1 + n) / n ** n) < 1e-9)
for n, eps in ((1.5, 3e-3), (1.0, 1e-2), (2.0, 1e-3)):
    rr = minimize_scalar(lambda x: -(eps + x) * (1 - x) ** n, bounds=(0, 1), method="bounded", options={"xatol": 1e-12})
    check("closed-form r_max equals the numerical maximum (n = %.1f, eps = %g)" % (n, eps), abs(T.r_max(n, eps) + rr.fun) < 1e-10)
Pi, Th = 0.5 * T.Pi_c0(1.5, 3e-3), 0.003
th = T.theta_peak_qss(Pi, Th, 1.5, 3e-3)
psi = Pi / Th
check("Lambert-W overshoot satisfies psi theta exp(-psi theta) = Pi r_max", abs(psi * th * np.exp(-psi * th) - Pi * T.r_max(1.5, 3e-3)) < 1e-9)
sub, sup = N.fk_peak(1.5, 0.01, 1.5), N.fk_peak(2.4, 0.01, 1.5)
check("exponential-form batch problem: subcritical peak small, supercritical O(1) (Theta = 0.01, Pi_c = 1.96)", sub < 0.05 and sup > 0.5, "peaks %.4f and %.3f" % (sub, sup))
q = N.fk_peak(1.5, 0.003, 1.5)
check("quasi-steady Lambert-W peak within 5 % of the integrated peak (Pi = 1.5, Theta = 0.003)", abs(T.theta_peak_qss(1.5, 0.003, 1.5, 3e-3) / q - 1) < 0.05, "QSS %.5f integrated %.5f" % (T.theta_peak_qss(1.5, 0.003, 1.5, 3e-3), q))
for Ar in (18.0, 19.9):
    y = T.arrhenius_fold_y(Ar)
    check("Arrhenius frozen fold: y = (1 + y/Ar)^2 and the factor tends to exp(1/Ar) to 0.5 %% (Ar = %.1f)" % Ar, abs(y - (1 + y / Ar) ** 2) < 1e-10 and abs(T.arrhenius_fold_factor(Ar) / T.arrhenius_factor(Ar) - 1) < 0.005,
          "factor %.4f, exp(1/Ar) %.4f" % (T.arrhenius_fold_factor(Ar), T.arrhenius_factor(Ar)))

# Proposition 5 -------------------------------------------------------------------------------------------------------
eps, n, vt = 3e-3, 1.5, 1.0
kc, am = T.kappa_c(eps, n)
check("kappa_c is the minimum of h and exceeds n", kc > n and abs(T.h_fold(am, eps, n) - kc) < 1e-9, "kappa_c = %.4f" % kc)
check("no folds below kappa_c, two above", T.folds(eps, n, 0.9 * kc) is None and T.folds(eps, n, 1.2 * kc) is not None)
lo, hi = T.folds(eps, n, 10.0)
dg = lambda x: (np.log(T.g_curve(x * (1 + 1e-6), eps, n, 10.0)) - np.log(T.g_curve(x * (1 - 1e-6), eps, n, 10.0)))
check("g has zero slope at both folds", abs(dg(lo)) < 1e-4 and abs(dg(hi)) < 1e-4)


def rhs(y, D, psi_):
    th_, al = y
    r_ = (eps + al) * np.exp(psi_ * th_) * (1 - al) ** n
    return np.array([D * r_ - th_ * (1 + 1 / vt), D * r_ - al])


psi = 20.0
al0 = 0.5
Dv = float(T.g_curve(al0, eps, n, T.kappa(psi, vt)))
y0 = np.array([al0 * vt / (1 + vt), al0])
h = 1e-6
Jnum = np.column_stack([(rhs(y0 + h * e, Dv, psi) - rhs(y0 - h * e, Dv, psi)) / (2 * h) for e in np.eye(2)])
Jan = T.jacobian(al0, eps, n, psi, vt)           # ordering (alpha, theta)
Jan_theta_alpha = Jan[[1, 0]][:, [1, 0]]          # reorder to (theta, alpha)
check("steady state is an equilibrium of the flow equations", np.max(np.abs(rhs(y0, Dv, psi))) < 1e-9)
check("analytic Jacobian equals the finite-difference Jacobian", np.max(np.abs(Jnum - Jan_theta_alpha)) < 1e-5, "max difference %.1e" % np.max(np.abs(Jnum - Jan_theta_alpha)))
tr_hi, det_hi = T.trace_det(hi, eps, n, 20.0, vt)
check("psi = 20: det = 0 and trace > 0 at the upper fold (the upper fold is not a stable-branch endpoint)", abs(det_hi) < 1e-8 and tr_hi > 6.0, "trace %.3f" % tr_hi)
trl, detl = T.trace_det(lo, eps, n, 20.0, vt)
check("psi = 20: the lower fold is a saddle-node (det = 0, trace < 0)", abs(detl) < 1e-8 and trl < 0)
a_ext, kind = T.upper_stable_from(eps, n, 20.0, vt)
check("psi = 20: the upper branch is stable only above the Hopf-type point (trace = 0, det > 0)", kind == "hopf" and abs(T.trace_det(a_ext, eps, n, 20.0, vt)[0]) < 1e-8 and T.trace_det(a_ext, eps, n, 20.0, vt)[1] > 0, "alpha_H = %.4f" % a_ext)
a_ext45, kind45 = T.upper_stable_from(eps, n, 4.5, vt)
check("psi = 4.5: the upper fold is a saddle-node (trace < 0)", kind45 == "fold")
kap20 = T.kappa(20.0, vt)


def start_on_upper(lnD):
    up = T.branches_at(float(np.exp(lnD)), eps, n, kap20)[-1]
    return (up * vt / (1 + vt) * 1.01, up * 1.005)


below = N.flow_attractor(-5.50, 20.0, vt, start_on_upper(-5.50), eps=eps, n=n, t_end=1500.0)
above = N.flow_attractor(-5.35, 20.0, vt, start_on_upper(-5.35), eps=eps, n=n, t_end=1500.0)
check("fixed-D simulation at psi = 20: perturbed upper state collapses just below the Hopf-type point (ln D = -5.50) and persists just above (ln D = -5.35)", below[1] < 1e-3 and above[0] > 0.9,
      "alpha ranges %s and %s" % (np.round(below, 4), np.round(above, 4)))
w20 = T.bistable_window(eps, n, 20.0, vt)
aH = w20["alpha_ext"]
h = 1e-6
dtr = (T.trace_det(aH + h, eps, n, 20.0, vt)[0] - T.trace_det(aH - h, eps, n, 20.0, vt)[0]) / (2 * h)
dlnD = (np.log(T.g_curve(aH + h, eps, n, T.kappa(20.0, vt))) - np.log(T.g_curve(aH - h, eps, n, T.kappa(20.0, vt)))) / (2 * h)
evH = np.linalg.eigvals(T.jacobian(aH, eps, n, 20.0, vt))
check("Hopf-type point (psi = 20): purely imaginary pair +/- i omega with omega = sqrt(det), and nonzero transversality d Re(lambda)/d ln D", np.max(np.abs(evH.real)) < 1e-6 and abs(abs(evH.imag[0]) - np.sqrt(T.trace_det(aH, eps, n, 20.0, vt)[1])) < 1e-6 and abs(0.5 * dtr / dlnD) > 1.0,
      "omega = %.3f, transversality %.2f" % (abs(evH.imag[0]), 0.5 * dtr / dlnD))
al_a, T_a, Tinf_a = N.arr_flow_curve(3.0, 1.0, 220.0, N=400)
i_ = 150
resid = (N._k1(T_a[i_]) + N._k2(T_a[i_]) * al_a[i_]) * (1 - al_a[i_]) ** 1.5 - al_a[i_] / 3.0
check("Arrhenius flow reactor: parametrized steady states satisfy the conversion balance", abs(resid) < 1e-8, "residual %.1e" % resid)
an_ = N.arr_flow_analysis(3.0, 1.0, 220.0, N=1500)
check("Arrhenius temperature path (dT_ad = 220 K, tau_res = tau_th = 3 min): a window of two stable states exists between about 128 and 152 C", an_["bistable"] and 120 < an_["window"]["T_ext"] < 135 and 148 < an_["window"]["T_ign"] < 156,
      "window %.2f to %.2f C" % (an_["window"]["T_ext"], an_["window"]["T_ign"]))
A_lo = T.attractor_loop_area(eps, n, 3.0, vt)[0]
A_hi, w = T.attractor_loop_area(eps, n, 20.0, vt)
check("attractor loop area is zero below kappa_c, positive above, and smaller than the fold-to-fold multiplicity area at psi = 20", A_lo == 0.0 and 0 < A_hi < T.static_loop_area(eps, n, T.kappa(20.0, vt))[0], "areas %.3f and %.3f" % (A_hi, T.static_loop_area(eps, n, T.kappa(20.0, vt))[0]))
print("\n%s" % ("ALL CHECKS PASSED" if not FAILS else "FAILED: " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
