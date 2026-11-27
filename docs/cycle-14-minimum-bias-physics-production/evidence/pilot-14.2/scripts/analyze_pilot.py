#!/usr/bin/env python3
"""Piloto 14.2: resumo fisico por BC e contagem de mensagens do PYTHIA."""
import collections, json, math, re, sys
from pathlib import Path
import ROOT

root_path, log_path = Path(sys.argv[1]), Path(sys.argv[2])
f = ROOT.TFile.Open(str(root_path))
t = f.Get("events")
cols = ["bcid", "n_interactions_requested", "n_interactions_generated",
        "generation_failures", "generator_particles", "transported_particles",
        "unknown_pdg_particles", "total_edep_mev", "unlineaged_steps",
        "segmentation_failures"]
rows = [{c: float(getattr(e, c)) for c in cols} for e in t]

def stats(v):
    n = len(v); m = sum(v) / n
    var = sum((x - m) ** 2 for x in v) / (n - 1) if n > 1 else 0.0
    return {"n": n, "mean": m, "var": var, "min": min(v), "max": max(v)}

out = {"file": str(root_path), "bcs": len(rows),
       "summary": {c: stats([r[c] for r in rows]) for c in cols if c != "bcid"}}
nreq = [r["n_interactions_requested"] for r in rows]
mu = 50.0
out["poisson_mu50"] = {
    "mean": stats(nreq)["mean"], "var": stats(nreq)["var"],
    "mean_pull": (stats(nreq)["mean"] - mu) / math.sqrt(mu / len(nreq)),
    "dispersion_index": stats(nreq)["var"] / stats(nreq)["mean"],
}
msgs = collections.Counter()
for line in log_path.read_text(errors="replace").splitlines():
    m = re.search(r"PYTHIA (Error|Warning|Abort)[^:]*?in ([^:]+::[^:]+):", line)
    if m:
        msgs[f"{m.group(1)} {m.group(2)}"] += 1
out["pythia_messages"] = dict(msgs.most_common())
out["pythia_messages_per_bc"] = {k: v / len(rows) for k, v in msgs.items()}
print(json.dumps(out, indent=2, sort_keys=True))
