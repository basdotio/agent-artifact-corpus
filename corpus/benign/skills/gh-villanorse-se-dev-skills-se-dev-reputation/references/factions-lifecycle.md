# NPC faction lifecycle

Tags: **[HARD]** verified in `Sandbox.Game.dll` IL / vanilla data / a real save, **[SOFT]** inferred, **[UNVERIFIED]** unchecked.

## How factions get created

| Path | When | Respects `IsDefault`? |
|---|---|---|
| `MyFactionCollection.CreateDefaultFactions` (from `MySession.InitializeFactions`) | Every definition with `IsDefault:true` whose tag isn't in the save yet | yes - this is the only path that reads it **[HARD]** |
| `TryGetOrCreateFactionByTag` from the world generator (`OperationAddShipPrefab`, `OperationSetupBasePrefab`) | World creation from a scenario whose operations carry `<FactionTag>` | no **[HARD]** |
| `TryGetOrCreateFactionByTag` from `MyAgentBot.Init` | An agent/animal bot whose definition has `<FactionTag>` spawns | no **[HARD]** |
| `TryGetOrCreateFactionByTag` from `MyWorldGeneratorStartingStateBase.CreateAndSetPlayerFaction` | Starting-state player faction | no **[HARD]** |
| Mod API `IMyFactionCollection.CreateNPCFaction` / `CreateFaction` | Any script (e.g. AiEnabled creates its own bot factions) | no **[HARD]** |
| Player faction screen | Player creates one | n/a |

- `CreateDefaultFactions` skips a tag that already exists, so it never updates or replaces a saved faction. **[HARD]**
- Vanilla `Scenarios.sbx` scenario starts add `EasyStartPirate` and `Pirate_Base_Large_mk.2` prefabs with `<FactionTag>SPRT</FactionTag>`, so worlds
  created from them get `SPRT` even when a mod sets it `IsDefault:false`. **[HARD]**
- Workshop bot packs often tag bots `SPRT`/`SPID`/`FSTC`; any such bot spawning (as an agent bot) recreates the faction. **[HARD]** (e.g. a bot mod's
  `RobotBots.sbc`) Whether a given mod spawns its bots through `MyAgentBot` must be checked per mod: AiEnabled-spawned bots of an `FSTC`-tagged type did
  not create `FSTC` in a real save. **[HARD]** (observed) / **[SOFT]** (reason)

Telling them apart in a save: default-faction creation makes a *new NPC identity per faction* named after the definition's `Founder`,
created in sequence, so several consecutive founder identities (e.g. `SPRT`, `FCTM`, `UNKN` together) mean `CreateDefaultFactions` ran while
those definitions were `IsDefault:true`. A single faction whose definition is `IsDefault:false` came from one of the by-tag paths. **[SOFT]**
(inferred from identity ids in two real saves) `rep_world.py` flags "in save but IsDefault=false".

## What persists

- A faction, its members, its bank account, its relations and every player's reputation with it are all in `Sandbox.sbc`. **[HARD]**
- On load a faction re-reads from its definition (by tag): `AutoAcceptMember`, `AcceptHumans`, `EnableFriendlyFire`, display name/description,
  `Score`, `ObjectivePercentageCompleted`, `StartingReputation`, `StaticReputation`. **[HARD]** (`MyFaction(MyObjectBuilder_Faction)` ctor)
- Nothing removes a faction because its definition changed or disappeared. **[HARD]** (no such path found; factions only leave via `RemoveFaction`)

## The pirate identity

`MyPirateAntennas` (session component) stores `PiratesIdentity` in the save and, in `BeforeStart`, looks up the `SPRT` faction by tag and makes that
identity a member. It does not create the faction. **[HARD]** Removing `SPRT` leaves the identity in place without a faction; with drones/encounters
disabled this is harmless. **[SOFT]**

## Removing a faction from a save

Game closed (it rewrites `Sandbox.sbc` on save/exit). There is no binary cache for `Sandbox.sbc`; `SANDBOX_0_0_0_.sbsB5` caches entities only. **[HARD]** (real saves)

Elements that reference a faction id, all removed by `scripts/rep_remove_faction.py`: **[HARD]** (found in real saves)

- `<MyObjectBuilder_Faction>` block (`FactionId`, `Tag`, members, `DamageInflicted`, ...)
- identity -> faction `<item><Key>identity</Key><Value>factionId</Value></item>` entries (the player-faction map)
- `<MyObjectBuilder_FactionRelation>` entries with the id as `FactionId1`/`FactionId2`
- `<MyObjectBuilder_PlayerFactionRelation>` entries with the id as `FactionId`
- `<MyObjectBuilder_FactionRequests>` entries (none were present in the saves examined)
- the faction's own bank `<MyObjectBuilder_AccountEntry>` (`OwnerIdentifier` = faction id)

The script leaves NPC identities alone, keeps a timestamped backup, and re-parses the result as XML before writing. Stop the creation source first or the
faction comes back. Scripted alternative: `MyAPIGateway.Session.Factions.RemoveFaction(factionId)` on the server. **[HARD]** (API exists) / **[UNVERIFIED]**
(side effects not tested).
