# Word choices

This list gives words and phrases to avoid and simpler replacements. It
supports rules W1, W2, W4, W5, V3, V4, and W7 in [rules.md](rules.md).

This list is original to this project. It is **not** the ASD-STE100
dictionary and it does not replace it. It contains common plain-language
replacements. It also contains some examples of the one-word-one-meaning
principle from the public FAQ of ASD (Aerospace, Security and Defence
Industries Association of Europe).

## How to use this list

- **From level**: the lowest level at which the replacement is required. At
  lower levels, the replacement is only a suggestion.
- **Lint**: `yes` if `scripts/check.py` flags the phrase automatically. `no`
  if the problem depends on the meaning, so only a human or a model can find
  it.
- Replace a phrase only when the replacement keeps the meaning. Do not
  replace a word that is part of a term, a UI label, a code element, or a
  quotation.
- Projects can add their own entries with `avoid_words` and
  `preferred_terms` in the configuration file (see
  [configuration.md](configuration.md)).

The checker reads the table below. Keep the five columns. Separate
alternatives in the **Avoid** column with a comma.

## List

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| utilize, utilise | use | 1 | yes | |
| in order to | to | 1 | yes | |
| prior to | before | 1 | yes | |
| subsequent to | after | 1 | yes | |
| due to the fact that, owing to the fact that | because | 1 | yes | |
| in the event that | if | 1 | yes | |
| at this point in time, at the present time | now | 1 | yes | |
| a large number of, numerous | many | 1 | yes | |
| a majority of | most | 1 | yes | |
| has the ability to, is able to | can | 1 | yes | |
| with regard to, with respect to, in regard to, in relation to, regarding | about | 1 | yes | "about" here means "concerned with". |
| commence, initiate | start | 1 | yes | |
| terminate | stop | 1 | yes | Keep "terminate" if it is a technical verb of your domain (for example, a process signal). |
| endeavor, endeavour | try | 1 | yes | |
| demonstrate | show | 1 | yes | |
| assistance | help | 1 | yes | |
| leverage | use | 1 | yes | Only as a verb. |
| sufficient | enough | 1 | yes | |
| accomplish, achieve, carry out | do | 1 | yes | |
| it is recommended that, it is recommended to | (give the instruction directly) | 1 | yes | "Restart the service." |
| click on | click | 1 | yes | |
| simply, just, easily, obviously | (delete the word) | 1 | yes | The word does not help the reader. It can also make the reader feel slow. |
| basically, actually, really, very | (delete the word) | 1 | yes | |
| the former, the latter | (repeat the term) | 1 | yes | |
| as soon as possible, ASAP | (give a time) | 1 | yes | Rule W7. |
| etc., and so on | (give the full list) | 1 | yes | Rule W7. |
| properly, appropriate, appropriately, as needed, if needed, if necessary | (give the criterion) | 1 | yes | Rule W7. |
| be careful, use caution | (give the specific instruction and the risk) | 1 | yes | Rule SF3. |
| begin | start | 2 | yes | |
| perform | do | 2 | yes | Often you can use the action verb: "perform a scan" becomes "scan". |
| ensure | make sure | 2 | yes | |
| additional | more, other | 2 | yes | |
| attempt | try | 2 | yes | Only as a verb. |
| modify | change | 2 | yes | |
| navigate to | go to | 2 | yes | |
| is located in, are located in | is in, are in | 2 | yes | |
| in addition | also | 2 | yes | |
| via | through, with | 2 | yes | |
| e.g. | for example | 2 | yes | |
| i.e. | that is | 2 | yes | |
| in case | if | 2 | yes | |
| respectively | (write separate sentences) | 2 | yes | |
| please | (delete the word in instructions) | 2 | yes | Keep it in messages to a person, if the style guide requires it. |
| should, may, might, could, would | must, can, do not | 2 | yes | Rule V5. |
| once | after, when | 2 | no | Only when "once" means "after". "Once" can also mean "one time". |
| since | because | 2 | no | Only when "since" means "because". |
| while | but, although | 2 | no | Only when "while" shows a contrast, not a time. |
| as | because | 2 | no | Only when "as" means "because". |
| verify | make sure, examine | 3 | yes | |
| allow, permit | let | 3 | yes | |
| require, requires, required | must, be necessary | 3 | yes | Keep "required" if it is a UI label or a field property. |
| display | show | 3 | yes | Only as a verb. Keep "display" as a noun for a screen. |
| indicate | show | 3 | yes | |
| provide | give, supply | 3 | yes | |
| however | but | 3 | yes | |
| check | examine, do a check of, make sure | 3 | no | ASD-STE100 approves "check" only as a noun. "Do a check of the log" is correct. "Check the log" is not. |
| about | approximately | 3 | no | ASD-STE100 approves "about" only with the meaning "concerned with". |
| fall | decrease | 3 | no | Only when "fall" means "decrease". ASD-STE100 approves "fall" only for movement down. |
<!-- controlled-language: on -->
