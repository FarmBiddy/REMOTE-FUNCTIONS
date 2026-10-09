# Milk quality and its value (`milk.quality`)

## Status

Accepted (milk-quality)

## Context

The Platform has Milk quality cards (SCC, TBC, butterfat, protein, compared with
the top 10% of Irish herds). In Ireland quality is money: co-ops pay on milk
components (A + B − C: € per kg fat + € per kg protein − a volume charge) and
apply SCC / TBC bonus or penalty bands. EU law sets hygiene limits on rolling
averages. The figures come from the co-op's monthly milk statements.

## Decision

1. **Input:** monthly statement figures `{year, month, milk_litres, fat_pct,
   protein_pct, scc_k, tbc_k}` (SCC in ×1000 cells/ml, TBC in ×1000 cfu/ml),
   optional `milking_cows`, `hectares`, `benchmarks`, `pricing`.
2. **Period figures are weighted by litres** (fat, protein, SCC, TBC): a
   simple average of monthly values would give a small winter month the same
   weight as the spring peak.
3. **EU compliance (Regulation (EC) 853/2004)** is Dairy policy, not an
   opinion: SCC rolling **geometric** mean over 3 months ≤ 400,000/ml; TBC
   rolling geometric mean over 2 months ≤ 100,000/ml. Each month reports its
   rolling value (over the months available, up to the window) and a breach
   flag; the period lists breach months.
4. **Milk solids** = litres × 1.03 kg/L × (fat% + protein%) / 100, with per cow
   and per hectare when those are sent. Feeds `kpi.summary.milk_solids_kg`.
5. **Benchmarks are inputs** (ICBF / Teagasc / co-op data, e.g. top 10% and
   average), never stored in the Engine. Output per metric: farm, benchmark,
   gap, and whether the farm is better (lower for SCC / TBC, higher for fat /
   protein).
6. **Value (when `pricing` is sent):** per month fat € = kg fat × € per kg,
   protein € likewise, volume charge = litres × c/L, SCC / TBC band adjustments
   (c/L for the band the month falls in; bands ascending, last band open-ended).
   Period: € totals and the price breakdown in c/L; `gain_to_top10_eur` = extra
   fat / protein value if the farm matched the top-10% composition (0 when
   already above); `gain_at_best_band_eur` = extra adjustment had every month
   been in the best SCC / TBC band.
7. Core gets `weighted_mean`, `geometric_mean`; Dairy holds the metric catalogue,
   EU limits, density, component pricing and band lookup; Application builds
   `milk.quality`.

## Consequences

- The Platform (or Biddy) extracts figures from milk statements; parsing PDFs is
  not Engine work.
- Not in this version: lactose, thermodurics, inhibitors, freezing point,
  per-cow milk recording, the production cost of high SCC (needs a loss
  coefficient supplied as an assumption).

## Related

ADR-0005, ADR-0028, ADR-0032, ADR-0047
