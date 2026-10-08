"""Figure 6 (Arrhenius temperature path and noise dependence of the exit) from results.json.   python figures_extra.py"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numerics as N    # noqa: E402

R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "..", "figures") + os.sep
plt.rcParams.update({"font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10, "legend.fontsize": 8.5, "savefig.dpi": 300, "font.family": "serif"})
BL, OR, GR, RD, GN = "#1f4e9c", "#c0661b", "#4d4d4d", "#b22222", "#2a7f3f"

af = [c for c in R["arrhenius_flow"]["cases"] if c["dtad"] == 220.0][0]
tau_r, vt_, dtad = R["arrhenius_flow"]["tau_res"], R["arrhenius_flow"]["vartheta"], 220.0
al2, T2, Tinf2 = N.arr_flow_curve(tau_r, vt_, dtad, 1.5, 3000)
ev2 = np.array([np.linalg.eigvals(N.arr_flow_jacobian(al2[i], T2[i], Tinf2[i], tau_r, vt_, dtad)) for i in range(len(al2))])
st2 = ev2.real.max(axis=1) < 0
fig, ax = plt.subplots(1, 2, figsize=(7.4, 3.2))
ax[0].plot(np.where(st2, Tinf2, np.nan), al2, color=BL, lw=1.7, label="stable")
ax[0].plot(np.where(~st2, Tinf2, np.nan), al2, color=GR, ls="--", lw=1.5, label="unstable")
wv = af["analysis"]["window"]
for rate, c in ((2.0, OR), (0.1, RD)):
    T_lo, T_hi = wv["T_ext"] - 15.0, wv["T_ign"] + 15.0
    T_leg = (T_hi - T_lo) / rate
    t1, t2, t3, t4, tend = 20.0, 20.0 + T_leg, 40.0 + T_leg, 40.0 + 2 * T_leg, 60.0 + 2 * T_leg

    def Ti(t, T_lo=T_lo, T_hi=T_hi, rate=rate, t1=t1, t2=t2, t3=t3, t4=t4):
        return T_lo if t <= t1 else T_lo + rate * (t - t1) if t <= t2 else T_hi if t <= t3 else T_hi - rate * (t - t3) if t <= t4 else T_lo

    def f(t, y, Ti=Ti):
        TT, a_ = y
        a_ = min(max(a_, 0.0), 1.0)
        r = (N._k1(TT) + N._k2(TT) * a_) * (1 - a_) ** 1.5
        return [(dtad * r - (TT - Ti(t)) * (1 / (vt_ * tau_r) + 1 / tau_r)) * tau_r, (r - a_ / tau_r) * tau_r]
    ts = np.arange(0, tend, 0.1)
    s_ = solve_ivp(f, [0, tend], [T_lo, 0.0], method="LSODA", rtol=1e-8, atol=1e-10, t_eval=ts, max_step=min(0.5, 0.5 / rate))
    ax[0].plot([Ti(t) for t in s_.t], s_.y[1], color=c, lw=1.0, label=r"ramp %g K per $\tau_{\rm res}$" % rate)
ax[0].axvline(wv["T_ext"], color=GN, lw=0.8, ls="-.")
ax[0].axvline(wv["T_ign"], color=RD, lw=0.8, ls="-.")
ax[0].set_xlim(wv["T_ext"] - 15, wv["T_ign"] + 15)
ax[0].set_xlabel(r"wall temperature $T_\infty$ (°C)")
ax[0].set_ylabel(r"conversion $\alpha$")
ax[0].set_title(r"(a) Arrhenius path, $\Delta T_{\rm ad}=220$ K")
ax[0].legend(fontsize=7.5, loc="center left")
hn = R["hopf_noise"]
tol = [d["rtol"] for d in hn["by_tolerance"]]
ax[1].semilogx(tol, [d["lnD_down"] for d in hn["by_tolerance"]], "o-", color=BL, label="down-switch (v = 0.001)")
ax[1].axhline(hn["lnD_hopf"], color=GN, ls="--", label="Hopf-type point")
ax[1].axhline(hn["lnD_upper_fold"], color=RD, ls=":", label="upper fold")
ax[1].invert_xaxis()
ax[1].set_xlabel("integrator tolerance (rtol)")
ax[1].set_ylabel(r"$\ln D$ at extinction")
ax[1].set_title(r"(b) Noise dependence of the exit ($\psi=20$)")
ax[1].legend(fontsize=7.5)
plt.tight_layout()
fig.savefig(OUT + "fig6_arrhenius_path.png")
fig.savefig(OUT + "fig6_arrhenius_path.pdf")
print("figure 6 written")
