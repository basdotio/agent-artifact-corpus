# Streak: scope

**Client:** a fictional client, for this example
**Prepared by:** Coleoni
**Version:** 0.1, from the briefing of 14 and 15 September 2026
**Status:** draft for review

## 1. Summary

The client has the game in a Figma file and in a few messages: a dark grid, one green pixel that jumps around, and the player following it with the mouse. Today it is only a picture. The client wants it playable at streak.coleoni.com, in English and Portuguese, and good enough to be recorded and posted.

The first release is one loop and nothing around it: follow the green pixel, keep the streak, and when the energy runs out, spend the pixels on upgrades. No sign-up, no ranking. Progress stays in the browser.

In one sentence: open the page, and you are already playing.

## 2. The problem

The one pain, in the client's words: **"todo joguinho de navegador pede conta antes de jogar"** (every little browser game asks for an account before you can play), followed by "cadastro, confirmar email, aí eu já desisto" (WhatsApp, 14 Sep, 09:12). What the client wants instead is in the same message: "tem que abrir e já jogar".

The other pains, and where they go:

- Not knowing how many people play each day (11:05): first release, with the analytics tag the client already uses.
- Wanting a ranking and a daily challenge (10:02): roadmap. Both need accounts, which is the pain itself on day one.
- A game that flashes fast and may bother people sensitive to light (16:10): first release, as a requirement (section 7).

## 3. First release

### The page, at streak.coleoni.com

- One page: the board on top, a short "how it works" section under it, and only "Feito por Coleoni" at the bottom (notes).
- It opens straight into the game: no sign-up, no email, no tutorial screen (09:12).
- The Google Analytics tag, so the daily player count shows up where the client already looks (11:05).

### The board

- A dark grid with one green pixel, ported from the Figma file (09:20).
- The player follows the pixel with the mouse; each catch in a row raises the streak and the multiplier; faster is better (09:12).
- Energy that runs out and ends the run; the run's pixels go to the wallet (09:12). How energy drains is question 1.
- One line of hint under the board, such as "Follow the green with your mouse." No tutorial (09:12).

### Between runs

- Upgrades bought with the pixels from the runs (09:12). The list and the prices are a balancing task (question 4), not a scope item.
- Best streak and pixels kept in the browser, so a returning player keeps them with no account (09:12).

## 4. Out of scope (and why)

Each line names what already does the job. The first release integrates with the analytics tag only; later phases may send data to the others, never rebuild them.

| Need | Stays in | Why |
| --- | --- | --- |
| Recording and posting clips | TikTok and the phone's screen recorder | The game only has to look good on video (09:41) |
| Sign-in and passwords | Google account | "se tiver conta, só com google, nada de senha" (10:02). No password system of our own, ever |
| Counting players per day | Google Analytics | Already in use: add the tag, no stats screen inside the game (11:05) |
| The look of the board | The Figma file | Port the dark grid and the green, do not redesign them (09:20) |
| Sending a score to friends | WhatsApp | The phone's share button already sends text (10:30) |
| Talking to players | Instagram direct messages | No contact form and no support page (15 Sep, 08:50) |
| Accounts and synced save | Roadmap | Day one works without them: progress stays in the browser |
| Global ranking and daily challenge | Roadmap | Needs accounts and a server that checks runs (10:02) |
| Days in a row, achievements, zen mode | Roadmap | Need real players to tune (notes) |
| A share card, like Wordle's squares | Roadmap | Comes with the daily challenge, which gives it something to share (10:30) |

## 5. Who uses it

| Who | What they do in the first release |
| --- | --- |
| Player | Plays without signing up, buys upgrades; progress kept in that browser |
| Client | Reads the daily player count in Google Analytics. No admin screen |

## 6. Roadmap

1. **Optional accounts with Google, synced save.** Waits because day one works without it; it comes before any ranking (10:02).
2. **Daily challenge, Wordle style:** one run a day, the same for everyone, with a global ranking. Waits for accounts and a server that checks runs (10:02).
3. **Days in a row and achievements.** Wait for data on how often players come back (notes).
4. **A share card for WhatsApp**, like Wordle's squares (10:30). Waits for the daily challenge.
5. **Zen mode, play without energy** (notes). Waits until the balancing of the main loop settles.

## 7. Requirements

- **Light warning:** a notice before the first run, because the game flashes fast, and a way to turn effects down (16:10).
- **Devices:** desktop with a mouse; phone is question 2 (15:48).
- **Languages:** English and Portuguese, switched on the page (notes).
- **Video:** smooth on a screen recording, with the green readable on a phone screen (09:41).
- **Copy:** short, second person to the player, no emoji.
- **Privacy:** the game keeps no personal data. The analytics tag follows the consent rules for visitors (LGPD); accounts, later, need a clear notice.

## 8. Deadline

The target: "dá pra ter algo jogável até sexta?" (14 Sep, 09:20), five days from the first message.

By Friday a playable loop can be tested: board, pixel, streak, multiplier, the end of a run. The upgrades, the light warning, the "how it works" section and the publish at streak.coleoni.com do not fit in five days; they fit in a second round the following week.

The biggest threat is accounts, the ranking and the daily challenge creeping in before the loop is fun. Each one needs a server, and none of them helps the first ten seconds.

## 9. Open questions

1. **What ends a run?** Energy that drains with time and refills with catches, a timer, or a miss. Blocks the board.
2. **Phone in the first release?** Players from TikTok are mostly on phones; the client asked "com o dedo?" (15:48). Blocks the input.
3. **The Figma file itself.** The 09:15 message is a screenshot, not the file. Blocks the final look, not the loop.
4. **How long should the upgrades last** for a regular player before they run out? Blocks the balancing.
5. **Which Google Analytics property** gets the tag, and who has access to it. Blocks the publish.
6. **Who creates the `streak` subdomain** and points it to the host. Blocks the publish.

## 10. Suggested approach

A single static page with the board drawn in a canvas, served as static files from any host. No server and no database in the first release: progress in the browser. A server and a database arrive only with accounts, on the roadmap.
