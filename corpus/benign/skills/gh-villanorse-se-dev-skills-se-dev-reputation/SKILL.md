---
name: se-dev-reputation
description: Use this skill when working on Space Engineers faction reputation or the NPC faction lifecycle, for example StaticReputation, reputation that won't change, vanilla damage and decay reputation, ReputationSettings and economy thresholds, MES ChangeReputation actions, or unwanted factions (SPRT and others) appearing in a world and removing them from a save.
---

# Space Engineers Reputation & NPC Factions

General guide to how vanilla SE stores and changes player<->faction reputation, how NPC factions get created and why
they never go away, and how mods (MES) change reputation. Nothing here is specific to one project. Claims are tagged:

- **[HARD]** verified in a file or source I opened (decompiled/IL of `Sandbox.Game.dll`, a real save, MES `.cs` source, vanilla `.sbc`)
- **[SOFT]** inferred from code or standard behavior, not observed running
- **[UNVERIFIED]** plausible but unchecked - test before relying on it

Source examined: SE `Bin64\Sandbox.Game.dll` (IL of `MyFactionCollection`, `MyFaction`, `MySessionComponentEconomy`, `MyAgentBot`,
`MyPirateAntennas`, world generator), vanilla `Content\Data`, MES 2.74.02, two real world saves. **[HARD]** Re-check after SE updates.

## Core model (read this first)

1. **Everything funnels into one setter.** `MyFactionCollection.ChangeReputationWithPlayer` is reached by the admin menu,
   the mod API `IMyFactionCollection.SetReputationBetweenPlayerAndFaction` (MES uses this), contracts, vanilla damage,
   decay and visual scripting. **[HARD]** Details: `references/vanilla-reputation.md`.
2. **`StaticReputation` freezes reputation for every path, not just damage.** In that setter, a static faction returns
   early if the player already has a value, or forces `StartingReputation` on the first write. **[HARD]**
   A reputation mod/admin command that "does nothing" against a faction is almost always this.
3. **Vanilla damage reputation is controlled by `ReputationSettings.sbc`** (`DefaultReputationSettings`): loss =
   `damage / ReputationLossDamage * <GrindingWelding|Damaging|Stealing|Killing>`. Set the multipliers to 0 to switch it off
   without making the faction static. **[HARD]**
4. **Decay pulls reputation back toward the faction's starting value** at `ReputationDecayPerHour` (economy definition,
   vanilla 50). Set it to 0 to keep earned reputation. **[HARD]** (field use) / **[SOFT]** (exact target per faction type)
5. **Factions persist in the save forever.** Definitions only decide what is *created*; nothing deletes a faction whose
   definition changes. **[HARD]** See `references/factions-lifecycle.md`.

## The traps that cost the most time

- **`IsDefault:false` does not keep a faction out.** It only skips default-faction creation for *new* worlds. Scenario
  starts (`AddShipPrefab` with `<FactionTag>`), agent bots with a `<FactionTag>`, and the mod API all create factions by tag,
  ignoring `IsDefault`. **[HARD]** A vanilla scenario start creates `SPRT`. **[HARD]** (`Scenarios.sbx`)
- **Changing `IsDefault`/`StaticReputation` doesn't touch existing factions' membership, but `StaticReputation`,
  `StartingReputation`, `AcceptHumans`, `AutoAcceptMember`, `EnableFriendlyFire` ARE re-read from the definition on every load**
  (`MyFaction(MyObjectBuilder_Faction)` ctor looks the definition up by tag). **[HARD]** So un-static'ing a faction works on an
  existing save after a reload.
- **Removing a faction means editing `Sandbox.sbc`** (game closed) or calling `IMyFactionCollection.RemoveFaction` from a script.
  **[HARD]** (API exists) - `scripts/rep_remove_faction.py` does the save edit safely.
- **MES grid-trigger reputation caps don't parse.** On `[RivalAI Action]`, `[ReputationMinCap:]`, `[ReputationMaxCap:]` and
  `[ReputationChangesForAllRadiusPlayerFactionMembers:]` have no parser (only MES Event actions parse them). Defaults
  -1500 / 1500 / false always apply. **[HARD]** See `references/mes-reputation.md`.
- **Mod load order decides which definition wins.** Mods higher in the world's mod list override lower ones. **[SOFT]**
  `rep_world.py` shows which file each effective faction definition came from.

## Workflow

1. **See what the world really has**: `python scripts/rep_world.py "<save folder>" --defs` - factions in the save, the effective
   definition flags for each (and which mod set them), every human player's reputation with a Hostile/Neutral/Friendly
   reading, frozen (static) entries marked, plus the effective ReputationSettings/economy values. Read-only.
2. **Reputation won't move**: check the `[STATIC: frozen]` marks. Switch the faction to `StaticReputation:false` and zero the
   damage multipliers / decay if you only wanted to block vanilla mechanics. Reload the world.
3. **Unwanted faction in the save**: find how it was created (`references/factions-lifecycle.md`), stop the source, then with the
   game closed: `python scripts/rep_remove_faction.py "<save folder>" --tags SPRT` (dry run) and again with `--apply`.

## Scripts (Python 3.8+, stdlib only; tested on real saves)

| Script | Purpose |
|---|---|
| `scripts/rep_world.py` | Report factions, effective definitions (with source file), player reputation, settings |
| `scripts/rep_remove_faction.py` | Remove factions by tag from `Sandbox.sbc`: dry run, backup, XML re-parse before writing |
| `scripts/rep_common.py` | Save parser + definition resolver (vanilla, then mods bottom-to-top of the mod list) |

Paths default to a Steam install on `C:`; override with `--game`, `--workshop`, `--mods`.

## References

- `references/vanilla-reputation.md` - storage, every change path, StaticReputation, damage formula, decay, thresholds, propagation, pirate cap
- `references/factions-lifecycle.md` - how factions get created, what persists, the pirate identity, removing a faction from a save
- `references/mes-reputation.md` - MES reputation actions, the API they use, parser gaps, early-outs
- `references/pitfalls.md` - symptom -> cause table and open questions
