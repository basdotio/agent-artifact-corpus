# Writing Style

Every field value in a test case must follow these rules. This isn't a matter of
taste - inconsistent style across test cases makes the file harder to scan and
harder for another skill to parse reliably later.

- No em dash (—). Use a period, a comma, or parentheses instead.
- No hedge filler: "it's worth noting", "in essence", "at the end of the day", "it's
  important to understand that", "essentially", "basically".
- No inflated adjectives unless a specific fact earns them. Avoid "robust",
  "seamless", "powerful", "comprehensive", "cutting-edge", "intuitive" as filler.
- No preamble or postamble inside a field value. State the fact. Don't write "This
  test verifies that..." before the actual content - the field label already says
  what it is.
- No preamble before the file's content either. Don't open a generated file with
  something like "Here are the generated test cases:". Start directly with content.
- Steps must be concrete, literal actions a person or a script could follow exactly:
  "Tap the Login button", not "Interact with the login flow appropriately".
- Sentences are short and declarative. One idea per sentence.
- A field value is scannable, not a paragraph. If a value needs more than two
  sentences to state, it's probably the wrong field, or the test case is trying to
  cover more than one behavior and should be split.

## Before / after

**Before (avoid this):**
> Expected: The system will seamlessly authenticate the user, leveraging Google's
> robust OAuth flow, and appropriately redirect them to the home screen once the
> process is properly completed.

**After:**
> Expected: User lands on Home screen. Session token is stored.

**Before (avoid this):**
> Steps: The user should interact with the login form in an appropriate manner,
> ensuring valid credentials are entered before proceeding.

**After:**
> Steps:
> 1. Enter a valid email and password
> 2. Tap the Login button
