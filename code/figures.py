"""Draws Figures 1-5 from results.json (and a few fast direct evaluations).   python figures.py"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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
BL, OR, GR, RD = "#1f4e9c", "#c0661b", "#4d4d4d", "#b22222"


def rates(T_C):
    return (float(T.arrhenius(C.A1, C.EA1, T_C)), float(T.arrhenius(C.A2, C.EA2, T_C)), float(T.arrhenius(C.A_REL, C.EA_REL, T_C)))


# ------------------------------------------------------------------ Figure 1: availability clock and sharpness law
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1))
a, b, kr = rates(140.0)
tt = np.linspace(0, 70, 800)
al = np.linspace(0.001, 0.995, 500)
iso = np.array([T.t_iso(x, a, b, 1.5) for x in al])
gat = np.array([T.t_gated(x, a, b, 1.5, kr) for x in al])
ax[0].plot(iso, al, color=GR, lw=1.6, label="no gate (isothermal)")
ax[0].plot(gat, al, color=BL, lw=1.6, label="gated: availability clock")
num = C.integrate([140.0], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=70.0)
for k, lev in (("t10", 0.1), ("t50", 0.5), ("t90", 0.9)):
    ax[0].plot(float(num[k][0]), lev, "o", color=OR, ms=5, zorder=5, label="integrated ODE" if k == "t10" else None)
ax[0].annotate("", xy=(T.t_gated(0.5, a, b, 1.5, kr), 0.5), xytext=(T.t_iso(0.5, a, b, 1.5), 0.5), arrowprops=dict(arrowstyle="<->", color=RD))
ax[0].text(T.t_iso(0.5, a, b, 1.5) + 1.0, 0.43, r"$\approx\tau_{\rm rel}=%.1f$ min" % (1 / kr), color=RD, fontsize=8)
ax[0].set_xlabel("time (min)"); ax[0].set_ylabel(r"conversion $\alpha$"); ax[0].set_title("(a) Gated cure at constant $T$ = 140 °C"); ax[0].legend(loc="lower right"); ax[0].set_xlim(0, 60)
rows = [r for r in R["isothermal"] if r["n"] == 1.0]
x = np.array([np.log(r["ratio"]) for r in rows])
ax[1].plot(x, [r["S_th"] for r in rows], "s-", color=GR, label=r"exact, $n=1$")
ax[1].plot(x, [r["S_law"] for r in rows], "--", color=BL, label=r"law $2\ln 9/\ln(b/9a)$")
rows15 = [r for r in R["isothermal"] if r["n"] == 1.5]
ax[1].plot([np.log(r["ratio"]) for r in rows15], [r["S_num"] for r in rows15], "o", color=OR, label=r"integrated, $n=1.5$")
ax[1].set_xlabel(r"$\ln(k_2/k_1)$"); ax[1].set_ylabel(r"sharpness $S=(t_{90}-t_{10})/t_{10}$"); ax[1].set_title("(b) Sharpness is set by the rate-constant ratio"); ax[1].legend()
plt.tight_layout(); plt.savefig(OUT + "fig1_clock_sharpness.png"); plt.close()

# ------------------------------------------------------------------ Figure 2: storage leakage and design rule
fig, ax = plt.subplots(1, 2, figsize=(7.2, 3.1))
L = [r for r in R["leakage"] if r["numeric"] > 1e-6]
cols = {3.0: RD, 6.0: BL, 10.0: OR}
for mg in (3.0, 6.0, 10.0):
    pts = [r for r in L if r["margin"] == mg]
    ax[0].loglog([r["numeric"] for r in pts], [r["analytic"] for r in pts], "o", color=cols[mg], label=r"$\Delta$ = %.0f °C" % mg)
lim = [1e-5, 0.2]
ax[0].plot(lim, lim, "k--", lw=0.8)
ax[0].set_xlabel("population ODE, storage conversion"); ax[0].set_ylabel("closed form"); ax[0].set_title("(a) Storage conversion after 150 min"); ax[0].legend()
epss = np.geomspace(5e-4, 0.08, 30)
for mg in (3.0, 6.0, 10.0):
    Ts = 118.0 - mg
    a_, b_, kr_ = rates(Ts)
    ss_ = np.array([T.sigma_star(e, mg, a_, b_, kr_, 150.0) for e in epss])
    ss_[ss_ > 40] = np.nan
    ax[1].loglog(epss, ss_, color=cols[mg], label=r"closed form, $\Delta$ = %.0f °C" % mg)
    pts = [r for r in R["design_rule"] if r["margin"] == mg and r["sigma_star_numeric"]]
    ax[1].plot([r["eps"] for r in pts], [r["sigma_star_numeric"] for r in pts], "o", color=cols[mg], mfc="white")
ax[1].set_xlabel(r"tolerance $\varepsilon$ on storage conversion"); ax[1].set_ylabel(r"largest admissible spread $\sigma^*$ (°C)"); ax[1].set_title("(b) Design rule (open symbols: ODE)"); ax[1].legend()
plt.tight_layout(); plt.savefig(OUT + "fig2_storage.png"); plt.close()

# ------------------------------------------------------------------ Figure 3: criticality
fig, ax = plt.subplots(1, 3, figsize=(10.2, 3.1))
for n, c in ((1.0, GR), (1.5, BL), (2.0, OR)):
    rows = [r for r in R["critical_fk"] if r["n"] == n]
    ax[0].semilogx([r["Theta"] for r in rows], [r["Pi_c_numeric"] for r in rows], "o-", color=c, label=r"$n=%.1f$" % n)
    ax[0].axhline(rows[0]["Pi_c0"], color=c, ls="--", lw=0.9)
ax[0].set_xlabel(r"$\Theta=\tau_{\rm th}k_2$"); ax[0].set_ylabel(r"critical number $\Pi_c=\psi\Theta$"); ax[0].set_title(r"(a) $\Pi_c\to e^{-1}(1+n)^{1+n}/n^n$"); ax[0].legend()
Pc = T.Pi_c0(1.5, 3e-3)
Pis = np.linspace(0.05, Pc, 200)
ax[1].plot(Pis / Pc, [-np.real(__import__("scipy.special", fromlist=["lambertw"]).lambertw(-p / (np.e * Pc))) for p in Pis], color=BL, label=r"$-W_0(-\Pi/e\Pi_c)$")
ax[1].plot(Pis / Pc, 1 - np.sqrt(2 * (1 - Pis / Pc)), ":", color=RD, label="fold normal form")
for r in R["fold_exponent"]:
    ax[1].plot(r["frac"], r["psi_theta_numeric"], "o", color=OR, label=r"integrated ($\Theta=0.002$)" if r["frac"] == 0.5 else None)
ax[1].set_xlabel(r"$\Pi/\Pi_c$"); ax[1].set_ylabel(r"$\psi\,\theta_{\rm peak}$"); ax[1].set_title("(b) Quasi-steady overshoot, fold at $\\Pi_c$"); ax[1].set_ylim(0, 1.1); ax[1].legend(loc="upper left")
rows = R["critical_arrhenius"]
ax[2].plot([r["prediction"] for r in rows], [r["Pi_c_arrhenius"] for r in rows], "o", color=BL, label="Arrhenius model, no gate")
g = [r for r in rows if r["Pi_c_gated"]]
ax[2].plot([r["prediction"] for r in g], [r["Pi_c_gated"] for r in g], "s", color=OR, label="with release lag")
lim = [1.8, 3.6]
ax[2].plot(lim, lim, "k--", lw=0.8)
ax[2].set_xlabel(r"prediction $\Pi_c^{\rm FK}(\Theta)\,e^{1/{\rm Ar}}$"); ax[2].set_ylabel(r"$\Pi_c$ of the Arrhenius model"); ax[2].set_title("(c) Arrhenius correction $e^{1/{\\rm Ar}}$"); ax[2].legend()
plt.tight_layout(); plt.savefig(OUT + "fig3_criticality.png"); plt.close()

# ------------------------------------------------------------------ Figure 4: flow reactor
fl = R["flow"]
case = [c for c in fl["cases"] if c["bistable"] and c["psi"] == 20.0][0]
eps, n, kap = fl["eps"], fl["n"], case["kappa"]
fig, ax = plt.subplots(1, 3, figsize=(10.2, 3.1))
al = np.concatenate([np.geomspace(1e-6, 0.999, 4000)])
D = T.g_curve(al, eps, n, kap)
ax[0].plot(np.log(D), al, color=BL, lw=1.6)
lo, hi = T.folds(eps, n, kap)
for x_ in (lo, hi):
    ax[0].plot(np.log(T.g_curve(x_, eps, n, kap)), x_, "o", color=RD)
ax[0].set_xlim(-8, 3); ax[0].set_xlabel(r"$\ln D$  ($D=k_2\tau_{\rm res}$)"); ax[0].set_ylabel(r"steady conversion $\alpha$"); ax[0].set_title(r"(a) S-curve, $\kappa=%.1f>\kappa_c=%.2f$" % (kap, fl["kappa_c"]))
psi, vt = case["psi"], fl["vartheta"]
for v, c in ((0.05, OR), (0.01, RD)):
    lo_, hi_ = case["lnD_down"] - 2.0, case["lnD_up"] + 2.0
    T_leg = (hi_ - lo_) / v
    from scipy.integrate import solve_ivp

    def lnD_of(t, v=v, lo_=lo_, hi_=hi_, T_leg=T_leg):
        return lo_ + v * t if t <= T_leg else hi_ - v * (t - T_leg)

    def f(t, y, v=v):
        th, a_ = y
        Dd = np.exp(lnD_of(t))
        r = (eps + max(a_, 0)) * np.exp(min(psi * th, 300)) * max(1 - a_, 0) ** n
        return [Dd * r - th * (1 + 1 / vt), Dd * r - a_]
    ts = np.arange(0, 2 * T_leg, 0.1)
    s = solve_ivp(f, [0, 2 * T_leg], [0, 0], method="LSODA", rtol=1e-8, atol=1e-12, t_eval=ts, max_step=min(0.5, 0.02 / v))
    ax[1].plot([lnD_of(t) for t in s.t], s.y[1], color=c, lw=1.1, label="sweep rate %.2f / $\\tau_{\\rm res}$" % v)
ax[1].plot(np.log(D), al, "k:", lw=0.9, label="steady states")
ax[1].set_xlim(-8, 3); ax[1].set_xlabel(r"$\ln D$"); ax[1].set_ylabel(r"$\alpha$"); ax[1].set_title("(b) Ignition-extinction loops"); ax[1].legend(loc="center left")
vs = [p["v"] for p in case["sweeps"]]
ax[2].plot(vs, [p["area"] for p in case["sweeps"]], "o-", color=BL, label="integrated loop area")
ax[2].axhline(case["static_area"], color=RD, ls="--", label="static loop (closed form) %.2f" % case["static_area"])
ax[2].set_xlabel(r"sweep rate $v$ (per residence time)"); ax[2].set_ylabel(r"loop area $\oint\alpha\,d\ln D$"); ax[2].set_title("(c) Extrapolation to zero sweep rate"); ax[2].set_xlim(0, 0.055); ax[2].legend()
plt.tight_layout(); plt.savefig(OUT + "fig4_flow_reactor.png"); plt.close()

# ------------------------------------------------------------------ Figure 5: recovery
rc = R["recovery"]
est = np.array(rc["estimates"])
fig, ax = plt.subplots(figsize=(3.6, 3.1))
ax.plot(est[:, 1], est[:, 0], "o", color=BL, ms=3.5, alpha=0.7, label="fits to noisy ODE data")
ax.plot(rc["true_Tm"], rc["true_sigma"], "*", color=RD, ms=13, label="true value")
ax.set_xlabel(r"recovered mean melting temperature $T_m$ (°C)"); ax.set_ylabel(r"recovered spread $\sigma$ (°C)"); ax.set_title("Recovery from storage curves"); ax.legend()
plt.tight_layout(); plt.savefig(OUT + "fig5_recovery.png"); plt.close()
print("figures written")
