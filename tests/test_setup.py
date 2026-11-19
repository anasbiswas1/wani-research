"""Smoke test: the copied modules import, the pair builder runs, and the shared data folder is reachable."""
import os, sys, random, importlib
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))


def test_modules_import():
    for m in ["paths", "structural_data", "structural_train", "metrics", "rank_metrics", "interval_panel",
              "tie_interval", "data_loaders", "detectors", "reslog", "ci_tools", "calibration_pool", "strict_threshold"]:
        importlib.import_module(m)


def test_pair_builder_forms():
    import structural_data as sd
    rng = random.Random(0)
    units = sd.build_units(sd.BENIGN_FAMILIES, 2, rng, "benign")
    assert units and all("unit" in u and "family" in u for u in units)
    forms = sd.standalone_forms(units[0]["unit"], rng, 3)
    assert forms[0] == units[0]["unit"]


def test_shared_data_reachable():
    import paths
    assert paths.PICALIB_DATA.exists(), str(paths.PICALIB_DATA)
    assert (paths.STRUCTURAL / "train.jsonl").exists()


def test_manifest_written():
    import json
    m = json.load(open(os.path.join(HERE, "data_manifest.json")))
    assert m["files"] and "structural/train.jsonl" in m["files"]
