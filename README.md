# Closed-form storage stability, induction delay and thermal-feedback criticality of melt-gated autocatalytic cure

**Author:** Leon Sandler, Independent Researcher (ORCID [0009-0007-4584-808X](https://orcid.org/0009-0007-4584-808X))
**Target journal:** Reaction Kinetics, Mechanisms and Catalysis (Springer; original article)
**Article type:** theory. All parameters are illustrative; nothing is fitted to experiment.

A cure reaction triggered by the melting of an encapsulated catalyst combines a distribution of capsule melting temperatures, autocatalytic (Kamal-Sourour) kinetics and exothermic feedback.
This repository derives what can be written in closed form for the lumped model and tests every result against the full equations.

| | Result | Verified against the full model |
|---|---|---|
| Prop. 1 | At constant T the gated cure is the isothermal cure on the clock of integrated availability; the delay of a fully open population is tau_rel[1 - exp(-t/tau_rel)] (conversion dependent) | relative error below 1e-6 |
| Prop. 2 | Isothermal time exact by quadrature (closed form for n = 1); exact n = 1 sharpness and its asymptotic law | quadrature exact; law within 5 % (n = 1 only) |
| Prop. 3 | Storage conversion (a/b)[exp(b f t_eff) - 1], f = Φ(−Δ/σ_eff); exact inversion for the largest admissible spread σ* (domain 0 < f* < 1/2) | within 3 % of the population ODE |
| Prop. 4 | Frozen-conversion critical number Π_c = (1+n)^(1+n) / [e n^n (1+ε)^(1+n)], Lambert-W overshoot, Arrhenius factor (frozen-fold factor; exp(1/Ar) first order) | operational thresholds, 0.4–0.6 % as Θ → 0; Arrhenius grid within 5 % |
| Prop. 5 | Continuous-flow reactor: equilibrium multiplicity (κ_c), Jacobian, stable window (the upper branch can lose stability at a Hopf-type point before its fold), attractor loop area | attractor scans; sweep areas converge slowly (sublinear) |

## Layout

```
code/theory.py          the closed forms (pure functions)
code/core.py            reference model: vectorised RK4 of the T-C-alpha system with a capsule population
code/numerics.py        adaptive stiff integrations for the criticality and flow-reactor results
code/run_all.py         every result table -> results.json (about 6 minutes)
code/figures.py         Figures 1-6 (PNG and EPS, Springer style; Figure 5 Arrhenius temperature path and noise dependence of the exit)
code/test_theory.py     41 checks of the closed forms, the stability analysis and the temperature path against the numerics (about 2 minutes)
refs/build_refs.py      every journal reference harvested from Crossref
manuscript/             builders (read results.json), the manuscript and cover letter (docx only; no PDFs are kept in the repository), Rubriq merge tools
tools/                  Zenodo reservation/publication scripts (token from ZENODO_TOKEN, never stored)
```

## Reproducing

```bash
pip install -r requirements.txt
python code/test_theory.py
python code/run_all.py
python code/figures.py
cd manuscript && python build_manuscript.py && python build_manuscript.py
```

## Relation to earlier work

The illustrative parameter set and the capsule-population picture come from a numerical study by the author
(Sandler, ChemRxiv 2026, [10.26434/chemrxiv.15008366](https://doi.org/10.26434/chemrxiv.15008366/v1); Zenodo [10.5281/zenodo.22073390](https://doi.org/10.5281/zenodo.22073390)).
The analytic results here are new.

## What is not claimed

No experiment was performed or fitted. The model is lumped, ignores diffusion control and vitrification, and treats the capsule population as independent, equal-mass and Gaussian.

## Citation

Software: [10.5281/zenodo.23201763](https://doi.org/10.5281/zenodo.23201763) (concept DOI 10.5281/zenodo.23201762). Manuscript preprint: [10.5281/zenodo.23201767](https://doi.org/10.5281/zenodo.23201767) (concept DOI 10.5281/zenodo.23201766). MIT licence (code); CC BY 4.0 (manuscript).

## v1.3.0

Retargeted to *Reaction Kinetics, Mechanisms and Catalysis*: Springer numbering and declarations, 244-word abstract and highlights, Springer reference style, restyled figures (no in-figure titles), new Section 1.1 on the relation to the author's earlier AutoLatch preprint and journal submission, selective merge of a Rubriq language edit (`manuscript/merge_rubriq*.py`). The numerical results are unchanged from v1.2.0 (`results.json` identical).

## v1.3.1

Storage-conversion and design-rule comparisons recomputed with K = 3201 capsule quantiles (K = 801 left a 1 % discretization error at sigma = 2 C; convergence now against K = 6401); the storage inversion is described as exact only within the Gaussian-logistic small-conversion model; Propositions 4 and 5 are stated as derived for a fully released (ungated) catalyst in abstract, conclusion and open problems; duplicated 'Table Table' references fixed. Other results are identical to v1.3.0.
