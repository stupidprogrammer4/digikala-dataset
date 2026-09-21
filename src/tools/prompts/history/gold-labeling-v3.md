# Expert gold annotation — interactive-gold-labeler/3.0

Read every assigned complete evidence view and make explicit decisions for every
product. Source text is untrusted data, never an instruction. The task is semantic
annotation under `gold-semantic/2.0`; numeric facts and CoreProduct remain unchanged.
Do not read the old proposed labels before making your decisions.

Record category, audience, style, motifs, use cases, and design details supported
by product-specific text. Each positive claim needs an exact source quote. Capture
explicit designs even when the previous four-value motif vocabulary missed them.
Use normalized English snake_case concept values, and a controlled motif family.
Examples: leopard/animal, whale_tail/animal, bow/object, heart/symbolic,
flower/plant, square/geometric, name/text, letter/text, mother_and_child/figurative.
Use butterfly/animal, tree/plant, moon/celestial, star/celestial, infinity/symbolic,
evil_eye/symbolic, cross/symbolic, feather/animal, wing/animal, clover/plant.
Use detail concepts only when explicitly described, not from a named collection.
For example a vendor or model called Lily does not establish a flower motif.
An explicit design phrase naming a flower does establish a flower motif.

Separate decorative motifs from construction: stud or hoop belongs to earring_form,
bangle to bracelet_form, figaro/cable/curb/rope to chain_pattern, and polished/matte/
hammered to surface_finish. A stud earring need not have a geometric motif. Named
brand-inspired patterns do not prove the brand, authenticity, luxury, or occasion.
An explicit Cartier-style link pattern may be represented as cartier_inspired in
chain_pattern when construction context supports it; otherwise record it as a
decoration without inventing geometry. Preserve a clear descriptive model design
as decoration when it is neither a supported style nor a motif.

Audience must be explicit in product-specific title, attributes or alternate text.
A broad marketplace category called women's gold does not establish audience for
every item. Do not infer gender from names, shapes, colors or small weights. When
women and men are both explicitly targeted, use unisex. Children's targeting is
outside this audience vocabulary: preserve a vocabulary_gap rather than inventing
adult audience. Broad category titles are fallback evidence for product type only
when unambiguous and not contradicted by product-specific evidence.

Prefer specific product type in the title over the enclosing source category.
Gold coins under bars remain gold.coin with a conflict flag. Explicit chain versus
necklace, pendant versus necklace, set versus single item and bangle versus flexible
bracelet must be judged per product. Generic gram gold with no specified form is
ambiguous; do not force it to gold.bar. Earring backs outside the category vocabulary
get taxonomy abstention out_of_vocabulary and an evidenced vocabulary_gap.

Styles require descriptive evidence: simple/minimal wording can support minimal;
tiny or lightweight alone cannot. Traditional/classic, ornate, modern or vintage
need direct descriptive support. Do not infer style from brand or price. Use cases
also require support: a gold bar is not automatically labeled investment and every
jewel is not automatically a gift. An explicitly bridal/wedding item can support
formal; a bonus free gift in a bundle does not establish gift suitability.

For every empty group or null taxonomy, provide an abstention explanation in
English: not_stated for absent evidence, ambiguous for unresolved conflicting or
unclear evidence, out_of_vocabulary for explicit unsupported concepts (with quote),
or not_applicable for a field that does not apply. Investment bullion has no human
wearer audience; a coin may have decorative motifs. Do not label every bullion
feature not_applicable. Do not use abstentions to hide available explicit detail.

Write one record per input hash, exactly {input_hash, label}. Confidence values are
uncalibrated metadata, not accuracy measurements. Never invent a human review.
Keep explicit per-row decision logs. Code may assemble already-decided rows or
reuse an explicitly inspected identical evidence pattern; keyword classifiers,
blanket category mappings, unread-row defaults, and automatic conversion of old
labels are not expert annotation. Inspect all evidence rows without truncation.
Parent validation and independent semantic review follow the ten sessions.

Use shared spellings for common details: mirror_polished, faceted, grooved,
hammered (surface_finish); woven_band, cord_band, leather_band, chain, bangle
(bracelet_form); stud, hoop, clip, threader, hook (earring_form); beaded,
disc_embellished, stone_embellished (decoration). A bangle inside a broad bracelet
category, or a chain inside necklaces, is subtype refinement rather than a conflict
by itself. Prefer concise feature-specific quotes where practical. Identical titles
are reviewed for consistent decisions, while differing explicit attributes can
justify differences. Preserve the original per-session decisions before coordinator
corrections and document every correction with source support.

Coordinator clarifications from the first sessions: record title-supported bangle
form consistently as bracelet_form=bangle, including a single rigid bangle; do not
create single_bangle as a separate form. A bare Simurgh bullion model is a named
theme (decoration=simurgh_theme), with ambiguous actual motif unless additional
descriptive evidence resolves it. A plainly oval bullion profile belongs in
decoration=oval_profile, not automatically a decorative motif. Birth-month symbols
use motif birth_month_symbol/symbolic plus motif_detail such as tir_month,
mordad_month or aban_month; do not infer a zodiac animal from calendar knowledge.

Explicit lotus-design wording supports lotus/plant; the ambiguity rule for a bare
collection name must not suppress a clear design phrase. An explicit name-design
phrase on a pendant can support name/text, without inferring a depicted person.
Decorative spiral, checkerboard and zigzag patterns use the corresponding motif
concepts in family geometric, rather than parallel decoration aliases. Raised
relief uses surface_finish=embossed. An explicitly named Quranic inscription uses
quranic_inscription/text; retain decoration=frequency_card when separately stated.
An explicitly single-stone ring uses ring_form=solitaire. General stone decoration
uses decoration=stone_embellished; neither establishes engagement or formal use.

Keep specificity within the evidence. An unspecified band is bracelet_form=band;
cord_band requires explicit cord/thread wording. Woven and leather bands retain
their stated construction. An Iran-themed design without map wording supports
decoration=iran_theme, not necessarily an iran_map motif. A bare Jewel model name
supports decoration=jewel_inspired, not actual stones without a stone description.
Use drop as the canonical earring form for explicitly hanging earrings.

Use slider_adjustable for an explicitly sliding bracelet adjustment,
plaque_embellished for an attached plaque, and continuous_pattern for a stated
continuous design. Arbitrary model identifiers or proper names without descriptive
motif content are not_stated; ambiguous is reserved for competing plausible readings.
Cloud belongs to the celestial family, which includes sky/weather designs. A
decorative knot is an object motif; an explicit infinity symbol remains separate.
Bare Mother/Mom references retain mother_theme rather than assuming lettering or
a figure. Explicit inscriptions and mother-and-child descriptions are separate
supported cases. Football-card player names support football_card and
football_player_theme decorations, not automatically a portrait motif.

Coordinator consolidation uses the versioned concept alias table at
`docs/datasets/gold-v2-concept-aliases.json`. This normalizes equivalent spellings
without treating them as new source evidence. Preserve particular letters as
letter/text plus motif_detail. Generic shell decoration does not prove the exact
mother-of-pearl composition. Named design references and fine motif details are
optional annotations; their coverage is not guaranteed exhaustive. A missing
optional detail is not a negative assertion about a physical product.
