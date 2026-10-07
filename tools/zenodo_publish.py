# -*- coding: utf-8 -*-
"""Publish the two Zenodo records reserved by zenodo_reserve.py:

  software     the tagged GitHub release as a zip (MIT)
  preprint     the manuscript (docx and pdf) (CC BY 4.0)

The DOIs were reserved first so that they could be written into the manuscript. The token is read from ZENODO_TOKEN and never written to disk.

    python zenodo_publish.py software|preprint [--version=1.0.0] [--ms=1] [--dry]
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("ZENODO_TOKEN")
if not TOKEN:
    raise SystemExit("ZENODO_TOKEN is not set in the environment")
API = "https://zenodo.org/api"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STATE = os.path.join("C:" + os.sep, "YouTube", "_gac_zenodo_state.json")
VERSION = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--version=")), "1.0.0")
MS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--ms=")), "1")
TAG = "v" + VERSION
DRY = "--dry" in sys.argv
GITHUB = "https://github.com/sandlerleon/gated-autocatalysis-criticality"
CREATORS = [{"name": "Sandler, Leon", "affiliation": "Independent Researcher", "orcid": "0009-0007-4584-808X"}]
TITLE_PAPER = "Closed-Form Storage Stability, Induction Delay, and Thermal-Feedback Criticality of Melt-Gated Autocatalytic Cure"
TITLE_CODE = "Gated autocatalytic cure: closed-form theory, reference model, tests, figures and manuscript"
KEYWORDS = ["autocatalytic cure kinetics", "thermal runaway", "encapsulated catalyst", "Lambert W function", "saddle-node bifurcation", "hysteresis",
            "Kamal-Sourour kinetics", "Semenov criticality", "design rule", "theory"]

ABOUT = """<p><strong>A theoretical paper. No experimental data are used and all parameters are illustrative.</strong> Prepared for submission to <em>The Journal of Chemical Physics</em>.
For a cure triggered by the melting of an encapsulated catalyst (distribution of capsule melting temperatures, Kamal-Sourour autocatalytic kinetics, exothermic feedback), the lumped model
is largely solvable in closed form: the gated cure is the isothermal cure on the clock of integrated catalyst availability; the isothermal cure time is exact by quadrature and its sharpness
is logarithmic in the rate-constant ratio; the storage conversion of a Gaussian capsule population gives a closed-form design rule for the admissible melting-temperature spread; thermal
feedback has a critical number e^-1 (1+n)^(1+n)/n^n with Lambert-W overshoot and an Arrhenius correction exp(1/Ar); and a continuous-flow reactor shows ignition-extinction hysteresis
whose static loop area is the zero-sweep-rate limit of the dynamic loops. Every result is tested against the full equations. The parameter set and capsule-population picture come from an earlier
numerical preprint of the author (doi 10.5281/zenodo.22073390).</p>"""
DESC_CODE = ABOUT + """<p>Contents: closed forms (<code>code/theory.py</code>), reference model and numerics, tests, the script that produces every result table, figure scripts, the
reference harvest (Crossref), the manuscript builder. Manuscript preprint: <a href="https://doi.org/{PP}">{PP}</a>.</p>"""
DESC_PAPER = ABOUT + """<p>Code and results: <a href="%s">%s</a>, archived at <a href="https://doi.org/{SW}">{SW}</a>.</p>""" % (GITHUB, GITHUB)


def clear_inherited(d):
    for f in req("GET", "%s/deposit/depositions/%s/files" % (API, d["id"])):
        req("DELETE", "%s/deposit/depositions/%s/files/%s" % (API, d["id"], f["id"]))


def req(method, url, data=None, headers=None, raw=None):
    h = {"Authorization": "Bearer " + TOKEN}
    if headers:
        h.update(headers)
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    if data is not None and raw is None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            t = resp.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise SystemExit("%s %s -> %s\n%s" % (method, url, e.code, e.read().decode()[:800]))


def upload(bucket, path, name):
    with open(path, "rb") as fh:
        req("PUT", "%s/%s" % (bucket, urllib.parse.quote(name)), raw=fh.read(), headers={"Content-Type": "application/octet-stream"})
    print("   uploaded %-62s %9.1f kB" % (name, os.path.getsize(path) / 1024.0))


def finish(did, meta):
    req("PUT", "%s/deposit/depositions/%s" % (API, did), data={"metadata": meta})
    print("   metadata written")
    if DRY:
        print("   DRY RUN - draft %s left unpublished" % did)
        return
    pub = req("POST", "%s/deposit/depositions/%s/actions/publish" % (API, did))
    rec = req("GET", "%s/records/%s" % (API, pub["id"]))
    print("   PUBLISHED  DOI %s  concept %s" % (rec.get("doi"), rec.get("conceptdoi")))


def software():
    st = json.load(open(STATE))
    d = st["software_" + VERSION] if "software_" + VERSION in st else st["software"]
    tmp = os.path.join(os.environ.get("TEMP", "."), "gated-autocatalysis-criticality-%s.zip" % VERSION)
    subprocess.check_call(["git", "-C", REPO, "archive", "--format=zip", "--prefix=gated-autocatalysis-criticality-%s/" % VERSION, "-o", tmp, TAG])
    print("=== software draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    clear_inherited(d)
    upload(d["bucket"], tmp, os.path.basename(tmp))
    meta = {"title": TITLE_CODE, "upload_type": "software", "description": DESC_CODE.replace("{PP}", st.get("publication_v" + MS, st["publication"])["doi"]),
            "creators": CREATORS, "keywords": KEYWORDS, "access_right": "open", "license": "mit-license", "version": VERSION, "language": "eng",
            "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": GITHUB + "/tree/" + TAG, "relation": "isSupplementTo", "scheme": "url"},
                                    {"identifier": st.get("publication_v" + MS, st["publication"])["doi"], "relation": "isSupplementTo", "scheme": "doi"}]}
    finish(d["id"], meta)


def preprint():
    st = json.load(open(STATE))
    d = st["publication_v" + MS] if "publication_v" + MS in st else st["publication"]
    print("=== preprint draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    clear_inherited(d)
    for name in ("Gated_Autocatalysis_Criticality_JCP.docx", "Gated_Autocatalysis_Criticality_JCP.pdf"):
        upload(d["bucket"], os.path.join(REPO, "manuscript", name), name)
    meta = {"title": TITLE_PAPER, "upload_type": "publication", "publication_type": "preprint",
            "description": DESC_PAPER.replace("{SW}", st.get("software_" + VERSION, st["software"])["doi"]), "creators": CREATORS, "keywords": KEYWORDS, "access_right": "open",
            "license": "cc-by-4.0", "version": MS, "language": "eng", "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": st.get("software_" + VERSION, st["software"])["doi"], "relation": "isSupplementedBy", "scheme": "doi"},
                                    {"identifier": GITHUB, "relation": "isSupplementedBy", "scheme": "url"}]}
    finish(d["id"], meta)


if __name__ == "__main__":
    what = [a for a in sys.argv[1:] if not a.startswith("--")]
    if what == ["software"]:
        software()
    elif what == ["preprint"]:
        preprint()
    else:
        raise SystemExit("usage: zenodo_publish.py software|preprint [--version=] [--ms=] [--dry]")
