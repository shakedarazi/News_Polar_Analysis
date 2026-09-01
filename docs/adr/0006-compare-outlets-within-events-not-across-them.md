---
status: accepted
---

# Compare outlets within events, not across them

`GET /api/analytics/polarity-by-source` averages every article an outlet
published and puts the five results side by side. The dashboard has shown that
chart since the beginning, and it invites a reading it cannot support: that the
differences between the bars are differences in how the outlets cover the news.

They are mostly differences in *what* the outlets cover. An outlet whose feed
skews political will score higher than one whose feed skews traffic and weather,
and neither number says anything about framing. This records the second
comparison added beside it, and why it is a separate endpoint rather than more
columns on the existing one.

## Holding the story fixed

For every event covered by two or more outlets, each outlet's value is compared
to the **median of that event**. The news itself is then constant across the
comparison, and what survives the subtraction is the editorial choice.

Measured on the current corpus, `audience_mean`, 41 usable events out of 69:

| outlet | deviation | 95% | Bonferroni |
|---|---|---|---|
| mako | +0.58 pp | [+0.26, +0.89] | [+0.20, +0.97] **significant** |
| ynet | −0.02 pp | [−0.32, +0.27] | [−0.39, +0.31] |
| haaretz | −0.39 pp | [−0.70, −0.01] significant | [−0.78, +0.04] |

The aggregate chart puts all five outlets inside 0.8 percentage points of one
another, which reads as "no difference". The paired comparison finds one that
survives correction. haaretz is the instructive row: it clears zero at 95% and
does not clear it once the correction is applied, and both intervals are drawn
so that difference is visible rather than decided off-screen.

On `dominance` nothing is significant at either level. That is reported as it
stands; a construction that only ever produces findings is not measuring.

## Two constraints that are part of the definition

**One version per outlet per event**, chosen as its most-commented article. An
outlet that published five follow-ups to one story would otherwise supply five
of nine versions, and the median would drift toward being that outlet — it would
be measured against itself. Ties break on the lowest `article_id` so the same
corpus always yields the same profile.

**Most events are pairs** — 88% of the usable ones. In a pair the median is the
midpoint, so the two deviations are forced to be +d/2 and −d/2: one comparison
recorded twice, not two independent observations. `pair_share` is returned by
the endpoint and printed under the chart rather than left for a reader to
discover, because at that share it changes how much the intervals mean.

## Bonferroni, and why both intervals are drawn

Five outlets tested at once at 95% gives a 23% chance that at least one crosses
zero by accident. The endpoint returns the plain interval and the interval
widened by 0.05/k, and only `significant_adjusted` is allowed to render the word
"מובהק". Both are drawn, nested, so the correction is something the reader can
see being applied rather than a number they have to trust.

## Why a separate endpoint

Merging these fields into `/api/analytics/polarity-by-source` would put two
different questions behind one shape, and the failure mode is silent: a caller
reads a within-event deviation as an outlet average, or the reverse. They also
have different denominators — the aggregate covers every analysed article, the
deviation covers only articles inside multi-source events — so a single response
would carry two incompatible `n`s.

## Cost

`src/analysis/event_stats.py` is pure Python with no numpy, because `src/api/`
imports it and CI asserts nothing on that path pulls numpy in. The bootstrap is
2,000 iterations against a fixed seed: a confidence interval that moves when the
page is refreshed is not a finding. Measured end to end, including the cached
event grouping and one `ANY()` query over the union of member ids: ~0.7s warm.
