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
SW_DOI, PP_DOI = ZEN["software"]["doi"], ZEN["publication"]["doi"]
REPO = "https://github.com/sandlerleon/gated-autocatalysis-criticality"
NOLN = os.environ.get("NO_LINENUM") == "1"

TITLE = "Closed-Form Storage Stability, Induction Delay, and Thermal-Feedback Criticality of Melt-Gated Autocatalytic Cure"

# ------------------------------------------------------------------ numbers
n_ord = 1.5
CL, IS, LK, DR, RC = R["clock"], R["isothermal"], R["leakage"], R["design_rule"], R["recovery"]
FK, AR, FL = R["critical_fk"], R["critical_arrhenius"], R["flow"]
clock_err = max(abs(r["clock"] - r["numeric"]) / r["numeric"] for r in CL)
iso_err = max(max(abs(r["t10_th"] - r["t10_num"]) / r["t10_num"], abs(r["t90_th"] - r["t90_num"]) / r["t90_num"]) for r in IS)
r140_1 = [r for r in IS if r["T"] == 140.0 and r["n"] == 1.0][0]
r140_15 = [r for r in IS if r["T"] == 140.0 and r["n"] == 1.5][0]
law_err = max(abs(r["S_law"] / r["S_th"] - 1) for r in IS if r["n"] == 1.0)
lk_ok = [r for r in LK if r["numeric"] > 1e-5]
lk_dev = [abs(r["analytic"] / r["numeric"] - 1) for r in lk_ok]
dr_ok = [r for r in DR if r["sigma_star_numeric"] and r["sigma_star_analytic"] and r["sigma_star_analytic"] < 40]
dr_dev = [abs(r["sigma_star_analytic"] / r["sigma_star_numeric"] - 1) for r in dr_ok]
fk15 = {r["Theta"]: r for r in FK if r["n"] == 1.5}
ar_dev = [abs(r["Pi_c_arrhenius"] / r["prediction"] - 1) for r in AR]
ar_fk_dev = [abs(r["Pi_c_arrhenius"] / r["Pi_c_fk"] - 1) for r in AR]
gated = [r for r in AR if r["Pi_c_gated"]]
fl_hi = [c for c in FL["cases"] if c["psi"] == 20.0][0]
fl_mid = [c for c in FL["cases"] if c["psi"] == 4.5][0]
fl_lo = [c for c in FL["cases"] if c["psi"] == 3.0][0]
PIC = {n: T.Pi_c0(n, 0.0) for n in (1.0, 1.5, 2.0)}
a140, b140 = float(T.arrhenius(2.0e3, 5.0e4, 140.0)), float(T.arrhenius(2.5e7, 6.5e4, 140.0))
krel140 = float(T.arrhenius(6.4e6, 6.0e4, 140.0))
NUM = {}
NUM.update(midx="%.2f" % fl_mid["extrapolated_area"], mids="%.3f" % fl_mid["static_area"], hierr="%.1f" % (100 * abs(fl_hi["extrapolated_area"] / fl_hi["static_area"] - 1)))
print("clock error %.2e | iso error %.2e | law err %.3f | leak dev max %.3f | sigma* dev max %.3f | Arr dev max %.3f" % (clock_err, iso_err, law_err, max(lk_dev), max(dr_dev), max(ar_dev)))

# ------------------------------------------------------------------ citations and numbering
CITE = []
LABFILE = os.path.join(OUT, "labels.json")
TLAB = json.load(open(LABFILE)) if os.path.exists(LABFILE) else {}
TLAB_NEW = {}
FIGN, TABN = [0], [0]


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


def FIG(path, caption, width=6.4):
    FIGN[0] += 1
    H.figure(doc, os.path.join(ROOT, "figures", path), width_in=width, cap="**Fig. %d** %s" % (FIGN[0], cites(sub(caption))))


def TAB(rows, caption, widths=None, size=8.5, label=None):
    TABN[0] += 1
    if label:
        TLAB_NEW[label] = TABN[0]
    H.caption(doc, "**Table %d** %s" % (TABN[0], cites(sub(caption))), keep_next=True)
    H.table(doc, [[cites(sub(c)) for c in r] for r in rows], widths=widths, size=size)


EQN = [0]


def EQ(nodes):
    EQN[0] += 1
    H.equation(doc, nodes, EQN[0])
    return EQN[0]


V, Tt, SUBN, SUPN, FRAC, DEL, Vs, SUBSUP = H.V, H.T, H.SUB, H.SUP, H.FRAC, H.DELIM, H.Vs, H.SUBSUP


def sv(base, s):
    return SUBN(V(base), Tt(s))


AVC = DEL(V("C"), "⟨", "⟩")                       # capsule-averaged availability
PLUS, MINUS, EQS = Tt(" + "), Tt(" − "), Tt(" = ")


def f2(x, k=2):
    return ("%." + str(k) + "f") % x


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
       "We show that this lumped model is largely solvable in closed form, and test every result against the full equations. "
       "(i) At constant temperature the gated cure is the isothermal cure evaluated on the integrated availability of the catalyst, so the gate delays every conversion level by essentially the "
       "release time constant (verified to %.0e relative error). (ii) The isothermal cure time is exact by one quadrature for any reaction order and in closed form "
       "for first order; its sharpness is set logarithmically by the rate-constant ratio. (iii) For Gaussian-distributed capsule melting "
       "temperatures with spread σ, the storage conversion follows from the open fraction Φ(−Δ/σ_eff) and gives a closed-form rule for the largest admissible spread, which agrees with the "
       "population equations within %.0f %%. (iv) Thermal feedback has a critical number Π_c = ψΘ = e⁻¹(1+n)^(1+n)/n^n (%.2f for n = 3/2) at a fold of the quasi-steady "
       "manifold; the overshoot below it is a Lambert-W function with a square-root normal form, bisected integrations approach it to %.1f %% as Θ → 0, and Arrhenius kinetics "
       "multiply it by exp(1/Ar). (v) In a continuous-flow reactor the same fold produces ignition–extinction hysteresis with a computed existence threshold κ_c = %.2f, and the loop area "
       "extrapolates to the static value as the sweep rate vanishes. All parameters are illustrative and no experimental data are used."
       % (max(clock_err, 1e-9), 100 * max(dr_dev), PIC[1.5], 100 * abs(fk15[0.003]["Pi_c_numeric"] / fk15[0.003]["Pi_c0"] - 1), FL["kappa_c"]))
H.para(doc, ABS, align="justify")
print("abstract words:", len(ABS.split()))
P("**Keywords:** autocatalytic cure kinetics; thermal runaway; encapsulated catalyst; Lambert W function; saddle-node bifurcation; hysteresis", align="left")

# ================================================================== 1 Introduction
HD("I. Introduction")
P("Encapsulating a reactive component and releasing it on demand is a general way to separate the stability of a formulation from the speed of its cure. The best-known "
  "instance is the self-healing polymer, in which embedded capsules release a healing agent when damaged [[white2001]]; thermally triggered variants use the melting of a wax or "
  "polymer shell, whose phase-change behavior is the subject of an extensive literature on microencapsulated phase-change materials [[jamekhorshid2014]]. When the released species catalyzes "
  "a thermoset cure, three features interact: the capsule population has a distribution of melting temperatures rather than a single one, the cure is autocatalytic "
  "and follows the form introduced by Kamal and Sourour [[kamal1973,sourour1976]], and the cure heat raises the temperature of the specimen, which accelerates the cure. The last "
  "interaction is the origin of thermal runaway in thick thermoset sections [[bogetti1992]] and is the subject of the classical theory of thermal explosion of Semenov and "
  "Frank-Kamenetskii [[semenov1928,frankkamenetskii1969]], while the multiplicity of steady states of a heated, continuously fed reactor goes back to van Heerden [[vanheerden1953,grayscott1990]].")
P("What is missing is a quantitative link between the few parameters that a calorimeter measures (the rate constants of the cure, the width of the melting endotherm of the capsules, "
  "the thermal time constant of a specimen) and the three properties that determine whether a gated formulation can be used: how long it can be stored, how long the gate delays the "
  "cure, and when the cure heat makes the temperature run away. Kinetic analysis of calorimetric data is well codified [[vyazovkin2011,zhao2019]], but it treats the rate law and "
  "the energy balance separately. Here we show that, for the lumped model of a melt-gated autocatalytic cure, those links can be written in closed form.")
P("The paper makes five contributions, each stated as a proposition and each verified against the full numerical model. (1) At constant temperature the gated cure is exactly the "
  "isothermal cure on the clock of integrated availability (Section III A). (2) The isothermal cure time is exact for any reaction order by one quadrature, and its sharpness obeys a logarithmic "
  "law (III B). (3) The storage conversion of a Gaussian capsule population has a closed form that inverts into a design rule for the admissible melting-temperature spread (III C). "
  "(4) Thermal feedback has a critical number at a fold of the quasi-steady manifold, with the overshoot given by the Lambert W function and the effect of Arrhenius kinetics by a "
  "closed-form factor (III D). (5) The same fold, in a continuous-flow reactor, produces an ignition–extinction hysteresis whose existence threshold and static loop area are computable, and "
  "whose loop area at finite sweep rate extrapolates to the static value (III E). A synthetic-data test shows how the closed forms behave as fitting functions (III F).")
P("The illustrative parameter set and the capsule-population picture were introduced in a numerical study by the author [[sandler2026]]. The analytic results below are new, and the "
  "comparisons of that study with first-order controls are not used here. The model is lumped and every parameter is illustrative: nothing is fitted to measurements, and the paper "
  "makes no claim about a particular material.")

# ================================================================== 2 Model
HD("II. Model and scaling")
HD("A. Equations", 2)
P("The conversion α of the resin obeys a Kamal–Sourour law with reaction order n for the unreacted fraction and first order in the autocatalytic term,")
EQ(FRAC(V("dα"), V("dt")) + EQS + AVC + Tt("(t)") + DEL(sv("k", "1") + PLUS + sv("k", "2") + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + Tt(","))
P("where ⟨C⟩ is the availability of the catalyst averaged over the capsule population (the fraction of the catalyst that has been released, 0 ≤ ⟨C⟩ ≤ 1). The temperature "
  "of the well-mixed specimen obeys a lumped energy balance with Newtonian loss and the adiabatic temperature rise ΔT_{ad} of the reaction,")
EQ(FRAC(V("dT"), V("dt")) + EQS + FRAC(DEL(sv("T", "∞") + MINUS + V("T")), sv("τ", "th")) + PLUS + sv("ΔT", "ad") + FRAC(V("dα"), V("dt")) + Tt("."))
P("Capsule *i* has a melting temperature T_{m,i}, drawn from a Gaussian of mean T_{m} and standard deviation σ, and releases its catalyst by first-order relaxation toward a "
  "logistic activation of width *w*_{0},")
EQ(FRAC(SUBN(V("dC"), V("i")), V("dt")) + EQS + sv("k", "rel") + DEL(V("T")) + DEL(SUBN(V("G"), V("i")) + DEL(V("T")) + MINUS + SUBN(V("C"), V("i")), "[", "]") + Tt(",   ") +
   SUBN(V("G"), V("i")) + EQS + SUPN(DEL(Tt("1") + PLUS + Tt("exp") + DEL(MINUS + FRAC(V("T") + MINUS + SUBN(V("T"), V("m,i")), sv("w", "0")))), Tt("−1")) + Tt(",   ") + AVC + EQS +
   FRAC(Tt("1"), V("K")) + Tt("∑") + SUBN(V("C"), V("i")) + Tt("."))
P("The rate constants are Arrhenius, *k*_{j} = *A*_{j} exp(−*E*_{j}/*RT*), for *j* = 1 (background), 2 (autocatalytic) and rel (release). The model has no spatial structure, "
  "no diffusion control and no vitrification; those limits are listed in Section VI. Throughout, the *illustrative* parameter set of @T:par@ is used; it is not fitted to any material.")
rows = [["Quantity", "Symbol", "Value"],
        ["Background rate constant", "A_{1}, E_{1}", "2.0 × 10^{3} min^{−1}, 50 kJ mol^{−1}"],
        ["Autocatalytic rate constant", "A_{2}, E_{2}", "2.5 × 10^{7} min^{−1}, 65 kJ mol^{−1}"],
        ["Reaction order", "n", "1.5 (1 and 2 where stated)"],
        ["Release rate constant", "A_{rel}, E_{rel}", "6.4 × 10^{6} min^{−1}, 60 kJ mol^{−1}"],
        ["Mean melting temperature, activation width", "T_{m}, w_{0}", "118 °C, 0.5 °C (3 °C for single-gate runs of Section III D)"],
        ["Adiabatic rise, thermal time constant", "ΔT_{ad}, τ_{th}", "220 K, varied (Section III D)"],
        ["Rate constants at 140 °C", "k_{1}, k_{2}, k_{rel}", "%.2e, %.3f, %.3f min^{−1}" % (a140, b140, krel140)]]
TAB(rows, "Illustrative parameter set (not fitted to any material). Arrhenius forms are *k* = *A* exp(−*E*/*RT*).", widths=[2.6, 1.3, 2.7], label="par")
HD("B. Dimensionless groups", 2)
P("With ε = k_{1}/k_{2}, the thermal number Θ = τ_{th}k_{2}(T_{∞}), the reduced exothermicity ψ = ΔT_{ad}E_{2}/(RT_{∞}^{2}), the activation number Ar = E_{2}/(RT_{∞}) and the release "
  "number Λ = k_{2}/k_{rel}, the combination that controls thermal feedback turns out to be")
EQ(Tt("Π") + EQS + Tt("ψ") + Tt("Θ") + EQS + FRAC(sv("ΔT", "ad") + sv("E", "2") + sv("τ", "th") + sv("k", "2"), V("R") + SUPN(sv("T", "∞"), Tt("2"))) + Tt("."))

# ================================================================== 3 Results
HD("III. Results")
HD("A. Proposition 1: the gated cure runs on the clock of integrated availability", 2)
P("**Proposition 1.** At constant temperature, let F(α) = (k_{1} + k_{2}α)(1 − α)^{n}. Then the gated conversion obeys")
EQ(SUBSUP(Tt("∫"), Tt("0"), V("α")) + FRAC(V("dx"), V("F") + DEL(V("x"))) + EQS + V("s") + DEL(V("t")) + Tt(",   ") + V("s") + DEL(V("t")) + EQS + SUBSUP(Tt("∫"), Tt("0"), V("t")) + AVC + DEL(V("t′")) + V("dt′") + Tt("."))
P("*Proof.* With T constant, dα/dt = ⟨C⟩(t)F(α) is separable: dα/F(α) = ⟨C⟩dt. Integration from the initial state gives the identity. ∎ The left side is the isothermal time "
  "t_{iso}(α) of the ungated resin, so the gated time to reach a conversion α is the time at which the integrated availability s(t) equals t_{iso}(α). For a capsule population that is fully open "
  "at the operating temperature, ⟨C⟩ = 1 − exp(−k_{rel}t) and s(t) = t − (1 − exp(−k_{rel}t))/k_{rel}, so that")
EQ(sv("t", "gated") + DEL(V("α")) + EQS + sv("t", "iso") + DEL(V("α")) + PLUS + FRAC(Tt("1") + MINUS + Tt("exp") + DEL(MINUS + sv("k", "rel") + sv("t", "gated")), sv("k", "rel")) + Tt("≈") + sv("t", "iso") + DEL(V("α")) + PLUS + sv("τ", "rel") + Tt("."))
P("The gate therefore delays every conversion level by the same time, the release time constant τ_{rel} = 1/k_{rel} (%.1f min at 140 °C in @T:par@), independently of the kinetics and of α. "
  "Integrating the full equations at constant temperature for 125, 140 and 155 °C and for α = 0.1, 0.5 and 0.9 gives gated times that agree with the closed form to a relative error of at most %.1e "
  "(the quadrature and the integrator differ only by truncation error); the delay for T = 140 °C is %.2f min against τ_{rel} = %.2f min. The statement is exact only at constant "
  "temperature: a heat-up transient or an exotherm adds a further, temperature-dependent delay that Proposition 1 does not describe." % (1 / krel140, max(clock_err, 1e-9),
  [r for r in CL if r["T"] == 140.0 and r["alpha"] == 0.5][0]["numeric"] - [r for r in CL if r["T"] == 140.0 and r["alpha"] == 0.5][0]["iso"], 1 / krel140))
HD("B. Proposition 2: isothermal cure time, induction, and sharpness", 2)
P("**Proposition 2.** With a = k_{1} and b = k_{2}, the isothermal time to reach conversion α is, for any n, t_{iso}(α) = ∫_{0}^{α} dx/[(a + bx)(1 − x)^{n}], and for n = 1")
EQ(sv("t", "iso") + DEL(V("α")) + EQS + FRAC(Tt("1"), V("a") + PLUS + V("b")) + Tt("ln") + FRAC(V("a") + PLUS + V("b") + V("α"), V("a") + DEL(Tt("1") + MINUS + V("α"))) + Tt("."))
P("*Proof.* Partial fractions of 1/[(a + bx)(1 − x)] give (a + b)^{−1}[b/(a + bx) + 1/(1 − x)], and integration gives the logarithm. ∎ For small α the factor (1 − x)^{n} is close to 1, "
  "so the induction time (α = 0.1) is almost independent of n; the late-time tail is not. For b ≫ a the exact n = 1 sharpness S = (t_{90} − t_{10})/t_{10} reduces to")
EQ(V("S") + Tt("≈") + FRAC(Tt("2 ln 9"), Tt("ln") + DEL(FRAC(V("b"), Tt("9") + V("a")))) + Tt("."))
P("Sharpness is therefore controlled by the rate-constant ratio alone, and only logarithmically: at 140 °C, b/a = %.0f gives S = %.2f exactly for n = 1 and %.2f from Eq. (%d), "
  "and a hundredfold change of the ratio changes S by a factor of about 1.3. The closed forms and the quadrature reproduce the integrated t_{10} and t_{90} for T = 110–155 °C and n = 1 and 1.5 to "
  "within %.1e (relative). The sharpness law is accurate to %.0f %% across that range for n = 1; for n = 1.5 the tail is longer and S rises from %.2f to %.2f at 140 °C, which the law does "
  "not capture (the quadrature does)." % (r140_1["ratio"], r140_1["S_th"], r140_1["S_law"], EQN[0], max(iso_err, 1e-9), 100 * law_err, r140_1["S_num"], r140_15["S_num"]))
FIG("fig1_clock_sharpness.png", "(a) Gated and ungated cure at constant temperature: the gated curve is the isothermal curve shifted by about τ_{rel}, and the integrated ODE (circles) agrees with the "
    "availability-clock formula. (b) Sharpness as a function of the rate-constant ratio: exact n = 1, the logarithmic law, and integrated results for n = 1.5.")

HD("C. Proposition 3: storage conversion of a capsule population and a design rule", 2)
P("A capsule that is open at the storage temperature T_{s} releases catalyst that then drives the autocatalytic cure at T_{s}. For a Gaussian spread σ of melting temperatures and a "
  "logistic activation of width *w*_{0}, the equilibrium open fraction at a margin Δ = T_{m} − T_{s} below the mean melting temperature is the Gaussian–logistic convolution, which the probit "
  "approximation (matching variances, π²w_{0}²/3 for the logistic) writes as")
EQ(V("f") + EQS + Tt("Φ") + DEL(MINUS + FRAC(V("Δ"), sv("σ", "eff"))) + Tt(",   ") + SUBN(V("σ"), Tt("eff")) + Tt("²") + EQS + SUPN(V("σ"), Tt("2")) + PLUS + FRAC(SUPN(Tt("π"), Tt("2")) + SUPN(sv("w", "0"), Tt("2")), Tt("3")) + Tt("."))
P("**Proposition 3.** If every capsule relaxes toward its own activation with the common rate constant k_{rel}(T_{s}), then ⟨C⟩(t) = f(1 − exp(−k_{rel}t)) and, for small conversion, the "
  "storage conversion after a time t is")
EQ(sv("α", "s") + DEL(V("t")) + EQS + V("a") + SUBSUP(Tt("∫"), Tt("0"), V("t")) + AVC + DEL(V("s")) + Tt("exp") + DEL(V("b") + SUBSUP(Tt("∫"), V("s"), V("t")) + AVC + DEL(V("u")) + V("du")) + V("ds") + Tt("."))
P("*Proof.* For α ≪ 1 and (1 − α)^{n} ≈ 1 the rate law is linear, dα/dt = ⟨C⟩(a + bα), which is solved by the integrating factor exp(b∫⟨C⟩). ∎ The tolerance ε on the storage conversion "
  "fixes the largest admissible open fraction f^{*} by α_{s}(t; f^{*}) = ε (a monotone one-dimensional root), and the design rule follows by inverting the probit relation:")
EQ(V("σ*") + EQS + FRAC(V("Δ"), V("z*")) + Tt(",   ") + V("z*") + EQS + MINUS + SUPN(Tt("Φ"), Tt("−1")) + DEL(SUPN(V("f"), Tt("*"))) + Tt("   (w₀ → 0)."))
P("For small ε, f^{*} ≈ ln(1 + εb/a)/(b t_{eff}) with t_{eff} = t − (1 − exp(−k_{rel}t))/k_{rel}. We tested the closed form against the capsule-population equations (K = 801 deterministic Gaussian quantiles "
  "of the melting temperature, constant temperature, t = 150 min) for margins of 3, 6 and 10 °C and spreads of 2–10 °C: the storage conversions agree within %.0f %% (median ratio %.3f), "
  "and the spread σ^{*} that solves α_{s} = ε agrees with the root of the population equations within %.0f %% for all %d cases for which the ODE reaches ε (@T:dr@). For ε = 0.01 and a 6 °C "
  "margin the rule gives σ^{*} = %.1f °C." % (100 * max(lk_dev), np.median([r["analytic"] / r["numeric"] for r in lk_ok]), 100 * max(dr_dev), len(dr_ok),
                                           [r for r in DR if r["margin"] == 6.0 and r["eps"] == 0.01][0]["sigma_star_analytic"]))
rows = [["Margin Δ (°C)", "Tolerance ε", "σ^{*} closed form (°C)", "σ^{*} population ODE (°C)", "Difference"]]
for r in DR:
    rows.append(["%.0f" % r["margin"], "%g" % r["eps"], ("%.2f" % r["sigma_star_analytic"] if r["sigma_star_analytic"] and r["sigma_star_analytic"] < 40 else "> 40"), "%.2f" % r["sigma_star_numeric"] if r["sigma_star_numeric"] else "> 40",
                 "%+.1f %%" % (100 * (r["sigma_star_analytic"] / r["sigma_star_numeric"] - 1)) if r["sigma_star_numeric"] and r["sigma_star_analytic"] else "–"])
TAB(rows, "Largest admissible melting-temperature spread σ^{*} for a storage time of 150 min: closed form (Proposition 3) against root-finding on the population equations.", widths=[1.2, 1.1, 1.6, 1.8, 1.0], label="dr")
FIG("fig2_storage.png", "(a) Closed-form storage conversion against the population ODE for margins of 3, 6 and 10 °C. (b) Largest admissible spread σ^{*} as a function of the tolerance ε; open symbols are roots of the "
    "population ODE.")

HD("D. Proposition 4: thermal-feedback criticality, overshoot, and Arrhenius correction", 2)
P("When the thermal time constant is short compared with the reaction time (Θ ≪ 1) the temperature rise θ = (T − T_{∞})/ΔT_{ad} follows the reaction quasi-statically, θ = Θ r(α) exp(ψθ), "
  "where r(α) = (ε + α)(1 − α)^{n} is the isothermal rate in units of k_{2} and the exponential is the Frank-Kamenetskii linearization of the Arrhenius law (valid at the fold, where the "
  "temperature rise is of order RT²/E_{2}). Multiplying by ψ gives ψθ exp(−ψθ) = Πr, whose solution, if Πr ≤ 1/e, is")
EQ(V("ψθ") + EQS + MINUS + sv("W", "0") + DEL(MINUS + Tt("Π") + V("r") + DEL(V("α"))) + Tt("."))
P("**Proposition 4.** The quasi-steady temperature rise ceases to exist, and the system ignites, when Πr(α) = 1/e is reached at the maximum of r. Hence")
EQ(sv("Π", "c") + EQS + FRAC(Tt("1"), Tt("e") + sv("r", "max")) + EQS + SUPN(Tt("e"), Tt("−1")) + FRAC(SUPN(DEL(Tt("1") + PLUS + V("n")), Tt("1+n")), SUPN(V("n"), V("n"))) + Tt("   (ε → 0),"))
P("which is %.3f, %.3f and %.3f for n = 1, 3/2 and 2. Below Π_{c} the peak overshoot is ψθ_{peak} = −W_{0}(−Π/(eΠ_{c})), and near the fold ψθ_{peak} ≈ 1 − [2(1 − Π/Π_{c})]^{1/2} "
  "(the normal form of a saddle-node bifurcation [[strogatz2015,corless1996]]), so the overshoot jumps from O(Θ) to O(1) as Π crosses Π_{c}. For comparison, the classical Semenov criterion "
  "for a source without consumption, r = 1 in the same units, gives 1/e = 0.37; consumption and autocatalysis raise the critical number by the factor 1/r_{max} ≈ %.1f for n = 3/2." % (PIC[1.0], PIC[1.5], PIC[2.0], 1 / T.r_max(1.5, 0.0)))
P("*Verification.* We integrated the exponential-form equations with isothermal start and bisected the threshold at which the peak temperature rise exceeds 0.3ΔT_{ad} (ε = 3 × 10^{−3}; @T:fk@). "
  "As Θ → 0 the numerical Π_{c} converges to Eq. (%d): at Θ = 0.003 the values are %.3f, %.3f and %.3f against %.3f, %.3f and %.3f (differences %.1f–%.1f %%); the threshold criterion matters little (Π_{c} = %.3f, %.3f, %.3f for "
  "0.15, 0.3 and 0.6). The finite-Θ shift is upward (Π_{c} = %.2f at Θ = 0.1 for n = 3/2). At Θ = 0.002 the overshoot at 0.5–0.98 Π_{c} follows the Lambert-W formula and approaches the "
  "square-root form (Fig. 3b)." % (EQN[0], *[[r for r in FK if r["n"] == n and r["Theta"] == 0.003][0]["Pi_c_numeric"] for n in (1.0, 1.5, 2.0)],
                                   *[[r for r in FK if r["n"] == n and r["Theta"] == 0.003][0]["Pi_c0"] for n in (1.0, 1.5, 2.0)],
                                   100 * min(abs(r["Pi_c_numeric"] / r["Pi_c0"] - 1) for r in FK if r["Theta"] == 0.003), 100 * max(abs(r["Pi_c_numeric"] / r["Pi_c0"] - 1) for r in FK if r["Theta"] == 0.003),
                                   *[R["critical_threshold_sensitivity"][k] for k in ("0.15", "0.3", "0.6")], fk15[0.1]["Pi_c_numeric"]))
rows = [["n", "Θ", "Π_{c} (integrated)", "Π_{c} (Θ → 0, Eq. above)"]] + [["%.1f" % r["n"], "%g" % r["Theta"], "%.3f" % r["Pi_c_numeric"], "%.3f" % r["Pi_c0"]] for r in FK]
TAB(rows, "Critical thermal-feedback number in the exponential (Frank-Kamenetskii) form: bisected integrations against the closed form for Θ → 0 (ε = 3 × 10^{−3}, threshold 0.3).", widths=[0.7, 0.9, 2.2, 2.6], label="fk")
P("*Arrhenius kinetics.* The Arrhenius law is slower than its exponential linearization at a temperature rise x = ΔT/T_{∞}: exp[Ar x/(1 + x)] ≈ exp(Ar x) exp(−Ar x²). At the fold ψθ = 1, i.e. x = 1/Ar, so the "
  "rate is reduced by exp(−1/Ar) and the critical number is raised by")
EQ(sv("Π", "c") + SUPN(Tt(""), Tt("Arr")) + Tt("≈") + sv("Π", "c") + SUPN(Tt(""), Tt("FK")) + DEL(V("Θ")) + Tt("exp") + DEL(FRAC(Tt("1"), Tt("Ar"))) + Tt("."))
P("We tested this with the true Arrhenius model (ungated, isothermal start) at 120, 140 and 160 °C and Θ = 0.01, 0.03, 0.1, bisecting the adiabatic rise (@T:arr@). The prediction Π_{c}^{FK}(Θ)exp(1/Ar) "
  "is within %.1f %% of the Arrhenius threshold in every case (the uncorrected exponential form is off by %.0f–%.0f %%). A catalyst that is released with a time constant τ_{rel} can only lower the heat "
  "production rate at a given conversion, since ⟨C⟩ ≤ 1, so the gated threshold cannot be below the ungated one. The effect is small here because the catalyst is fully released (τ_{rel} = 6 min) long before the rate peaks: at 140 °C and Θ = 0.03 the release lag raised Π_{c} from %.3f to %.3f." % (
      100 * max(ar_dev), 100 * min(ar_fk_dev), 100 * max(ar_fk_dev), [r for r in AR if r["T"] == 140.0 and r["Theta"] == 0.03][0]["Pi_c_arrhenius"], [r for r in AR if r["T"] == 140.0 and r["Theta"] == 0.03][0]["Pi_c_gated"]))
rows = [["T (°C)", "Θ", "Ar", "Π_{c} Arrhenius", "Π_{c} FK(Θ)", "FK(Θ) exp(1/Ar)", "Difference", "Π_{c} with release lag"]]
for r in AR:
    rows.append(["%.0f" % r["T"], "%g" % r["Theta"], "%.1f" % r["Ar"], "%.3f" % r["Pi_c_arrhenius"], "%.3f" % r["Pi_c_fk"], "%.3f" % r["prediction"],
                 "%+.1f %%" % (100 * (r["Pi_c_arrhenius"] / r["prediction"] - 1)), "%.3f" % r["Pi_c_gated"] if r["Pi_c_gated"] else "–"])
TAB(rows, "Critical number of the Arrhenius model (ungated, isothermal start; threshold 0.3) against the exponential-form critical number multiplied by exp(1/Ar), and the effect of a release lag.", widths=[0.6, 0.5, 0.5, 1.0, 0.9, 1.0, 0.8, 1.2], size=8, label="arr")
FIG("fig3_criticality.png", "(a) Critical number against Θ for n = 1, 3/2 and 2 (points: integrations; dashed: Eq. above). (b) Quasi-steady overshoot below Π_{c}: Lambert-W formula, fold normal form, and integrations. "
    "(c) Arrhenius critical number against the prediction FK(Θ)exp(1/Ar).", width=6.6)

HD("E. Proposition 5: continuous-flow reactor, bistability, and ignition–extinction hysteresis", 2)
P("The same fold has a hysteretic counterpart in a continuously fed reactor, as for any thermally coupled flow reactor [[vanheerden1953,grayscott1990]]. Let fresh resin of conversion 0 enter at the wall temperature with "
  "residence time τ_{res}, and let ϑ = τ_{th}/τ_{res} and D = k_{2}τ_{res}. In units of τ_{res} and in the exponential form,")
EQ(FRAC(V("dα"), Tt("dt′")) + EQS + V("D") + V("r") + MINUS + V("α") + Tt(",   ") + FRAC(V("dθ"), Tt("dt′")) + EQS + V("D") + V("r") + MINUS + V("θ") + DEL(Tt("1") + PLUS + FRAC(Tt("1"), Tt("ϑ"))) + Tt(",   ") + V("r") + EQS + DEL(V("ε") + PLUS + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + SUPN(Tt("e"), Tt("ψθ")) + Tt("."))
P("**Proposition 5.** The steady states satisfy θ = ϑα/(1 + ϑ) = κα/ψ and are given parametrically by")
EQ(V("D") + EQS + FRAC(V("α"), DEL(V("ε") + PLUS + V("α")) + SUPN(DEL(Tt("1") + MINUS + V("α")), V("n")) + Tt("exp") + DEL(V("κα"))) + Tt(",   ") + V("κ") + EQS + FRAC(Tt("ψϑ"), Tt("1") + PLUS + Tt("ϑ")) + Tt("."))
P("*Proof.* At steady state the conversion balance gives rD = α, and the heat balance gives θ(1 + 1/ϑ) = rD = α, so θ = ϑα/(1 + ϑ) = κα/ψ; substituting ψθ = κα into rD = α gives the expression. ∎ The curve D(α) is "
  "non-monotonic, so three steady states coexist in a window of D, if and only if d ln D/dα = 0 has two roots, i.e. n/(1 − α) + ε/[α(ε + α)] = κ has two roots. The left side has a single minimum, so the "
  "bistability threshold is κ_{c} = min_{α}[n/(1 − α) + ε/(α(ε + α))] (κ_{c} = %.3f for n = 3/2 and ε = 3 × 10^{−3}, slightly above n; as ε → 0, κ_{c} → n). At the two folds the system switches (saddle-node bifurcations), "
  "and an up-and-down sweep of D traces a hysteresis loop whose static area in the (ln D, α) plane is A_{0} = ∫(α_{upper} − α_{lower}) d ln D between the folds." % FL["kappa_c"])
P("*Verification.* We swept ln D up and down at rates v = 0.05, 0.02, 0.01 and 0.005 per residence time (ϑ = 1). For ψ = 20 (κ = %.0f > κ_{c}) the loop is wide: the switching values of ln D are %.2f (down) and %.2f (up) in the "
  "closed form and the integrated loop area decreases monotonically with v from %.2f to %.2f, extrapolating (linear in v from the two slowest sweeps) to %.2f against the static value %.2f. "
  "For ψ = 4.5 (κ = %.2f, just above κ_{c}) the static area is %.2f and the extrapolated area is %.2f; for ψ = 3 (κ = %.2f < κ_{c}) the static loop is absent and the extrapolated area is %.2f (@T:flow@). "
  "A finite-rate loop therefore exists below the threshold as well, and only its extrapolation to zero sweep rate distinguishes a static loop from a rate-dependent one. Close to the threshold the "
  "relaxation at the fold is slow (critical slowing down), so a linear extrapolation from sweeps no slower than 0.005 per residence time overestimates the area (@midx@ against @mids@ for ψ = 4.5); far above the threshold it is accurate to about @hierr@ %%." % (
      fl_hi["kappa"], fl_hi["lnD_down"], fl_hi["lnD_up"], fl_hi["sweeps"][0]["area"], fl_hi["sweeps"][-1]["area"], fl_hi["extrapolated_area"], fl_hi["static_area"],
      fl_mid["kappa"], fl_mid["static_area"], fl_mid["extrapolated_area"], fl_lo["kappa"], fl_lo["extrapolated_area"]))
rows = [["ψ", "κ", "Bistable", "Static area A_{0}", "Integrated area at v = 0.05", "at v = 0.005", "Extrapolated (v → 0)"]]
for c in FL["cases"]:
    rows.append(["%.1f" % c["psi"], "%.2f" % c["kappa"], "yes" if c["bistable"] else "no", "%.3f" % c["static_area"], "%.3f" % c["sweeps"][0]["area"], "%.3f" % c["sweeps"][-1]["area"], "%.3f" % c["extrapolated_area"]])
TAB(rows, "Hysteresis loop area in the (ln D, α) plane for the continuous-flow reactor (ϑ = 1, n = 3/2, ε = 3 × 10^{−3}, κ_{c} = %.3f)." % FL["kappa_c"], widths=[0.5, 0.6, 0.8, 1.2, 1.5, 1.0, 1.3], label="flow")
FIG("fig4_flow_reactor.png", "(a) Steady-state curve of the flow reactor with its two folds (κ = %.0f). (b) Ignition–extinction loops at two sweep rates against the steady states. (c) Loop area against sweep "
    "rate and the closed-form static area." % fl_hi["kappa"], width=6.6)

HD("F. Closed forms as fitting functions: a synthetic-data test", 2)
P("The storage curves depend on the capsule population only through the open fraction, i.e. through z = Δ/σ_{eff} at each storage temperature, so the pair (T_{m}, σ) is determined only through the "
  "line z(T_{s}) = (T_{m} − T_{s})/σ. To see how well it can be recovered, synthetic isothermal storage curves were generated with the *population ODE* (not with the closed form) for σ = %.1f °C and T_{m} = %.0f °C at "
  "three storage temperatures (%s °C) and five times (30–150 min), with Gaussian noise of %.3f in conversion, and fitted by least squares with the closed form (%d noise realizations). "
  "The estimates are σ̂ = %.1f ± %.1f °C and T̂_{m} = %.1f ± %.1f °C with a correlation of %.2f (Fig. 5): the two parameters are almost degenerate, only their combination is well constrained, "
  "and σ̂ is biased high along the degenerate direction. A calorimetric determination of T_{m} from the endotherm, with an uncertainty of 0.5 °C, is therefore necessary "
  "to use storage curves to measure σ." % (RC["true_sigma"], RC["true_Tm"], ", ".join("%.0f" % t for t in RC["temps"]), RC["noise"], RC["n_trials"], RC["sigma_mean"], RC["sigma_sd"], RC["Tm_mean"], RC["Tm_sd"], RC["corr"]))
RP = R.get("recovery_prior")
if RP:
    P("Constraining T_{m} to the true value with an uncertainty of %.1f °C (a prior of that width on the mean melting temperature) reduces the scatter of the recovered spread to σ̂ = %.1f ± %.1f °C." % (RP["Tm_prior_sd"], RP["sigma_mean"], RP["sigma_sd"]))
FIG("fig5_recovery.png", "Least-squares recovery of (T_{m}, σ) from noisy synthetic storage curves; each point is one noise realization (every fifth shown).", width=3.6)

# ================================================================== 4 status
HD("IV. Status of the claims and approximations")
rows = [["Result", "Status", "Assumption it rests on", "Where it fails or is untested"],
        ["Availability clock (Prop. 1)", "Exact", "Constant temperature; one availability function ⟨C⟩(t)", "Temperature transients and exotherm: delay becomes temperature dependent"],
        ["Isothermal time and sharpness (Prop. 2)", "Exact (quadrature); n = 1 closed form; sharpness law asymptotic", "m = 1; no diffusion control", "Sharpness law inaccurate for n ≠ 1; vitrification not modelled"],
        ["Storage conversion and σ^{*} (Prop. 3)", "Asymptotic (small conversion), verified to a few percent", "Gaussian spread; equal-mass independent capsules; probit approximation", "Large tolerance (ε ≳ 0.05); skewed or bimodal melting distributions; capsule–capsule heat exchange"],
        ["Critical number (Prop. 4)", "Asymptotic in Θ → 0 and Ar → ∞; verified numerically", "Exponential linearization at the fold; ungated bound", "Finite Θ shifts Π_{c} upward (computed, not closed-form); spatial gradients absent"],
        ["Arrhenius factor exp(1/Ar)", "First-order correction, verified", "Fold at x = 1/Ar", "Small Ar; higher-order terms"],
        ["Flow-reactor bistability (Prop. 5)", "Exact for the stated model", "Perfect mixing; exponential form; ungated", "Real reactors: finite mixing time, wall–fluid temperature difference"],
        ["Parameter recovery (III F)", "Numerical experiment", "Gaussian noise; population ODE as truth", "Not a test on real calorimetry"]]
TAB(rows, "Status of the principal results, their assumptions, and where they fail or have not been tested. All parameters are illustrative.", widths=[1.6, 1.4, 1.9, 1.9], size=8, label="status")
P("Three approximations carry the paper: the lumped, well-mixed energy balance; the exponential linearization of the Arrhenius law at the fold; and the Gaussian, independent-capsule description of the "
  "population. The first is a deliberate scope limit and the second is quantified (Table 5); the third is tested only against the population equations that use the same description.")

# ================================================================== 5 signatures
HD("V. Falsifiable signatures")
P("Each proposition predicts a measurement that a standard calorimetric or rheological experiment can make, none of which has been made here. (1) *Constant delay.* Isothermal DSC at several temperatures "
  "above the melting endotherm, comparing the gated resin with the same resin with the catalyst dissolved, should show a delay that is independent of the conversion level and equal to τ_{rel}(T) "
  "(Proposition 1); a delay that depends on α falsifies the single-availability-function description. (2) *Storage design rule.* The melting endotherm gives T_{m} and σ; isothermal storage at a margin Δ for a "
  "time t should then give a conversion within a few tens of percent of Proposition 3, and a conversion that is systematically larger would indicate a tail of capsules with low melting temperature that the Gaussian "
  "description misses. (3) *Critical thermal time constant.* At fixed T_{∞}, specimens of increasing thickness (τ_{th} grows as thickness squared) should show an abrupt rise of the overshoot "
  "at τ_{th} = Π_{c}/(ψ k_{2}) (Proposition 4); the abruptness, from O(Θ) to O(ΔT_{ad}), is the signature of the fold. (4) *Static hysteresis.* In a flow reactor, the loop of conversion against flow rate "
  "(or against temperature at fixed flow) should persist after extrapolation of its area to zero sweep rate when κ > κ_{c}, and should vanish after extrapolation when κ < κ_{c}; a loop that closes as the sweep slows "
  "is rate-dependent and not bistability.")

# ================================================================== 6 open problems
HD("VI. Open problems")
P("(a) *Spatial extension.* The lumped balance replaces the classical slab, cylinder or sphere. The critical Frank-Kamenetskii parameter of a consuming, autocatalytic source in a spatially resolved specimen, and its "
  "relation to Π_{c} above, are open. (b) *Finite-Θ correction.* The upward shift of Π_{c} with Θ is computed numerically; a closed-form first correction would complete Proposition 4. (c) *Non-Gaussian "
  "populations.* Proposition 3 needs only the lower tail of the melting-temperature distribution; skewed and bimodal distributions, and capsule–capsule heat exchange, are untested. (d) *Diffusion control and vitrification.* "
  "These stop the cure before completion and change the late-time tail of Proposition 2. (e) *Noise.* In small specimens or flow channels the fold may be crossed by fluctuations; the first-passage statistics "
  "are unexplored. (f) *Experiment.* The propositions are untested on a real encapsulated system; the signatures of Section V are the proposed tests.")

# ================================================================== 7 conclusion
HD("VII. Conclusion")
P("A melt-gated autocatalytic cure with exothermic feedback is, in the lumped limit, far more solvable than its numerical treatment suggests. The gate acts as a clock shift (Proposition 1), the "
  "isothermal cure is exact by quadrature and its sharpness is logarithmic in the rate-constant ratio (Proposition 2), the storage stability of a capsule population reduces to a Gaussian tail "
  "and a one-dimensional integral that inverts into a design rule (Proposition 3), thermal runaway is a fold with the closed-form critical number e⁻¹(1+n)^{1+n}/n^{n} and an Arrhenius correction exp(1/Ar) "
  "(Proposition 4), and the continuous-flow reactor adds an ignition–extinction hysteresis with a computable existence threshold (Proposition 5). All results are tested against the full equations; none "
  "is tested against experiment, and the parameters are illustrative.")

HD("Declarations")
P("**Funding.** The author received no funding for this work.")
P("**Competing interests.** The author declares no competing interests.")
P("**Author contributions.** Leon Sandler: conceptualization, methodology, software, formal analysis, investigation, writing – original draft, writing – review and editing, visualization.")
P("**Use of artificial intelligence.** A large language model (Claude, Anthropic) assisted with derivations, code, figures and drafting. The author reviewed and edited the content, checked every "
  "closed-form result against the numerical model, resolved every journal reference through Crossref, and takes full responsibility for the paper. No such tool is an author, and none was used to generate or alter data.")
P("**Data and code availability.** The model code, the closed-form module, the tests, the figure scripts, the results file and the manuscript builder are available at %s and archived on Zenodo "
  "at https://doi.org/%s; this manuscript is archived as a preprint at https://doi.org/%s." % (REPO, SW_DOI, PP_DOI))

HD("Appendix A. Numerical protocol and run table")
P("The reference model integrates Eqs. (1)–(3) for all scenarios at once with a vectorized fixed-step fourth-order Runge–Kutta scheme (step 0.01–0.05 min; reaction heat is set to zero once α ≥ 0.999 so that "
  "energy is conserved). Capsule populations use K = 801 deterministic Gaussian quantiles of the melting temperature. The thermal-feedback and flow-reactor problems are integrated with an adaptive stiff "
  "solver (LSODA, relative tolerance 10^{−8}–10^{−9}). Thresholds are bisected to the stated tolerance. Nothing is stochastic except the synthetic-noise test (seed 20261007; 200 realizations).")
rows = [["Study", "Method", "Grid", "Compared with"],
        ["Availability clock", "RK4, constant T, step 0.01 min", "T = 125, 140, 155 °C; α = 0.1, 0.5, 0.9", "Closed form"],
        ["Isothermal cure", "RK4, step 0.01 min", "T = 110–155 °C; n = 1, 1.5", "Quadrature; n = 1 closed form; law"],
        ["Storage conversion", "RK4 population (K = 801), step 0.05 min", "Δ = 3, 6, 10 °C; σ = 2–10 °C; t = 150 min", "Closed form"],
        ["Design rule", "Root-finding on the population ODE", "Δ = 3, 6, 10 °C; ε = 0.001, 0.01, 0.05", "Closed form"],
        ["Criticality (exponential form)", "LSODA, bisection (30 steps)", "n = 1, 1.5, 2; Θ = 0.1–0.003", "e⁻¹(1+n)^{1+n}/n^{n}"],
        ["Criticality (Arrhenius)", "LSODA, bisection (26 steps)", "T = 120, 140, 160 °C; Θ = 0.01–0.1", "FK(Θ) exp(1/Ar)"],
        ["Flow reactor", "LSODA sweeps", "ψ = 3, 4.5, 20; v = 0.05–0.005", "Static loop area"],
        ["Parameter recovery", "Least squares, 200 noise draws", "3 temperatures × 5 times", "Truth"]]
TAB(rows, "Run table of the numerical studies; every result is reproduced by code/run_all.py.", widths=[1.5, 2.0, 2.0, 1.4], size=8, label="runs")

HD("References")
for k in CITE:
    q = doc.add_paragraph()
    H.add_rich(q, "[%d] %s" % (CITE.index(k) + 1, REFS[k]["entry"]), size=10)
    q.paragraph_format.space_after = H.Pt(3)

doc.core_properties.author = "Leon Sandler"
doc.core_properties.title = TITLE
outp = os.path.join(OUT, "Gated_Autocatalysis_Criticality_JCP%s.docx" % ("_noLineNumbers" if NOLN else ""))
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
