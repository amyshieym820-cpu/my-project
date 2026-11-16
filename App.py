import math
import requests
import streamlit as st

from factors import CFG, NOREUSE, calculate, baseline, method_label, build_suggestions, carbon_level

st.set_page_config(
    page_title="Film Green Book",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
:root { --green: #0E3B2C; }
.stApp { background: #ffffff; }
h1, h2, h3, p, label { color: #0E3B2C; }
section[data-testid="stSidebar"] { background: #f3f7f4; }
div[data-testid="stMetric"] {
    background: #0E3B2C; padding: 18px; border-radius: 14px;
}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: white !important;
}
div.stButton > button[kind="primary"] {
    background: #0E3B2C; border-color: #0E3B2C; color: white;
}
.small-note { color: #668074; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.title("Film Green Book")
st.write(
    "Estimate the carbon footprint of art-department props and materials. "
    "Compare buying new with second-hand, rental, reuse, and different transport choices."
)

def new_item():
    return {
        "name": "",
        "cat": "Wood / plywood",
        "w": 1.0,
        "q": 1,
        "method": "coupang",
        "ship": "single",
        "b": 1,
        "mode": "transit",
        "o": "",
        "d": "",
        "km": 0.0,
    }

if "items" not in st.session_state:
    st.session_state.items = [new_item()]

def locate_address(address):
    """Return (lat, lon) using OpenStreetMap Nominatim."""
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"format": "jsonv2", "limit": 1, "countrycodes": "kr", "q": address},
        headers={"User-Agent": "FilmGreenBook/1.0 (carbon estimate app)"},
        timeout=15,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])

def road_distance(origin, destination):
    """Return driving distance in km, or None if routing fails."""
    a = locate_address(origin)
    b = locate_address(destination)
    if not a or not b:
        return None
    url = (
        "https://router.project-osrm.org/route/v1/driving/"
        f"{a[1]},{a[0]};{b[1]},{b[0]}"
    )
    response = requests.get(url, params={"overview": "false"}, timeout=20)
    response.raise_for_status()
    routes = response.json().get("routes", [])
    if not routes:
        return None
    return round(routes[0]["distance"] / 1000, 1)

def fmt(value):
    return f"{value:,.1f}"

left, right = st.columns([1.5, 1], gap="large")

with left:
    st.subheader("Props and materials")
    for i, item in enumerate(st.session_state.items):
        with st.container(border=True):
            top = st.columns([4, 1])
            with top[0]:
                st.markdown(f"**Item {i + 1}**")
            with top[1]:
                if st.button("Remove", key=f"remove_{i}", use_container_width=True):
                    st.session_state.items.pop(i)
                    st.rerun()

            c1, c2 = st.columns(2)
            item["name"] = c1.text_input("Item name", item["name"], key=f"name_{i}", placeholder="e.g. Set plywood")
            item["cat"] = c2.selectbox("Material", list(CFG["cat"]), index=list(CFG["cat"]).index(item["cat"]), key=f"cat_{i}")

            c1, c2, c3 = st.columns(3)
            item["w"] = max(0.0, c1.number_input("Weight each (kg)", min_value=0.0, value=float(item["w"]), step=0.1, key=f"weight_{i}"))
            item["q"] = max(1, c2.number_input("Quantity", min_value=1, value=int(item["q"]), step=1, key=f"qty_{i}"))
            methods = list(CFG["method"])
            item["method"] = c3.selectbox(
                "Purchase method", methods,
                format_func=lambda k: CFG["method"][k]["n"],
                index=methods.index(item["method"]), key=f"method_{i}"
            )

            method = CFG["method"][item["method"]]
            if method["on"]:
                c1, c2 = st.columns(2)
                item["ship"] = c1.selectbox(
                    "Shipping", ["single", "bundle"],
                    format_func=lambda x: "Shipped individually" if x == "single" else "Bundled",
                    index=0 if item["ship"] == "single" else 1, key=f"ship_{i}"
                )
                item["b"] = c2.number_input(
                    "Items per box", min_value=1, value=max(1, int(item["b"])),
                    step=1, disabled=item["ship"] != "bundle", key=f"box_{i}"
                )
            else:
                modes = list(CFG["mode"])
                item["mode"] = st.selectbox(
                    "Travel mode (round trip)", modes,
                    format_func=lambda k: CFG["mode"][k][0],
                    index=modes.index(item["mode"]), key=f"mode_{i}"
                )

            st.markdown("**Transport (optional)**")
            c1, c2 = st.columns(2)
            item["o"] = c1.text_input("Origin (seller / warehouse)", item["o"], key=f"origin_{i}")
            item["d"] = c2.text_input("Destination (set / workshop)", item["d"], key=f"destination_{i}")
            c1, c2 = st.columns([1, 1])
            item["km"] = max(0.0, c1.number_input(
                "Distance (km, one way)", min_value=0.0, value=float(item["km"]),
                step=0.5, key=f"distance_{i}"
            ))
            if c2.button("Find road distance", key=f"route_{i}", use_container_width=True):
                if item["o"].strip() and item["d"].strip():
                    with st.spinner("Finding addresses and calculating route..."):
                        try:
                            distance = road_distance(item["o"].strip(), item["d"].strip())
                            if distance is None:
                                st.warning("Could not find a route. Enter the distance manually.")
                            else:
                                item["km"] = distance
                                st.session_state[f"distance_{i}"] = distance
                                st.success(f"Driving distance: {distance} km (one way)")
                        except requests.RequestException:
                            st.warning("The address or routing service is unavailable. Enter the distance manually.")
                else:
                    st.info("Enter both origin and destination first.")

            result = calculate(item)
            st.caption(
                f"Estimated item footprint: **{fmt(result['t'])} kg CO₂e** "
                f"(production {fmt(result['prod'])} + transport {fmt(result['tr'])})"
            )

    if st.button("＋ Add an item", type="primary", use_container_width=True):
        st.session_state.items.append(new_item())
        st.rerun()

    st.caption(
        "Address lookup uses OpenStreetMap Nominatim and driving routes use the public OSRM demo service. "
        "You can always enter or edit the one-way distance manually."
    )

# Recalculate after all controls have updated the session-state item values.
items = st.session_state.items
results = [calculate(item) for item in items]
bases = [baseline(item) for item in items]
total = sum(x["t"] for x in results)
base_total = sum(x["t"] for x in bases)
production = sum(x["prod"] for x in results)
transport = sum(x["tr"] for x in results)
water_saved = sum(x["water"] for x in results)
saved = max(0.0, base_total - total)

with right:
    st.subheader("Results")
    st.metric("Total carbon emissions", f"{fmt(total)} kg CO₂e")
    st.markdown("**Compared with buying everything new online and shipping individually**")
    st.write(f"Baseline: **{fmt(base_total)} kg CO₂e**")
    st.write(f"Production: **{fmt(production)} kg CO₂e**")
    st.write(f"Packaging, transport, and travel: **{fmt(transport)} kg CO₂e**")

    level, message = carbon_level(total)
    st.info(message)
    st.markdown("### Saved by your sourcing choices")
    st.write(f"**{fmt(saved)} kg CO₂e** avoided ({fmt(saved / base_total * 100) if base_total else '0.0'}%).")
    meals = saved / CFG["meal"]
    st.write(f"About **{fmt(meals)} meals** worth of carbon footprint.")
    st.write(f"Water footprint avoided: **{water_saved:,.0f} L**.")
    st.write(f"Equivalent yearly CO₂ absorption: **{fmt(saved / CFG['tree'])} trees**.")

    st.download_button(
        "Download results (CSV)",
        data=(
            "Item,Material,Method,Weight each (kg),Quantity,Distance one way (km),"
            "Production (kg CO2e),Transport (kg CO2e),Total (kg CO2e)\n"
            + "\n".join(
                f'"{it["name"].replace(chr(34), chr(39))}",'
                f'"{it["cat"]}","{method_label(it)}",{it["w"]},{it["q"]},'
                f'{it["km"]},{r["prod"]:.3f},{r["tr"]:.3f},{r["t"]:.3f}'
                for it, r in zip(items, results)
            )
        ),
        file_name="film_green_book_results.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.divider()
st.subheader("Ways to cut emissions")
suggestions = build_suggestions(items, results)
if suggestions:
    extra = sum(x["saving"] for x in suggestions)
    st.write(f"Applying the alternatives below could save another **{fmt(extra)} kg CO₂e**.")
    for suggestion in suggestions:
        st.markdown(
            f"- **{suggestion['name']}**: {suggestion['current']} → "
            f"**{suggestion['alternative']}** "
            f"(<span style='color:#0E3B2C'>−{fmt(suggestion['saving'])} kg CO₂e</span>)",
            unsafe_allow_html=True,
        )
else:
    st.write("No material alternative savings identified with the current assumptions.")

with st.expander("Practical ways to reduce carbon"):
    st.markdown("""
    - **Reuse first.** Reuse stock, scrap, or rental props where practical.
    - **Buy used.** Second-hand furniture, fabric, and fixtures can avoid new production.
    - **Bundle online orders.** Combine items into fewer boxes.
    - **Cut trips and distance.** Combine store pickups and source close to the set.
    - **Choose lower-carbon materials.** Fabric and electronics have relatively high factors in this estimate.
    - **Buy only what you need.** Plan quantities with the shooting schedule.
    - **Plan the afterlife.** Store or donate props and scrap after wrap.
    """)

st.divider()
st.caption(
    "All factors are simplified estimates based on public averages. "
    "Meal and water comparisons are illustrative metrics, not measured quantities."
)
