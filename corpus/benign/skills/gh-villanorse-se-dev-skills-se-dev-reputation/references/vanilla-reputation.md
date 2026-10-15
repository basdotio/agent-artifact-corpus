# Vanilla reputation

Tags: **[HARD]** verified in `Sandbox.Game.dll` IL / vanilla `.sbc` / a real save, **[SOFT]** inferred, **[UNVERIFIED]** unchecked.

## Storage

- Player<->faction reputation lives in `MyFactionCollection.m_relationsBetweenPlayersAndFactions`, keyed by (identity, faction),
  value `(relation, reputation)`. **[HARD]**
- Saved in `Sandbox.sbc` as `<MyObjectBuilder_PlayerFactionRelation>` (`PlayerId`, `FactionId`, `Relation`, `Reputation`).
  Faction<->faction entries are `<MyObjectBuilder_FactionRelation>` (`FactionId1`, `FactionId2`). **[HARD]** (real save)
- A player with no entry has no stored value; the faction's default relationship/starting reputation applies. **[SOFT]**

## Every change path ends in `ChangeReputationWithPlayer`

| Caller | Route | Notes |
|---|---|---|
| Admin menu (reputation tab) | `MyGuiScreenAdminMenu.RequestChangeReputation` -> `AddFactionPlayerReputation` | **[HARD]** |
| Mod API `SetReputationBetweenPlayerAndFaction` | -> `MyFactionCollection.SetReputationBetweenPlayerAndFaction` -> `ChangeReputationWithPlayer` | used by MES **[HARD]** |
| Contracts (finish/fail, hunt, bounty) | `AddFactionPlayerReputation` | **[HARD]** |
| Vanilla damage | `DamageFactionPlayerReputation` -> `GetReputationDamageDelta` -> `AddFactionPlayerReputation` | **[HARD]** |
| Decay | `MySessionComponentEconomy.HandleReputationDecay` -> `AddFactionPlayerReputation` | **[HARD]** |
| Visual scripting | `MyVisualScriptLogicProvider.SetRelationBetweenPlayerAndFaction` | **[HARD]** |
| Faction relation changes | `ChangeFactionRelation` / `ForceRelationToPlayers` | **[HARD]** |

`AddFactionPlayerReputation` is server-only, builds a change list in `GenerateChanges`, raises a sync event and calls
`AddFactionPlayerReputationSuccess`, which calls `ChangeReputationWithPlayer` per change. **[HARD]**

## StaticReputation

Decoded from `ChangeReputationWithPlayer(identity, faction, reputation, reason)`: **[HARD]**

```csharp
bool hasEntry = m_relationsBetweenPlayersAndFactions.ContainsKey(pair);
if (TryGetFactionById(faction) is MyFaction f && f.StaticReputation) {
    if (hasEntry) return;                         // frozen
    if (f.StartingReputation.HasValue)
        reputation = f.StartingReputation.Value;  // first write is forced to the starting value
}
// ... fire FactionReputationChanged, translate to relation, store
```

- Applies to every row of the table above, admin included. There is no bypass flag. **[HARD]**
- The "reputation changed" notification is also suppressed for static factions (`AddFactionPlayerReputationSuccess`). **[HARD]**
- `DamageFactionPlayerReputation`, `ChangeRelationWithPlayer` and `ForceRelationToPlayers` check it too. **[HARD]**
- The flag is re-read from the faction definition (looked up by tag) every time a world loads, both for new and loaded factions. **[HARD]**
  Existing frozen values stay as they are after un-static'ing, but can change from then on.

## Vanilla damage reputation (`ReputationSettings.sbc`)

`MyObjectBuilder_ReputationSettingsDefinition`, subtype `DefaultReputationSettings`, with `DamageSettings` (normal factions)
and `PirateDamageSettings` (the pirate faction): **[HARD]**

```xml
<ReputationLossDamage>200</ReputationLossDamage>
<GrindingWelding>1</GrindingWelding>
<Damaging>1</Damaging>
<Stealing>1</Stealing>
<Killing>0</Killing>
```

- Accumulated damage per player is kept in the faction (`MyFaction.DamageInflicted`); the delta is roughly
  `DamageInflicted / ReputationLossDamage * <multiplier for the damage type>`. **[HARD]** (IL of `GetReputationDamageDelta`)
- Set all four multipliers to `0` to turn off vanilla damage reputation while keeping reputation changeable by scripts. **[HARD]** (multiplier is a factor)
- `MaxReputationGainInTime` / `ResetTimeMinForRepGain` are only read by `CheckIfMaxPirateRep`: they cap reputation *gain with the pirate faction*
  within a time window. **[HARD]**

## Relations, thresholds, decay (`SessionComponents_Economy.sbc`)

- `TranslateReputationToRelationship` compares against the economy definition's `ReputationHostileMin`, `ReputationNeutralMin`,
  `ReputationFriendlyMin`, `ReputationFriendlyMax`. Vanilla -1500 / -500 / 500 / 1500: below -500 is hostile, -500 to 499 neutral,
  500+ friendly. **[HARD]** (fields) / **[SOFT]** (exact enum mapping)
- `ReputationDecayPerHour` (vanilla 50) drives `HandleReputationDecay`, which moves an NPC faction's reputation toward
  `GetEffectiveStartingReputation(faction)`. Set 0 to disable. **[HARD]** (field use) / **[SOFT]** (target for each faction type)
- `ReputationPlayerDefault` feeds `GetDefaultReputationPlayer`. **[HARD]**
- The economy definition's `PirateId` names the faction definition treated as "the pirates" for pirate-only rules. **[HARD]**
- Note the vanilla definition's `xsi:type` is spelled `MyObjectbuilder_SessionComponentEconomyDefinition` (lower-case b). **[HARD]**

## Propagation to other factions

`GenerateChanges` can also change reputation with *other* factions based on each one's relation (Neutral/Hostile/Friend) to the
target faction, using `MyReputationModifiers` from the economy component. **[HARD]** (IL) Which callers pass the propagate flag and
the default modifier values were not traced. **[UNVERIFIED]** `SetReputationBetweenPlayerAndFaction` (mod API) does not go through
`GenerateChanges`, so it never propagates. **[HARD]**
