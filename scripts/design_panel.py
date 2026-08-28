#!/usr/bin/env python3
"""Rank CytoPilot catalog assignments and flag compensation-review pairs."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


BRIGHTNESS = {
    "pe": 5.0,
    "bv421": 4.7,
    "apc": 4.5,
    "bv605": 4.1,
    "bv650": 4.0,
    "bv711": 3.9,
    "fitc": 3.4,
    "bv510": 3.3,
    "pecy7": 3.2,
    "apccy7": 3.1,
    "percpcy55": 2.8,
}

TARGET_BRIGHTNESS = {"dim": 4.7, "medium": 3.8, "bright": 3.0}
TANDEM_DONORS = {
    frozenset(("pe", "pecy7")): "PE donor/tandem relationship; degradation or free donor can increase spread",
    frozenset(("apc", "apccy7")): "APC donor/tandem relationship; degradation or free donor can increase spread",
}
NON_ANTIBODY_FLUOROPHORES = {
    "7aad",
    "cfse",
    "dapi",
    "fluo3",
    "pi",
}


class InputError(ValueError):
    pass


def key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError(f"Expected a JSON object in {path}")
    return value


def parse_spectra(path: Path) -> dict[str, dict[str, float]]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise InputError(f"Cannot read spectra source {path}: {exc}") from exc
    if path.suffix.casefold() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InputError(f"Cannot read spectra JSON {path}: {exc}") from exc
        entries = payload.get("spectra", payload) if isinstance(payload, dict) else payload
        if not isinstance(entries, (dict, list)):
            raise InputError(f"Expected spectra JSON object or array in {path}")
        iterable = entries.values() if isinstance(entries, dict) else entries
        result: dict[str, dict[str, float]] = {}
        for item in iterable:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            try:
                result[key(item["name"])] = {
                    "ex": float(item["ex"]),
                    "em": float(item["em"]),
                    "em_width": float(item["em_width"]),
                }
            except (KeyError, TypeError, ValueError) as exc:
                raise InputError(f"Invalid spectrum record for {item.get('name')!r} in {path}") from exc
        if not result:
            raise InputError(f"No fluorophore spectra could be parsed from {path}")
        return result

    pattern = re.compile(
        r'"(?P<id>[a-z0-9]+)"\s*:\s*\{[^{}]*?name:\s*"(?P<name>[^"]+)"'
        r'[^{}]*?ex:\s*(?P<ex>\d+(?:\.\d+)?)[^{}]*?em:\s*(?P<em>\d+(?:\.\d+)?)'
        r'[^{}]*?exWidth:\s*(?P<exw>\d+(?:\.\d+)?)[^{}]*?emWidth:\s*(?P<emw>\d+(?:\.\d+)?)',
        re.DOTALL,
    )
    result: dict[str, dict[str, float]] = {}
    for match in pattern.finditer(text):
        result[key(match.group("name"))] = {
            "ex": float(match.group("ex")),
            "em": float(match.group("em")),
            "em_width": float(match.group("emw")),
        }
    if not result:
        raise InputError(f"No fluorophore spectra could be parsed from {path}")
    return result


def marker_specs(request: dict[str, Any]) -> list[dict[str, Any]]:
    raw = request.get("markers")
    if not isinstance(raw, list) or not raw:
        raise InputError("request.markers must be a non-empty list")
    result = []
    seen = set()
    for item in raw:
        spec = {"name": item} if isinstance(item, str) else dict(item) if isinstance(item, dict) else None
        if not spec or not str(spec.get("name", "")).strip():
            raise InputError("Each marker must be a string or an object with name")
        name = str(spec["name"]).strip()
        normalized = key(name)
        if normalized in seen:
            raise InputError(f"Duplicate marker: {name}")
        seen.add(normalized)
        expression = str(spec.get("expression", "medium")).casefold()
        if expression not in TARGET_BRIGHTNESS:
            raise InputError(f"Invalid expression for {name}: {expression}")
        raw_coexpression = spec.get("coexpress_with", [])
        if not isinstance(raw_coexpression, list):
            raise InputError(f"coexpress_with for {name} must be a list")
        result.append(
            {
                "name": name,
                "key": normalized,
                "expression": expression,
                "critical": bool(spec.get("critical", False)),
                "coexpress_with": {key(x) for x in raw_coexpression},
            }
        )
    return result


def select_instrument(catalog: dict[str, Any], requested: object) -> dict[str, Any]:
    instruments = [x for x in catalog.get("instruments", []) if isinstance(x, dict)]
    if not instruments:
        raise InputError("Catalog contains no instruments")
    if requested:
        for instrument in instruments:
            if str(instrument.get("id")) == str(requested):
                return instrument
        raise InputError(f"Instrument not found: {requested}")
    return instruments[0]


def detector_maps(instrument: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    by_name: dict[str, dict[str, Any]] = {}
    by_fluor: dict[str, str] = {}
    for detector in instrument.get("detectors", []):
        if not isinstance(detector, dict) or not detector.get("name"):
            continue
        name = str(detector["name"])
        by_name[name] = detector
        for fluor in detector.get("fluorophores", []):
            by_fluor[key(fluor)] = name
    return by_name, by_fluor


def record_marker_keys(record: dict[str, Any]) -> set[str]:
    return {key(record.get("marker")), *(key(x) for x in record.get("aliases", []))}


def reactivity_matches(record: dict[str, Any], species: str) -> bool:
    if not species:
        return True
    terms = f"{record.get('reactivity', '')} {record.get('species', '')}".casefold()
    return species.casefold() in terms


def overlap(first: dict[str, float] | None, second: dict[str, float] | None) -> float | None:
    if not first or not second:
        return None
    shared = 0.0
    total = 0.0
    for wavelength in range(350, 851, 2):
        a_sigma = max(first["em_width"], 1.0) / 2.355
        b_sigma = max(second["em_width"], 1.0) / 2.355
        a = math.exp(-0.5 * ((wavelength - first["em"]) / a_sigma) ** 2)
        b = math.exp(-0.5 * ((wavelength - second["em"]) / b_sigma) ** 2)
        shared += min(a, b)
        total += max(a, b)
    return shared / total if total else 0.0


def pair_facts(
    left: dict[str, Any],
    right: dict[str, Any],
    spectra: dict[str, dict[str, float]],
    detectors: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    lf, rf = key(left["fluorophore"]), key(right["fluorophore"])
    score = overlap(spectra.get(lf), spectra.get(rf))
    reasons: list[str] = []
    level = "low"
    if left["detector"] == right["detector"]:
        return {"level": "infeasible", "overlap_score": score, "reasons": ["same detector"]}
    tandem_reason = TANDEM_DONORS.get(frozenset((lf, rf)))
    if tandem_reason:
        level = "high"
        reasons.append(tandem_reason)
    if score is not None and score >= 0.42:
        level = "high"
        reasons.append("high approximate emission overlap")
    elif score is not None and score >= 0.24:
        if level != "high":
            level = "medium"
        reasons.append("adjacent approximate emission spectra")
    left_detector = detectors.get(left["detector"], {})
    right_detector = detectors.get(right["detector"], {})
    same_laser = left_detector.get("laser_nm") == right_detector.get("laser_nm")
    if same_laser and level == "low":
        level = "medium"
        reasons.append("different detectors on the same laser; review measured spillover/spread")
    if score is None:
        reasons.append("spectral reference unavailable; empirical review required")
    if not reasons:
        reasons.append("no prominent approximate pair risk; empirical single stains still required")
    return {"level": level, "overlap_score": score, "reasons": reasons}


def candidate_score(spec: dict[str, Any], candidate: dict[str, Any]) -> float:
    fluor_brightness = BRIGHTNESS.get(key(candidate["fluorophore"]), 3.5)
    target = TARGET_BRIGHTNESS[spec["expression"]]
    mismatch = abs(target - fluor_brightness)
    if spec["critical"] and fluor_brightness < 4.0:
        mismatch += 1.2
    return mismatch


def build_candidates(
    specs: list[dict[str, Any]],
    catalog: dict[str, Any],
    by_fluor: dict[str, str],
    species: str,
    include_unverified: bool,
    fixed: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    records = [x for x in catalog.get("reagents", []) if isinstance(x, dict) and x.get("type") == "antibody"]
    for spec in specs:
        options = []
        required_fluor = key(fixed.get(spec["key"], ""))
        for record in records:
            if spec["key"] not in record_marker_keys(record):
                continue
            if not include_unverified and record.get("review_status") != "verified":
                continue
            if not reactivity_matches(record, species):
                continue
            fluor = str(record.get("fluorophore", "")).strip()
            if not fluor or (required_fluor and key(fluor) != required_fluor):
                continue
            detector = str(record.get("detector", "")).strip() or by_fluor.get(key(fluor), "")
            if not detector:
                continue
            options.append(
                {
                    "marker": spec["name"],
                    "reagent": record.get("name"),
                    "clone": record.get("clone"),
                    "fluorophore": fluor,
                    "detector": detector,
                    "brand": record.get("brand"),
                    "catalog_no": record.get("catalog_no"),
                    "record_id": record.get("id"),
                    "review_status": record.get("review_status"),
                    "source_status": "cataloged_verified" if record.get("review_status") == "verified" else "cataloged_unverified",
                }
            )
        result[spec["key"]] = sorted(options, key=lambda x: candidate_score(spec, x))
    return result


def solve(
    specs: list[dict[str, Any]],
    candidates: dict[str, list[dict[str, Any]]],
    spectra: dict[str, dict[str, float]],
    detectors: dict[str, dict[str, Any]],
    max_states: int,
) -> tuple[list[dict[str, Any]], int, bool]:
    ordered = sorted(specs, key=lambda s: (len(candidates[s["key"]]) or 999, not s["critical"]))
    best_score = float("inf")
    best: list[dict[str, Any]] = []
    states = 0
    truncated = False

    def visit(index: int, chosen: list[tuple[dict[str, Any], dict[str, Any]]], used: set[str], cost: float) -> None:
        nonlocal best_score, best, states, truncated
        if states >= max_states:
            truncated = True
            return
        states += 1
        if cost >= best_score:
            return
        if index == len(ordered):
            best_score = cost
            best = [candidate for _, candidate in chosen]
            return
        spec = ordered[index]
        options = candidates[spec["key"]]
        if not options:
            visit(index + 1, chosen, used, cost + (40 if spec["critical"] else 25))
            return
        any_feasible = False
        for candidate in options:
            if candidate["detector"] in used:
                continue
            any_feasible = True
            extra = candidate_score(spec, candidate)
            for other_spec, other in chosen:
                facts = pair_facts(candidate, other, spectra, detectors)
                pair_cost = {"high": 8.0, "medium": 2.5, "low": 0.2}.get(facts["level"], 100.0)
                coexpressed = other_spec["key"] in spec["coexpress_with"] or spec["key"] in other_spec["coexpress_with"]
                extra += pair_cost * (2.0 if coexpressed else 1.0)
            visit(index + 1, chosen + [(spec, candidate)], used | {candidate["detector"]}, cost + extra)
        if not any_feasible:
            visit(index + 1, chosen, used, cost + (40 if spec["critical"] else 25))

    visit(0, [], set(), 0.0)
    return best, states, truncated


def gap_suggestions(
    unresolved: list[dict[str, Any]],
    used: set[str],
    instrument: dict[str, Any],
) -> list[dict[str, Any]]:
    result = []
    for spec in unresolved:
        choices = []
        target = TARGET_BRIGHTNESS[spec["expression"]]
        for detector in instrument.get("detectors", []):
            name = str(detector.get("name", ""))
            if not name or name in used:
                continue
            for fluor in detector.get("fluorophores", []):
                if key(fluor) in NON_ANTIBODY_FLUOROPHORES:
                    continue
                brightness = BRIGHTNESS.get(key(fluor), 3.5)
                choices.append(
                    {
                        "fluorophore": fluor,
                        "detector": name,
                        "filter": detector.get("filter"),
                        "laser_nm": detector.get("laser_nm"),
                        "heuristic_brightness": brightness,
                        "rank_score": round(abs(target - brightness), 3),
                        "status": "conjugate_specification_only",
                    }
                )
        result.append({"marker": spec["name"], "suggestions": sorted(choices, key=lambda x: x["rank_score"])[:5]})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--spectra", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    try:
        request = load_json(args.request)
        catalog = load_json(args.catalog)
        spectra = parse_spectra(args.spectra)
        specs = marker_specs(request)
        instrument = select_instrument(catalog, request.get("instrument_id"))
        detectors, by_fluor = detector_maps(instrument)
        raw_fixed = request.get("fixed_assignments", {})
        if not isinstance(raw_fixed, dict):
            raise InputError("fixed_assignments must be an object")
        fixed = {key(k): str(v) for k, v in raw_fixed.items()}
        candidates = build_candidates(
            specs,
            catalog,
            by_fluor,
            str(request.get("species", "")),
            bool(request.get("include_unverified", False)),
            fixed,
        )
        max_states = max(100, int(request.get("max_states", 200000)))
        assignments, states, truncated = solve(specs, candidates, spectra, detectors, max_states)
        assigned_keys = {key(x["marker"]) for x in assignments}
        unresolved = [x for x in specs if x["key"] not in assigned_keys]
        used_assignments = {x["detector"]: x for x in assignments}
        unresolved_details = []
        for spec in unresolved:
            options = candidates[spec["key"]]
            blockers = [
                {
                    "requested_marker": spec["name"],
                    "candidate_fluorophore": option["fluorophore"],
                    "detector": option["detector"],
                    "occupied_by_marker": used_assignments[option["detector"]]["marker"],
                    "occupied_by_fluorophore": used_assignments[option["detector"]]["fluorophore"],
                }
                for option in options
                if option["detector"] in used_assignments
            ]
            unresolved_details.append(
                {
                    "marker": spec["name"],
                    "reason": "same_detector_conflict" if blockers else "no_catalog_match_or_fixed_assignment_unavailable",
                    "infeasible_conflicts": blockers,
                }
            )
        pairs = []
        for i, left in enumerate(assignments):
            for right in assignments[i + 1 :]:
                facts = pair_facts(left, right, spectra, detectors)
                pairs.append(
                    {
                        "markers": [left["marker"], right["marker"]],
                        "fluorophores": [left["fluorophore"], right["fluorophore"]],
                        "detectors": [left["detector"], right["detector"]],
                        "risk": facts["level"],
                        "overlap_score": None if facts["overlap_score"] is None else round(facts["overlap_score"], 3),
                        "reasons": facts["reasons"],
                    }
                )
        pairs.sort(key=lambda x: ({"infeasible": 0, "high": 1, "medium": 2, "low": 3}[x["risk"]], -(x["overlap_score"] or 0)))
        used = {x["detector"] for x in assignments}
        result = {
            "schema_version": "cytopilot-panel-design-0.1",
            "instrument": {"id": instrument.get("id"), "name": instrument.get("name")},
            "species": request.get("species") or "not_specified",
            "assignments": sorted(assignments, key=lambda x: next(i for i, s in enumerate(specs) if s["key"] == key(x["marker"]))),
            "unresolved_markers": [x["name"] for x in unresolved],
            "unresolved_details": unresolved_details,
            "gap_recommendations": gap_suggestions(unresolved, used, instrument),
            "compensation_review_pairs": pairs,
            "single_stain_controls": [
                {"fluorophore": x["fluorophore"], "detector": x["detector"], "required": True}
                for x in assignments
            ],
            "solver": {"states_examined": states, "truncated": truncated, "max_states": max_states},
            "warnings": [
                "Cataloged/verified means recorded and reviewed, not confirmed physical stock.",
                "Approximate overlap scores rank review priority and are not compensation percentages.",
                "Generate the compensation matrix from matched single-stain controls and inspect spreading error.",
                "Brightness tiers are heuristics; titration and instrument-specific stain index take precedence.",
                *(["Search was truncated at max_states; review whether a better assignment exists."] if truncated else []),
            ],
        }
        rendered = json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    except (InputError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
