Lexicon Expansion Rules

This document defines the rules used to expand base lexicon entries into an expanded lexicon used at runtime.

1. Purpose of Expansion

Expansion exists to:

Increase recall without runtime complexity

Handle common linguistic prefixes

Preserve deterministic behavior

Expansion is performed offline only.

2. Base Lexicon

The base lexicon contains:

Canonical word forms

One category per word

No prefixes or suffixes

The base lexicon is manually curated.

3. Prefix Expansion Rules

For each base word, generate variants using common Hebrew prefixes:

ה

ו

ב

ל

מ

כ

ש

Rules:

Single prefix only

Prefix must attach directly to the word

No prefix stacking beyond one character

4. Combined Prefix Rule (Limited)

Optionally, a limited set of two-prefix combinations may be generated.

Rules:

Only highly common combinations

Maximum of two prefixes

Must be explicitly whitelisted

This is intentionally conservative.

5. Minimum Length Constraint

Expansion rules apply only if:

Base word length is at least 3 characters

This prevents excessive noise and over-generation.

6. Conflict Resolution

If multiple base words expand to the same surface form:

The conflict must be resolved offline

Each surface form must map to exactly one category

Ambiguous entries are removed or reassigned

Runtime ambiguity is not allowed.

7. Output of Expansion

The expansion process produces:

lexicon_expanded.json

word_to_category mapping

Deterministic ordering

The expanded lexicon is treated as immutable.

8. Validation Rules

Before deployment, the expanded lexicon must be validated:

No duplicate surface forms

Every surface form maps to exactly one category

Version hash must be reproducible

9. Expansion and Versioning

The lexicon version is computed from:

The expanded lexicon content

Deterministic hashing

Any change produces a new version identifier.

End of document
