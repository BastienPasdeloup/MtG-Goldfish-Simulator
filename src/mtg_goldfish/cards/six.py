"""Six — {2}{G} Legendary Creature — Treefolk 2/4, reach.
Whenever Six attacks, mill three cards; you may put a land card from among
them into your hand (deterministic: keep the first land milled — attack
triggers can't branch).

Retrace: while Six is in play (during your turn), you may cast NONLAND PERMANENT
cards from your graveyard by discarding a land card in addition to their mana
cost — a self-mill recursion engine. Modelled via `alt_cast_actions`: one cast
per distinct affordable graveyard permanent; the discarded land is chosen
deterministically (a basic if any) — a documented approximation."""
from __future__ import annotations

from .base import Card
from .registry import register


@register
class Six(Card):
    card_name = "Six"

    def on_attack(self, state, perm):
        top = state.library[:3]
        kept = next((c for c in top if c.is_land), None)
        for c in top:
            state.library.remove(c)
            if c is kept:
                state.hand.append(c)
            else:
                state.to_graveyard(c)
        state.emit(f"Six attacks: mill 3, keep {kept.name if kept else 'no land'}")

    def alt_cast_actions(self, state, perm):
        from ..engine.actions import _impl, begin_cast, can_afford, resolve_to_battlefield
        from .base import CardAction

        # Retrace's extra cost is discarding a land, so it needs one in hand.
        if not any(c.is_land for c in state.hand):
            return []
        out: list[CardAction] = []
        seen: set[str] = set()
        for card in state.graveyard:
            # Only NONLAND PERMANENT cards have retrace; skip custom-cast cards
            # (real cast-time targeting) — they can't take the default path here.
            if card.is_land or not card.is_permanent or card.name in seen:
                continue
            impl = _impl(card)
            if impl.cast_actions(state) is not None:
                continue
            cost = impl.cast_cost(state)
            if not can_afford(state, cost):
                continue
            seen.add(card.name)

            def fn(st, name=card.name, cost=cost):
                c = next((x for x in st.graveyard if x.name == name), None)
                if c is None:
                    return None
                land = (next((l for l in st.hand
                              if l.is_land and "basic" in l.type_line.lower()), None)
                        or next((l for l in st.hand if l.is_land), None))
                if land is None:
                    return None
                st.discard(land)
                if not begin_cast(st, c, cost, zone=st.graveyard, tag="retrace"):
                    return None
                return resolve_to_battlefield(st, c)

            out.append(CardAction(
                f"cast {card.name} from graveyard (retrace)", fn, sorcery_speed=True))
        return out
