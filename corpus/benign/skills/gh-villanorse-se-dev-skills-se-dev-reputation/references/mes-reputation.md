# MES (Modular Encounters Systems) reputation

Tags: **[HARD]** verified in MES 2.74.02 source, **[SOFT]** inferred, **[UNVERIFIED]** unchecked. For MES in general use the `se-dev-mes` skill.

## How MES changes reputation

- `ChangeReputationWithPlayers` (RivalAI action and MES Event action) -> `FactionHelper.ChangeReputationWithPlayersInRadius` ->
  `ChangePlayerReputationWithFactions` -> `RelationManager.SetReputationWithFaction` ->
  `MyAPIGateway.Session.Factions.SetReputationBetweenPlayerAndFaction`, then a sync message to the player's client. **[HARD]**
- So it goes through the vanilla setter: **a `StaticReputation` faction ignores every MES reputation action.** **[HARD]**
- It sets an absolute value (old + amount, clamped), so vanilla propagation to other factions never happens. **[HARD]**
- Early-out: if the current reputation is already <= -1500 and the change is negative, or >= 1500 and positive, the player is skipped. **[HARD]**
- The new value is clamped to `[ReputationMinCap, ReputationMaxCap]`. **[HARD]**
- Tags used with it: `[ReputationChangeRadius:]`, `[ReputationChangeFactions:]` (list), `[ReputationChangeAmount:]` (int list, paired 1:1 with the
  factions list or the change is dropped: "Faction Tag and Rep Amount Counts Do Not Match"), `[ReputationPlayerConditionIds:]`. **[HARD]**
- Related actions: `ChangeAttackerReputation` (uses `[ReputationChangesForAllAttackPlayerFactionMembers:]`) and `ChangeReputationBetweenFactions`
  (`[ChangeReputationPropagatesToPlayers:]`). **[HARD]** (call sites; not traced further)

## Parser gap on grid triggers

| Tag | `[RivalAI Action]` (grid trigger) | `[MES Event Action]` |
|---|---|---|
| `ReputationMinCap` | **not parsed** - always -1500 | parsed |
| `ReputationMaxCap` | **not parsed** - always 1500 | parsed |
| `ReputationChangesForAllRadiusPlayerFactionMembers` | **not parsed** - always false | parsed |

The fields exist in `ActionReferenceProfile.cs` with those defaults and are passed to the helper, but the tag dictionary has no entry for them;
`EventActionReference.cs` does. **[HARD]** Writing them on a grid-trigger action is a silent no-op. Workarounds **[SOFT]**: do the radius/faction-member
share and caps from an MES Event, or gate the grid-trigger action with conditions instead of caps.

## Checking it live

- `/MES.BehaviorDebug.Action.true` then `/MES.IGLBD` shows the action firing; a static faction produces no error, only no change. **[SOFT]**
- `rep_world.py` on the save after the test shows whether the stored value moved, and marks static factions `[STATIC: frozen]`. **[HARD]** (tool output)
