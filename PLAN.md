# Risk Decision Lab plan

The prototype should move from a point ranking toward a decision report that distinguishes
what the MIT data says from what the analyst assumes. The next stages are ordered to reduce
the largest decision uncertainty first.

## 1. Simple mitigation-cost stability — complete

- Allow default and per-domain relative cost ranges in an assumption set.
- Sample those ranges reproducibly with an explicit sample count and random seed.
- Report best, median, and worst rank and the share of sampled rankings in the top N.
- Label the result as a share of sampled assumptions, not a real-world probability.
- Ship a deliberately broad example assumption set and automated tests.

## 2. Validate against the complete MIT snapshot

- Download the raw Repository v4 and Delphi snapshot using the commands in `README.md`.
- Run the new analysis across all 24 domains and save a compact reproducible result.
- Inspect domains that are always high priority, always low priority, or highly unstable.
- Check whether conclusions are robust to sample count and reasonable alternative ranges.

Exit criterion: repeated runs with fixed inputs reproduce the same report, and changing
the sampling budget no longer materially changes the reported top-N shares.

## 3. Add uncertainty from the Delphi estimates

- Determine whether the snapshot exposes usable bootstrap draws or only aggregate
  confidence intervals.
- Resample the expert estimates without treating confidence-interval endpoints as a
  probability distribution.
- Report cost uncertainty and estimate uncertainty separately before combining them.
- Replace the current global median-CI warning with domain-level uncertainty output.

Exit criterion: the report shows which rank changes come from expert disagreement and
which come from unknown mitigation cost.

## 4. Make mitigation assumptions defensible

- Define the minimum elicitation fields: relative cost, time to implement, feasibility,
  expected effectiveness, and coordination or verification burden.
- Record a source, owner, date, and confidence for every non-data assumption.
- Test correlated costs instead of assuming every domain varies independently.
- Ask domain experts for ranges; do not infer false precision from the mitigation catalogue.

Exit criterion: each range has provenance and reviewers can replace it without changing
the model code.

## 5. Produce a decision-facing report

- Highlight robust priorities, assumption-sensitive priorities, and the missing input
  with the highest value of information.
- Add small plots only where they clarify rank ranges or uncertainty sources.
- Export machine-readable results alongside the human-readable report.
- Consider a web interface only after the semantics and outputs have stabilised.

Exit criterion: a decision-maker can explain why a domain is prioritised, which assumption
could reverse that decision, and what evidence should be collected next.

## Known limitations of the current simple analysis

- Cost ranges are analyst inputs, not measurements.
- Independent log-uniform draws are a transparent stress test, not a calibrated model of
  the world.
- Best and worst observed ranks depend on the declared ranges and finite sample.
- Delphi uncertainty is displayed but not yet propagated through sampled rankings.
- Broad domain estimates cannot be assigned to individual Repository risk rows.
