# Five original ecommerce design directions

Five starting briefs for **new** ecommerce brands, each with a detailed customer and operator blueprint. They are design proposals, not finished websites and not copies of any store. Pick the one closest to the owner's business, read **only that direction's file**, and turn it into the project's own design contract. Never apply a direction to an existing brand without the owner's approval, and never mix several directions into one brand.

| Direction | Blueprint | Customer decision | Brand traits |
| --- | --- | --- | --- |
| D1 | [Considered living goods](ecommerce-direction-01.md) | Fit in space and physical delivery | calm, tangible, thoughtful |
| D2 | [Clear technical equipment](ecommerce-direction-02.md) | Compare specifications and configure options | exact, assured, organized |
| D3 | [Movement and fit apparel](ecommerce-direction-03.md) | Select style, size and availability | energetic but controlled, human, useful |
| D4 | [Informed beauty and personal care](ecommerce-direction-04.md) | Match shade, formulation and verified attributes | considerate, clear, inclusive |
| D5 | [Dependable digital access](ecommerce-direction-05.md) | Choose compatible entitlement and receive access | straightforward, secure, dependable |

Each blueprint maps every C01–C20 and A01–A12 route (marking irrelevant ones), and lists identity, media, card roles, motion IDs, a prototype gate and a failure test. Its colour pairs are illustrative: verify them with `scripts/contrast_check.py` in the real UI states. The text pairs pass comfortably (about 7:1 to 16:1), but every listed divider sits between 1.6:1 and 2.8:1 against its canvas. That is fine for decorative dividers only: input, checkbox and other control borders need a separate border role at 3:1 or more. The shared [asset register](ecommerce-assets.md), [responsive specification](ecommerce-responsive.md) and [transaction traces](ecommerce-transaction-traces.md) apply only to the routes and business conditions the chosen direction actually has.

## From brief to real site

1. Review the direction with the owner: brand traits, page order, available data, media rights, filters, core card, and whether each motion is needed.
2. Write the project's design contract (`assets/templates/design-contract.md`) with the real name, identity, content and verified token colours and font rights.
3. Build and verify the pages the business needs, in task order, using the lanes in SKILL.md.

Report status honestly as `brief → owner-approved brand → working pages → verified in a real project`. A coloured homepage is not a completed direction. For the skill itself, a sector counts as validated when one real project has been built or audited with it end to end and its evaluation set passes (see [sector-program.md](sector-program.md)); five complete prototypes are not required.
