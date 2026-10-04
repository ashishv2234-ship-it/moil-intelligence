"""Synthetic (made-up) drill-hole data for the demo. Replace with real assays when the geology team uploads them."""
import math, random

MINES = [(21.8, 80.2), (21.2, 79.6), (21.3, 79.1), (21.3, 79.3), (21.4, 79.3)]  # same as seed.py, for the self-test only


def make_demo_holes(seed: int = 21):
    """Returns (code, lat, lng, depth_m, mn_pct) tuples. Grade is higher along a NE-SW belt through the mines,
    plus two pockets away from the mines that the model should flag as new prospects."""
    rnd = random.Random(seed)
    rows = []
    for _ in range(90):
        lng = rnd.uniform(79.0, 80.4)
        lat = 21.2 + 0.45 * (lng - 79.1) + rnd.gauss(0, 0.2)
        d = abs(lat - (21.2 + 0.45 * (lng - 79.1)))
        mn = 8 + 34 * math.exp(-((d / 0.12) ** 2)) + rnd.gauss(0, 3)
        rows.append((lat, lng, mn))
    for _ in range(6):  # pocket A: well-drilled, rich
        rows.append((21.9 + rnd.gauss(0, 0.04), 79.6 + rnd.gauss(0, 0.04), 36 + rnd.gauss(0, 4)))
    for _ in range(3):  # pocket B: thinly drilled, promising
        rows.append((21.05 + rnd.gauss(0, 0.03), 80.1 + rnd.gauss(0, 0.03), 31 + rnd.gauss(0, 4)))
    out = []
    for i, (la, ln, mn) in enumerate(rows):
        out.append((f"DH-{i + 1:03d}", round(min(max(la, 21.0), 22.1), 4), round(min(max(ln, 79.0), 80.5), 4),
                    round(rnd.uniform(40, 300)), round(min(max(mn, 3), 52), 1)))
    return out
