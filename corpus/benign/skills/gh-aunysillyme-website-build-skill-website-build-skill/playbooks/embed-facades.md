# Load providers after deliberate activation

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: how can a visitor choose a player without paying its cost on arrival?

## Validate the control

Require a valid provider ID and an allowed destination before rendering a facade.
Use the selected provider's current identifier and URL requirements.
An absent or whitespace-only ID omits the entire control and records the omission.
Do not replace it with a dead iframe, empty suffix, or empty link.

## Render a local first state

Show a local authorized poster, a useful description, and a real button.
Reserve player space using actual aspect ratio to prevent layout shifts.
Give the button an accessible action name, not only a play-shaped icon.
Keep a safe outbound link available when loading or embedding fails.
Do not fetch provider posters, preconnect, or inject provider SDKs before activation.

## Implement a bounded state transition

```text
idle -> deliberate button activation -> loading -> ready
loading -> error -> retry or safe outbound fallback
ready + repeated activation -> no second iframe
invalid identifier -> no facade and no outbound provider control
```

Create the iframe only on intentional keyboard or pointer activation.
Set its title, reviewed source, and minimum necessary permissions.
Select sandbox behavior from the provider's actual requirements and test it.
Keep focus predictable while replacing content and announce loading/error states.
Do not remove the focused button without a deliberate focus destination.
Provide a no-JavaScript path to the approved outbound destination.

## Verify the network boundary

Start a clean browser session without cached provider resources.
Inspect requests before activation: no iframe, poster, script, or provider connection.
Activate by keyboard and pointer in separate checks.
Inspect requests, layout stability, focus, error recovery, and repeated activation.
Test with production CSP and network failure, including blocked third-party cookies.
Record exact route, candidate, environment, request log, and results.
Apply checklists/build.md B04 and checklists/performance-seo.md PS03.

## Failure modes and sources

- Cosmetic facade: a hidden iframe already fetched the provider.
- Remote poster: the first state still contacts the provider.
- Lost focus: swapping markup strands a keyboard user.
- Overbroad policy: frame permissions allow unrelated origins or capabilities.

Open the chosen provider's official embedding documentation and current browser
iframe documentation. Retain the source ledger and network inspection evidence.
Click-to-play is a performance/privacy boundary, not proof of consent compliance.
