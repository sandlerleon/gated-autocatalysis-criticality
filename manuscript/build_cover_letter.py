# -*- coding: utf-8 -*-
"""Cover letter for The Journal of Chemical Physics (Regular Article), revised after the scientific corrections.   python build_cover_letter.py -> out/Cover_Letter_JCP.docx"""
import json
import os
import sys

from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docx_helpers as H  # noqa: E402

ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_gac_zenodo_state.json")))
SW, PP = (ZEN.get("software_1.1.0") or ZEN["software"])["doi"], (ZEN.get("publication_v2") or ZEN["publication"])["doi"]
R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
REPO = "https://github.com/sandlerleon/gated-autocatalysis-criticality"
TITLE = "Closed-Form Storage Stability, Induction Delay, and Thermal-Feedback Criticality of Melt-Gated Autocatalytic Cure"
dr = [r for r in R["design_rule"] if r["sigma_star_ode"] and r["sigma_star_closed"] and r["sigma_star_closed"] < 40]
dev = max(abs(r["sigma_star_closed"] / r["sigma_star_ode"] - 1) for r in dr)
case20 = [c for c in R["flow"]["cases"] if c["psi"] == 20.0][0]
doc = H.new_document(size=11, line=1.15)


def para(text, bold=False, after=6):
    p = doc.add_paragraph()
    if bold:
        p.add_run(text).bold = True
    else:
        H.add_rich(p, text)
    p.paragraph_format.space_after = Pt(after)
    return p


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    H.add_rich(p, text)
    p.paragraph_format.space_after = Pt(3)


for line in ("Leon Sandler", "Independent researcher, Northbrook, Illinois, USA", "sandler.leon@gmail.com", "ORCID: https://orcid.org/0009-0007-4584-808X"):
    para(line, after=0)
para("")
para("7 October 2026")
para("The Editors\nThe Journal of Chemical Physics", after=10)
para("Submission of a Regular Article: “%s”" % TITLE, bold=True, after=10)
para("Dear Editors,")
para("I submit the enclosed theoretical paper for consideration in The Journal of Chemical Physics, in the section on Polymers and Soft Matter (Theoretical Methods and Algorithms would also be appropriate). "
     "It concerns the reaction dynamics of a cure triggered by the melting of an encapsulated catalyst, with a distribution of capsule melting temperatures, autocatalytic kinetics and exothermic feedback. "
     "The paper is purely theoretical: no experimental data are used and all parameters are illustrative.")
para("What is new, and what is not", bold=True, after=3)
para("Several ingredients are standard, and the paper says so: separable cure kinetics with a generalized time, the Semenov and Frank-Kamenetskii fold, its extension to reactant consumption, and the "
     "multiplicity and stability analysis of continuous stirred reactors. The new content is their assembly for a melt-gated autocatalytic cure, with results of three different kinds that the manuscript "
     "keeps apart:", after=3)
bullet("*Exact results.* At constant temperature the gated cure is the isothermal cure on the clock of integrated catalyst availability; for a fully activated population the delay is "
       "τ_{rel}[1 − exp(−t/τ_{rel})], which depends on conversion and approaches the release time constant only at late conversion. The isothermal cure time is exact by quadrature. The steady states of the flow reactor and the Jacobian are exact for the stated model.")
bullet("*Closed forms with stated approximations.* The storage conversion of a Gaussian capsule population, (a/b)[exp(b f t_{eff}) − 1] with f = Φ(−Δ/σ_{eff}), and the bound on the melting-temperature spread that "
       "follows from it (agreement with the full population equations within %.0f %% over the tested grid). The frozen-conversion critical number (1+n)^{1+n}/[e n^{n}(1+ε)^{1+n}] of the thermal balance, with an Arrhenius correction that agrees with integrations "
       "to a few percent over the tested range." % (100 * dev))
bullet("*Numerical evidence.* Operational ignition thresholds from integrations; the window of two stable states of the flow reactor, whose upper branch can lose stability at a Hopf-type point before its fold "
       "(ψ = 20: the stable window starts at ln D = %.2f rather than at the fold, and finite-rate sweep loops approach the attractor loop area %.2f slowly). The manuscript states where each result has been tested and where it has not." % (
           case20["window"]["lnD_ext"], case20["attractor_area"]))
para("Chemical-physics significance", bold=True, after=3)
para("For encapsulated-catalyst and latent-cure systems, the quantities a calorimeter measures (rate constants, the width of the melting endotherm, a thermal time constant) enter the storage, delay and "
     "runaway behavior through a small number of closed-form relations, and the manuscript states them with their domains of validity and the signatures that would test them. Whether these model reductions "
     "constitute a sufficient advance for the Journal is for the Editors to judge; I have tried to make the claims no stronger than the checks that support them.")
para("Relation to an earlier preprint", bold=True, after=3)
para("The parameter set (rate constants and orders, release rate constant, logistic activation and mean melting temperature, adiabatic rise), the capsule-population picture and the reference integrator "
     "come from a numerical study that I posted as a preprint (ChemRxiv 10.26434/chemrxiv.15008366; Zenodo 10.5281/zenodo.22073390) and cite. The closed forms, the stability analysis and the "
     "verification here are new; the control-family comparisons of that preprint are not used.")
para("Data, code and disclosures", bold=True, after=3)
para("All code, tests, raw result tables and figure scripts are public at %s (release v1.1.0) and archived at https://doi.org/%s; the manuscript is available as a preprint at https://doi.org/%s. "
     "The manuscript describes in Section II C the use of Claude Sonnet 5.5 (Anthropic), used through the Claude Code command-line environment, for derivations, code, figures and drafting, and states that every number "
     "is produced by the released scripts. I am the sole author, have no competing interests and received no funding. The manuscript is not under consideration elsewhere." % (REPO, SW, PP))
para("Thank you for considering the paper.")
para("Yours sincerely,", after=18)
para("Leon Sandler")
out = os.path.join(HERE, "out", "Cover_Letter_JCP.docx")
doc.save(out)
print("saved", out)
