# -*- coding: utf-8 -*-
"""Builds the manuscript (Journal of Chemical Physics, Regular Article) from results.json. Every number in the text is read from the results.

    python build_manuscript.py          (run twice so that table numbers resolve)   ->  out/Gated_Autocatalysis_Criticality_JCP.docx
"""
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
import docx_helpers as H  # noqa: E402
import theory as T        # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
REFS = json.load(open(os.path.join(ROOT, "refs", "refs_cache.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_gac_zenodo_state.json")))
SW_DOI, PP_DOI = (ZEN.get("software_1.1.0") or ZEN["software"])["doi"], (ZEN.get("publication_v2") or ZEN["publication"])["doi"]
RELEASE = os.environ.get("RELEASE_TAG", "v1.1.0")
REPO = "https://github.com/sandlerleon/gated-autocatalysis-criticality"

TITLE = "Closed-Form Storage Stability, Induction Delay, and Thermal-Feedback Criticality of Melt-Gated Autocatalytic Cure"

# ------------------------------------------------------------------ numbers
n_ord = 1.5
CL, DA, IA, IS, LK, DR, RC, RP = R["clock"], R["delay_vs_alpha"], R["incomplete_activation"], R["isothermal"], R["leakage"], R["design_rule"], R["recovery"], R["recovery_prior"]
FK, AR, FL, CV = R["critical_fk"], R["critical_arrhenius"], R["flow"], R["convergence"]
clock_err = max(abs(r["clock"] - r["numeric"]) / r["numeric"] for r in CL)
iso_err = max(max(abs(r["t10_th"] - r["t10_num"]) / r["t10_num"], abs(r["t90_th"] - r["t90_num"]) / r["t90_num"]) for r in IS)
r140_1 = [r for r in IS if r["T"] == 140.0 and r["n"] == 1.0][0]
r140_15 = [r for r in IS if r["T"] == 140.0 and r["n"] == 1.5][0]
law_err = max(abs(r["S_law"] / r["S_exact_n1"] - 1) for r in IS if r["n"] == 1.0)
SE = R["sharpness_endpoints"]
lk_ok = [r for r in LK if r["numeric"] > 1e-5]
lk_dev = [abs(r["closed_form"] / r["numeric"] - 1) for r in lk_ok]
dr_ok = [r for r in DR if r["sigma_star_ode"] and r["sigma_star_closed"] and r["sigma_star_closed"] < 40]
dr_dev = [abs(r["sigma_star_closed"] / r["sigma_star_ode"] - 1) for r in dr_ok]
fk15 = {r["Theta"]: r for r in FK if r["n"] == 1.5}
EPS = 3e-3
PIC0 = {n: T.Pi_c0(n, 0.0) for n in (1.0, 1.5, 2.0)}
PICE = {n: T.Pi_c0(n, EPS) for n in (1.0, 1.5, 2.0)}
ar_dev = [abs(r["Pi_c_arrhenius"] / r["prediction_fold"] - 1) for r in AR]
ar_dev1 = [abs(r["Pi_c_arrhenius"] / r["prediction_first_order"] - 1) for r in AR]
ar_fk_dev = [abs(r["Pi_c_arrhenius"] / r["Pi_c_fk"] - 1) for r in AR]
gated = [r for r in AR if r["Pi_c_gated"]]
Ar_lo, Ar_hi = min(r["Ar"] for r in AR), max(r["Ar"] for r in AR)
KC = FL["kappa_c"]
CASE = {c["psi"]: c for c in FL["cases"]}
STAB = {s["psi"]: s for s in FL["stability"]}
a140, b140, kr140 = float(T.arrhenius(2.0e3, 5.0e4, 140.0)), float(T.arrhenius(2.5e7, 6.5e4, 140.0)), float(T.arrhenius(6.4e6, 6.0e4, 140.0))
conv_K = max(abs(c["rel_diff"]) for c in CV if c["kind"] == "K" and c["K"] == 801)
conv_dt = max(abs(c["rel_diff"]) for c in CV if c["kind"] == "dt" and c["dt"] == 0.05)
KELVIN = FL["RT2_over_E2_K_at_140C"]
print("clock err %.2e | iso err %.2e | law err %.3f | leak dev %.3f | sigma* dev %.3f | Arr dev (fold) %.3f (first order) %.3f" % (clock_err, iso_err, law_err, max(lk_dev), max(dr_dev), max(ar_dev), max(ar_dev1)))

# ------------------------------------------------------------------ citations and numbering
CITE = []
LABFILE = os.path.join(OUT, "labels.json")
TLAB = json.load(open(LABFILE)) if os.path.exists(LABFILE) else {}
TLAB_NEW = {}
FIGN, TABN = [0], [0]
NUM = {}


def compress(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append("%d–%d" % (nums[i], nums[j]) if j - i >= 2 else ", ".join(str(n) for n in nums[i:j + 1]))
        i = j + 1
    return ", ".join(out)


def cites(text):
    def rep(m):
        nums = []
        for k in m.group(1).split(","):
            k = k.strip()
            assert k in REFS, "unknown reference key " + k
            if k not in CITE:
                CITE.append(k)
            nums.append(CITE.index(k) + 1)
        return "[" + compress(nums) + "]"
    return re.sub(r"\[\[([^\]]+)\]\]", rep, text)


def sub(text):
    text = re.sub(r"@T:(\w+)@", lambda m: "Table %s" % TLAB.get(m.group(1), "?"), text)
    return re.sub(r"@(\w+)@", lambda m: str(NUM[m.group(1)]) if m.group(1) in NUM else m.group(0), text)


doc = H.new_document(size=11, line=1.5)
H.page_numbers_and_line_numbers(doc, line_numbers=False)


def P(text, **kw):
    kw.setdefault("align", "justify")
    return H.para(doc, cites(sub(text)), **kw)


def HD(text, level=1):
    return H.heading(doc, text, level)


def FIG(path, caption, alt, width=6.4):
    FIGN[0] += 1
    H.figure(doc, os.path.join(ROOT, "figures", path), width_in=width, cap="**Fig. %d** %s" % (FIGN[0], cites(sub(caption))), alt=alt)


def TAB(rows, caption, widths=None, size=8.5, label=None):
    TABN[0] += 1
    if label:
        TLAB_NEW[label] = TABN[0]
    H.caption(doc, "**Table %d** %s" % (TABN[0], cites(sub(caption))), keep_next=True)
    H.table(doc, [[cites(sub(c)) for c in r] for r in rows], widths=widths, size=size)


EQN = [0]


def EQ(nodes, name=None):
    EQN[0] += 1
    H.equation(doc, nodes, EQN[0])
    if name:
        NUM[name] = EQN[0]
    return EQN[0]


V, Tt, SUBN, SUPN, FRAC, DEL, Vs, SUBSUP = H.V, H.T, H.SUB, H.SUP, H.FRAC, H.DELIM, H.Vs, H.SUBSUP


def sv(base, s):
    return SUBN(V(base), Tt(s))


AVC = DEL(V("C"), "⟨", "⟩")
PLUS, MINUS, EQS = Tt(" + "), Tt(" − "), Tt(" = ")


def f1(x):
    return "%.1f" % x


def f2(x):
    return "%.2f" % x


def f3(x):
    return "%.3f" % x


def pct(x, k=1):
    return ("%." + str(k) + "f") % (100 * x)


def d_ar(a):
    return [d for d in DA if d["alpha"] == a][0]


# ================================================================== title, abstract
p = doc.add_paragraph()
H.add_rich(p, TITLE, size=16, bold=True)
for line in ("Leon Sandler", "Independent researcher, Northbrook, Illinois, USA", "Corresponding author: sandler.leon@gmail.com", "ORCID: 0009-0007-4584-808X"):
    q = doc.add_paragraph()
    H.add_rich(q, line, size=10.5)
    q.paragraph_format.space_after = H.Pt(0)
doc.add_paragraph()
HD("Abstract")
ABS = ("A cure triggered by the melting of an encapsulated catalyst combines a distribution of capsule melting temperatures, autocatalytic kinetics, and exothermic feedback. "
       "We derive what can be written in closed form for the lumped model and test each result against the full equations. "
       "(i) At constant temperature the gated cure is exactly the isothermal cure on the integrated availability of the catalyst; the delay of a fully activated population is "
       "τ_rel[1 − exp(−t/τ_rel)], approaching the release time constant τ_rel only at late conversion. "
       "(ii) The isothermal cure time is exact by one quadrature. "
       "(iii) For Gaussian capsule melting temperatures of spread σ the storage conversion is (a/b)[exp(b f t_eff) − 1] with open fraction f = Φ(−Δ/σ_eff), which bounds σ to within %s %% of the "
       "population equations. "
       "(iv) The frozen-conversion thermal balance has an algebraic branch only for Π = ψΘ below Π_c = (1+n)^(1+n)/[e n^n (1+ε)^(1+n)] (%s for n = 3/2); "
       "integrated thresholds approach it as Θ → 0 and, with Arrhenius kinetics, exceed it by about exp(1/Ar) (within %s %% on the tested grid). "
       "(v) In a continuous-flow reactor the steady-state curve has two folds above κ_c = %s, but the upper branch can lose stability at a Hopf-type point before its fold; "
       "the window of two stable states and its loop area are computed, and finite-rate loops approach it slowly. All parameters are illustrative; no experimental data are used."
       % (pct(max(dr_dev), 0), f2(PICE[1.5]), pct(max(ar_dev), 0), f2(KC)))
H.para(doc, ABS, align="justify")
NUM["absw"] = len(ABS.split())
print("abstract words:", NUM["absw"])
assert NUM["absw"] <= 250, NUM["absw"]
P("**Keywords:** autocatalytic cure kinetics; thermal runaway; encapsulated catalyst; Lambert W function; saddle-node and Hopf bifurcation; hysteresis", align="left")

# ================================================================== I Introduction
HD("I. Introduction")
P("Encapsulating a reactive component and releasing it on demand is a general way to separate the stability of a formulation from the speed of its cure. The best-known "
  "instance is the self-healing polymer, in which embedded capsules release a healing agent when damaged [[white2001]]; thermally triggered variants use the melting of a wax or "
  "polymer shell, whose phase-change behavior is the subject of a literature on microencapsulated phase-change materials [[jamekhorshid2014]] and whose release is described by a family of "
  "release models [[siepmann2012]]. When the released species catalyzes a thermoset cure, three features interact: the capsule population has a distribution of melting temperatures rather than a "
  "single one, the cure is autocatalytic and follows the form introduced by Kamal and Sourour [[kamal1973,sourour1976]], and the cure heat raises the temperature of the specimen, which "
  "accelerates the cure. The cure exotherm makes the temperature field of thick thermoset sections depend on the cure history [[bogetti1992]], and the feedback between heat release and "
  "rate is the subject of the classical theory of thermal explosion of Semenov and Frank-Kamenetskii [[semenov1928,frankkamenetskii1969]]. That theory has been extended to reactant "
  "consumption [[adler1964]] and to the induction period [[kassoy1980]], and the multiplicity and stability of the steady states of a heated, continuously fed reactor were analyzed by "
  "van Heerden, by Aris and Amundson, and by Uppal, Ray and Poore [[vanheerden1953,aris1958,uppal1974,grayscott1990]].")
P("Calorimetric kinetic analysis is well codified [[vyazovkin2011,zhao2019]], and the separable form of the cure law is a standard route to closed-form cure times, with the "
  "temperature history entering through a generalized time [[ozawa1965]]. In that literature the rate law and the thermal runaway of a specimen are usually treated separately. The question "
  "addressed here is narrower: for the lumped model of a *melt-gated* autocatalytic cure, which statements linking the quantities that a calorimeter measures (the rate constants of the cure, "
  "the width of the melting endotherm of the capsules, the thermal time constant of a specimen) to storage stability, delay and runaway can be written in closed form, and how well do "
  "they hold against the full equations?")
P("The paper separates standard identities from results specific to this system. Proposition 1 is the generalized-time identity [[ozawa1965]] applied to the catalyst availability; its content is the "
  "identification of the clock and the resulting delay law (Section III A). Proposition 2 collects standard integrals and one sharpness law (III B). Proposition 3, the storage conversion of a Gaussian capsule "
  "population and the bound on the melting-temperature spread that follows from it, is specific to the gated system (III C). Proposition 4 applies the Semenov fold of the frozen-conversion balance to the "
  "Kamal–Sourour consumption law, which gives a closed-form critical number, its overshoot below the fold and an Arrhenius correction (III D); the classical treatment of consumption "
  "[[adler1964]] is not specific to autocatalysis. Proposition 5 gives the steady states, the Jacobian and the stable window of a continuous-flow reactor with this kinetics (III E). A synthetic-data "
  "test shows how the closed forms behave as fitting functions (III F). To the author's knowledge, in the sources examined, these results have not been assembled for a gated autocatalytic cure.")
P("The illustrative parameter set and the capsule-population picture were introduced in a numerical study by the author [[sandler2026]]: the rate constants and orders of Table 1, the "
  "release rate constant, the logistic activation and the mean melting temperature, the adiabatic rise, and the reference integrator come from that study. The analytic results below are new, "
  "and the comparisons of that study with first-order controls are not used here. The model is lumped and every parameter is illustrative: nothing is fitted to measurements, and the paper "
  "makes no claim about a particular material.")

# ================================================================== II Model
HD("II. Model and scaling")
HD("A. Equations", 2)
P("The conversion α of the resin obeys a Kamal–Sourour law with reaction order n for the unreacted fraction and first order in the autocatalytic term,")
EQ(FRAC(V("dα"), V("dt")) + EQS + AVC + Tt("(t)") + DEL(sv("k", "1") + PLUS + sv("k", "2") + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + Tt(","), "e1")
P("where ⟨C⟩ is the availability of the catalyst averaged over the capsule population (the fraction of the catalyst that has been released, 0 ≤ ⟨C⟩ ≤ 1). The temperature "
  "of the well-mixed specimen obeys a lumped energy balance with Newtonian loss and the adiabatic temperature rise ΔT_{ad} of the reaction,")
EQ(FRAC(V("dT"), V("dt")) + EQS + FRAC(DEL(sv("T", "∞") + MINUS + V("T")), sv("τ", "th")) + PLUS + sv("ΔT", "ad") + FRAC(V("dα"), V("dt")) + Tt("."), "e2")
P("Capsule *i* has a melting temperature T_{m,i}, drawn from a Gaussian of mean T_{m} and standard deviation σ, and releases its catalyst by first-order relaxation toward a "
  "logistic activation of width *w*_{0},")
EQ(FRAC(SUBN(V("dC"), V("i")), V("dt")) + EQS + sv("k", "rel") + DEL(V("T")) + DEL(SUBN(V("G"), V("i")) + DEL(V("T")) + MINUS + SUBN(V("C"), V("i")), "[", "]") + Tt(",   ") +
   SUBN(V("G"), V("i")) + EQS + SUPN(DEL(Tt("1") + PLUS + Tt("exp") + DEL(MINUS + FRAC(V("T") + MINUS + SUBN(V("T"), V("m,i")), sv("w", "0")))), Tt("−1")) + Tt(",   ") + AVC + EQS +
   FRAC(Tt("1"), V("K")) + Tt("∑") + SUBN(V("C"), V("i")) + Tt("."), "e3")
P("The initial state is α(0) = 0 and C_{i}(0) = 0 unless stated, and T(0) = T_{∞} for the isothermal-start problems of Sections III A–D. The rate constants are Arrhenius, *k*_{j} = *A*_{j} exp(−*E*_{j}/*RT*), "
  "for *j* = 1 (background), 2 (autocatalytic) and rel (release). The model has no spatial structure, no diffusion control and no vitrification (Section VI). Throughout, the *illustrative* parameter set "
  "of @T:par@ is used.")
rows = [["Quantity", "Symbol", "Value"],
        ["Background rate constant", "A_{1}, E_{1}", "2.0 × 10^{3} min^{−1}, 50 kJ mol^{−1}"],
        ["Autocatalytic rate constant", "A_{2}, E_{2}", "2.5 × 10^{7} min^{−1}, 65 kJ mol^{−1}"],
        ["Reaction order", "n", "1.5 (1 and 2 where stated)"],
        ["Release rate constant", "A_{rel}, E_{rel}", "6.4 × 10^{6} min^{−1}, 60 kJ mol^{−1}"],
        ["Mean melting temperature, activation width", "T_{m}, w_{0}", "118 °C, 0.5 °C"],
        ["Adiabatic rise, thermal time constant", "ΔT_{ad}, τ_{th}", "220 K, varied (Section III D)"],
        ["Rate constants at 140 °C", "k_{1}, k_{2}, k_{rel}", "%.2e, %.3f, %.3f min^{−1}" % (a140, b140, kr140)]]
TAB(rows, "Illustrative parameter set (not fitted to any material; taken from Ref. [[sandler2026]]). Arrhenius forms are *k* = *A* exp(−*E*/*RT*). Note that *E*_{1} ≠ *E*_{2}.", widths=[2.6, 1.3, 2.7], label="par")
HD("B. Dimensionless groups and the exponential comparison model", 2)
P("Define ε = k_{1}/k_{2}, the thermal number Θ = τ_{th}k_{2}(T_{∞}), the reduced exothermicity ψ = ΔT_{ad}E_{2}/(RT_{∞}^{2}), the activation number Ar = E_{2}/(RT_{∞}) and the release "
  "number Λ = k_{2}/k_{rel}. The combination that controls thermal feedback is")
EQ(Tt("Π") + EQS + Tt("ψ") + Tt("Θ") + EQS + FRAC(sv("ΔT", "ad") + sv("E", "2") + sv("τ", "th") + sv("k", "2"), V("R") + SUPN(sv("T", "∞"), Tt("2"))) + Tt("."), "ePi")
P("The *exponential comparison model* used in Sections III D and III E replaces the Arrhenius dependence of both rate constants by the common Frank-Kamenetskii form k_{j}(T) = k_{j}(T_{∞}) exp(ψθ), "
  "θ = (T − T_{∞})/ΔT_{ad}, and treats ε as a constant. This is exact when the activation energies are equal and is a good description of the rate near the fold when the background term is "
  "negligible there: the fold occurs at conversions of order 0.4, where the autocatalytic term (α ≈ 0.4) exceeds the background term (ε = 3 × 10^{−3}) by two orders of magnitude, so the "
  "different activation energy of k_{1} (50 against 65 kJ mol^{−1}) matters little. The *Arrhenius simulations* of Sections III D (@T:arr@) do not use this simplification: both k_{1}(T) and k_{2}(T) "
  "follow their own Arrhenius law and ε = k_{1}/k_{2} is evaluated at T_{∞}.")
HD("C. Computation and use of AI assistance", 2)
P("All numerical results are produced by the released scripts (run_all.py writes results.json; every number in the text is read from it, none is typed by hand), with the reference integrator, "
  "solver settings and protocols given in Appendix A. The model code, the closed-form module, the tests, the figure scripts and a first draft of the text were produced with the assistance of "
  "Claude Sonnet 5.5 (model identifier claude-sonnet-5-5; Anthropic), used through the Claude Code command-line environment on the author's computer, because the author is an independent "
  "researcher without a computational group. The assistant wrote and ran code, drafted derivations and checked algebra; closed forms were verified against independent numerical integration by the "
  "test suite (code/test_theory.py) and by the comparisons reported in Section III, and every journal reference was resolved through Crossref. The assistant did not enter or alter any numerical result "
  "by hand. The author is responsible for the content.")

# ================================================================== III Results
HD("III. Results")
HD("A. Proposition 1: the gated cure runs on the clock of integrated availability", 2)
P("**Proposition 1.** At constant temperature, with α(0) = 0 and C_{i}(0) = 0, let F(α) = (k_{1} + k_{2}α)(1 − α)^{n}. Then the gated conversion obeys")
EQ(SUBSUP(Tt("∫"), Tt("0"), V("α")) + FRAC(V("dx"), V("F") + DEL(V("x"))) + EQS + V("s") + DEL(V("t")) + Tt(",   ") + V("s") + DEL(V("t")) + EQS + SUBSUP(Tt("∫"), Tt("0"), V("t")) + AVC + DEL(V("t′")) + V("dt′") + Tt("."), "eclock")
P("*Proof.* With T constant, dα/dt = ⟨C⟩(t)F(α) is separable: dα/F(α) = ⟨C⟩dt. Integration from the initial state gives the identity. ∎ This is the generalized-time identity [[ozawa1965]] with the "
  "integrated availability as the clock. The left side is the isothermal time t_{iso}(α) of the ungated resin, so the gated time to reach α is the time at which s(t) = t_{iso}(α). For a "
  "population that is fully open at the operating temperature, ⟨C⟩ = 1 − exp(−t/τ_{rel}) with τ_{rel} = 1/k_{rel}, so s(t) = t − τ_{rel}[1 − exp(−t/τ_{rel})] and")
EQ(sv("t", "gated") + DEL(V("α")) + MINUS + sv("t", "iso") + DEL(V("α")) + EQS + sv("τ", "rel") + DEL(Tt("1") + MINUS + Tt("exp") + DEL(MINUS + FRAC(sv("t", "gated") + DEL(V("α")), sv("τ", "rel")))) + Tt("."), "edelay")
P("The delay is therefore conversion dependent: it lies between 0 and τ_{rel} and approaches τ_{rel} only when t_{gated} ≫ τ_{rel}. The fractional deficit from τ_{rel} is below 1 %% when t_{gated}/τ_{rel} exceeds "
  "ln 100 = %.3f. At 140 °C (τ_{rel} = %.2f min) the delay is %.2f min at α = 0.001 (t_{gated}/τ_{rel} = %.2f), %.2f min at α = 0.01, and %.2f, %.2f and %.2f min at α = 0.1, 0.5 and 0.9 (@T:delay@); the "
  "constant shift is a good description for α ≳ 0.1 at this temperature and fails at early conversion. Independent adaptive integration of the gate and cure equations reproduces Eq. (@edelay@) to "
  "the integration tolerance in every row, and integrating the full model with the reference RK4 integrator at 125, 140 and 155 °C and α = 0.1, 0.5, 0.9 reproduces the gated times of Eq. (@eclock@) "
  "to a relative error of at most %.1e." % (R["delay_1pct_ratio"], 1 / kr140, d_ar(0.001)["delay"], d_ar(0.001)["ratio"], d_ar(0.01)["delay"], d_ar(0.1)["delay"], d_ar(0.5)["delay"], d_ar(0.9)["delay"], clock_err))
P("For incomplete activation, with open fraction f < 1 (a fraction of the capsules that has not melted at the operating temperature), the clock is s(t) = f[t − τ_{rel}(1 − exp(−t/τ_{rel}))], so the delay "
  "relative to the ungated resin is not a constant shift: the gated cure is slowed in proportion to 1/f as well. For f = 0.5 at 140 °C the integrated times to α = 0.1, 0.5 and 0.9 are %.1f, %.1f and %.1f min, "
  "and the clock gives %.1f, %.1f and %.1f min, while the fully open population reaches them at %.1f, %.1f and %.1f min. A population whose mean melting temperature lies below the operating temperature "
  "is not necessarily fully open: a broad population has a tail of capsules that melt above it, and f must be computed from the melting-temperature distribution (Section III C). The statement is "
  "exact only at constant temperature; a heat-up transient or an exotherm adds a temperature-dependent delay that Proposition 1 does not describe." % (
      IA[0]["t_ode"], IA[1]["t_ode"], IA[2]["t_ode"], IA[0]["t_clock"], IA[1]["t_clock"], IA[2]["t_clock"], IA[0]["t_full_open"], IA[1]["t_full_open"], IA[2]["t_full_open"]))
rows = [["α", "t_{iso}(α) (min)", "t_{gated} (min), integrated", "Delay (min)", "τ_{rel}[1 − exp(−t_{gated}/τ_{rel})] (min)", "t_{gated}/τ_{rel}"]]
for d in DA:
    rows.append(["%g" % d["alpha"], f2(d["t_iso"]), f2(d["t_gated"]), f2(d["delay"]), f2(d["delay_formula"]), f2(d["ratio"])])
TAB(rows, "Delay of a fully open population relative to the ungated resin at 140 °C (n = 3/2, τ_{rel} = %.2f min): integrated gate and cure equations against Eq. (@edelay@)." % (1 / kr140), widths=[0.6, 1.1, 1.4, 0.9, 1.7, 1.0], label="delay")

HD("B. Proposition 2: isothermal cure time, induction, and sharpness", 2)
P("**Proposition 2.** With a = k_{1} and b = k_{2}, the isothermal time to reach conversion α is, for any n, t_{iso}(α) = ∫_{0}^{α} dx/[(a + bx)(1 − x)^{n}], and for n = 1")
EQ(sv("t", "iso") + DEL(V("α")) + EQS + FRAC(Tt("1"), V("a") + PLUS + V("b")) + Tt("ln") + FRAC(V("a") + PLUS + V("b") + V("α"), V("a") + DEL(Tt("1") + MINUS + V("α"))) + Tt("."), "eiso")
P("*Proof.* Partial fractions of 1/[(a + bx)(1 − x)] give (a + b)^{−1}[b/(a + bx) + 1/(1 − x)], and integration gives the logarithm. ∎ For small α the factor (1 − x)^{n} is close to 1, "
  "so the induction time (α = 0.1) is almost independent of n; the late-time tail is not. For n = 1 the sharpness S = (t_{90} − t_{10})/t_{10} is exactly")
EQ(V("S") + EQS + FRAC(Tt("ln") + DEL(FRAC(Tt("9") + DEL(V("a") + PLUS + Tt("0.9") + V("b")), V("a") + PLUS + Tt("0.1") + V("b"))), Tt("ln") + DEL(FRAC(V("a") + PLUS + Tt("0.1") + V("b"), Tt("0.9") + V("a")))), "esharp")
P("and, for b ≫ 9a and n = 1 only, it reduces to the asymptotic law")
EQ(V("S") + Tt("≈") + FRAC(Tt("2 ln 9"), Tt("ln") + DEL(FRAC(V("b"), Tt("9") + V("a")))) + Tt("."), "elaw")
P("Sharpness is then controlled by the rate-constant ratio alone, and only logarithmically. At 140 °C, b/a = %.0f gives S = %.2f exactly for n = 1 and %.2f from Eq. (@elaw@), with a difference of "
  "%s %%; the law is accurate to %s %% across 110–155 °C for n = 1. A hundredfold increase of b/a, from 159 to 15,900, lowers the exact S from %.2f to %.2f, a factor of %.1f. For n ≠ 1 the law does not "
  "apply: at 140 °C the integrated sharpness rises from %.2f (n = 1) to %.2f (n = 3/2) because of the longer tail, and the quadrature should be used. The closed forms and the quadrature reproduce the "
  "integrated t_{10} and t_{90} for T = 110–155 °C and n = 1 and 3/2 to within %.1e (relative)." % (
      r140_1["ratio"], r140_1["S_exact_n1"], r140_1["S_law"], pct(abs(r140_1["S_law"] / r140_1["S_exact_n1"] - 1)), pct(law_err, 0), SE[0]["S_exact"], SE[1]["S_exact"], SE[0]["S_exact"] / SE[1]["S_exact"],
      r140_1["S_num"], r140_15["S_num"], iso_err))
FIG("fig1_clock_sharpness.png", "(a) Gated and ungated cure at constant temperature (140 °C): the gated curve is the isothermal curve evaluated on the integrated-availability clock, and the integrated ODE (circles) agrees. "
    "(b) Delay of the gated cure relative to the ungated resin as a function of the conversion level: integrated (points), Eq. (@edelay@) (line), and the limit τ_{rel} (dashed). "
    "(c) Sharpness against the rate-constant ratio: exact n = 1, the asymptotic law Eq. (@elaw@), and integrated results for n = 3/2.",
    "Three panels. (a) Conversion against time for the ungated and gated resin with integrated points. (b) Delay against conversion approaching the release time constant. (c) Sharpness against the logarithm of the rate-constant ratio.", width=6.7)

HD("C. Proposition 3: storage conversion of a capsule population and a bound on the spread", 2)
P("A capsule that is open at the storage temperature T_{s} releases catalyst that drives the cure at T_{s}. For a Gaussian spread σ of melting temperatures and a logistic activation of width *w*_{0}, "
  "the equilibrium open fraction at a margin Δ = T_{m} − T_{s} is the Gaussian–logistic convolution, which the probit approximation (matching the variance π²w_{0}²/3 of the logistic) writes as")
EQ(V("f") + EQS + Tt("Φ") + DEL(MINUS + FRAC(V("Δ"), sv("σ", "eff"))) + Tt(",   ") + SUBN(V("σ"), Tt("eff")) + Tt("²") + EQS + SUPN(V("σ"), Tt("2")) + PLUS + FRAC(SUPN(Tt("π"), Tt("2")) + SUPN(sv("w", "0"), Tt("2")), Tt("3")) + Tt("."), "ef")
P("The approximation, not the identity, carries the error of this step; it is tested below. **Proposition 3.** If every capsule relaxes toward its own activation with the common rate constant k_{rel}(T_{s}), then "
  "⟨C⟩(t) = f[1 − exp(−k_{rel}t)] and, in the small-conversion limit (α ≪ 1, (1 − α)^{n} ≈ 1), the storage conversion after a time t is")
EQ(sv("α", "s") + DEL(V("t")) + EQS + FRAC(V("a"), V("b")) + DEL(Tt("exp") + DEL(V("b") + V("f") + sv("t", "eff")) + MINUS + Tt("1"), "[", "]") + Tt(",   ") + sv("t", "eff") + EQS + V("t") + MINUS + sv("τ", "rel") + DEL(Tt("1") + MINUS + Tt("exp") + DEL(MINUS + FRAC(V("t"), sv("τ", "rel")))) + Tt("."), "eleak")
P("*Proof.* In the small-conversion limit the rate law is linear, dα/dt = ⟨C⟩(a + bα), so that α = (a/b)[exp(b s(t)) − 1] with s(t) = ∫⟨C⟩dt = f t_{eff}. ∎ The tolerance η on the storage conversion "
  "(a symbol distinct from ε = k_{1}/k_{2}) then fixes the largest admissible open fraction exactly, f^{*} = ln(1 + ηb/a)/(b t_{eff}), and the bound on the spread follows by inverting Eq. (@ef@), including *w*_{0}:")
EQ(SUPN(V("σ"), Tt("*")) + EQS + Tt("√") + DEL(DEL(FRAC(V("Δ"), SUPN(V("z"), Tt("*"))), "(", ")") + Tt("²") + MINUS + FRAC(SUPN(Tt("π"), Tt("2")) + SUPN(sv("w", "0"), Tt("2")), Tt("3")), "[", "]") + Tt(",   ") + SUPN(V("z"), Tt("*")) + EQS + MINUS + SUPN(Tt("Φ"), Tt("−1")) + DEL(SUPN(V("f"), Tt("*"))) + Tt("."), "esigma")
P("This is defined for 0 < f^{*} < 1/2 (a finite positive bound). If f^{*} ≥ 1/2 no finite upper bound on the spread is imposed, because even a population centered at the margin Δ above the storage temperature "
  "cannot exceed the tolerance; if the radicand is negative, even σ = 0 violates the tolerance because the logistic width alone opens too large a fraction. Eq. (@esigma@) with *w*_{0} = 0.5 °C generated @T:dr@; "
  "the column for *w*_{0} → 0 shows the limit, which differs from it most for the narrowest widths. "
  "We tested the closed forms against the capsule-population equations (K = 801 deterministic Gaussian quantiles of the melting temperature, constant temperature, t = 150 min) for margins of 3, 6 and 10 °C and "
  "spreads of 2–10 °C: the storage conversions agree within %s %% (difference = closed form/numerical − 1; median ratio %.3f), the closed form agrees with the defining integral to %.0e, "
  "and the spread σ^{*} that solves α_{s} = η agrees with the root of the population equations within %s %% for all %d cases in which the ODE reaches η (@T:dr@). "
  "For η = 0.01 and a 6 °C margin the bound is σ^{*} = %.1f °C." % (pct(max(lk_dev), 0), np.median([r["closed_form"] / r["numeric"] for r in lk_ok]), R["leak_closed_vs_quad_max_rel"], pct(max(dr_dev), 0), len(dr_ok),
                                                                [r for r in DR if r["margin"] == 6.0 and r["eta"] == 0.01][0]["sigma_star_closed"]))
rows = [["Margin Δ (°C)", "Tolerance η", "f^{*}", "σ^{*} Eq. (@esigma@) (°C)", "σ^{*}, w_{0} → 0 (°C)", "σ^{*} population ODE (°C)", "Difference"]]
for r in DR:
    cf = r["sigma_star_closed"]
    rows.append(["%.0f" % r["margin"], "%g" % r["eta"], f3(r["f_star"]), f2(cf) if cf and cf < 40 else "> 40", f2(r["sigma_star_closed_w0_zero"]) if r["sigma_star_closed_w0_zero"] and r["sigma_star_closed_w0_zero"] < 40 else "> 40",
                 f2(r["sigma_star_ode"]) if r["sigma_star_ode"] else "> 40", "%+.1f %%" % (100 * (cf / r["sigma_star_ode"] - 1)) if (r["sigma_star_ode"] and cf and cf < 40) else "–"])
TAB(rows, "Largest admissible melting-temperature spread σ^{*} for a storage time of 150 min and *w*_{0} = 0.5 °C: Eq. (@esigma@), its *w*_{0} → 0 limit, and root-finding on the population equations (difference = closed form/ODE − 1).",
    widths=[0.9, 0.8, 0.7, 1.4, 1.1, 1.3, 0.8], size=8, label="dr")
FIG("fig2_storage.png", "(a) Closed-form storage conversion Eq. (@eleak@) against the population ODE for margins of 3, 6 and 10 °C. (b) Largest admissible spread σ^{*} (Eq. (@esigma@)) as a function of the tolerance η; "
    "open symbols are roots of the population ODE.", "Two panels. (a) Log-log scatter of closed-form against ODE storage conversion lying on the identity line. (b) Largest admissible spread against tolerance for three margins with ODE roots.")

HD("D. Proposition 4: thermal-feedback criticality, overshoot, and Arrhenius correction", 2)
P("When the thermal time constant is short compared with the reaction time (Θ ≪ 1), the temperature rise θ = (T − T_{∞})/ΔT_{ad} of the exponential comparison model follows the reaction quasi-statically with the "
  "conversion frozen, θ = Θ r(α) exp(ψθ), where r(α) = (ε + α)(1 − α)^{n} is the isothermal rate in units of k_{2}. Multiplying by ψ gives ψθ exp(−ψθ) = Πr, whose solution, if Πr ≤ 1/e, is")
EQ(V("ψθ") + EQS + MINUS + sv("W", "0") + DEL(MINUS + Tt("Π") + V("r") + DEL(V("α"))) + Tt("."), "eW")
P("**Proposition 4.** For the ungated exponential model in the quasi-steady limit with frozen conversion, the low-temperature algebraic branch of Eq. (@eW@) ceases to exist when Πr(α) = 1/e. Maximizing r over α gives "
  "the limiting fold criterion. For r = (ε + α)(1 − α)^{n} the interior maximum is at α^{*} = (1 − nε)/(1 + n), provided nε < 1, with r_{max} = n^{n}(1 + ε)^{n+1}/(1 + n)^{n+1}, so")
EQ(sv("Π", "c") + EQS + FRAC(Tt("1"), Tt("e") + sv("r", "max")) + EQS + FRAC(SUPN(DEL(Tt("1") + PLUS + V("n")), Tt("1+n")), Tt("e") + SUPN(V("n"), V("n")) + SUPN(DEL(Tt("1") + PLUS + V("ε")), Tt("1+n"))) + Tt(",   ") + sv("Π", "c") + Tt("→") + SUPN(Tt("e"), Tt("−1")) + FRAC(SUPN(DEL(Tt("1") + PLUS + V("n")), Tt("1+n")), SUPN(V("n"), V("n"))) + Tt("   (ε → 0)."), "ePic")
P("The finite-ε value is %.4f, %.4f and %.4f for n = 1, 3/2 and 2 at ε = 3 × 10^{−3}, against the ε → 0 limits %.4f, %.4f and %.4f; the finite-ε formula explains why the integrated values of @T:fk@ at small Θ lie slightly below the limits. "
  "Below Π_{c} the quasi-steady peak is ψθ_{peak} = −W_{0}(−Π/(eΠ_{c})), and close to the fold it follows ψθ_{peak} ≈ 1 − [2(1 − Π/Π_{c})]^{1/2}, the normal form of a saddle-node bifurcation of the algebraic "
  "equation [[strogatz2015,corless1996]]. This is a statement about the frozen-conversion algebraic manifold. For a finite batch the reactant is consumed and the temperature rise is bounded by the available "
  "reaction heat, so whether the fold marks ignition must be tested by integration. We therefore define an *operational* threshold as the Π (or ΔT_{ad}) at which the integrated peak rise exceeds "
  "0.3ΔT_{ad}, and the conclusions about overshoot below are numerical. For comparison, the classical Semenov criterion for a source without consumption, r = 1 in the same units, gives 1/e = 0.37; consumption "
  "and autocatalysis raise the frozen-conversion critical number by the factor 1/r_{max} ≈ %.1f for n = 3/2 (reactant consumption in the Semenov problem was treated in Ref. [[adler1964]])." % (PICE[1.0], PICE[1.5], PICE[2.0], PIC0[1.0], PIC0[1.5], PIC0[2.0], 1 / T.r_max(1.5, 0.0)))
P("*Verification in the exponential model.* We integrated the exponential-form equations with isothermal start and bisected the operational threshold (ε = 3 × 10^{−3}; @T:fk@). "
  "As Θ → 0 the operational Π_{c} converges to Eq. (@ePic@) with finite ε: at Θ = 0.003 the values are %.3f, %.3f and %.3f against %.3f, %.3f and %.3f (differences %s–%s %%). The threshold definition matters "
  "little (Π_{c} = %.3f, %.3f, %.3f for 0.15, 0.3 and 0.6 of ΔT_{ad}). The finite-Θ shift is upward (Π_{c} = %.2f at Θ = 0.1 for n = 3/2); it is computed, not given in closed form. At Θ = 0.002 the integrated peak "
  "at 0.5–0.98 Π_{c} follows the Lambert-W formula and approaches the square-root form (Fig. 3b)." % (
      *[[r for r in FK if r["n"] == n and r["Theta"] == 0.003][0]["Pi_c_numeric"] for n in (1.0, 1.5, 2.0)], *[PICE[n] for n in (1.0, 1.5, 2.0)],
      pct(min(abs(r["Pi_c_numeric"] / r["Pi_c_finite_eps"] - 1) for r in FK if r["Theta"] == 0.003)), pct(max(abs(r["Pi_c_numeric"] / r["Pi_c_finite_eps"] - 1) for r in FK if r["Theta"] == 0.003)),
      *[R["critical_threshold_sensitivity"][k] for k in ("0.15", "0.3", "0.6")], fk15[0.1]["Pi_c_numeric"]))
rows = [["n", "Θ", "Π_{c}, integrated (operational)", "Π_{c}, Eq. (@ePic@) finite ε", "Π_{c}, ε → 0"]] + [["%.1f" % r["n"], "%g" % r["Theta"], f3(r["Pi_c_numeric"]), f3(r["Pi_c_finite_eps"]), f3(r["Pi_c_eps0"])] for r in FK]
TAB(rows, "Critical thermal-feedback number in the exponential (Frank-Kamenetskii) model: operational thresholds from integrations (peak rise 0.3ΔT_{ad}, ε = 3 × 10^{−3}) against Eq. (@ePic@) with finite ε and its ε → 0 limit.",
    widths=[0.6, 0.7, 2.0, 2.0, 1.3], label="fk")
P("*Arrhenius kinetics.* For a single Arrhenius source at a temperature rise x = ΔT/T_{∞} the exponent is Ar·x/(1 + x), against Ar·x in the exponential model. With y = ψθ the frozen-conversion balance is "
  "y exp[−y/(1 + y/Ar)] = Πr, and its fold is at y_{f} satisfying y = (1 + y/Ar)^{2}; the critical number is then")
EQ(sv("Π", "c") + SUPN(Tt(""), Tt("Arr")) + EQS + sv("Π", "c") + SUPN(Tt(""), Tt("FK")) + Tt(" · e ") + SUBN(V("y"), V("f")) + Tt("exp") + DEL(MINUS + FRAC(SUBN(V("y"), V("f")), Tt("1") + PLUS + SUBN(V("y"), V("f")) + Tt("/Ar"))) + Tt("≈") + sv("Π", "c") + SUPN(Tt(""), Tt("FK")) + Tt("exp") + DEL(FRAC(Tt("1"), Tt("Ar"))), "earr")
P("The factor exp(1/Ar) is only the first-order (large-Ar) estimate of the first factor; for Ar = %.1f–%.1f the two differ by about %s %%. With distinct activation energies of the competing rate terms the fold condition "
  "must be solved for the actual sum of rates. We tested the correction with the true Arrhenius model (ungated, isothermal start, both k_{1} and k_{2} Arrhenius) at 120, 140 and 160 °C (Ar = %.1f–%.1f) and "
  "Θ = 0.01, 0.03, 0.1, bisecting the adiabatic rise to the same operational threshold (@T:arr@). The prediction Π_{c}^{FK}(Θ) times the fold factor is within %s %% of the Arrhenius threshold in every one of the nine "
  "cases (times exp(1/Ar): within %s %%; the uncorrected exponential value is off by %s–%s %%). This is empirical agreement over the tested grid; the correction has not been tested at small Ar or for other Θ. "
  "Release lag raised the operational threshold in the cases tested: at Θ = 0.03 it increased Π_{c} from %.3f, %.3f and %.3f to %.3f, %.3f and %.3f at 120, 140 and 160 °C. No general inequality is claimed, because a smaller "
  "availability at the same conversion does not by itself show that the temperature histories compare." % (
      Ar_lo, Ar_hi, pct(abs(AR[0]["factor_fold"] / AR[0]["factor_first_order"] - 1), 1), Ar_lo, Ar_hi, pct(max(ar_dev), 1), pct(max(ar_dev1), 1), pct(min(ar_fk_dev), 0), pct(max(ar_fk_dev), 0),
      *[[r for r in AR if r["T"] == t and r["Theta"] == 0.03][0]["Pi_c_arrhenius"] for t in (120.0, 140.0, 160.0)], *[[r for r in AR if r["T"] == t and r["Theta"] == 0.03][0]["Pi_c_gated"] for t in (120.0, 140.0, 160.0)]))
rows = [["T (°C)", "Θ", "Ar", "Π_{c} Arrhenius", "Π_{c} FK(Θ)", "× fold factor", "Difference", "× exp(1/Ar)", "Difference", "Π_{c}, release lag"]]
for r in AR:
    rows.append(["%.0f" % r["T"], "%g" % r["Theta"], "%.1f" % r["Ar"], f3(r["Pi_c_arrhenius"]), f3(r["Pi_c_fk"]), f3(r["prediction_fold"]), "%+.1f %%" % (100 * (r["prediction_fold"] / r["Pi_c_arrhenius"] - 1)),
                 f3(r["prediction_first_order"]), "%+.1f %%" % (100 * (r["prediction_first_order"] / r["Pi_c_arrhenius"] - 1)), f3(r["Pi_c_gated"]) if r["Pi_c_gated"] else "–"])
TAB(rows, "Operational critical number of the Arrhenius model (ungated, isothermal start; peak rise 0.3ΔT_{ad}) against the exponential-model value FK(Θ) multiplied by the frozen-fold factor of Eq. (@earr@) and by exp(1/Ar) "
          "(difference = prediction/Arrhenius − 1), and the effect of a release lag.", widths=[0.5, 0.45, 0.45, 0.8, 0.75, 0.7, 0.7, 0.75, 0.7, 0.8], size=7.5, label="arr")
FIG("fig3_criticality.png", "(a) Operational critical number against Θ for n = 1, 3/2 and 2 (points: integrations; dashed: finite-ε Eq. (@ePic@)). (b) Quasi-steady overshoot below Π_{c}: Lambert-W formula, fold normal form, and integrations. "
    "(c) Arrhenius operational critical number against FK(Θ) times the frozen-fold factor.", "Three panels. (a) Critical number against Theta for three reaction orders with asymptotes. (b) Peak overshoot against Pi over Pi critical with Lambert-W curve and integrated points. (c) Scatter of Arrhenius critical number against prediction near the identity line.", width=6.7)

HD("E. Proposition 5: continuous-flow reactor, steady states, stability, and hysteresis", 2)
P("Let fresh resin of conversion 0 enter at the wall temperature with residence time τ_{res}, and let ϑ = τ_{th}/τ_{res} and D = k_{2}τ_{res}. In units of τ_{res} and in the exponential model,")
EQ(FRAC(V("dα"), Tt("dt′")) + EQS + V("D") + V("r") + MINUS + V("α") + Tt(",   ") + FRAC(V("dθ"), Tt("dt′")) + EQS + V("D") + V("r") + MINUS + V("θ") + DEL(Tt("1") + PLUS + FRAC(Tt("1"), Tt("ϑ"))) + Tt(",   ") + V("r") + EQS + DEL(V("ε") + PLUS + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + SUPN(Tt("e"), Tt("ψθ")) + Tt("."), "eflow")
P("*Control parameter.* D is swept with ϑ and ψ held fixed. Physically this is a sweep of the specimen temperature T_{∞} at fixed τ_{th} and τ_{res}: D and Θ are both proportional to k_{2}(T_{∞}), so ϑ is constant, "
  "and in the exponential model a change of ln D by one unit corresponds to a temperature change of RT²/E_{2} = %.1f K at 140 °C. A sweep of the flow rate at fixed temperature changes τ_{res} and therefore ϑ; it "
  "is a different parameter path and is not analyzed here." % KELVIN)
P("**Proposition 5 (steady states).** The steady states satisfy θ = ϑα/(1 + ϑ) = κα/ψ and are given parametrically by")
EQ(V("D") + EQS + FRAC(V("α"), DEL(V("ε") + PLUS + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + Tt("exp") + DEL(V("κα"))) + Tt(",   ") + V("κ") + EQS + FRAC(Tt("ψϑ"), Tt("1") + PLUS + Tt("ϑ")) + Tt("."), "ess")
P("*Proof.* At steady state the conversion balance gives rD = α, and the heat balance gives θ(1 + 1/ϑ) = rD = α, so θ = ϑα/(1 + ϑ) = κα/ψ; substituting ψθ = κα into rD = α gives the expression. ∎ "
  "D(α) is non-monotonic, so three steady states coexist in a window of D, if and only if d ln D/dα = 0 has two roots, n/(1 − α) + ε/[α(ε + α)] = κ. The left side has a single minimum, so three equilibria exist "
  "if and only if κ > κ_{c} = min_{α}[n/(1 − α) + ε/(α(ε + α))] (κ_{c} = %.3f for n = 3/2 and ε = 3 × 10^{−3}; κ_{c} → n as ε → 0). Equilibrium multiplicity does not by itself establish two stable states or "
  "switching at both folds." % KC)
P("**Stability.** Let q = α/(ε + α) − nα/(1 − α). Differentiating Eq. (@eflow@) at a steady state, with D and ϑ fixed, gives the Jacobian in the variables (α, θ)")
EQ(V("J") + EQS + Tt("[[ q − 1 ,  ψα ] , [ q ,  ψα − 1 − 1/ϑ ]]"), "eJ")
P("with trace q + ψα − 2 − 1/ϑ and determinant (1 + 1/ϑ)(1 − q) − ψα. At a fold the determinant vanishes and the other eigenvalue equals the trace. The lower fold has a negative trace for all cases below, so it is a "
  "saddle-node at which the lower (unreacted) state disappears. The upper fold has a negative trace, and is a saddle-node at which a stable upper state disappears, only for ψ below about %.2f (ϑ = 1); above it the "
  "trace at the upper fold is positive (+%.2f for ψ = 20: α = %.4f, ln D = %.3f), so the upper branch near its fold is unstable and becomes stable only above a larger conversion α_{H} at which the trace vanishes "
  "(α_{H} = %.4f, ln D_{H} = %.3f for ψ = 20, with determinant %.1f > 0, a Hopf-type point). The window of two stable states is therefore (ln D_{ext}, ln D_{ign}), where ln D_{ign} is the lower (ignition) fold and "
  "ln D_{ext} is the upper fold when its trace is negative and ln D_{H} otherwise (@T:flowstab@)." % (
      FL["psi_hopf_replaces_fold"], STAB[20.0]["trace_upper_fold"], STAB[20.0]["alpha_fold_hi"], STAB[20.0]["lnD_fold_hi"], STAB[20.0]["window"]["alpha_ext"], STAB[20.0]["window"]["lnD_ext"],
      T.trace_det(STAB[20.0]["window"]["alpha_ext"], 3e-3, 1.5, 20.0, 1.0)[1]))
rows = [["ψ", "κ", "Equilibria", "Trace at upper fold", "Upper stable from", "ln D window of two stable states", "Window width (K)", "Attractor loop area", "Fold-to-fold area"]]
for psi in (3.0, 4.5, 6.0, 8.0, 12.0, 20.0):
    s = STAB[psi]
    if not s["folds"]:
        rows.append(["%.1f" % psi, f2(s["kappa"]), "1 (κ < κ_{c})", "–", "–", "–", "–", "0", "0"])
        continue
    w = s["window"]
    rows.append(["%.1f" % psi, f2(s["kappa"]), "3", "%+.2f" % s["trace_upper_fold"], "%s, α = %.3f" % (w["kind"], w["alpha_ext"]), "%.3f to %.3f" % (w["lnD_ext"], w["lnD_ign"]), f1((w["lnD_ign"] - w["lnD_ext"]) * KELVIN),
                 f3(s["attractor_area"]), f3(s["multiplicity_area"])])
TAB(rows, "Steady states and stability of the continuous-flow reactor (ϑ = 1, n = 3/2, ε = 3 × 10^{−3}, κ_{c} = %.3f). The upper branch is stable from the upper fold ('fold') or from the Hopf-type point ('hopf'); the window width "
          "is the temperature interval RT²/E_{2}(ln D_{ign} − ln D_{ext}) at 140 °C; the attractor loop area is ∫(α_{upper} − α_{lower}) d ln D over the window of two stable states, and the fold-to-fold area uses the full "
          "multiplicity interval." % KC, widths=[0.4, 0.5, 0.9, 0.8, 1.0, 1.2, 0.7, 0.8, 0.8], size=7.5, label="flowstab")
assert all(s["trace_lower_fold"] < 0 for s in FL["stability"] if s["folds"]), "lower fold is not always a saddle-node"
att20 = [a for a in FL["attractors"] if a["psi"] == 20.0]
att45 = [a for a in FL["attractors"] if a["psi"] == 4.5]
P("*Verification by attractors.* We integrated Eq. (@eflow@) at fixed D from the unreacted state, from a mid-conversion state and from small perturbations of the upper steady state, for nine values of ln D around "
  "each window (ψ = 4.5 and 20). Two distinct long-time states were found for exactly those values of ln D that lie inside the window of @T:flowstab@ (ψ = 4.5: %d of %d inside values show two attractors; ψ = 20: %d of %d), "
  "one state outside it, and no sustained oscillation anywhere (largest late-time oscillation amplitude in α: %.1e). At ψ = 20 the perturbed upper state collapses to the lower state for ln D just below ln D_{H}, "
  "so the loss of stability at the Hopf-type point is, in these simulations, abrupt (subcritical-like), not a transition to a stable cycle; the unstable cycle, if any, was not computed." % (
      sum(1 for a in att45 if a["in_window"] and len(a["attractors"]) >= 2), sum(1 for a in att45 if a["in_window"]), sum(1 for a in att20 if a["in_window"] and len(a["attractors"]) >= 2), sum(1 for a in att20 if a["in_window"]),
      max(a["max_oscillation"] for a in FL["attractors"])))
OUTSIDE_SINGLE = all(len(a["attractors"]) == 1 for a in FL["attractors"] if not a["in_window"])
INSIDE_DOUBLE = all(len(a["attractors"]) == 2 for a in FL["attractors"] if a["in_window"])
print("attractor scan: outside single", OUTSIDE_SINGLE, "inside two", INSIDE_DOUBLE)
c20, c45, c8, c3 = CASE[20.0], CASE[4.5], CASE[8.0], CASE[3.0]
P("*Verification by sweeps.* We swept ln D up and down at rates v = 0.02, 0.01, 0.005, 0.002, 0.001, 0.0005 and 0.0002 per residence time (protocol in Appendix A: start at the unreacted state, dwell 20 residence times at each turning point, "
  "sweep bounds ±2 in ln D beyond the window). The loop area decreases monotonically with v but converges slowly. For ψ = 20 it falls from %.3f to %.3f against the attractor loop area %.3f of @T:flowstab@; a fit "
  "A(v) = A_{0} + cv^{p} to the seven rates gives A_{0} = %.3f with p = %.2f, which a two-point linear intercept would not capture. The downward switching of the sweeps occurs "
  "at ln D = %.2f (v = 0.0002), between the Hopf-type point (%.2f) and the fold (%.2f), because the loss of stability near a Hopf-type point is delayed at finite rate. For ψ = 4.5, just above κ_{c}, "
  "the attractor loop area is %.3f and the integrated area at v = 0.0002 is %.3f (fit A_{0} = %.3f, p = %.2f); for ψ = 8 the attractor loop area is %.3f, the integrated area at v = 0.0002 is %.3f and the fit gives %.3f; for ψ = 3 (κ = %.2f < κ_{c}) there is no static loop and the area at v = 0.0002 "
  "is %.3f (fit %.3f). A finite-rate loop therefore exists below the threshold as well, and only the convergence with v distinguishes a static loop from a rate-dependent one (@T:flow@)." % (
      c20["sweeps"][0]["area"], c20["sweeps"][-1]["area"], c20["attractor_area"], c20["fit_A0"], c20["fit_p"], c20["sweeps"][-1]["lnD_down"], c20["window"]["lnD_ext"], np.log(c20["window"]["D_fold_hi"]),
      c45["attractor_area"], c45["sweeps"][-1]["area"], c45["fit_A0"], c45["fit_p"], c8["attractor_area"], c8["sweeps"][-1]["area"], c8["fit_A0"], c3["kappa"], c3["sweeps"][-1]["area"], c3["fit_A0"]))
rows = [["ψ", "κ", "Attractor loop area", "Fold-to-fold area", "v = 0.02", "0.01", "0.005", "0.002", "0.001", "0.0005", "0.0002", "Fit A_{0} (p)"]]
for psi in (3.0, 4.5, 8.0, 20.0):
    c = CASE[psi]
    rows.append(["%.1f" % psi, f2(c["kappa"]), f3(c["attractor_area"]), f3(c["multiplicity_area"])] + [f3(p["area"]) for p in c["sweeps"]] + ["%s (%s)" % (f3(c["fit_A0"]), f2(c["fit_p"])) if c["fit_A0"] is not None else "–"])
TAB(rows, "Integrated hysteresis-loop area ∮α d ln D of the sweeps at seven sweep rates v (per residence time), with the attractor loop area, the fold-to-fold multiplicity area and a power-law fit A(v) = A_{0} + cv^{p} "
          "(ϑ = 1, n = 3/2, ε = 3 × 10^{−3}).", widths=[0.35, 0.45, 0.7, 0.7, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.85], size=7, label="flow")
FIG("fig4_flow_reactor.png", "(a) Steady-state curve of the flow reactor at ψ = 20 (κ = 10) with stable (solid) and unstable (dashed) segments, the two folds (squares) and the Hopf-type point (circle). (b) Sweep loops "
    "at two rates against the steady states. (c) Loop area against sweep rate, the power-law fit, and the attractor loop area.", "Three panels. (a) Steady conversion against ln D with solid stable and dashed unstable parts and marked fold and Hopf points. (b) Up and down sweep loops. (c) Loop area against sweep rate approaching the attractor loop area.", width=6.7)

HD("F. Closed forms as fitting functions: a synthetic-data test", 2)
P("With a known logistic width *w*_{0}, the storage curves depend on the capsule population only through the open fraction, i.e. through z = (T_{m} − T_{s})/σ_{eff} at each storage temperature, so the pair (T_{m}, σ) is "
  "determined only through the line z(T_{s}) = (T_{m} − T_{s})/σ_{eff}; an unknown *w*_{0} would add a third, confounded parameter. To see how well the pair can be recovered, synthetic isothermal storage curves were generated "
  "with the *population ODE* (not with the closed form) for σ = %.1f °C, T_{m} = %.0f °C and *w*_{0} = %.1f °C at three storage temperatures (%s °C) and five times (30–150 min), with Gaussian noise of %.3f in conversion, "
  "and fitted by least squares with the closed form (known *w*_{0}; %d noise realizations). The estimates are σ̂ = %.1f ± %.1f °C and T̂_{m} = %.1f ± %.1f °C with a correlation of %.2f (Fig. 5): the two parameters are almost "
  "degenerate in this design, and σ̂ is biased high along the degenerate direction. An independent constraint on T_{m}, here a prior of %.1f °C (as from a calorimetric endotherm), markedly improved recovery in this tested design, "
  "to σ̂ = %.1f ± %.1f °C. Other temperatures, times or noise levels may also improve identifiability; no claim is made about real calorimetry." % (
      RC["true_sigma"], RC["true_Tm"], RC["w0"], ", ".join("%.0f" % t for t in RC["temps"]), RC["noise"], RC["n_trials"], RC["sigma_mean"], RC["sigma_sd"], RC["Tm_mean"], RC["Tm_sd"], RC["corr"], RP["Tm_prior_sd"], RP["sigma_mean"], RP["sigma_sd"]))
FIG("fig5_recovery.png", "Least-squares recovery of (T_{m}, σ) from noisy synthetic storage curves; each point is one noise realization (every fifth shown).", "Scatter of recovered mean melting temperature and spread, elongated along a degenerate direction around the true value.", width=3.6)

# ================================================================== IV status
HD("IV. Status of the claims and approximations")
rows = [["Result", "Status", "Assumption it rests on", "Where it fails or is untested"],
        ["Availability clock (Prop. 1)", "Exact", "Constant temperature; α(0) = 0, C_{i}(0) = 0; one availability function ⟨C⟩(t)", "Temperature transients and exotherm; the delay is conversion dependent (Eq. (@edelay@)), and incomplete activation changes the clock"],
        ["Isothermal time and sharpness (Prop. 2)", "Exact (quadrature); n = 1 closed form; sharpness law asymptotic", "m = 1; no diffusion control", "Sharpness law only for n = 1 and b ≫ 9a; vitrification not modelled"],
        ["Storage conversion and σ^{*} (Prop. 3)", "Linearized closed form; probit approximation; verified to a few percent", "Gaussian spread; equal-mass independent capsules; small conversion", "Large tolerance (η ≳ 0.05); skewed or bimodal distributions; capsule–capsule heat exchange"],
        ["Critical number (Prop. 4)", "Frozen-conversion fold, closed form; operational thresholds numerical", "Exponential comparison model; ungated; Θ → 0", "Finite Θ shifts Π_{c} upward (computed only); whether the fold marks ignition of a finite batch is numerical; spatial gradients absent"],
        ["Arrhenius factor", "Frozen-fold factor (exact for one Arrhenius source); exp(1/Ar) first-order", "Single Arrhenius source for the fold", "Tested only for Ar = %.1f–%.1f and Θ ≤ 0.1; not tested at small Ar" % (Ar_lo, Ar_hi)],
        ["Flow reactor multiplicity (Prop. 5)", "Exact for the stated model", "Perfect mixing; exponential model; ungated; ϑ, ψ fixed", "Real reactors: finite mixing time, wall–fluid temperature difference"],
        ["Flow reactor stability", "Jacobian exact; stable window computed; checked by simulation", "As above", "Loss of stability at the Hopf-type point studied for ψ = 20 only; unstable cycle not computed"],
        ["Parameter recovery (III F)", "Numerical experiment", "Gaussian noise; population ODE as truth; known *w*_{0}", "Not a test on real calorimetry"]]
TAB(rows, "Status of the principal results, their assumptions, and where they fail or have not been tested. All parameters are illustrative.", widths=[1.5, 1.5, 1.8, 2.0], size=8, label="status")
P("Three approximations carry the paper: the lumped, well-mixed energy balance; the exponential linearization of the Arrhenius law near the fold; and the Gaussian, independent-capsule description of the "
  "population. The first is a deliberate scope limit and the second is quantified (@T:arr@); the third is tested only against population equations that use the same description.")

# ================================================================== V signatures
HD("V. Falsifiable signatures")
P("Each proposition predicts a measurement that a standard calorimetric or rheological experiment can make; none has been made here. (1) *Availability clock.* Isothermal DSC at several temperatures above the melting "
  "endotherm, comparing the gated resin with the same resin with the catalyst dissolved, should give a delay that depends on conversion as Eq. (@edelay@) and approaches τ_{rel}(T) at late conversion; a conversion-dependent "
  "delay does not falsify the single-availability-function description, which predicts it. What would falsify it is a failure of the measured gated curves, replotted on the integrated-availability clock (measured "
  "independently, for example by release assays), to collapse onto the ungated curve. (2) *Storage bound.* The melting endotherm gives T_{m} and σ; isothermal storage at a margin Δ for a time t should then give a conversion "
  "within a few tens of percent of Eq. (@eleak@); a systematically larger conversion would indicate a tail of capsules with low melting temperature that the Gaussian description misses. (3) *Critical thermal time constant.* "
  "At fixed T_{∞}, specimens of increasing thickness (τ_{th} grows as thickness squared) should show a rapid rise of the peak temperature rise at an operational threshold near Π_{c}/(ψk_{2}), with the Arrhenius "
  "factor of Eq. (@earr@); the abruptness of the rise, from O(Θ) to O(ΔT_{ad}), is the signature of the fold. (4) *Static hysteresis.* In a continuously fed reactor with flow rate and wall time constant held fixed, a "
  "temperature sweep (the path of Section III E) should give a loop whose area converges to a nonzero limit as the sweep slows when ψ is sufficiently above its threshold, and to zero when κ < κ_{c}; a loop that closes as the "
  "sweep slows is rate dependent and not bistability. A sweep of the flow rate at fixed temperature is a different path (ϑ changes) and is not covered by the analysis.")

# ================================================================== VI open problems
HD("VI. Open problems")
P("(a) *Spatial extension.* The lumped balance replaces the classical slab, cylinder or sphere. The critical Frank-Kamenetskii parameter of a consuming, autocatalytic source in a spatially resolved specimen, and its "
  "relation to Π_{c} above, are open. (b) *Finite-Θ correction.* The upward shift of Π_{c} with Θ is computed numerically; a closed-form first correction would complete Proposition 4. (c) *Nature of the Hopf-type point.* "
  "Whether the loss of stability of the upper branch of the flow reactor is sub- or supercritical in general, and the unstable cycle that mediates it, were studied only for ψ = 20. (d) *Non-Gaussian populations.* Proposition 3 "
  "needs only the lower tail of the melting-temperature distribution; skewed and bimodal distributions, and capsule–capsule heat exchange, are untested. (e) *Diffusion control and vitrification.* These stop the cure before "
  "completion and change the late-time tail of Proposition 2. (f) *Noise.* In small specimens or flow channels the fold may be crossed by fluctuations. (g) *Experiment.* The propositions are untested on a real encapsulated "
  "system; the signatures of Section V are the proposed tests.")

# ================================================================== VII conclusion
HD("VII. Conclusion")
P("For the lumped model of a melt-gated autocatalytic cure, several statements can be made exactly or in closed form. The gated cure at constant temperature is the isothermal cure on the clock of integrated availability, and "
  "the delay of a fully open population is τ_{rel}[1 − exp(−t/τ_{rel})] (Proposition 1). The isothermal cure time is exact by quadrature, and the n = 1 sharpness is a logarithm of the rate-constant ratio (Proposition 2). The storage "
  "conversion of a Gaussian capsule population is (a/b)[exp(b f t_{eff}) − 1], which inverts into a bound on the melting-temperature spread (Proposition 3). The frozen-conversion thermal balance has a critical number "
  "(1+n)^{1+n}/[e n^{n}(1+ε)^{1+n}], with an Arrhenius correction that is close to exp(1/Ar) in the tested grid (Proposition 4). The continuous-flow reactor has three equilibria above κ_{c}, but the upper branch can lose stability "
  "at a Hopf-type point before its fold, so the hysteresis window and its loop area must be computed from the stable states (Proposition 5). All results are tested against the full equations; none is tested against "
  "experiment, and the parameters are illustrative.")

HD("Declarations")
P("**Funding.** The author received no funding for this work.")
P("**Competing interests.** The author declares no competing interests.")
P("**Author contributions.** Leon Sandler: conceptualization, methodology, software, formal analysis, investigation, writing – original draft, writing – review and editing, visualization.")
P("**Use of artificial intelligence.** Claude Sonnet 5.5 (Anthropic) was used for derivations, code, figures and drafting as described in Section II C; the author is responsible for the content.")
P("**Data availability.** The model code, the closed-form module, the tests, the figure scripts, the results file (results.json) and the manuscript builder are available at %s (release %s) and archived on Zenodo "
  "at https://doi.org/%s; this manuscript is archived as a preprint at https://doi.org/%s." % (REPO, RELEASE, SW_DOI, PP_DOI))

HD("Appendix A. Numerical protocol, tolerances and convergence")
P("*Reference integrator.* Eqs. (@e1@)–(@e3@) are integrated for all scenarios at once with a vectorized fixed-step fourth-order Runge–Kutta scheme (step 0.01 min for Sections III A and III B, 0.05 min for the population "
  "runs of III C; end time 150 min for storage, 300–600 min for cure times). Conversion is limited to [0, 1] and the reaction heat is ΔT_{ad} dα/dt without cut-off, so the energy balance is conserved: in the adiabatic limit the "
  "integrated temperature rise equals ΔT_{ad}α to %.1e K (Section II, test_theory.py). Capsule populations use K = 801 deterministic Gaussian quantiles z_{i} = Φ^{−1}[(i − 1/2)/K]. Convergence: relative to K = 3201 the storage conversion "
  "at K = 801 differs by at most %.1e, and relative to step 0.0125 min the step 0.05 min differs by at most %.1e (@T:conv@; difference = value/reference − 1)." % (abs(R["energy"]["rise"] - R["energy"]["dTad_alpha"]), conv_K, conv_dt))
P("*Adaptive integrations.* The exponential-model criticality problem is integrated with LSODA (rtol 10^{−9}, atol 10^{−13}, max step 0.02, end time 40/k_{2}); the Arrhenius criticality problem with LSODA (rtol 10^{−8}, atol 10^{−12}, "
  "end time 60/k_{2}, temperature floored at 200 K in the rate); the flow reactor with LSODA (rtol 10^{−8}, atol 10^{−12}, max step min(0.5, 0.02/v)); fixed-D attractor runs with LSODA (rtol 10^{−11}, atol 10^{−14}, end time 3000 "
  "residence times; the last 10 % is used to classify the state); constant-temperature delay checks with RK45 (rtol 10^{−12}).")
P("*Thresholds.* The operational critical number is the Π (exponential model, bracket [0.3, 8], 30 bisection steps) or the adiabatic rise (Arrhenius model, bracket [3, 8000] K in logarithm, 26 steps) at which the integrated "
  "peak temperature rise (T_{max} − T_{∞})/ΔT_{ad} first exceeds 0.3, starting from T(0) = T_{∞}. *Sweeps.* Start at (θ, α) = (0, 0) at the lower bound of ln D (window lower edge minus 2), dwell 20 residence times, sweep up at rate v to the upper "
  "bound (window upper edge plus 2), dwell 20, sweep down, dwell 20; the area is the signed integral of α d ln D over the two sweep legs (output step 0.05). *Design bound.* σ^{*} from Eq. (@esigma@) with *w*_{0} = 0.5 °C; the ODE root "
  "is bracketed in [0.3, 40] °C (xtol 10^{−3}). *Recovery.* 200 noise realizations (seed 20261007, prior test seed 20261008), bounded least squares. *Errors.* In every table, difference = closed form (or prediction)/numerical − 1. "
  "*Software.* Python %s, NumPy %s, SciPy %s; release %s of the repository contains the exact scripts and results.json." % (R["versions"]["python"], R["versions"]["numpy"], R["versions"]["scipy"], RELEASE))
rows = [["Quantity", "Setting", "Value at setting", "Reference", "Relative difference"]]
for sg in (2.0, 4.0):
    for c in CV:
        if c["kind"] == "K" and c["sigma"] == sg:
            rows.append(["Storage conversion (σ = %.0f °C, Δ = 6 °C)" % sg, "K = %d" % c["K"], "%.6f" % c["value"], "%.6f (K = 3201)" % c["reference"], "%+.1e" % c["rel_diff"]])
    for c in CV:
        if c["kind"] == "dt" and c["sigma"] == sg:
            rows.append(["Storage conversion (σ = %.0f °C, Δ = 6 °C)" % sg, "step %.4g min" % c["dt"], "%.6f" % c["value"], "%.6f (step 0.0125)" % c["reference"], "%+.1e" % c["rel_diff"]])
TAB(rows, "Convergence of the reference integrator with population size and step (storage conversion after 150 min, Δ = 6 °C, *w*_{0} = 0.5 °C; the narrower spread σ = 2 °C is the tail-sensitive case).", widths=[2.0, 1.0, 1.0, 1.4, 1.1], size=8, label="conv")
rows = [["Study", "Method", "Grid", "Compared with"],
        ["Availability clock", "RK4 (step 0.01 min) and RK45 (rtol 10^{−12}), constant T", "T = 125, 140, 155 °C; α = 0.001–0.9", "Eqs. (@eclock@), (@edelay@)"],
        ["Isothermal cure", "RK4, step 0.01 min", "T = 110–155 °C; n = 1, 3/2", "Quadrature; Eqs. (@eiso@), (@esharp@), (@elaw@)"],
        ["Storage conversion", "RK4 population (K = 801), step 0.05 min", "Δ = 3, 6, 10 °C; σ = 2–10 °C; t = 150 min", "Eq. (@eleak@)"],
        ["Design bound", "Root-finding on the population ODE", "Δ = 3, 6, 10 °C; η = 0.001, 0.01, 0.05", "Eq. (@esigma@)"],
        ["Criticality (exponential model)", "LSODA, bisection", "n = 1, 3/2, 2; Θ = 0.1–0.003", "Eq. (@ePic@)"],
        ["Criticality (Arrhenius)", "LSODA, bisection", "T = 120, 140, 160 °C; Θ = 0.01–0.1", "Eq. (@earr@)"],
        ["Flow reactor", "Jacobian; LSODA attractors and sweeps", "ψ = 3, 4.5, 6, 8, 12, 20; v = 0.02–0.001", "Eqs. (@ess@), (@eJ@), attractor loop area"],
        ["Parameter recovery", "Bounded least squares, 200 noise draws", "3 temperatures × 5 times", "Truth"]]
TAB(rows, "Run table of the numerical studies; every result is reproduced by code/run_all.py.", widths=[1.5, 2.1, 2.0, 1.4], size=8, label="runs")

HD("References")
for k in CITE:
    q = doc.add_paragraph()
    H.add_rich(q, "[%d] %s" % (CITE.index(k) + 1, REFS[k]["entry"]), size=10)
    q.paragraph_format.space_after = H.Pt(3)

doc.core_properties.author = "Leon Sandler"
doc.core_properties.title = TITLE
outp = os.path.join(OUT, "Gated_Autocatalysis_Criticality_JCP.docx")
doc.save(outp)
json.dump(TLAB_NEW, open(LABFILE, "w"))
words = 0
body = False
for q in doc.paragraphs:
    t = q.text.strip()
    if t.startswith("I. Introduction"):
        body = True
    if t == "References":
        body = False
    if body and t:
        words += len(t.split())
print("saved", outp, "| figures:", FIGN[0], "| tables:", TABN[0], "| references:", len(CITE), "| body words (excl. tables):", words, "| labels:", TLAB_NEW)
