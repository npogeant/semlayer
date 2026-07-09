# 0001: Semantic model schema shape

## Status

Accepted

## Context

Issue #2 asked for a declarative YAML schema covering entities, dimensions,
metrics, and relationships, listing a minimum field set for each. Before any
parsing or validation code is written (issues #3, #4), the shape of the
schema needs to be settled so later work has a stable target.

## Decisions

**Flat, top-level lists instead of nesting dimensions/metrics under
entities.** Formats like LookML or dbt semantic models often nest
dimensions and measures inside a model block. We instead keep `entities`,
`dimensions`, `metrics`, and `relationships` as four separate top-level
lists, with dimensions and metrics referencing their `entity` by name. This
was chosen because issue #3 requires "loading a semantic model split across
multiple files" — flat lists merge trivially across files (concatenate the
lists), whereas nested definitions would require deep-merging entities
defined partially in more than one file.

**Entities require a `primary_key`.** The issue's field list for entities
didn't include one, but relationships need a well-defined join anchor, and
future validation (issue #4) needs a way to detect duplicate rows after a
join. Adding `primary_key` now avoids a breaking schema change later.

**Relationships carry explicit `source_key` / `target_key`, not just a join
type.** A join type (`inner`, `left`, ...) says how to combine two entities
but not which columns to join on. Since the loader has no dependency on a
specific database (issue #3's DoD) and can't infer keys from a live schema,
the join columns must be declared explicitly.

**`type` is used for two different concepts and that's intentional.** On a
dimension, `type` means data classification (`categorical`, `time`,
`boolean`, `numeric`). On a relationship, `type` means cardinality
(`one_to_one`, `one_to_many`, ...). Both are called `type` because each is
the obvious/only "type" in its own context; qualifying them (e.g.
`data_type` / `cardinality`) was considered but rejected as unnecessary
verbosity given the two never appear on the same object.

**No nested filters, calculated dimensions, or multi-hop join paths yet.**
The issue's DoD asks for a schema that documents the four base constructs
with an example that demonstrates each — not a feature-complete metrics
layer. Filters on metrics, derived/expression dimensions, and relationship
chains are deferred until a concrete use case in a later issue needs them,
to avoid speculative schema surface that the loader and validator would
have to support unused.

## Consequences

- The loader (#3) can merge multi-file models by concatenating the four
  lists before resolving name references.
- The validator (#4) can check relationship keys against each entity's
  columns once column introspection exists, and can use `primary_key` to
  reason about join fan-out.
- Extending the schema later (e.g. calculated dimensions) is additive — new
  optional fields — and shouldn't require revisiting this document's core
  shape.
