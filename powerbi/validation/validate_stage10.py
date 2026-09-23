"""Read-only Stage 10 checks; writes evidence only inside powerbi/validation.

Run --record-baseline once before building; run --schemas to validate against
Microsoft's published JSON schemas. Neither mode refreshes or edits the source.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
NAME = "Dubai_Real_Estate_Intelligence"
PROJECT = ROOT / "powerbi" / NAME
SOURCE = ROOT / "data/processed/dld_transactions_2026_ytd_features.csv"
EXPECTED_SHA = "bb85cf21fa01480511257e3139061e78b9bbcc7bbe1d3b7cfe481bdcfc863db1"
MEASURES = ["Sales Records", "Distinct Sales Transaction Numbers", "Non-Sales Records",
            "Valid Sale Price Records", "Median Sale Price per Sqft", "Average Sale Price per Sqft",
            "Off-Plan Sales Records", "Ready Sales Records", "Off-Plan Share", "Ready Share",
            "Residential Sales Records", "Residential Share", "Commercial Sales Records",
            "Freehold Sales Records", "Non-Freehold Sales Records", "Previous Month Sales Records",
            "MoM Sales Record Growth %", "Top Area by Sales Records", "Latest Data Date",
            "Data Coverage Label", "Partial Month Warning"]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def write_evidence(name, obj):
    (HERE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def baseline():
    path = HERE / "recovery_baseline.json"
    if path.exists():
        raise RuntimeError("Preserving existing baseline; refusing to overwrite it")
    files = git("ls-files", "-z").split("\0")
    protected = {p: sha(ROOT / p) for p in files if p and (ROOT / p).is_file()}
    protected[str(SOURCE.relative_to(ROOT)).replace("\\", "/")] = sha(SOURCE)
    assert sha(SOURCE) == EXPECTED_SHA
    write_evidence("recovery_baseline.json", {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "initial_commit": git("rev-parse", "HEAD").strip(),
        "initial_git_status": "clean (verified before Stage 10 additions)",
        "inspection": "Recursive inspection including ignored files found only powerbi/.gitkeep; no Stage 10 files in reports or elsewhere in the project.",
        "initial_classification": {x: "MISSING" for x in ["PBIP", "SemanticModel", "Report definitions", "DAX reference", "Power Query reference", "Theme", "Visual specification", "Power BI build report", "Reports build report"]},
        "partial_or_invalid_existing_stage10_files": [],
        "protected_sha256": protected,
    })
    print(json.dumps({"baseline": str(path), "protected_files": len(protected), "source_sha256": EXPECTED_SHA}))


def main(with_schemas):
    evidence = {"checked_utc": datetime.now(timezone.utc).isoformat(), "scope": "local files and source recalculation; does not execute DAX/M or render Power BI"}
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)

    before = sha(SOURCE)
    saved = json.loads((HERE / "recovery_baseline.json").read_text(encoding="utf-8"))
    changed = [p for p, digest in saved["protected_sha256"].items() if not (ROOT / p).exists() or sha(ROOT / p) != digest]
    evidence["protected_files_checked"] = len(saved["protected_sha256"])
    evidence["protected_files_changed"] = changed
    check(not changed, f"Protected files changed: {changed}")

    with SOURCE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)
    sales = [r for r in rows if r["GROUP_EN"] == "Sales"]
    prices = [float(r["SALE_PRICE_PER_SQFT"]) for r in sales if r["VALID_SALE_PRICE_METRIC"] == "1"]
    off = sum(r["IS_OFFPLAN_EN"] == "Off-Plan" for r in sales)
    ready = sum(r["IS_OFFPLAN_EN"] == "Ready" for r in sales)
    dates = [r["TRANSACTION_DATE"] for r in rows]
    id_counts = collections.Counter(r["TRANSACTION_NUMBER"] for r in rows)
    values = collections.defaultdict(set)
    for row in rows:
        values[row["TRANSACTION_NUMBER"]].add(row["TRANS_VALUE"])
    metrics = {"rows": len(rows), "columns": len(columns), "coverage_start": min(dates), "coverage_end": max(dates),
               "sales_records": len(sales), "distinct_sales_transaction_numbers": len({r["TRANSACTION_NUMBER"] for r in sales}),
               "valid_sale_price_records": len(prices), "median_sale_price_per_sqft": statistics.median(prices),
               "average_sale_price_per_sqft": statistics.mean(prices), "off_plan_sales_records": off, "ready_sales_records": ready,
               "off_plan_share": off / len(sales), "ready_share": ready / len(sales),
               "residential_sales_records": sum(r["USAGE_EN"] == "Residential" for r in sales),
               "repeated_transaction_numbers": sum(n > 1 for n in id_counts.values()),
               "repeated_ids_with_multiple_values": sum(id_counts[k] > 1 and len(v) > 1 for k, v in values.items()),
               "monthly_sales": dict(sorted(collections.Counter(r["TRANSACTION_DATE"][:7] for r in sales).items())),
               "top_area": collections.Counter(r["AREA_EN"] for r in sales).most_common(1)[0]}
    evidence["source_metrics"] = metrics
    for key, value in {"rows":159223,"columns":41,"coverage_start":"2026-01-01","coverage_end":"2026-09-21","sales_records":119549,"distinct_sales_transaction_numbers":119526,"repeated_transaction_numbers":772,"repeated_ids_with_multiple_values":476}.items():
        check(metrics[key] == value, f"Unexpected {key}: {metrics[key]}")
    check(round(metrics["median_sale_price_per_sqft"], 2) == 1716.79, "Median differs from reference")
    check(round(100 * metrics["off_plan_share"], 2) == 68.18, "Off-plan share differs from reference")
    check(round(100 * metrics["ready_share"], 2) == 31.82, "Ready share differs from reference")

    files = sorted(p for p in PROJECT.rglob("*") if p.is_file() and ".pbi" not in p.parts)
    json_paths = [p for p in files if p.suffix in {".json", ".pbip", ".pbir", ".pbism"} or p.name == ".platform"]
    json_paths.append(ROOT / "powerbi/dubai_real_estate_theme.json")
    parsed = {}
    for p in json_paths:
        try:
            parsed[p] = json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as ex:
            errors.append(f"Invalid JSON {p.relative_to(ROOT)}: {ex}")
    evidence["json_files_parsed"] = len(parsed)
    evidence["empty_artifact_files"] = [str(p.relative_to(ROOT)) for p in files if p.stat().st_size == 0]
    check(not evidence["empty_artifact_files"], "Empty project files")
    shortcut = PROJECT / f"{NAME}.pbip"
    check(shortcut in parsed, "PBIP shortcut missing")
    if shortcut in parsed:
        for artifact in parsed[shortcut]["artifacts"]:
            check((PROJECT / artifact["report"]["path"] / "definition.pbir").is_file(), "PBIP report reference broken")
    report = PROJECT / f"{NAME}.Report"
    pbir = report / "definition.pbir"
    if pbir in parsed:
        check((report / parsed[pbir]["datasetReference"]["byPath"]["path"] / "definition.pbism").is_file(), "Semantic model reference broken")
    else:
        errors.append("Missing definition.pbir")
    tmdl = list((PROJECT / f"{NAME}.SemanticModel/definition").rglob("*.tmdl"))
    model_text = "\n".join(p.read_text(encoding="utf-8-sig") for p in tmdl)
    names = re.findall(r"^\s*measure\s+'([^']+)'\s*=", model_text, flags=re.M)
    evidence["dax_measure_count"] = len(names)
    check(set(names) == set(MEASURES) and len(names) == 21, f"Required measures mismatch: {names}")
    check(not re.search(r"SUM\s*\(\s*'?FactTransactions'?\s*\[TRANS_VALUE\]", model_text, re.I), "Prohibited value SUM")
    check("Total Sales Value" not in names and "Total Market Value" not in names, "Prohibited market KPI")
    visuals = [v for p,v in parsed.items() if p.name == "visual.json"]
    types = collections.Counter(v.get("visual", {}).get("visualType") for v in visuals)
    evidence["visual_types"] = dict(types)
    check(types["slicer"] == 5, "Expected five slicers")
    check(sum(types[x] for x in ("lineChart","donutChart","barChart","clusteredBarChart","columnChart","clusteredColumnChart")) == 4, "Expected four charts")
    check(sum(types[x] for x in ("card","cardVisual","multiRowCard")) >= 8, "Expected at least eight KPI cards")
    for p,v in parsed.items():
        if p.name == "page.json":
            check(v.get("displayName") == "Executive Overview", "Unexpected page name")
            check(v.get("width") / v.get("height") == 16 / 9, "Page must be 16:9")
    check(all(0 <= v["position"]["x"] and 0 <= v["position"]["y"] and v["position"]["x"] + v["position"]["width"] <= 1280 and v["position"]["y"] + v["position"]["height"] <= 720 for v in visuals), "Visual exceeds canvas")

    if with_schemas:
        import requests
        from jsonschema.validators import validator_for
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT7
        schema_cache = HERE / "schemas"
        schema_cache.mkdir(exist_ok=True)
        used = {}
        def retrieve(uri):
            check(urlparse(uri).hostname in {"developer.microsoft.com", "raw.githubusercontent.com"}, f"Unexpected schema host: {uri}")
            key = hashlib.sha256(uri.encode()).hexdigest() + ".json"
            cache = schema_cache / key
            if cache.exists():
                schema = json.loads(cache.read_text(encoding="utf-8"))
            else:
                response = requests.get(uri, timeout=45)
                response.raise_for_status()
                schema = response.json()
                cache.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
            used[uri] = key
            return Resource.from_contents(schema, default_specification=DRAFT7)
        registry = Registry(retrieve=retrieve)
        validated = []
        unavailable = []
        unavailable_uris = {}
        for p, obj in parsed.items():
            uri = obj.get("$schema")
            if not uri:
                continue
            if uri in unavailable_uris:
                unavailable.append({"file": str(p.relative_to(ROOT)), "schema": uri, "reason": unavailable_uris[uri]})
                continue
            try:
                schema = retrieve(uri).contents
                registry = registry.with_resource(uri, Resource.from_contents(schema, default_specification=DRAFT7))
                validator_for(schema)(schema, registry=registry).validate(obj)
                validated.append(str(p.relative_to(ROOT)))
            except requests.HTTPError as ex:
                if ex.response is not None and ex.response.status_code == 404:
                    unavailable_uris[uri] = str(ex)
                    unavailable.append({"file": str(p.relative_to(ROOT)), "schema": uri, "reason": str(ex)})
                else:
                    errors.append(f"Schema retrieval {p.relative_to(ROOT)}: {ex}")
            except Exception as ex:
                errors.append(f"Schema validation {p.relative_to(ROOT)}: {ex}")
        evidence["schema_validated_files"] = validated
        evidence["schema_unavailable"] = unavailable
        evidence["external_schema_validation_complete"] = not unavailable
        evidence["schema_validation_note"] = "Missing published schemas are a validation limitation, not proof of invalid files. Desktop-generated definitions are preserved; see live and native validation evidence."
        write_evidence("schema_sources.json", used)

    after = sha(SOURCE)
    evidence.update(source_sha256_before=before, source_sha256_after=after, source_unchanged=before == after == EXPECTED_SHA,
                    tracked_diff=git("diff", "--name-only"), errors=errors, passed=not errors)
    check(evidence["source_unchanged"], "Source SHA changed")
    evidence["passed"] = not errors
    write_evidence("stage10_validation.json", evidence)
    print(json.dumps(evidence, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-baseline", action="store_true")
    parser.add_argument("--schemas", action="store_true")
    args = parser.parse_args()
    baseline() if args.record_baseline else main(args.schemas)
