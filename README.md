# Closed-form storage stability, induction delay and thermal-feedback criticality of melt-gated autocatalytic cure

**Author:** Leon Sandler, Independent Researcher (ORCID [0009-0007-4584-808X](https://orcid.org/0009-0007-4584-808X))
**Target journal:** The Journal of Chemical Physics (Regular Article; Polymers and Soft Matter / Theoretical Methods and Algorithms)
**Article type:** theory. All parameters are illustrative; nothing is fitted to experiment.

A cure reaction triggered by the melting of an encapsulated catalyst combines a distribution of capsule melting temperatures, autocatalytic (Kamal-Sourour) kinetics and exothermic feedback.
This repository derives what can be written in closed form for the lumped model and tests every result against the full equations.

| | Result | Verified against the full model |
|---|---|---|
| Prop. 1 | At constant T the gated cure is the isothermal cure on the clock of integrated availability: every conversion level is delayed by the release time constant | relative error about 1e-8 |
| Prop. 2 | Isothermal time exact by quadrature (closed form for n = 1); sharpness S ≈ 2 ln 9 / ln(k2/9k1) | quadrature exact; law within 5 % |
| Prop. 3 | Storage conversion of a Gaussian capsule population, f = Φ(−Δ/σ_eff); closed-form design rule for the largest admissible spread σ* | within a few % of the population ODE |
| Prop. 4 | Critical thermal-feedback number Π_c = ψΘ = e⁻¹(1+n)^(1+n)/n^n (1.98 for n = 3/2), Lambert-W overshoot, fold normal form, Arrhenius factor exp(1/Ar) | bisected integrations, 0.5 % as Θ → 0 |
| Prop. 5 | Continuous-flow reactor: bistability threshold κ_c, S-curve, static hysteresis-loop area, extrapolation to zero sweep rate | loop areas converge to the static value |

## Layout

```
code/theory.py          the closed forms (pure functions)
code/core.py            reference model: vectorised RK4 of the T-C-alpha system with a capsule population
code/numerics.py        adaptive stiff integrations for the criticality and flow-reactor results
code/run_all.py         every result table -> results.json (about 5 minutes)
code/figures.py         Figures 1-5
code/test_theory.py     17 fast checks of the closed forms against the numerics
refs/build_refs.py      every journal reference harvested from Crossref
manuscript/             builder (reads results.json) and the manuscript
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

Software: see the Zenodo record linked from the release. Manuscript preprint: see the Zenodo record linked from the release. MIT licence (code); CC BY 4.0 (manuscript).
