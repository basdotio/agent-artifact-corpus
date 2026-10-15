"""Report factions and reputation for a Space Engineers world save.

python rep_world.py <world folder> [--defs] [--player NAME] [--game DIR] [--workshop DIR] [--mods DIR]

Default output: every faction in the save with its founder/members, the effective definition
flags that apply to it (IsDefault, StaticReputation, StartingReputation, and which file set them),
and each human player's reputation with it.
--defs   also print the effective ReputationSettings / economy reputation values and their source.
--player limit the reputation table to players whose name contains NAME.
Read-only; safe to run while the game is open.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rep_common as rc


def relation(rep, eco):
    """Mirrors MySessionComponentEconomy.TranslateReputationToRelationship thresholds."""
    try:
        nmin = int(eco["ReputationNeutralMin"]); fmin = int(eco["ReputationFriendlyMin"])
    except (TypeError, KeyError, ValueError):
        nmin, fmin = -500, 500
    if rep < nmin:
        return "Hostile"
    if rep < fmin:
        return "Neutral"
    return "Friendly"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--defs", action="store_true")
    ap.add_argument("--player", default="")
    ap.add_argument("--game", default=rc.DEFAULT_GAME)
    ap.add_argument("--workshop", default=rc.DEFAULT_WORKSHOP)
    ap.add_argument("--mods", default=rc.DEFAULT_LOCAL_MODS)
    a = ap.parse_args()
    if not os.path.exists(os.path.join(a.world, "Sandbox.sbc")):
        rc.die("no Sandbox.sbc in " + a.world)

    w = rc.World(a.world)
    defs, missing = rc.load_definitions(a.world, a.game, a.workshop, a.mods)
    eco = defs.economy or {}

    print("World: %s" % a.world)
    if missing:
        print("  (mods not found on disk, their definitions are ignored: %s)" % ", ".join(missing))
    print("\nFactions in the save:")
    for f in sorted(w.factions.values(), key=lambda x: x["tag"] or ""):
        d = defs.factions.get(f["tag"])
        founder = [i for i, fo, _ in f["members"] if fo]
        fname = w.identities.get(founder[0], "?") if founder else "-"
        flags = "no definition (player faction?)"
        warn = ""
        if d:
            flags = "IsDefault=%s Static=%s StartRep=%s" % (d["IsDefault"], d["StaticReputation"], d["StartingReputation"])
            if d["IsDefault"] != "true":
                warn = "  <- in save but IsDefault=false: created by tag/API/scenario, not by default-faction creation"
        print("  %-8s %-24s id=%s members=%d founder=%s%s" % (f["tag"], f["name"], f["id"], len(f["members"]), fname, warn))
        print("           %s" % flags)
        if d:
            print("           def: %s" % d["source"])
    notin = [t for t, d in defs.factions.items() if d["IsDefault"] == "true" and t not in w.by_tag]
    if notin:
        print("\n  IsDefault=true definitions with no faction in the save (created only for NEW worlds): %s" % ", ".join(sorted(notin)))
    if w.pirates_identity:
        print("\n  PirateAntennas identity: %s (%s), faction %s" % (
            w.pirates_identity, w.identities.get(w.pirates_identity, "?"),
            w.ftag(w.member_map.get(w.pirates_identity, ""))))

    humans = w.humans()
    rows = [r for r in w.player_rep if r[0] in humans and a.player.lower() in humans[r[0]].lower()]
    print("\nPlayer reputation (humans only):")
    if not rows:
        print("  none stored (a player with no entry uses the faction's starting/default reputation)")
    for pid, fid, rep in sorted(rows, key=lambda r: (humans[r[0]], w.ftag(r[1]))):
        d = defs.factions.get(w.ftag(fid))
        lock = "  [STATIC: frozen]" if d and d["StaticReputation"] == "true" else ""
        print("  %-24s %-8s %6d  %-8s%s" % (humans[pid], w.ftag(fid), rep, relation(rep, eco), lock))

    if a.defs:
        print("\nEffective reputation settings:")
        rs = defs.rep_settings
        if rs:
            print("  ReputationSettings from %s" % rs["source"])
            for sec in ("DamageSettings", "PirateDamageSettings"):
                if sec in rs:
                    print("    %-21s %s" % (sec, " ".join("%s=%s" % kv for kv in rs[sec].items())))
            print("    MaxReputationGainInTime=%s ResetTimeMinForRepGain=%s (pirate faction gains only)" % (
                rs.get("MaxReputationGainInTime"), rs.get("ResetTimeMinForRepGain")))
        if eco:
            print("  Economy from %s" % eco["source"])
            print("    " + " ".join("%s=%s" % (k.replace("Reputation", ""), v) for k, v in eco.items() if k != "source"))
        print("  %d definition sources applied: vanilla, then mods bottom-to-top of the world's mod list" % len(defs.sources))


if __name__ == "__main__":
    main()
