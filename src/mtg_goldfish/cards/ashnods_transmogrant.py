"""Ashnod's Transmogrant — {1} Artifact.
{T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature.
That creature becomes an artifact in addition to its other types.

One branch per distinct nonartifact creature you control; the counter is added and
the creature's type line gains "Artifact" (via a permanent `becomes`, keeping its
printed power/toughness)."""
from __future__ import annotations

from .base import Card, CardAction
from .registry import register


@register
class AshnodsTransmogrant(Card):
    card_name = "Ashnod's Transmogrant"

    def battlefield_actions(self, state, perm):
        if perm.tapped:
            return []
        seen, targets = set(), []
        for p in state.battlefield:
            if p.is_creature_now and not p.is_artifact and p.name not in seen:
                seen.add(p.name)
                targets.append(p.uid)
        acts = []
        for tuid in targets:
            tname = state.find_permanent(tuid).name

            def make(tuid=tuid):
                def pay(st):
                    src = st.find_permanent(perm.uid)
                    if src is None or src.tapped:
                        return False
                    src.tapped = True
                    st.leaves_battlefield(src, "graveyard", reason="sacrifice")
                    return True

                def resolve(st):
                    t = st.find_permanent(tuid)
                    if t is not None:
                        t.counters["+1/+1"] = t.counters.get("+1/+1", 0) + 1
                        if not t.is_artifact:
                            t.becomes = {"type_line": f"Artifact {t.type_line}",
                                         "permanent": True}
                        st.emit(f"Ashnod's Transmogrant: +1/+1 counter on {t.name}, it becomes an artifact")
                    return None
                return pay, resolve

            pay, resolve = make()
            acts.append(CardAction.activated(
                f"Ashnod's Transmogrant: {{T}}, sacrifice → +1/+1 on {tname} (becomes artifact)",
                pay, resolve, source_name="Ashnod's Transmogrant",
                ability_text="+1/+1 counter on target nonartifact creature; it becomes an artifact"))
        return acts
