"""Fast checks of the closed forms against the numerical reference model (about 1 minute). run_all.py produces the full tables."""
import os
import sys

import numpy as np
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


# Proposition 1 and 2 -------------------------------------------------------------------------------------------------
a, b, kr = rates(140.0)
num = C.integrate([140.0], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=300.0)
err = max(abs(T.t_gated(al, a, b, 1.5, kr) - float(num[k][0])) / float(num[k][0]) for al, k in ((0.1, "t10"), (0.5, "t50"), (0.9, "t90")))
check("availability clock reproduces the gated cure times (n = 1.5, T = 140 C) to 0.05 %", err < 5e-4, "max rel. error %.2e" % err)
iso = C.integrate([140.0], tau_th=1e9, gated=False, p=dict(dtad=0.0, n=1.0), T0_off=0.0, dt=0.01, tmax=300.0)
check("n = 1 closed form equals the integrator (t10, t90) to 0.05 %", abs(T.t_iso_n1(0.1, a, b) - float(iso["t10"][0])) / float(iso["t10"][0]) < 5e-4 and abs(T.t_iso_n1(0.9, a, b) - float(iso["t90"][0])) / float(iso["t90"][0]) < 5e-4)
check("quadrature for n = 1 equals the closed form", abs(T.t_iso(0.9, a, b, 1.0) - T.t_iso_n1(0.9, a, b)) < 1e-12)
check("sharpness law within 5 % of the exact n = 1 sharpness at 140 C", abs(T.sharpness_law(a, b) / T.sharpness_iso_n1(a, b) - 1) < 0.05, "law %.3f exact %.3f" % (T.sharpness_law(a, b), T.sharpness_iso_n1(a, b)))

# Proposition 3 -------------------------------------------------------------------------------------------------------
K = 801
zq = norm.ppf((np.arange(K) + 0.5) / K)
Ts = 112.0
a, b, kr = rates(Ts)
numl = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=6.0 * zq, dt=0.05, T0_off=0.0)["a_end"][0])
anl = T.leak(T.f_active(6.0, 6.0), a, b, kr, 150.0)
check("closed-form storage conversion within 3 % of the population ODE (margin 6 C, sigma 6 C)", abs(anl / numl - 1) < 0.03, "numeric %.5f closed form %.5f" % (numl, anl))
ss = T.sigma_star(0.01, 6.0, a, b, kr, 150.0)
chk = float(C.integrate([Ts], Tmelt=118.0, width=0.5, off=ss * zq, dt=0.05, T0_off=0.0)["a_end"][0])
check("population ODE at the closed-form sigma* gives a storage conversion within 10 % of the tolerance", abs(chk / 0.01 - 1) < 0.10, "sigma* %.2f gives %.5f" % (ss, chk))
check("leakage is monotone in the open fraction", T.leak(0.1, a, b, kr, 150.0) < T.leak(0.2, a, b, kr, 150.0))

# Proposition 4 -------------------------------------------------------------------------------------------------------
for n in (1.0, 1.5, 2.0):
    check("Pi_c(eps = 0) equals e^-1 (1+n)^(1+n) / n^n for n = %.1f" % n, abs(T.Pi_c0(n, 0.0) - np.exp(-1) * (1 + n) ** (1 + n) / n ** n) < 1e-6)
Pi, Th = 0.5 * T.Pi_c0(1.5, 3e-3), 0.003
th = T.theta_peak_qss(Pi, Th, 1.5, 3e-3)
psi = Pi / Th
check("Lambert-W overshoot satisfies psi theta exp(-psi theta) = Pi r_max", abs(psi * th * np.exp(-psi * th) - Pi * T.r_max(1.5, 3e-3)) < 1e-9)
sub, sup = N.fk_peak(1.5, 0.01, 1.5), N.fk_peak(2.4, 0.01, 1.5)
check("exponential-form batch problem: subcritical peak small, supercritical O(1) (Theta = 0.01, Pi_c = 1.93)", sub < 0.05 and sup > 0.5, "peaks %.4f and %.3f" % (sub, sup))
q = N.fk_peak(1.5, 0.003, 1.5)
check("quasi-steady Lambert-W peak within 5 % of the integrated peak (Pi = 1.5, Theta = 0.003)", abs(T.theta_peak_qss(1.5, 0.003, 1.5, 3e-3) / q - 1) < 0.05, "QSS %.5f integrated %.5f" % (T.theta_peak_qss(1.5, 0.003, 1.5, 3e-3), q))

# Proposition 5 -------------------------------------------------------------------------------------------------------
eps, n = 3e-3, 1.5
kc, am = T.kappa_c(eps, n)
check("kappa_c is the minimum of h and exceeds n", kc > n and abs(T.h_fold(am, eps, n) - kc) < 1e-9, "kappa_c = %.4f" % kc)
check("no folds below kappa_c, two above", T.folds(eps, n, 0.9 * kc) is None and T.folds(eps, n, 1.2 * kc) is not None)
lo, hi = T.folds(eps, n, 10.0)
dg = lambda x: (np.log(T.g_curve(x * (1 + 1e-6), eps, n, 10.0)) - np.log(T.g_curve(x * (1 - 1e-6), eps, n, 10.0)))
check("g has zero slope at both folds", abs(dg(lo)) < 1e-4 and abs(dg(hi)) < 1e-4)
A_lo, _, _ = T.static_loop_area(eps, n, 0.9 * kc)
A_hi, _, _ = T.static_loop_area(eps, n, 10.0)
check("static loop area is zero below and positive above the threshold", A_lo == 0.0 and A_hi > 1.0, "area %.3f" % A_hi)
print("\n%s" % ("ALL CHECKS PASSED" if not FAILS else "FAILED: " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
