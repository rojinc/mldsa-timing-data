"""Build the released CSVs of the RP2040 validation blocks from a validation session folder.

Usage:  python3 -I ingest_validation.py <session_dir> <data>

<session_dir> is results/validation_<stamp>_<id> written by host/validate_blocks.py.  For every
completed phase set<N>_vblock<B> of each board the results.jsonl rows of phase 'main' are validated
with the campaign's own validate_result() (signature digest, RNG, stack guard, reset nonce,
K = 1 + z + w0 + ct0 + hint) and written to
<data>/measurements/signing/rp2040/validation/rp2040_<u>_set<N>_validation.csv with the columns of
the main campaign CSVs (board, uid, set, boot_block, key, message, repetition, partition, index,
start_us, sign_us, verify_us, K, n_z, n_w0, n_ct0, n_hint, sha256).  Warm-up calls are not released.
A summary (blocks, calls, randomness file digests) is written to validation_summary.json.
"""
import sys, os, json, glob, hashlib
import pandas as pd

SESSION = sys.argv[1]; DATA = sys.argv[2]
sys.path.insert(0, os.path.join(SESSION, "..", "..", "host"))
try:
    from campaign import validate_result
except Exception:
    validate_result = None
    print("campaign.py not importable from the session's package; rows are taken without the protocol re-validation")

out_dir = os.path.join(DATA, "measurements", "signing", "rp2040", "validation"); os.makedirs(out_dir, exist_ok=True)
manifest = json.load(open(os.path.join(SESSION, "session.json")))
summary = {"session": os.path.basename(SESSION), "frozen_rule_sha256": manifest.get("frozen_rule_sha256"), "boards": manifest["boards"], "phases": []}
for label, uid in manifest["boards"].items():
    prog = json.load(open(os.path.join(SESSION, label, "progress.json")))
    by_set = {}
    for phase, folder in sorted(prog["completed"].items()):
        if "_vblock" not in phase:
            continue
        level = int(phase[3:phase.index("_")]); block = int(phase.split("vblock")[1])
        p = os.path.join(SESSION, label, folder)
        status = json.load(open(os.path.join(p, "status.json")))
        if status["status"] != "COMPLETE":
            print("skipping incomplete", label, phase); continue
        nonce = json.load(open(os.path.join(p, "device.json")))["after_reset"]["boot_nonce"]
        rows = [json.loads(l) for l in open(os.path.join(p, "results.jsonl"))]
        main = [r for r in rows if r["phase"] == "main"]
        if validate_result:
            for r in main:
                validate_result(r, level, r["key"], r["mode"], nonce)
        rnd = json.load(open(os.path.join(p, "randomness.json")))
        df = pd.DataFrame([dict(board=label, uid=uid, set=level, boot_block=block, key=r["key"], message=r["message"], repetition=r["repetition"], partition="validation",
                                index=r["index"], start_us=r["start_us"], sign_us=r["sign_us"], verify_us=r["verify_us"], K=r["K"],
                                n_z=r["reject"][0], n_w0=r["reject"][1], n_ct0=r["reject"][2], n_hint=r["reject"][3], sha256=r["sha256"]) for r in main])
        by_set.setdefault(level, []).append(df)
        summary["phases"].append(dict(board=label, set=level, boot_block=block, folder=folder, main_calls=len(main), warmup_calls=len(rows) - len(main),
                                      randomness_file=rnd["file"], randomness_sha256=rnd["sha256"], results_sha256=status["results_sha256"]))
    for level, dfs in by_set.items():
        D = pd.concat(dfs, ignore_index=True).sort_values(["boot_block", "index"])
        f = os.path.join(out_dir, f"{label}_set{level}_validation.csv"); D.to_csv(f, index=False)
        print(f"{label} set {level}: {len(D)} validated calls in {D.boot_block.nunique()} blocks -> {f}")
json.dump(summary, open(os.path.join(out_dir, "validation_summary.json"), "w"), indent=1)
print("summary ->", os.path.join(out_dir, "validation_summary.json"))
