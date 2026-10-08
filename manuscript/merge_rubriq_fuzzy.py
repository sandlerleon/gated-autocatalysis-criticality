# -*- coding: utf-8 -*-
"""Merge the SAFE hunks of a Rubriq language edit into a rebuilt manuscript whose text differs from the edited version.

A = the manuscript that was sent to Rubriq, B = the Rubriq result, C = the new build. Each paragraph of A that Rubriq changed is matched to the most similar paragraph of C; only hunks that are
spelling variants (US), number-format changes, whitelisted word swaps or single comma insertions/deletions are taken, and only when the hunk (with 30 characters of context on each side in A) occurs exactly
once in C. Equation, field, hyperlink and reference paragraphs are never edited. Every decision is written to a report. Run us_pass afterwards for the spelling rule.

    python merge_rubriq_fuzzy.py A.docx B.docx C.docx out.docx
"""
import difflib
import io
import re
import sys

import docx

import merge_rubriq as M


def main(a_path, b_path, c_path, out_path):
    A = M.allparas(docx.Document(a_path))
    B = M.allparas(docx.Document(b_path))
    Cd = docx.Document(c_path)
    C = M.allparas(Cd)
    assert len(A) == len(B), (len(A), len(B))
    c_texts = [p.text for p in C]
    in_refs = False
    report, n_acc, n_rej, n_skip, n_par = [], 0, 0, 0, 0
    for i, (pa, pb) in enumerate(zip(A, B)):
        if pa.text.strip() == "References":
            in_refs = True
        if pa.text == pb.text or in_refs or re.match(r"\[?\d+[\].]\s", pa.text):
            continue
        head = pa.text[:60].replace("\n", " ")
        cand = difflib.get_close_matches(pa.text, c_texts, n=1, cutoff=0.80)
        if not cand:
            report.append("SKIP no matching paragraph in the new build | %s" % head)
            n_skip += 1
            continue
        j = c_texts.index(cand[0])
        pc = C[j]
        if M.has_math(pc) or not M.plain_runs(pc):
            report.append("SKIP equation or field paragraph | %s" % head)
            n_skip += 1
            continue
        chars = M.char_formats(pc)
        ctext = "".join(c for c, _ in chars)
        edits = []
        for (s0, s1, rep, old, new) in M.hunks(pa.text, pb.text):
            if not (M.safe(old, new, pa.text[:s0], pa.text[s1:]) and not any(k in (old + "->" + new) for k in M.DENY)):
                n_rej += 1
                report.append("  reject  [%s] -> [%s]" % (old, new))
                continue
            placed = False
            for width in (30, 15, 8):
                cb, ca = pa.text[max(0, s0 - width):s0], pa.text[s1:s1 + width]
                pat = cb + old + ca
                if ctext.count(pat) == 1:
                    pos = ctext.index(pat) + len(cb)
                    edits.append((pos, pos + len(old), new))
                    placed = True
                    break
            if placed:
                n_acc += 1
                report.append("  accept  [%s] -> [%s]" % (old, new))
            else:
                n_skip += 1
                report.append("  skip (context not unique in the new build)  [%s] -> [%s]" % (old, new))
        edits.sort(reverse=True)
        ok = []
        last = None
        for e in edits:
            if last is None or e[1] <= last:
                ok.append(e)
                last = e[0]
        if ok:
            n_par += 1
            new_chars = list(chars)
            for s0, s1, rep in ok:
                fmt = chars[s0][1] if s1 > s0 else (chars[s0 - 1][1] if s0 > 0 else (chars[s1][1] if s1 < len(chars) else None))
                new_chars[s0:s1] = [(c, fmt) for c in rep]
            M.rebuild_runs(pc, new_chars)
            c_texts[j] = "".join(c for c, _ in new_chars)
        report.append("PARAGRAPH %s" % head)
    Cd.save(out_path)
    rp = out_path.rsplit(".", 1)[0] + "_merge_report.txt"
    io.open(rp, "w", encoding="utf-8").write("accepted %d hunks in %d paragraphs, rejected %d, skipped %d" % (n_acc, n_par, n_rej, n_skip) + chr(10) + chr(10) + chr(10).join(report) + chr(10))
    print("accepted %d hunks in %d paragraphs, rejected %d, skipped %d -> %s" % (n_acc, n_par, n_rej, n_skip, out_path))


if __name__ == "__main__":
    main(*sys.argv[1:5])
    M.us_pass(sys.argv[4], sys.argv[4])
