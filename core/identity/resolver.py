"""Deterministic identity resolution via union-find (Segment Unify's model): records that
share any identifier collapse to one profile; a priority order picks the canonical main_id;
blocked values (null/anonymous) prevent runaway merges. Probabilistic stitch is a later
score-returning method behind the same function."""

from __future__ import annotations

_PRIORITY = ["user_id", "email", "anon_id"]  # main_id rank (Segment's priority idea)
_BLOCKED = {"", "null", "anonymous", "none", "undefined"}  # never merge on these


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def _key(id_type: str, value: str) -> str:
    return f"{id_type}:{value}"


def resolve_identities(records: list[dict]) -> list[dict]:
    """records = [{email, anon_id, user_id, ...traits}]. Returns unified profiles, each
    with a main_id (by priority), all stitched identifiers, a record count, and merged
    traits."""
    uf = _UnionFind()
    node_records: dict[str, list[int]] = {}
    for i, rec in enumerate(records):
        ids = [
            (t, str(rec.get(t, "")).strip().lower())
            for t in _PRIORITY
            if str(rec.get(t, "")).strip().lower() not in _BLOCKED
        ]
        keys = [_key(t, v) for t, v in ids]
        for k in keys:
            node_records.setdefault(k, []).append(i)
        for k in keys[1:]:
            uf.union(keys[0], k)

    groups: dict[str, set[str]] = {}
    for node in node_records:
        groups.setdefault(uf.find(node), set()).add(node)

    profiles: list[dict] = []
    for nodes in groups.values():
        idxs: set[int] = set()
        for n in nodes:
            idxs.update(node_records[n])
        main_id = None
        for t in _PRIORITY:
            main_id = next((n for n in sorted(nodes) if n.startswith(f"{t}:")), None)
            if main_id:
                break
        traits: dict = {}
        for i in idxs:
            for k, v in records[i].items():
                if k not in _PRIORITY and v:
                    traits[k] = v
        profiles.append({
            "main_id": main_id,
            "identifiers": sorted(nodes),
            "record_count": len(idxs),
            "traits": traits,
        })
    profiles.sort(key=lambda p: -p["record_count"])
    return profiles
