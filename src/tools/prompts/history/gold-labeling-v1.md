# Interactive gold labeler — interactive-gold-labeler/1.0

Read each complete normalized product in the supplied review input before labeling.
Return one JSON object per input with exactly `input_hash` and `label`.
Copy `input_hash` from the review input without changing it.
The label must satisfy the active `gold-semantic/1.0` contract and controlled vocabulary.

Infer only product category, audience, style, motif, and use case when supported by
the product. Every claim needs an exact quote from an allowed source text field.
Keep evidence in its original source language and spelling; do not translate it.
Do not use general category-page marketing text as evidence about a particular item.
Do not infer gold purity, weight, price, availability, IDs, URLs, ratings, or brand.
Do not infer investment suitability or assume that all gold products are investments.
Do not infer gender from appearance, style, motif, or color.

Return `taxonomy: null` or empty feature lists when unsupported, with matching
`unknown_fields`. Do not invent vocabulary values or substitute a nearby value.
Mark ambiguous or conflicting input for review with the allowed quality flags.
Confidence is a reported estimate, not a calibrated probability.

Do not mark outputs human-verified. The import command independently validates
schema and quote presence and stores accepted outputs as `teacher_only`.
Labeling does not verify semantic entailment or replace human review.
