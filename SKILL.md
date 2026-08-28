---
name: cytopilot-design-panel
description: Design and review conventional flow-cytometry antibody panels for CytoPilot using its recorded reagent catalog, instrument lasers/detectors, and fluorophore spectra. Use when users ask to combine markers and fluorophores, select recorded antibodies, resolve channel conflicts, recommend missing antibodies or conjugates, assess spectral spillover and compensation-risk pairs, or prepare single-stain/FMO control requirements for a proposed panel.
license: MIT
---

# CytoPilot Panel Design

Design a traceable panel without treating a catalog record as proof of physical stock or an approximate spectrum as an empirical compensation matrix.

## Gather minimum inputs

Obtain or infer:

- target markers and species/reactivity;
- instrument or laser/detector configuration;
- marker expression as `dim`, `medium`, or `bright`;
- critical gates and markers co-expressed on the same population;
- sample treatment, including fixation/permeabilization and viability dye needs;
- catalog and spectra paths. For a standalone smoke test, use the synthetic files in `examples/`.

Ask only for missing information that materially changes the panel. If expression is unknown, use `medium` and label the assumption. Never infer stock quantity from catalog presence.

## Run the deterministic library pass

Create a request JSON following [references/input-output.md](references/input-output.md), then run:

```powershell
python scripts/design_panel.py --request request.json --catalog catalog.json --spectra spectra.json --pretty
```

Resolve paths relative to the current workspace. Use the bundled Python runtime if `python` is unavailable. Treat the script result as a ranked design aid, not experimental validation.

The script must:

1. Use only `verified` records by default.
2. Match marker aliases and requested reactivity.
3. Reject two assignments mapped to the same conventional detector.
4. Prefer brighter heuristic tiers for dim/critical markers while preserving options for other markers.
5. Penalize approximate emission overlap, especially for co-expressed pairs.
6. Return unresolved markers and compatible unoccupied fluorophore/detector suggestions.

## Recommend missing antibodies

For every unresolved marker:

1. Recommend a fluorophore/detector specification from the script's `gap_recommendations` before choosing a product.
2. If web access is available and the user wants a concrete product, search official manufacturer catalogs for marker, clone, species/reactivity, fluorophore, fixation compatibility, and product status. Cite the exact official product page and retrieval date.
3. Prefer a validated clone for the requested application and sample type. Do not assume two products with the same marker are interchangeable.
4. Label concrete external products `external_candidate_unverified` until a person verifies the label/product sheet and adds the record through CytoPilot review.
5. If official evidence is unavailable, give only a specification such as “Human CDX, PE conjugate, clone to verify”; never invent a brand, clone, or catalog number.

Do not write external recommendations into the user's catalog unless the user explicitly asks to add them. New records must enter as `review_status: pending`.

## Interpret compensation risk correctly

Read [references/panel-rules.md](references/panel-rules.md) before finalizing a panel.

Report three distinct outcomes:

- `infeasible`: two fluorophores use the same detector; compensation cannot make a conventional detector distinguish them.
- `high` or `medium` review priority: spectral proximity, tandem/donor relationship, or same-laser adjacency suggests meaningful spillover or spreading error. State the affected marker–fluorophore pairs.
- `low/not flagged`: no prominent approximate risk was found; this does not mean zero spillover.

Never publish an estimated spectral-overlap coefficient as a compensation percentage. Actual compensation coefficients must come from single-stain controls acquired with the same instrument settings and relevant reagent/sample conditions.

## Produce the answer

Return these sections, using tables when more than two markers are present:

1. **Recommended panel** — marker, antibody/clone, fluorophore, detector, source status, and rationale.
2. **Missing items** — library gap, proposed fluorophore/detector, concrete external candidate only when verified from an official source.
3. **Compensation review pairs** — marker pair, fluorophore pair, risk level, reason, and action.
4. **Controls** — one single-stain control for every fluorophore, unstained control, viability control when applicable, and FMO controls for critical/dim/continuous gates.
5. **Assumptions and limitations** — instrument, species, expression assumptions, catalog review versus physical stock, and need for titration/pilot validation.

Always include:

- “Cataloged/verified” does not mean physically in stock unless inventory fields explicitly confirm it.
- Same-detector conflicts require reassignment, not more compensation.
- Single-stain controls and empirical review of compensation/spreading are required before use.
- Tandem dyes require lot- and condition-aware controls and protection from degradation.

## Handle existing panels

When the user supplies a complete panel, evaluate it rather than redesigning it automatically. Preserve fixed assignments, flag conflicts and high-priority pairs, then offer the smallest set of swaps that removes infeasible conflicts and reduces co-expression spread.
