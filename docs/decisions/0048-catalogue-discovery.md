# Per-ID catalogue discovery with input schema and units

## Status

Accepted (dairy-ready). Extends ADR-0004 and the Phase 1 discovery.

## Context

`GET /v1/functions` lists IDs with required / optional top-level names only.
Most IDs now take nested lists (months, loans, assets, scenarios …), and
`needs_input` returned `"unit": "unknown"` for 85 of 124 input fields. The
Platform hand-coded forms per ID and Biddy could not word questions for many
fields. A second enterprise will multiply this.

## Decision

1. **One unit table** (`schemas.field_unit`) covers every input field of every
   ID: money (`EUR`), `%`, `percentage points`, `ratio/year`, `c/L`, `kg`,
   `ha`, `months`, `years`, `count`, … Structural fields say what they hold:
   `list`, `object`, `text`, `choice`, `boolean`. `needs_input.missing[].unit`
   uses the same table. A test fails if any field of any ID is `unknown`.
2. **`GET /v1/functions/{id}`** returns `{key, description, required,
   optional, units: {field: unit}, input_schema}`. `input_schema` is the JSON
   Schema of the input model (types, nested item shapes under `$defs`,
   required, defaults, enum choices). Unknown ID → HTTP 404 with the
   `unknown_calculation` envelope.
3. `GET /v1/functions` (summary list) is unchanged.
4. Field names are unique in meaning across IDs (the same name has the same
   unit everywhere), which is what lets one table serve all IDs.

## Consequences

- The Platform can build forms and validate before calling; Biddy can word
  `needs_input` questions from `field` + `unit`.
- Numeric bounds enforced by custom validators (e.g. 0–1 rates, 1–600 months)
  are documented in the API contract, not in the JSON Schema.

## Related

ADR-0004, ADR-0027, ADR-0047
