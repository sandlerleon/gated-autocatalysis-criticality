# -*- coding: utf-8 -*-
"""Harvest the bibliographic records of every cited journal article from Crossref (nothing is typed by hand for these) and write
refs/refs_cache.json and refs/ref_keys.json. Patents, regulatory guidelines and web pages are listed by hand in MANUAL.

    python build_refs.py
"""
import html
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DOIS = {
    "kamal1973": "10.1002/pen.760130110", "sourour1976": "10.1016/0040-6031(76)80056-1", "corless1996": "10.1007/BF02124750",
    "saltelli2010": "10.1016/j.cpc.2009.09.018", "vyazovkin2011": "10.1016/j.tca.2011.03.034", "white2001": "10.1038/35057232",
    "jamekhorshid2014": "10.1016/j.rser.2013.12.033", "bogetti1992": "10.1177/002199839202600502", "semenov1928": "10.1007/bf01340021",
    "vanheerden1953": "10.1021/ie50522a030", "zhao2019": "10.3390/polym11111797",
    "ozawa1965": "10.1246/bcsj.38.1881", "adler1964": "10.1016/0010-2180(64)90035-5", "kassoy1980": "10.1137/0139035", "aris1958": "10.1016/0009-2509(58)80019-6",
    "uppal1974": "10.1016/0009-2509(74)80089-8", "siepmann2012": "10.1016/j.jconrel.2011.10.006",
}
MANUAL = {
    "frankkamenetskii1969": "Frank-Kamenetskii DA. Diffusion and Heat Transfer in Chemical Kinetics, 2nd ed. New York: Plenum Press; 1969.",
    "grayscott1990": "Gray P, Scott SK. Chemical Oscillations and Instabilities: Non-linear Chemical Kinetics. Oxford: Clarendon Press; 1990.",
    "strogatz2015": "Strogatz SH. Nonlinear Dynamics and Chaos, 2nd ed. Boulder: Westview Press; 2015.",
    "sandler2026": "Sandler L. Coupled thermal activation and autocatalytic cure kinetics: a theoretical and computational study of delayed reactive transformation. "
                   "ChemRxiv 2026. https://doi.org/10.26434/chemrxiv.15008366/v1; archived at https://doi.org/10.5281/zenodo.22073390",
}


def fetch(doi):
    req = urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "refbuild (mailto:sandler.leon@gmail.com)"})
    return json.load(urllib.request.urlopen(req, timeout=60))["message"]


def initials(given):
    parts = re.split(r"[\s\-.]+", given.strip())
    return "".join(p[0] for p in parts if p)


def fmt(m, doi):
    au = m.get("author", [])
    names = ["%s %s" % (a.get("family", ""), initials(a.get("given", ""))) for a in au if a.get("family")]
    names = names if len(names) <= 6 else names[:6] + ["et al"]
    title = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m["title"][0]))).strip().rstrip(".")
    j = (m.get("short-container-title") or m.get("container-title") or [""])[0]
    j = html.unescape(html.unescape(j)).replace(".", "").replace("  ", " ").strip()
    year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
    vol, page = m.get("volume"), m.get("page")
    tail = "%s %s" % (j, year)
    if vol:
        tail = "%s. %s;%s" % (j, year, vol) + (":%s" % page.replace("-", "–") if page else "")
    else:
        tail = "%s. %s" % (j, year)
    return "%s. %s. %s. https://doi.org/%s" % (", ".join(names), title, tail, doi)


def main():
    cache = {}
    for k, d in DOIS.items():
        try:
            m = fetch(d)
        except Exception as e:
            print("FAILED", k, d, e)
            continue
        cache[k] = {"doi": d, "entry": fmt(m, d), "title": m["title"][0], "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0]}
        print(k, "->", cache[k]["entry"][:140])
    for k, v in MANUAL.items():
        cache[k] = {"doi": None, "entry": v}
    json.dump(cache, open(os.path.join(HERE, "refs_cache.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    json.dump(sorted(cache), open(os.path.join(HERE, "ref_keys.json"), "w", encoding="utf-8"), indent=1)
    print(len(cache), "entries")


if __name__ == "__main__":
    main()
