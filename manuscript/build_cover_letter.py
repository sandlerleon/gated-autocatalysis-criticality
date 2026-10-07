# -*- coding: utf-8 -*-
"""Cover letter for The Journal of Chemical Physics (Regular Article).   python build_cover_letter.py -> out/Cover_Letter_JCP.docx"""
import json
import os
import sys

from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docx_helpers as H  # noqa: E402

ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_gac_zenodo_state.json")))
SW, PP = ZEN["software"]["doi"], ZEN["publication"]["doi"]
R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
REPO = "https://github.com/sandlerleon/gated-autocatalysis-criticality"
TITLE = "Closed-Form Storage Stability, Induction Delay, and Thermal-Feedback Criticality of Melt-Gated Autocatalytic Cure"
doc = H.new_document(size=11, line=1.15)


def para(text, bold=False, after=6):
    p = doc.add_paragraph()
    if bold:
        p.add_run(text).bold = True
    else:
        H.add_rich(p, text)
    p.paragraph_format.space_after = Pt(after)
    return p


for line in ("Leon Sandler", "Independent researcher, Northbrook, Illinois, USA", "sandler.leon@gmail.com", "ORCID: https://orcid.org/0009-0007-4584-808X"):
    para(line, after=0)
para("")
para("6 October 2026")
para("The Editors\nThe Journal of Chemical Physics", after=10)
para("Submission of a Regular Article: “%s”" % TITLE, bold=True, after=10)
para("Dear Editors,")
para("I submit the enclosed theoretical paper for consideration in The Journal of Chemical Physics, in the section on Polymers and Soft Matter (the Theoretical Methods and Algorithms section "
     "would also be appropriate). It treats a problem of reaction dynamics: a cure that is triggered by the melting of an encapsulated catalyst, with a distribution of capsule melting "
     "temperatures, autocatalytic kinetics and exothermic feedback on the temperature. The central result is that this lumped model is largely solvable in closed form.")
para("What the paper establishes", bold=True, after=3)
for t in ("At constant temperature the gated cure is exactly the isothermal cure evaluated on the clock of integrated catalyst availability, so the gate delays every conversion level by "
          "essentially the release time constant (Proposition 1).",
          "The isothermal cure time is exact by one quadrature for any reaction order and in closed form for first order; sharpness obeys a logarithmic law in the rate-constant ratio (Proposition 2).",
          "The storage conversion of a Gaussian capsule population has a closed form in the open fraction Φ(−Δ/σ_eff), and inverts into a design rule for the largest admissible spread of melting "
          "temperatures that agrees with the population equations within %.0f %% (Proposition 3)." % (100 * max(abs(r["sigma_star_analytic"] / r["sigma_star_numeric"] - 1) for r in R["design_rule"] if r["sigma_star_numeric"] and r["sigma_star_analytic"] and r["sigma_star_analytic"] < 40)),
          "Thermal feedback has a critical number Π_c = ψΘ = e⁻¹(1+n)^(1+n)/n^n at a fold of the quasi-steady manifold, with overshoot given by the Lambert W function, a square-root normal form, "
          "and an Arrhenius correction exp(1/Ar) (Proposition 4).",
          "In a continuous-flow reactor the same fold gives an ignition–extinction hysteresis with a computed existence threshold, and the loop area extrapolates to the static value as the sweep "
          "rate vanishes (Proposition 5)."):
    p = doc.add_paragraph(style="List Bullet")
    H.add_rich(p, t)
    p.paragraph_format.space_after = Pt(3)
para("Every result is tested against the full equations. The paper also states the status and failure modes of each claim, and its falsifiable signatures.", after=6)
para("Scope and honesty about it", bold=True, after=3)
para("The paper is purely theoretical and no experimental data are used; all parameters are illustrative and are not fitted to any material. I have tried to state this plainly throughout, "
     "including in a table of the status of every claim. The parameter set and the capsule-population picture were introduced in a numerical study that I posted as a preprint "
     "(ChemRxiv 10.26434/chemrxiv.15008366; Zenodo 10.5281/zenodo.22073390); the analytic results here are new, and the comparisons of that study are not used. "
     "That preprint is cited in the manuscript.")
para("Data, code and disclosures", bold=True, after=3)
para("All code, tests and figure scripts are public at %s and archived at https://doi.org/%s; the manuscript is available as a preprint at https://doi.org/%s. A large language model (Claude, Anthropic) "
     "assisted with derivations, code, figures and drafting; I reviewed and verified the content, checked every closed-form result against the numerical model, resolved every journal reference "
     "through Crossref, and take full responsibility, as stated in the manuscript. I am the sole author, have no competing interests and received no funding. The manuscript is not under "
     "consideration elsewhere." % (REPO, SW, PP))
para("Thank you for considering the paper.")
para("Yours sincerely,", after=18)
para("Leon Sandler")
out = os.path.join(HERE, "out", "Cover_Letter_JCP.docx")
doc.save(out)
print("saved", out)
