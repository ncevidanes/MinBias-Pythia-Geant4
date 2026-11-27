#!/usr/bin/env python3
"""Piloto 14.2: monolitico contra shards concatenados, em blocos (uproot).

Mesma regra do Ciclo 11 (analyze_partition_stability.py): arvores events,
hits e generator identicas bit a bit, na ordem de gravacao; metadata igual
exceto OPERATIONAL_METADATA. Le em blocos para caber em pouca memoria.
"""
import json, sys
import numpy as np
import uproot

OPERATIONAL_METADATA = {"events", "first_bcid", "threads", "output_file",
                        "config_file", "normalized_config"}
STEP = 1_000_000
# Como GLOBAL_FIELDS do Ciclo 11: run e event sao indices locais do processo.
LOCAL_FIELDS = {"run", "event"}
mono_path, shard_paths = sys.argv[1], sys.argv[2:]
mono = uproot.open(mono_path)
shards = [uproot.open(p) for p in shard_paths]
report = {"monolithic": mono_path, "shards": shard_paths, "trees": {}}

def read_concat(trees, branches, start, stop):
    parts, off = [], 0
    for t in trees:
        n = int(t.num_entries)
        a, b = max(start - off, 0), min(stop - off, n)
        if a < b:
            parts.append(t.arrays(branches, entry_start=a, entry_stop=b, library="np"))
        off += n
    return {k: np.concatenate([p[k] for p in parts]) for k in branches}

ok_all = True
for name in ("events", "hits", "generator"):
    mt = mono[name]; sts = [s[name] for s in shards]
    all_branches = list(mt.keys())
    branches = [b for b in all_branches if b not in LOCAL_FIELDS]
    nm, ns = int(mt.num_entries), int(sum(t.num_entries for t in sts))
    res = {"entries_monolithic": nm, "entries_shards": ns, "branches": len(branches),
           "branch_sets_equal": all(list(t.keys()) == all_branches for t in sts),
           "excluded_local_fields": sorted(LOCAL_FIELDS & set(all_branches))}
    diff = []
    if nm == ns and res["branch_sets_equal"] and nm > 0:
        for start in range(0, nm, STEP):
            stop = min(start + STEP, nm)
            a = mt.arrays(branches, entry_start=start, entry_stop=stop, library="np")
            b = read_concat(sts, branches, start, stop)
            for k in branches:
                x, y = a[k], b[k]
                same = x.dtype == y.dtype and x.shape == y.shape and (
                    x.tobytes() == y.tobytes() if x.dtype != object
                    else all(np.array_equal(u, v) for u, v in zip(x, y)))
                if not same and k not in diff:
                    diff.append(k)
    res["differing_branches"] = diff
    res["equal"] = nm == ns and res["branch_sets_equal"] and not diff
    ok_all &= res["equal"]
    report["trees"][name] = res

def meta(f):
    t = f["metadata"]
    return {k: v[0] for k, v in t.arrays(library="np").items()}
def norm(v):
    return v.decode() if isinstance(v, bytes) else (v.tolist() if hasattr(v, "tolist") else v)
mm = meta(mono)
mdiff = {}
for p, s in zip(shard_paths, shards):
    sm = meta(s)
    d = sorted(k for k in set(mm) | set(sm)
               if k not in OPERATIONAL_METADATA and norm(mm.get(k)) != norm(sm.get(k)))
    mdiff[p] = d
report["metadata_differences_outside_operational"] = mdiff
report["metadata_equal"] = all(not d for d in mdiff.values())
report["PARTITION_RESULT"] = "PASS" if ok_all and report["metadata_equal"] else "FAIL"
print(json.dumps(report, indent=2, default=str))
