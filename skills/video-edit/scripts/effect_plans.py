#!/usr/bin/env python3
"""effect_plans.py — per-segment effect recipes, selected by preset name.

A plan is a pure decision: given what a cut is (hero / drop entry / downbeat /
opener), return effect names render.py knows. Effects are programmatic, not a
DSL: a new feel is a small function registered in PLANS.
"""


def aggressive(i, hero, primary, entry, downbeat, tag):
    """Dense, every cut carries something; the opener detonates."""
    if hero:
        return ["freezeflash", "shake"] if primary else ["punch", "shake", "rgbsplit"]
    fx = ["punch", "dropflash" if downbeat else "beatflash"]
    if entry or i % 3 == 0:
        fx.append("shake")
    if i % 3 == 1:
        fx.append("rgbsplit")
    return fx


def quality(i, hero, primary, entry, downbeat, tag):
    """Retimed variant: effects only on structure, so slow-mo reads clean."""
    if hero:
        return ["dropflash"] if primary else ["beatflash"]
    if entry:
        return ["dropflash"]
    if downbeat and i % 4 == 0:
        return ["beatflash"]
    return []


def none(i, hero, primary, entry, downbeat, tag):
    return []


def product(i, hero, primary, entry, downbeat, tag):
    """Text-beat friendly: no flashes, snaps and slides carry the cuts."""
    if hero or entry:
        return ["zoomsnap"]
    if i % 4 == 0:
        return ["slideu"]
    return ["punch"] if i % 2 == 0 else []


def broadcast(i, hero, primary, entry, downbeat, tag):
    """Wipes and punch; replay speed comes from render.speed."""
    if hero:
        return ["whipl", "punch"]
    if entry:
        return ["whipr"]
    return ["punch"] if i % 2 == 0 else ["slideu"]


def trailer(i, hero, primary, entry, downbeat, tag):
    """Hard transitions, no flashes; titles and silence ranges do the drama."""
    if hero or entry:
        return ["zoomsnap"]
    if i % 3 == 0:
        return ["whipl"]
    return ["punch"]


def slow(i, hero, primary, entry, downbeat, tag):
    """Sparse: one move on a hero, otherwise nothing."""
    return ["punch"] if hero else []


PLANS = {"aggressive": aggressive, "quality": quality, "none": none,
         "product": product, "broadcast": broadcast, "trailer": trailer,
         "slow": slow}


def get(name):
    if name not in PLANS:
        raise SystemExit(f'unknown effects plan "{name}"; available: {", ".join(PLANS)}')
    return PLANS[name]
