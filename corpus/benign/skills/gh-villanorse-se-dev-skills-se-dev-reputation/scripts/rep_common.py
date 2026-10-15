"""Shared helpers for the se-dev-reputation scripts (Python 3.8+, stdlib only).

- Reads a world's Sandbox.sbc (factions, members, identities, player<->faction and
  faction<->faction reputation) with regexes, so multi-MB saves load quickly.
- Resolves the faction / reputation / economy definitions a world actually uses:
  vanilla Content\\Data first, then the world's mods from the bottom of the mod list
  to the top (top of the list = highest priority, applied last).
"""
import os
import re
import sys

try:  # names in saves can hold private-use glyphs; don't crash a cp1252 console
    sys.stdout.reconfigure(errors="replace")
except (AttributeError, ValueError):
    pass

def _env(name, default=""):
    return os.environ.get(name, default)

DEFAULT_GAME = r"C:\Program Files (x86)\Steam\steamapps\common\SpaceEngineers"
DEFAULT_WORKSHOP = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\244850"
DEFAULT_LOCAL_MODS = os.path.join(_env("APPDATA"), "SpaceEngineers", "Mods")


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8", errors="replace")


def strip_comments(s):
    return re.sub(r"<!--.*?-->", "", s, flags=re.S)


def tag(block, name, default=None):
    m = re.search(r"<" + name + r">([^<]*)</" + name + r">", block)
    return m.group(1).strip() if m else default


# ----------------------------------------------------------------------------- save

class World:
    def __init__(self, folder):
        self.folder = folder
        self.path = os.path.join(folder, "Sandbox.sbc")
        self.text = read_text(self.path)
        s = self.text
        self.factions = {}      # id -> dict(tag, name, members[list of (identity, is_founder, is_leader)])
        for m in re.finditer(r"<MyObjectBuilder_Faction>.*?</MyObjectBuilder_Faction>", s, re.S):
            b = m.group(0)
            fid = tag(b, "FactionId")
            members = [(tag(mb, "PlayerId"), tag(mb, "IsFounder") == "true", tag(mb, "IsLeader") == "true")
                       for mb in re.findall(r"<MyObjectBuilder_FactionMember>.*?</MyObjectBuilder_FactionMember>", b, re.S)]
            self.factions[fid] = {"id": fid, "tag": tag(b, "Tag"), "name": tag(b, "Name"),
                                  "type": tag(b, "FactionType"), "members": members}
        self.by_tag = {f["tag"]: f for f in self.factions.values()}
        self.identities = {}    # id -> display name
        for m in re.finditer(r"<MyObjectBuilder_Identity>.*?</MyObjectBuilder_Identity>", s, re.S):
            b = m.group(0)
            self.identities[tag(b, "IdentityId")] = tag(b, "DisplayName", "")
        self.npc_identities = set()
        m = re.search(r"<NonPlayerIdentities>(.*?)</NonPlayerIdentities>", s, re.S)
        if m:
            self.npc_identities = set(re.findall(r"<long>(\d+)</long>", m.group(1)))
        # identity -> faction id (the save's player-faction map)
        self.member_map = {}
        for k, v in re.findall(r"<item>\s*<Key>(\d+)</Key>\s*<Value>(\d+)</Value>\s*</item>", s):
            if v in self.factions:
                self.member_map[k] = v
        self.player_rep = []    # (identity, faction id, reputation)
        for m in re.finditer(r"<MyObjectBuilder_PlayerFactionRelation>.*?</MyObjectBuilder_PlayerFactionRelation>", s, re.S):
            b = m.group(0)
            self.player_rep.append((tag(b, "PlayerId"), tag(b, "FactionId"), int(tag(b, "Reputation", "0"))))
        self.faction_rel = []   # (faction1, faction2, relation, reputation)
        for m in re.finditer(r"<MyObjectBuilder_FactionRelation>.*?</MyObjectBuilder_FactionRelation>", s, re.S):
            b = m.group(0)
            self.faction_rel.append((tag(b, "FactionId1"), tag(b, "FactionId2"), tag(b, "Relation"),
                                     int(tag(b, "Reputation", "0"))))
        m = re.search(r"<PiratesIdentity>(\d+)</PiratesIdentity>", s)
        self.pirates_identity = m.group(1) if m else None

    def ftag(self, fid):
        f = self.factions.get(fid)
        return f["tag"] if f else "?" + str(fid)

    def humans(self):
        return {i: n for i, n in self.identities.items() if i not in self.npc_identities}


def world_mods(folder):
    """[(name, published_id)] in the order the world lists them (top first)."""
    cfg = os.path.join(folder, "Sandbox_config.sbc")
    if not os.path.exists(cfg):
        return []
    s = read_text(cfg)
    out = []
    for m in re.finditer(r"<ModItem\b[^>]*>(.*?)</ModItem>", s, re.S):
        b = m.group(1)
        out.append((tag(b, "Name", ""), tag(b, "PublishedFileId", "0")))
    return out


def mod_dir(name, pid, workshop, local_mods):
    if pid and pid != "0":
        p = os.path.join(workshop, pid)
        if os.path.isdir(p):
            return p
    for cand in (name, name.replace(".sbm", "")):
        p = os.path.join(local_mods, cand)
        if cand and os.path.isdir(p):
            return p
    return None


# ----------------------------------------------------------------------- definitions

def _data_files(root):
    data = os.path.join(root, "Data")
    if not os.path.isdir(data):
        return []
    out = []
    for dp, _, fs in os.walk(data):
        for f in fs:
            if f.lower().endswith(".sbc"):
                out.append(os.path.join(dp, f))
    return sorted(out)


class Definitions:
    """Effective faction/reputation/economy definitions. Later sources override earlier ones."""

    def __init__(self):
        self.factions = {}          # tag -> dict(values..., source)
        self.rep_settings = None    # dict(values..., source)
        self.economy = None         # dict(values..., source)
        self.sources = []

    def load_source(self, root, label):
        self.sources.append(label)
        for path in _data_files(root):
            try:
                s = strip_comments(read_text(path))
            except OSError:
                continue
            if "Faction" in s:
                for m in re.finditer(r"<Faction\s+([^>]*)>(.*?)</Faction>", s, re.S):
                    attrs, b = m.group(1), m.group(2)
                    t = re.search(r'Tag="([^"]*)"', attrs)
                    if not t or "<Id>" not in b:
                        continue
                    self.factions[t.group(1)] = {
                        "tag": t.group(1),
                        "subtype": tag(b, "SubtypeId"),
                        "IsDefault": tag(b, "IsDefault", "false"),
                        "StaticReputation": tag(b, "StaticReputation", "false"),
                        "StartingReputation": tag(b, "StartingReputation"),
                        "DefaultRelationToPlayers": tag(b, "DefaultRelationToPlayers"),
                        "DiscoveredByDefault": tag(b, "DiscoveredByDefault"),
                        "Type": tag(b, "Type"),
                        "source": "%s (%s)" % (label, os.path.relpath(path, root)),
                    }
            if "ReputationSettingsDefinition" in s:
                m = re.search(r'<Definition xsi:type="MyObjectBuilder_ReputationSettingsDefinition">(.*?)</Definition>', s, re.S)
                if m:
                    b = m.group(1)
                    d = {"source": "%s (%s)" % (label, os.path.relpath(path, root))}
                    for sec in ("DamageSettings", "PirateDamageSettings"):
                        sm = re.search(r"<" + sec + r">(.*?)</" + sec + r">", b, re.S)
                        if sm:
                            d[sec] = {k: tag(sm.group(1), k) for k in
                                      ("ReputationLossDamage", "GrindingWelding", "Damaging", "Stealing", "Killing")}
                    d["MaxReputationGainInTime"] = tag(b, "MaxReputationGainInTime")
                    d["ResetTimeMinForRepGain"] = tag(b, "ResetTimeMinForRepGain")
                    self.rep_settings = d
            if "sessioncomponenteconomydefinition" in s.lower():
                m = re.search(r'<Definition xsi:type="MyObjectBuilder_SessionComponentEconomyDefinition">(.*?)</Definition>', s, re.S | re.I)
                if m:
                    b = m.group(1)
                    keys = ("ReputationHostileMin", "ReputationHostileMid", "ReputationNeutralMin", "ReputationNeutralMid",
                            "ReputationFriendlyMin", "ReputationFriendlyMid", "ReputationFriendlyMax",
                            "ReputationDecayPerHour", "ReputationPlayerDefault")
                    d = {k: tag(b, k) for k in keys}
                    d["source"] = "%s (%s)" % (label, os.path.relpath(path, root))
                    self.economy = d


def load_definitions(world_folder, game=DEFAULT_GAME, workshop=DEFAULT_WORKSHOP, local_mods=DEFAULT_LOCAL_MODS):
    defs = Definitions()
    defs.load_source(os.path.join(game, "Content"), "vanilla")
    missing = []
    for name, pid in reversed(world_mods(world_folder)):   # bottom of list first, top applied last
        d = mod_dir(name, pid, workshop, local_mods)
        if d is None:
            missing.append(name or pid)
            continue
        defs.load_source(d, name if pid in ("", "0") else "%s [%s]" % (name, pid))
    return defs, missing


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(2)
