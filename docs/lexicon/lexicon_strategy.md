Lexicon Strategy and Design Decisions

This document defines the lexicon strategy used for both article analysis and comment analysis, including the rationale for the chosen approach.

1. Purpose of the Lexicon

Lexicons are used to:

Perform deterministic, rule-based text matching

Enable interpretable category signals

Avoid model-based or probabilistic behavior in the critical path

Lexicons are the foundation of all text analysis in this system.

2. Lexicon Types

The system uses two lexicon types:

Article lexicon

Contains 7 semantic categories

Used for window-level article analysis

Comment polarity lexicon

Single category

Used for audience reaction analysis

These lexicons are independent and versioned separately.

3. Chosen Approach: Expanded Lexicon (Approach A)

The baseline approach is offline lexicon expansion.

Core idea:

Expand lexicon entries ahead of time

Do not modify tokens during runtime

Perform simple O(1) lookups during processing

This approach maximizes determinism and simplicity.

4. Why Expanded Lexicon Was Chosen

Expanded lexicon was chosen because it:

Is fully deterministic

Avoids runtime heuristics

Preserves token boundaries

Simplifies debugging and validation

Scales linearly with input size

Runtime text normalization remains minimal.

5. Runtime Matching Rules

During processing:

Tokens are not modified

No prefix stripping is applied

No stemming or lemmatization is applied

Each token maps to at most one category

All intelligence is pushed offline into lexicon preparation.

6. Versioning Requirements

Every lexicon has a version identifier.

Rules:

Any lexicon content change requires a new version

Lexicon version must be stored with every output row

Old lexicon versions must remain usable

Lexicon versions are immutable.

7. Future Strategy (Not Enabled)

Prefix stripping or morphological normalization may be introduced in the future.

This is considered:

Experimental

Potentially language-dependent

More complex to validate

It is explicitly not part of the baseline system.

End of document
