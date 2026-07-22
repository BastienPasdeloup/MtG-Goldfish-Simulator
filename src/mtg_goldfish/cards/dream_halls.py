"""Dream Halls — {3}{U}{U} Enchantment.
"Rather than pay the mana cost for a spell, its controller may discard a card
that shares a color with that spell."

Modelled as an alternative casting static (`alt_cast_actions`): for each castable
spell in hand (or a commander in the command zone) that shares a color with some
OTHER hand card, offer to discard that card and cast the spell paying no mana.

Limitation: only spells with the engine's default cast (no custom cast-time
targeting/modes) are offered this way — a targeted removal spell or counterspell
still uses its normal cast path, so it never resolves target-less here."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class DreamHalls(Card):
    card_name = "Dream Halls"

    def alt_cast_actions(self, state, perm):
        from ..engine.actions import (_find_in_zone, _impl, _is_instant_speed,
                                       cast_without_paying)
        from .base import CardAction

        # Spells that could be cast: hand non-lands, plus a castable commander.
        spells: list[tuple[str, object]] = []
        seen: set[str] = set()
        for c in state.hand:
            if c.is_land or not c.colors or c.name in seen:
                continue
            seen.add(c.name)
            spells.append(("hand", c))
        seen_cmd: set[str] = set()
        for c in state.command_zone:
            if c.is_land or not c.colors or c.name in seen_cmd:
                continue
            # Respect the one-commander-cast-per-game rule.
            if state.commander_cast_this_game and not state.commander_cast_count.get(c.name):
                continue
            seen_cmd.add(c.name)
            spells.append(("command", c))

        out: list[CardAction] = []
        for zone_name, c in spells:
            impl = _impl(c)
            # Only default-cast spells (creatures, most permanents, vanilla
            # spells). Custom cast_actions imply real cast-time targeting.
            if not impl.is_castable(state) or impl.cast_actions(state) is not None:
                continue
            inst = _is_instant_speed(c) or (state.cast_sorcery_as_flash and c.is_sorcery)
            disc_names: set[str] = set()
            for d in state.hand:
                if d is c or d.name in disc_names:
                    continue
                if not (set(c.colors) & set(d.colors)):
                    continue
                disc_names.add(d.name)

                def fn(st, spell_name=c.name, disc_name=d.name, zn=zone_name):
                    zone = st.hand if zn == "hand" else st.command_zone
                    spell = _find_in_zone(zone, spell_name)
                    dcard = _find_in_zone(st.hand, disc_name)
                    if spell is None or dcard is None:
                        return None
                    st.discard(dcard)
                    return cast_without_paying(
                        st, spell, zone=zone, is_commander=(zn == "command"),
                        tag=f"Dream Halls, discard {disc_name}")

                out.append(CardAction(
                    f"cast {c.name} (Dream Halls — discard {d.name})",
                    fn, sorcery_speed=not inst))
        return out
