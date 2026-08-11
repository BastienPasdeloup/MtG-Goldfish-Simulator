"""Urza, Lord High Artificer — {2}{U}{U} Legendary Creature — Human Artificer 1/4.
When Urza enters, create a 0/0 colorless Construct artifact creature token with
"This token gets +1/+1 for each artifact you control." (see ConstructToken).
Tap an untapped artifact you control: Add {U}. (artifact_mana_grant)
{5}: Shuffle your library, then exile the top card. Until end of turn, you may
play that card without paying its mana cost.

The {5} impulse is modelled by moving the card to hand and granting a one-shot
free cast tied to its name (state.free_casts + a name-matched grant); the grant
is spent when used and cleared at end of turn."""
from __future__ import annotations

from ..engine.mana import ManaAbility, ManaCost
from .base import Card, CardAction
from .registry import register


@register
class UrzaLordHighArtificer(Card):
    card_name = "Urza, Lord High Artificer"

    def on_etb(self, state, permanent):
        state.make_token("Construct", 0, 0, "Token Artifact Creature — Construct")
        state.emit("Urza: create a Construct token (+1/+1 per artifact)")

    def artifact_mana_grant(self, state, perm):
        # "Tap an untapped artifact you control: Add {U}."
        return ManaAbility(amount=1, choices=("U",))

    def battlefield_actions(self, state, perm):
        from ..engine.actions import can_afford, pay_cost

        cost = ManaCost(generic=5)
        if not can_afford(state, cost):
            return []

        def pay(st):
            return pay_cost(st, cost)

        def resolve(st):
            st.shuffle_library()
            if not st.library:
                st.emit("Urza: {5} — library is empty")
                return None
            top = st.library.pop(0)
            st.hand.append(top)
            st.free_casts.append({"name": top.name, "label": "Urza impulse"})
            st.emit(f"Urza: {{5}} — exile {top.name}; you may play it free this turn")
            return None

        return [CardAction.activated(
            "Urza: {5} — impulse the top card (play it free this turn)",
            pay, resolve, source_name="Urza, Lord High Artificer",
            ability_text="Shuffle, exile the top card; you may play it free this turn")]
