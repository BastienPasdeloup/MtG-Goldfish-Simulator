"""Peter Parker's Camera — {1} Artifact. Enters with three film counters.
{2}, {T}, Remove a film counter: copy target activated or triggered ability you
control. (You may choose new targets for the copy.)

The copy ability is a RESPONSE to an ability already on the stack, so it lives in
the instant-speed priority window the engine opens before each triggered/
activated ability resolves (see GameState._stack_response_branches). When the
window offers it, the Camera pays {2}, taps, removes a film counter and puts a
copy of the ability now on top of the stack ABOVE the original — so the copy
resolves first, then the original. Copying e.g. Atraxa's ETB therefore reveals
the top ten twice (the copy re-reads the library at its own resolution), and
both resolutions attribute their put-in-hand cards to Atraxa.

Only explored when instant-speed play is enabled in the run configuration."""
from __future__ import annotations

from .base import Card
from .registry import register

# Defensive bound: never stack more than this many pending copies on one line
# (the tap cost already limits a single Camera to one copy per line; this only
# guards against pathological multi-Camera / untap loops).
_MAX_PENDING_COPIES = 8


@register
class PeterParkersCamera(Card):
    card_name = "Peter Parker's Camera"

    def enters_with_counters(self, state):
        return {"film": 3}

    def stack_response_actions(self, state, perm):
        from ..engine.game_state import StackAbility, StackResponse
        from ..engine.mana import ManaCost
        from ..engine.actions import can_afford

        if perm.tapped or perm.counters.get("film", 0) <= 0:
            return []
        # Target: the ability currently on top of the stack (a triggered or
        # activated ability you control — in a goldfish everything is yours).
        target = state.stack[-1] if state.stack else None
        if not isinstance(target, StackAbility) or target.kind not in ("triggered", "activated"):
            return []
        pending = sum(1 for s in state.stack
                      if isinstance(s, StackAbility) and s.label.endswith("(copy)"))
        if pending >= _MAX_PENDING_COPIES:
            return []
        cost = ManaCost(generic=2)
        if not can_afford(state, cost):
            return []

        uid = perm.uid

        def apply(st) -> bool:
            from ..engine.actions import pay_cost

            live = st.find_permanent(uid)
            if live is None or live.tapped or live.counters.get("film", 0) <= 0:
                return False
            tgt = st.stack[-1] if st.stack else None
            if not isinstance(tgt, StackAbility) or tgt.kind not in ("triggered", "activated"):
                return False
            if not pay_cost(st, ManaCost(generic=2)):
                return False
            live.tapped = True
            live.counters["film"] = live.counters.get("film", 0) - 1
            st.note_event("activated", "Peter Parker's Camera",
                          detail=f"copy {tgt.label}")
            # `name` = the copied ability's source (e.g. "Atraxa, Grand Unifier");
            # `copied_by` = the copier; `target_kind` = the copied ability's kind
            # ("triggered"/"activated"). Queried via state.ability_copied(...).
            st.note_event("copy_ability", tgt.source_name or tgt.label,
                          detail=tgt.label, copied_by="Peter Parker's Camera",
                          target_kind=tgt.kind)
            # The copy resolves first: push it ABOVE the original on the stack.
            # It carries the original's source/kind so its effects (cards put in
            # hand, permanents made, ...) are attributed to the same source.
            copy = StackAbility(
                label=f"{tgt.label} (copy)",
                resolve=tgt.resolve,
                source_name=tgt.source_name,
                kind=tgt.kind,
                trigger_text=tgt.trigger_text,
                ability_text=tgt.ability_text,
            )
            st.stack.append(copy)
            st.emit(f"Peter Parker's Camera: copy {tgt.label} "
                    f"(film {live.counters['film']} left)")
            return True

        return [StackResponse(f"Peter Parker's Camera: copy {target.label}", apply)]
