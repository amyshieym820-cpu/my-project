import math

"""Emission factors and calculation helpers for Film Green Book."""

CFG = {
    # category: [new-product production kgCO2e/kg, water footprint L/kg]
    "cat": {
        "Wood / plywood": [0.9, 50],
        "Fabric / costume": [15, 6000],
        "Plastic": [3, 200],
        "Metal": [4, 300],
        "Paper / cardboard": [1.3, 400],
        "Glass / ceramic": [1.2, 30],
        "Furniture / finished goods": [2.5, 300],
        "Electronics": [20, 1500],
        "Paint / chemicals": [3, 100],
        "Other": [2, 200],
    },
    # on: online shipping; mult: production emissions vs new; pk: parcel kgCO2e
    "method": {
        "coupang": {"n": "Coupang", "on": True, "mult": 1, "pk": 0.55},
        "naver": {"n": "Naver Shopping", "on": True, "mult": 1, "pk": 0.70},
        "daiso": {"n": "Daiso store", "on": False, "mult": 1},
        "danggeun": {"n": "Danggeun (used)", "on": False, "mult": 0.05},
        "rental": {"n": "Prop rental house", "on": False, "mult": 0.03},
        "reuse": {"n": "Reuse from stock / scrap", "on": False, "mult": 0.01},
    },
    # kgCO2e per passenger-km (simplified estimate)
    "mode": {
        "walk": ["Walk / bike", 0],
        "transit": ["Public transit", 0.07],
        "car": ["Car", 0.19],
        "van": ["Van / truck", 0.28],
    },
    "truck": 0.00015,  # freight kgCO2e per kg-km
    "road": 1.3,       # straight-line to road-distance multiplier fallback
    "meal": 2.0,
    "drink": 2,
    "tree": 6.6,
    "mid": 20,
    "high": 50,
}

NOREUSE = ["Paint / chemicals"]


def calculate(item, override=None):
    """Calculate production, transport, total emissions, and avoided water."""
    override = override or {}
    method_key = override.get("method", item["method"])
    method = CFG["method"][method_key]
    category = CFG["cat"][item["cat"]]
    weight = float(item["w"]) * int(item["q"])
    distance = float(item.get("km", 0) or 0)

    production = weight * category[0] * method["mult"]

    if method["on"]:
        shipping = override.get("ship", item.get("ship", "single"))
        per_box = max(1, int(override.get("b", item.get("b", 1))))
        boxes = math_ceil_div(int(item["q"]), per_box) if shipping == "bundle" else int(item["q"])
        parcel_factor = method["pk"] * boxes
        transport = parcel_factor + weight * distance * CFG["truck"]
    else:
        transport = distance * 2 * CFG["mode"][item.get("mode", "transit")][1]
        if method_key == "daiso":
            transport += weight * 150 * CFG["truck"]

    water = weight * category[1] * (1 - method["mult"])
    return {
        "prod": production,
        "tr": transport,
        "t": production + transport,
        "water": water,
    }


def math_ceil_div(a, b):
    return (a + b - 1) // b


def baseline(item):
    return calculate(item, {"method": "coupang", "ship": "single"})


def method_label(item, method_key=None, shipping=None):
    key = method_key or item["method"]
    method = CFG["method"][key]
    label = method["n"]
    if method["on"]:
        ship = shipping or item.get("ship", "single")
        label += ", bundled" if ship == "bundle" else ", shipped individually"
    return label


def carbon_level(total):
    if total >= CFG["high"]:
        return "high", "High emissions. Check the alternatives below."
    if total >= CFG["mid"]:
        return "mid", "Moderate emissions. See if any items can be reduced."
    return "low", "Low emissions."


def build_suggestions(items, current_results):
    """Find the lowest-emission eligible sourcing alternative for each item."""
    suggestions = []
    for item, current in zip(items, current_results):
        best = None
        for key, method in CFG["method"].items():
            if item["cat"] in NOREUSE and key in ("danggeun", "rental", "reuse"):
                continue
            if key == item["method"] and not (method["on"] and item.get("ship") == "single"):
                continue
            override = (
                {"method": key, "ship": "bundle", "b": max(1, int(item["q"]))}
                if method["on"] else {"method": key}
            )
            candidate = calculate(item, override)
            if best is None or candidate["t"] < best["result"]["t"]:
                best = {
                    "method": key,
                    "shipping": "bundle" if method["on"] else None,
                    "result": candidate,
                }

        if best:
            saving = current["t"] - best["result"]["t"]
            if current["t"] > 0 and saving >= 0.3 and saving / current["t"] >= 0.1:
                suggestions.append({
                    "name": item.get("name") or "Untitled item",
                    "current": method_label(item),
                    "alternative": method_label(item, best["method"], best["shipping"]),
                    "saving": saving,
                })

    return sorted(suggestions, key=lambda x: x["saving"], reverse=True)
