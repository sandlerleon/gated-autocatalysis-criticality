"""Draws Figures 1-5 from results.json (and a few fast direct evaluations); PNG (300 dpi) and vector PDF.   python figures.py"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.special import lambertw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core as C        # noqa: E402
import numerics as N    # noqa: E402
import theory as T      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "..", "figures") + os.sep
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10, "legend.fontsize": 8.5, "savefig.dpi": 300, "font.family": "serif"})
BL, OR, GR, RD, GN = "#1f4e9c", "#c0661b", "#4d4d4d", "#b22222", "#2a7f3f"


def save(fig, name):
    fig.savefig(OUT + name + ".png")
    fig.savefig(OUT + name + ".pdf")
    plt.close(fig)


def rates(T_C):
    return (float(T.arrhenius(C.A1, C.EA1, T_C)), float(T.arrhenius(C.A2, C.EA2, T_C)), float(T.arrhenius(C.A_REL, C.EA_REL, T_C)))


# ------------------------------------------------------------------ Figure 1: availability clock, delay, sharpness
fig, ax = plt.subplots(1, 3, figsize=(10.2, 3.1))
a, b, kr = rates(140.0)
al = np.linspace(0.001, 0.995, 500)
iso = np.array([T.t_iso(x, a, b, 1.5) for x in al])
gat = np.array([T.t_gated(x, a, b, 1.5, kr) for x in al])
ax[0].plot(iso, al, color=GR, lw=1.6, label="no gate (isothermal)")
ax[0].plot(gat, al, color=BL, lw=1.6, label="gated: availability clock")
num = C.integrate([140.0], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=70.0)
for k, lev in (("t10", 0.1), ("t50", 0.5), ("t90", 0.9)):
    ax[0].plot(float(num[k][0]), lev, "o", color=OR, ms=5, zorder=5, label="integrated ODE" if k == "t10" else None)
ax[0].set_xlabel("time (min)"); ax[0].set_ylabel(r"conversion $\alpha$"); ax[0].set_title("(a) Gated cure at 140 °C"); ax[0].legend(loc="lower right"); ax[0].set_xlim(0, 80)
tgrid = np.linspace(0, 30, 300)
ax[1].plot(gat, [T.gate_delay(t, kr) for t in gat], color=BL, lw=1.6, label=r"$\tau_{\rm rel}[1-e^{-t/\tau_{\rm rel}}]$")
ax[1].axhline(1 / kr, color=RD, ls="--", lw=1.0, label=r"$\tau_{\rm rel}$ = %.1f min" % (1 / kr))
ax[1].plot([d["t_gated"] for d in R["delay_vs_alpha"]], [d["delay"] for d in R["delay_vs_alpha"]], "o", color=OR, label="integrated ODE")
ax[1].set_xscale("log"); ax[1].set_xlim(2, 120); ax[1].set_xlabel(r"gated time $t_{\rm gated}$ (min)"); ax[1].set_ylabel("delay vs. ungated (min)"); ax[1].set_title("(b) The delay depends on conversion"); ax[1].legend(loc="lower right")
rows = [r for r in R["isothermal"] if r["n"] == 1.0]
x = np.array([np.log(r["ratio"]) for r in rows])
ax[2].plot(x, [r["S_exact_n1"] for r in rows], "s-", color=GR, label=r"exact, $n=1$")
ax[2].plot(x, [r["S_law"] for r in rows], "--", color=BL, label=r"asymptotic law ($n=1$)")
rows15 = [r for r in R["isothermal"] if r["n"] == 1.5]
ax[2].plot([np.log(r["ratio"]) for r in rows15], [r["S_num"] for r in rows15], "o", color=OR, label=r"integrated, $n=3/2$")
ax[2].set_xlabel(r"$\ln(k_2/k_1)$"); ax[2].set_ylabel(r"sharpness $S=(t_{90}-t_{10})/t_{10}$"); ax[2].set_title("(c) Sharpness vs. rate-constant ratio"); ax[2].legend()
plt.tight_layout(); save(fig, "fig1_clock_sharpness")

# ------------------------------------------------------------------ Figure 2: storage leakage and design rule
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1))
L = [r for r in R["leakage"] if r["numeric"] > 1e-6]
cols = {3.0: RD, 6.0: BL, 10.0: OR}
for mg in (3.0, 6.0, 10.0):
    pts = [r for r in L if r["margin"] == mg]
    ax[0].loglog([r["numeric"] for r in pts], [r["closed_form"] for r in pts], "o", color=cols[mg], label=r"$\Delta$ = %.0f °C" % mg)
lim = [1e-5, 0.2]
ax[0].plot(lim, lim, "k--", lw=0.8)
ax[0].set_xlabel("population ODE, storage conversion"); ax[0].set_ylabel("closed form"); ax[0].set_title("(a) Storage conversion after 150 min"); ax[0].legend()
etas = np.geomspace(5e-4, 0.08, 40)
for mg in (3.0, 6.0, 10.0):
    Ts = 118.0 - mg
    a_, b_, kr_ = rates(Ts)
    ss_ = np.array([T.sigma_star(e, mg, a_, b_, kr_, 150.0) for e in etas])
    ss_[~np.isfinite(ss_) | (ss_ > 40)] = np.nan
    ax[1].loglog(etas, ss_, color=cols[mg], label=r"closed form, $\Delta$ = %.0f °C" % mg)
    pts = [r for r in R["design_rule"] if r["margin"] == mg and r["sigma_star_ode"]]
    ax[1].plot([r["eta"] for r in pts], [r["sigma_star_ode"] for r in pts], "o", color=cols[mg], mfc="white")
ax[1].set_xlabel(r"tolerance $\eta$ on storage conversion"); ax[1].set_ylabel(r"largest admissible spread $\sigma^*$ (°C)"); ax[1].set_title("(b) Bound on the spread (open: ODE)"); ax[1].legend()
plt.tight_layout(); save(fig, "fig2_storage")

# ------------------------------------------------------------------ Figure 3: criticality
fig, ax = plt.subplots(1, 3, figsize=(10.2, 3.1))
for n, c in ((1.0, GR), (1.5, BL), (2.0, OR)):
    rows = [r for r in R["critical_fk"] if r["n"] == n]
    ax[0].semilogx([r["Theta"] for r in rows], [r["Pi_c_numeric"] for r in rows], "o-", color=c, label=r"$n=%.1f$" % n)
    ax[0].axhline(rows[0]["Pi_c_finite_eps"], color=c, ls="--", lw=0.9)
ax[0].set_xlabel(r"$\Theta=\tau_{\rm th}k_2$"); ax[0].set_ylabel(r"operational critical number $\Pi_c=\psi\Theta$"); ax[0].set_title(r"(a) $\Pi_c\to(1+n)^{1+n}/[e\,n^n(1+\varepsilon)^{1+n}]$", fontsize=9); ax[0].legend()
Pc = T.Pi_c0(1.5, 3e-3)
Pis = np.linspace(0.05, Pc, 200)
ax[1].plot(Pis / Pc, [-np.real(lambertw(-p / (np.e * Pc))) for p in Pis], color=BL, label=r"$-W_0(-\Pi/e\Pi_c)$")
ax[1].plot(Pis / Pc, 1 - np.sqrt(2 * (1 - Pis / Pc)), ":", color=RD, label="fold normal form")
for r in R["fold_exponent"]:
    ax[1].plot(r["frac"], r["psi_theta_numeric"], "o", color=OR, label=r"integrated ($\Theta=0.002$)" if r["frac"] == 0.5 else None)
ax[1].set_xlabel(r"$\Pi/\Pi_c$"); ax[1].set_ylabel(r"$\psi\,\theta_{\rm peak}$"); ax[1].set_title("(b) Quasi-steady overshoot below the fold"); ax[1].set_ylim(0, 1.1); ax[1].legend(loc="upper left")
rows = R["critical_arrhenius"]
ax[2].plot([r["prediction_fold"] for r in rows], [r["Pi_c_arrhenius"] for r in rows], "o", color=BL, label=r"FK$(\Theta)\times$ frozen-fold factor")
ax[2].plot([r["prediction_first_order"] for r in rows], [r["Pi_c_arrhenius"] for r in rows], "x", color=GR, label=r"FK$(\Theta)\times e^{1/{\rm Ar}}$")
g = [r for r in rows if r["Pi_c_gated"]]
ax[2].plot([r["prediction_fold"] for r in g], [r["Pi_c_gated"] for r in g], "s", color=OR, mfc="none", label="with release lag")
lim = [1.9, 2.8]
ax[2].plot(lim, lim, "k--", lw=0.8)
ax[2].set_xlabel("prediction"); ax[2].set_ylabel(r"operational $\Pi_c$, Arrhenius model"); ax[2].set_title("(c) Arrhenius model (tested grid)"); ax[2].legend(fontsize=7.5)
plt.tight_layout(); save(fig, "fig3_criticality")

# ------------------------------------------------------------------ Figure 4: flow reactor with stability
fl = R["flow"]
eps, n, vt = fl["eps"], fl["n"], fl["vartheta"]
case = [c for c in fl["cases"] if c["psi"] == 20.0][0]
psi = 20.0
kap = case["kappa"]
w = case["window"]
fig, ax = plt.subplots(1, 3, figsize=(10.2, 3.2))
al = np.geomspace(1e-6, 0.99999, 6000)
D = T.g_curve(al, eps, n, kap)
stable = np.array([(lambda td: td[0] < 0 and td[1] > 0)(T.trace_det(x, eps, n, psi, vt)) for x in al])
lnD = np.log(D)
for seg_mask, ls, lab in ((stable, "-", "stable"), (~stable, "--", "unstable")):
    xs = np.where(seg_mask, lnD, np.nan)
    ys = np.where(seg_mask, al, np.nan)
    ax[0].plot(xs, ys, color=BL if ls == "-" else GR, ls=ls, lw=1.7, label=lab)
fl2 = T.folds(eps, n, kap)
ax[0].plot(np.log(T.g_curve(fl2[0], eps, n, kap)), fl2[0], "s", color=RD, label="folds")
ax[0].plot(np.log(T.g_curve(fl2[1], eps, n, kap)), fl2[1], "s", color=RD)
ax[0].plot(w["lnD_ext"], w["alpha_ext"], "o", color=GN, label="Hopf-type point")
ax[0].set_xlim(-8, 1); ax[0].set_xlabel(r"$\ln D$  ($D=k_2\tau_{\rm res}$)"); ax[0].set_ylabel(r"steady conversion $\alpha$"); ax[0].set_title(r"(a) Steady states, $\psi=20$ ($\kappa=%.0f$)" % kap); ax[0].legend(loc="center left", fontsize=8)
lo_, hi_ = case["sweep_bounds"]
for v, c in ((0.02, OR), (0.002, RD)):
    T_leg = (hi_ - lo_) / v
    t1, t2, t3, t4, tend = 20.0, 20.0 + T_leg, 40.0 + T_leg, 40.0 + 2 * T_leg, 60.0 + 2 * T_leg

    def lnD_of(t, v=v, t1=t1, t2=t2, t3=t3, t4=t4):
        return lo_ if t <= t1 else lo_ + v * (t - t1) if t <= t2 else hi_ if t <= t3 else hi_ - v * (t - t3) if t <= t4 else lo_

    def f(t, y, v=v):
        th, a_ = y
        Dd = np.exp(lnD_of(t))
        r = (eps + max(a_, 0)) * np.exp(min(psi * th, 300)) * max(1 - a_, 0) ** n
        return [Dd * r - th * (1 + 1 / vt), Dd * r - a_]
    ts = np.arange(0, tend, 0.2)
    s = solve_ivp(f, [0, tend], [0, 0], method="LSODA", rtol=1e-8, atol=1e-12, t_eval=ts, max_step=min(0.5, 0.02 / v))
    ax[1].plot([lnD_of(t) for t in s.t], s.y[1], color=c, lw=1.1, label="sweep rate %g / $\\tau_{\\rm res}$" % v)
ax[1].plot(np.where(stable, lnD, np.nan), np.where(stable, al, np.nan), color=BL, lw=0.9, ls=":", label="stable steady states")
ax[1].axvline(w["lnD_ext"], color=GN, lw=0.8, ls="-."); ax[1].axvline(w["lnD_ign"], color=RD, lw=0.8, ls="-.")
ax[1].set_xlim(-8, 1); ax[1].set_xlabel(r"$\ln D$"); ax[1].set_ylabel(r"$\alpha$"); ax[1].set_title("(b) Sweep loops and the stable window"); ax[1].legend(loc="center left", fontsize=7.5)
vs = np.array([p["v"] for p in case["sweeps"]])
ax[2].plot(vs, [p["area"] for p in case["sweeps"]], "o-", color=BL, label="integrated loop area")
vf = np.linspace(0, 0.021, 100)
ax[2].plot(vf, case["fit_A0"] + case["fit_c"] * vf ** case["fit_p"], "-", color=GR, lw=0.9, label=r"fit $A_0+cv^p$, $p=%.2f$" % case["fit_p"])
ax[2].axhline(case["attractor_area"], color=RD, ls="--", label="attractor loop area %.2f" % case["attractor_area"])
ax[2].axhline(case["multiplicity_area"], color=GR, ls=":", label="fold-to-fold area %.2f" % case["multiplicity_area"])
ax[2].set_xlabel(r"sweep rate $v$ (per residence time)"); ax[2].set_ylabel(r"loop area $\oint\alpha\,d\ln D$"); ax[2].set_title("(c) Convergence with sweep rate"); ax[2].set_xlim(0, 0.022); ax[2].legend(fontsize=7.5)
plt.tight_layout(); save(fig, "fig4_flow_reactor")

# ------------------------------------------------------------------ Figure 5: recovery
rc = R["recovery"]
est = np.array(rc["estimates"])
fig, ax = plt.subplots(figsize=(3.6, 3.1))
ax.plot(est[:, 1], est[:, 0], "o", color=BL, ms=3.5, alpha=0.7, label="fits to noisy ODE data")
ax.plot(rc["true_Tm"], rc["true_sigma"], "*", color=RD, ms=13, label="true value")
ax.set_xlabel(r"recovered mean melting temperature $T_m$ (°C)"); ax.set_ylabel(r"recovered spread $\sigma$ (°C)"); ax.set_title("Recovery from storage curves"); ax.legend()
plt.tight_layout(); save(fig, "fig5_recovery")
print("figures written")
