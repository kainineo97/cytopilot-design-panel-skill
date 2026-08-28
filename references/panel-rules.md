# Panel design and compensation rules

## Assignment rules

1. Treat detector uniqueness as a hard constraint for conventional flow cytometry.
2. Prioritize critical and dim markers for bright, well-separated fluorophores.
3. Avoid placing highly co-expressed markers in combinations with high spread risk.
4. Reserve dimmer or tandem channels for abundant markers when alternatives exist.
5. Confirm species/reactivity, clone suitability, fixation/permeabilization compatibility, and antigen sensitivity to processing.
6. Treat heuristic brightness tiers as starting points only; antibody titration and stain index on the actual instrument take precedence.

## Risk categories

- **Infeasible**: identical detector assignment. Reassign one fluorophore.
- **High review priority**: approximate emission overlap score at least 0.42, or a donor/tandem relationship such as PE with PE-Cy7 or APC with APC-Cy7. Use matched single stains and inspect spreading error; preferentially separate co-expressed dim markers.
- **Medium review priority**: overlap score from 0.24 to below 0.42, or adjacent detectors on the same laser. Review compensation and FMO placement.
- **Low review priority**: below the thresholds and without a special relationship. Still include both single-stain controls.

The bundled script models curves from approximate peak and width values used by CytoPilot's spectrum viewer. These are useful for triage but do not replace full manufacturer spectra, instrument-specific detector response, autofluorescence, or measured spillover.

## Required controls

- Unstained cells for autofluorescence and baseline context.
- One single-stain control per fluorophore, including viability dyes.
- A positive signal bright enough to calculate the matrix, with negative and positive populations under matching detector settings.
- Reagent-matched controls for tandem dyes when bead binding, fixation, or treatment changes signal behavior.
- FMO for critical, dim, continuous, or strongly spread-affected gates; do not mechanically require FMO for every marker.
- Biological controls when the interpretation requires them.

## Language guardrails

Say “review this pair during compensation” or “high spillover/spread risk,” not “compensate fluor A against fluor B by X%” unless an empirical matrix supplies that directional value. Say “recorded and verified in the catalog,” not “in stock,” unless explicit inventory fields confirm availability.
