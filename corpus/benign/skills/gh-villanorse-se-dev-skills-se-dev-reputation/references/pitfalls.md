# Pitfalls and open questions

Tags: **[HARD]** verified, **[SOFT]** inferred, **[UNVERIFIED]** unchecked.

## Symptom -> cause

| Symptom | Cause | How to check / fix |
|---|---|---|
| Admin menu, a reputation mod, or MES actions don't change reputation with a faction | `StaticReputation:true` on that faction **[HARD]** | `rep_world.py` shows `[STATIC: frozen]`; set it false, zero vanilla multipliers if needed, reload |
| Reputation stuck at the faction's `StartingReputation` for everyone | same; the first write is forced to the starting value **[HARD]** | as above |
| Shooting/grinding an NPC changes reputation when you didn't want it to | vanilla `DamageSettings` multipliers **[HARD]** | override `DefaultReputationSettings` with `GrindingWelding/Damaging/Stealing/Killing` = 0 |
| Earned reputation drifts back over time | `ReputationDecayPerHour` **[HARD]** | set 0 in the economy definition |
| A faction you set `IsDefault:false` is still in the world | it already exists in the save, or a by-tag path created it (scenario prefab, agent bot, script) **[HARD]** | `rep_world.py` flags it; stop the source, then `rep_remove_faction.py` |
| Your faction definition change has no effect | another mod higher in the load order defines the same tag **[SOFT]** | `rep_world.py` prints the winning file |
| MES rep caps / faction-member sharing ignored on a grid trigger | tags not parsed on `[RivalAI Action]` **[HARD]** | `references/mes-reputation.md` |
| MES reputation change silently skipped for some players | already at +/-1500 in the direction of the change **[HARD]** | expected |

## Tooling traps

- Save identity names can contain private-use glyphs (SE icon characters); the scripts replace them instead of crashing a cp1252 console. **[HARD]**
- The vanilla economy `xsi:type` is `MyObjectbuilder_...` (lower-case b); match case-insensitively. **[HARD]**
- `rep_world.py` reads definitions from mod folders on disk; a mod missing locally is listed and skipped. **[HARD]**

## Open questions

- Exact default `MyReputationModifiers` and which callers propagate reputation to other factions. **[UNVERIFIED]**
- Whether `RemoveFaction` via the API cleans relations/bank accounts the way the save edit does. **[UNVERIFIED]**
- Load order: modeled as "top of the world's mod list wins". **[SOFT]** Confirm against a two-mod test if it matters.
