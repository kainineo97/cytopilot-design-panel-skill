# Input and output contract

## Request JSON

```json
{
  "instrument_id": "challenbio-fongcyte-g510",
  "species": "Human",
  "markers": [
    {"name": "CD34", "expression": "dim", "critical": true, "coexpress_with": ["CD45"]},
    {"name": "CD45", "expression": "bright"},
    "CD42b"
  ],
  "fixed_assignments": {
    "CD45": "BV605"
  },
  "include_unverified": false,
  "max_states": 200000
}
```

`markers` accepts strings or objects. Defaults are `expression: medium`, `critical: false`, and no co-expression relationships. `fixed_assignments` maps marker names to required fluorophores; use this to review an existing partial panel.

The script's catalog and spectra paths are command-line arguments so the request remains portable.

## Output JSON

- `assignments`: selected catalog records with marker, clone, fluorophore, detector, catalog number, and review/source status.
- `unresolved_markers`: markers with no feasible recorded assignment.
- `unresolved_details`: distinguishes a missing catalog/fixed conjugate from a same-detector conflict and names the blocking assignment.
- `gap_recommendations`: ranked free instrument fluorophores/detectors for unresolved markers; these are conjugate specifications, not verified antibody products.
- `compensation_review_pairs`: pairwise `high`, `medium`, or `low` review priorities and reasons.
- `single_stain_controls`: every selected fluorophore/detector requiring an empirical single-stain control.
- `warnings`: assumptions, catalog limitations, and solver limits.

The approximate `overlap_score` is only a ranking feature. It is symmetric and must not be interpreted as a directional spillover or compensation coefficient.

## Exit codes

- `0`: a result was produced, including partial results with unresolved markers.
- `2`: invalid request, catalog, instrument, or spectra input.
