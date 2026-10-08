"""Draws Figures 1-6 from results.json (and a few fast direct evaluations) at final print size: no titles inside the figures, panel letters inside the axes,
sans-serif lettering of about 8 pt, 119 mm (4.7 in) wide for multi-panel figures; PNG at 600 dpi and vector EPS.   python figures.py"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
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
plt.rcParams.update({"font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5, "legend.fontsize": 7, "savefig.dpi": 600,
                     "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "mathtext.fontset": "dejavusans",
                     "axes.linewidth": 0.6, "lines.linewidth": 1.2, "ps.fonttype": 42})
BL, OR, GR, RD, GN = "#1f4e9c", "#c0661b", "#4d4d4d", "#b22222", "#2a7f3f"
W = 4.7          # 119 mm


def save(fig, name):
    fig.savefig(OUT + name + ".png")
    fig.savefig(OUT + name + ".eps")
    plt.close(fig)


def letter(ax, s, x=0.03, y=0.95):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top", ha="left")


def three_panel(height=5.0):
    fig = plt.figure(figsize=(W, height))
    gs = GridSpec(2, 2, figure=fig, height_ratios=[1, 1], hspace=0.36, wspace=0.38, left=0.13, right=0.98, top=0.985, bottom=0.075)
    return fig, fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])


def rates(T_C):
    return (float(T.arrhenius(C.A1, C.EA1, T_C)), float(T.arrhenius(C.A2, C.EA2, T_C)), float(T.arrhenius(C.A_REL, C.EA_REL, T_C)))


# ------------------------------------------------------------------ Figure 1: availability clock, delay, sharpness
fig, a0, a1, a2 = three_panel(4.8)
a, b, kr = rates(140.0)
al = np.linspace(0.001, 0.995, 500)
iso = np.array([T.t_iso(x, a, b, 1.5) for x in al])
gat = np.array([T.t_gated(x, a, b, 1.5, kr) for x in al])
a0.plot(iso, al, color=GR, label="no gate")
a0.plot(gat, al, color=BL, label="gated, clock formula")
num = C.integrate([140.0], tau_th=1e9, width=0.5, p=dict(dtad=0.0), T0_off=0.0, dt=0.01, tmax=70.0)
for k, lev in (("t10", 0.1), ("t50", 0.5), ("t90", 0.9)):
    a0.plot(float(num[k][0]), lev, "o", color=OR, ms=3.5, zorder=5, label="integrated ODE" if k == "t10" else None)
a0.set_xlabel("Time (min)")
a0.set_ylabel("Conversion")
a0.legend(loc="center left", bbox_to_anchor=(0.0, 0.42), framealpha=0.9)
a0.set_xlim(0, 80)
letter(a0, "(a)")
a1.plot(gat, [T.gate_delay(t, kr) for t in gat], color=BL, label="Eq. (6)")
a1.axhline(1 / kr, color=RD, ls="--", lw=0.9, label="release time %.1f min" % (1 / kr))
a1.plot([d["t_gated"] for d in R["delay_vs_alpha"]], [d["delay"] for d in R["delay_vs_alpha"]], "o", color=OR, ms=3.5, label="integrated ODE")
a1.set_xscale("log")
a1.set_xlim(2, 120)
a1.set_xlabel("Gated time (min)")
a1.set_ylabel("Delay (min)")
a1.legend(loc="center right", bbox_to_anchor=(1.0, 0.45), framealpha=0.9)
letter(a1, "(b)")
rows = [r for r in R["isothermal"] if r["n"] == 1.0]
x = np.array([np.log(r["ratio"]) for r in rows])
a2.plot(x, [r["S_exact_n1"] for r in rows], "s-", color=GR, ms=3.5, label="exact, n = 1")
a2.plot(x, [r["S_law"] for r in rows], "--", color=BL, label="asymptotic law, n = 1")
rows15 = [r for r in R["isothermal"] if r["n"] == 1.5]
a2.plot([np.log(r["ratio"]) for r in rows15], [r["S_num"] for r in rows15], "o", color=OR, ms=3.5, label="integrated, n = 3/2")
a2.set_xlabel("ln(k$_2$/k$_1$)")
a2.set_ylabel("Sharpness S")
a2.legend(loc="center right", bbox_to_anchor=(1.0, 0.6))
letter(a2, "(c)", x=0.93)
save(fig, "fig1_clock_sharpness")

# ------------------------------------------------------------------ Figure 2: storage leakage and design rule
fig, ax = plt.subplots(1, 2, figsize=(W, 2.5))
L = [r for r in R["leakage"] if r["numeric"] > 1e-6]
cols = {3.0: RD, 6.0: BL, 10.0: OR}
for mg in (3.0, 6.0, 10.0):
    pts = [r for r in L if r["margin"] == mg]
    ax[0].loglog([r["numeric"] for r in pts], [r["closed_form"] for r in pts], "o", ms=3.5, color=cols[mg], label=r"$\Delta$ = %.0f °C" % mg)
lim = [1e-5, 0.2]
ax[0].plot(lim, lim, "k--", lw=0.7)
ax[0].set_xlabel("Population ODE, storage conversion")
ax[0].set_ylabel("Closed form")
ax[0].legend(loc="lower right")
letter(ax[0], "(a)")
etas = np.geomspace(5e-4, 0.08, 40)
for mg in (3.0, 6.0, 10.0):
    Ts = 118.0 - mg
    a_, b_, kr_ = rates(Ts)
    ss_ = np.array([T.sigma_star(e, mg, a_, b_, kr_, 150.0) for e in etas])
    ss_[~np.isfinite(ss_) | (ss_ > 40)] = np.nan
    ax[1].loglog(etas, ss_, color=cols[mg], label=r"$\Delta$ = %.0f °C" % mg)
    pts = [r for r in R["design_rule"] if r["margin"] == mg and r["sigma_star_ode"]]
    ax[1].plot([r["eta"] for r in pts], [r["sigma_star_ode"] for r in pts], "o", ms=3.5, color=cols[mg], mfc="white")
ax[1].set_xlabel("Tolerance $\\eta$ on storage conversion")
ax[1].set_ylabel("Largest spread $\\sigma^*$ (°C)")
ax[1].legend(loc="upper left")
letter(ax[1], "(b)", y=0.17, x=0.75)
plt.tight_layout()
save(fig, "fig2_storage")

# ------------------------------------------------------------------ Figure 3: criticality
fig, a0, a1, a2 = three_panel(5.0)
for n, c in ((1.0, GR), (1.5, BL), (2.0, OR)):
    rows = [r for r in R["critical_fk"] if r["n"] == n]
    a0.semilogx([r["Theta"] for r in rows], [r["Pi_c_numeric"] for r in rows], "o-", ms=3.5, color=c, label="n = %.1f" % n)
    a0.axhline(rows[0]["Pi_c_finite_eps"], color=c, ls="--", lw=0.8)
a0.set_xlabel(r"$\Theta=\tau_{\rm th}k_2$")
a0.set_ylabel(r"Operational $\Pi_c=\psi\Theta$")
a0.legend(loc="upper left", bbox_to_anchor=(0.12, 1.0))
letter(a0, "(a)", x=0.03, y=0.95)
Pc = T.Pi_c0(1.5, 3e-3)
Pis = np.linspace(0.05, Pc, 200)
a1.plot(Pis / Pc, [-np.real(lambertw(-p / (np.e * Pc))) for p in Pis], color=BL, label=r"$-W_0(-\Pi/e\Pi_c)$")
a1.plot(Pis / Pc, 1 - np.sqrt(2 * (1 - Pis / Pc)), ":", color=RD, label="fold normal form")
for r in R["fold_exponent"]:
    a1.plot(r["frac"], r["psi_theta_numeric"], "o", ms=3.5, color=OR, label=r"integrated ($\Theta=0.002$)" if r["frac"] == 0.5 else None)
a1.set_xlabel(r"$\Pi/\Pi_c$")
a1.set_ylabel(r"$\psi\,\theta_{\rm peak}$")
a1.set_ylim(0, 1.1)
a1.legend(loc="upper left", bbox_to_anchor=(0.12, 1.0))
letter(a1, "(b)", x=0.03, y=0.95)
rows = R["critical_arrhenius"]
a2.plot([r["prediction_fold"] for r in rows], [r["Pi_c_arrhenius"] for r in rows], "o", ms=3.5, color=BL, label=r"FK$(\Theta)\times$ frozen-fold factor")
a2.plot([r["prediction_first_order"] for r in rows], [r["Pi_c_arrhenius"] for r in rows], "x", ms=3.5, color=GR, label=r"FK$(\Theta)\times e^{1/{\rm Ar}}$")
g = [r for r in rows if r["Pi_c_gated"]]
a2.plot([r["prediction_fold"] for r in g], [r["Pi_c_gated"] for r in g], "s", ms=3.5, color=OR, mfc="none", label="with release lag")
lim = [1.9, 2.8]
a2.plot(lim, lim, "k--", lw=0.7)
a2.set_xlabel("Prediction")
a2.set_ylabel(r"Operational $\Pi_c$, Arrhenius model")
a2.legend(loc="upper left", bbox_to_anchor=(0.12, 1.0))
letter(a2, "(c)", x=0.03, y=0.95)
save(fig, "fig3_criticality")

# ------------------------------------------------------------------ Figure 4: flow reactor with stability
fl = R["flow"]
eps, n, vt = fl["eps"], fl["n"], fl["vartheta"]
case = [c for c in fl["cases"] if c["psi"] == 20.0][0]
psi = 20.0
kap = case["kappa"]
w = case["window"]
fig, a0, a1, a2 = three_panel(5.0)
al = np.geomspace(1e-6, 0.99999, 6000)
D = T.g_curve(al, eps, n, kap)
stable = np.array([(lambda td: td[0] < 0 and td[1] > 0)(T.trace_det(x, eps, n, psi, vt)) for x in al])
lnD = np.log(D)
a0.plot(np.where(stable, lnD, np.nan), al, color=BL, lw=1.4, label="stable")
a0.plot(np.where(~stable, lnD, np.nan), al, color=GR, ls="--", lw=1.2, label="unstable")
fl2 = T.folds(eps, n, kap)
a0.plot(np.log(T.g_curve(fl2[0], eps, n, kap)), fl2[0], "s", ms=3.5, color=RD, label="folds")
a0.plot(np.log(T.g_curve(fl2[1], eps, n, kap)), fl2[1], "s", ms=3.5, color=RD)
a0.plot(w["lnD_ext"], w["alpha_ext"], "o", ms=4, color=GN, label="Hopf-type point")
a0.set_xlim(-8, 1)
a0.set_xlabel("ln D")
a0.set_ylabel("Steady conversion")
a0.legend(loc="center right", bbox_to_anchor=(1.0, 0.45), framealpha=0.9)
letter(a0, "(a)")
lo_, hi_ = case["sweep_bounds"]
for v, c in ((0.02, OR), (0.002, RD)):
    T_leg = (hi_ - lo_) / v
    t1, t2, t3, t4, tend = 20.0, 20.0 + T_leg, 40.0 + T_leg, 40.0 + 2 * T_leg, 60.0 + 2 * T_leg

    def lnD_of(t, v=v, t1=t1, t2=t2, t3=t3, t4=t4):
        return lo_ if t <= t1 else lo_ + v * (t - t1) if t <= t2 else hi_ if t <= t3 else hi_ - v * (t - t3) if t <= t4 else lo_

    def f(t, y, v=v, lnD_of=lnD_of):
        th, a_ = y
        Dd = np.exp(lnD_of(t))
        r = (eps + max(a_, 0)) * np.exp(min(psi * th, 300)) * max(1 - a_, 0) ** n
        return [Dd * r - th * (1 + 1 / vt), Dd * r - a_]
    ts = np.arange(0, tend, 0.2)
    s = solve_ivp(f, [0, tend], [0, 0], method="LSODA", rtol=1e-8, atol=1e-12, t_eval=ts, max_step=min(0.5, 0.02 / v))
    a1.plot([lnD_of(t) for t in s.t], s.y[1], color=c, lw=1.0, label="v = %g" % v)
a1.plot(np.where(stable, lnD, np.nan), np.where(stable, al, np.nan), color=BL, lw=0.8, ls=":", label="stable states")
a1.axvline(w["lnD_ext"], color=GN, lw=0.7, ls="-.")
a1.axvline(w["lnD_ign"], color=RD, lw=0.7, ls="-.")
a1.set_xlim(-8, 1)
a1.set_xlabel("ln D")
a1.set_ylabel("Conversion")
a1.legend(loc="center", bbox_to_anchor=(0.55, 0.45), framealpha=0.9)
letter(a1, "(b)")
vs = np.array([p["v"] for p in case["sweeps"]])
a2.plot(vs, [p["area"] for p in case["sweeps"]], "o-", ms=3.5, color=BL, label="integrated loop area")
vf = np.linspace(0, 0.021, 100)
a2.plot(vf, case["fit_A0"] + case["fit_c"] * vf ** case["fit_p"], "-", color=GR, lw=0.8, label=r"fit $A_0+cv^p$, $p=%.2f$" % case["fit_p"])
a2.axhline(case["attractor_area"], color=RD, ls="--", label="stable-state loop area %.2f" % case["attractor_area"])
a2.axhline(case["multiplicity_area"], color=GR, ls=":", label="fold-to-fold area %.2f" % case["multiplicity_area"])
a2.set_xlabel("Sweep rate v (per residence time)")
a2.set_ylabel("Loop area")
a2.set_xlim(0, 0.022)
a2.legend(loc="center right")
letter(a2, "(c)")
save(fig, "fig4_flow_reactor")

# ------------------------------------------------------------------ Figure 5: Arrhenius temperature path and noise dependence of the exit
af = [c for c in R["arrhenius_flow"]["cases"] if c["dtad"] == 220.0][0]
tau_r, vt_, dtad = R["arrhenius_flow"]["tau_res"], R["arrhenius_flow"]["vartheta"], 220.0
al2, T2, Tinf2 = N.arr_flow_curve(tau_r, vt_, dtad, 1.5, 3000)
ev2 = np.array([np.linalg.eigvals(N.arr_flow_jacobian(al2[i], T2[i], Tinf2[i], tau_r, vt_, dtad)) for i in range(len(al2))])
st2 = ev2.real.max(axis=1) < 0
fig, ax = plt.subplots(1, 2, figsize=(W, 2.6))
ax[0].plot(np.where(st2, Tinf2, np.nan), al2, color=BL, lw=1.4, label="stable")
ax[0].plot(np.where(~st2, Tinf2, np.nan), al2, color=GR, ls="--", lw=1.2, label="unstable")
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
    ax[0].plot([Ti(t) for t in s_.t], s_.y[1], color=c, lw=0.9, label="ramp %g K per residence time" % rate)
ax[0].axvline(wv["T_ext"], color=GN, lw=0.7, ls="-.")
ax[0].axvline(wv["T_ign"], color=RD, lw=0.7, ls="-.")
ax[0].set_xlim(wv["T_ext"] - 15, wv["T_ign"] + 15)
ax[0].set_xlabel("Wall temperature (°C)")
ax[0].set_ylabel("Conversion")
ax[0].legend(fontsize=6.3, loc="upper left")
letter(ax[0], "(a)", x=0.8, y=0.55)
hn = R["hopf_noise"]
tol = [d["rtol"] for d in hn["by_tolerance"]]
ax[1].semilogx(tol, [d["lnD_down"] for d in hn["by_tolerance"]], "o-", ms=3.5, color=BL, label="sweep, v = 0.001")
ax[1].axhline(hn["lnD_hopf"], color=GN, ls="--", label="Hopf-type point")
ax[1].axhline(hn["lnD_upper_fold"], color=RD, ls=":", label="upper fold")
ax[1].invert_xaxis()
ax[1].set_xlabel("Integrator tolerance")
ax[1].set_ylabel("ln D at extinction")
ax[1].set_ylim(-5.68, -5.40)
ax[1].legend(loc="center right", fontsize=6.5)
letter(ax[1], "(b)", y=0.5)
plt.tight_layout()
save(fig, "fig5_arrhenius_path")

# ------------------------------------------------------------------ Figure 6: recovery
rc = R["recovery"]
est = np.array(rc["estimates"])
fig, ax = plt.subplots(figsize=(3.3, 2.8))
ax.plot(est[:, 1], est[:, 0], "o", color=BL, ms=3, alpha=0.7, label="fits to noisy ODE data")
ax.plot(rc["true_Tm"], rc["true_sigma"], "*", color=RD, ms=10, label="true value")
ax.set_xlabel(r"Recovered mean melting temperature (°C)")
ax.set_ylabel(r"Recovered spread (°C)")
ax.legend(loc="upper left")
plt.tight_layout()
save(fig, "fig6_recovery")
print("figures written")
