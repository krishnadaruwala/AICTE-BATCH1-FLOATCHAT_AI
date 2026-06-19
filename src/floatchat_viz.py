"""
floatchat_viz — all FloatChat visualizations.

    * float_map      — Folium map of float positions (returns HTML string)
    * depth_profile  — Plotly temperature-vs-depth
    * ts_diagram     — Plotly temperature-salinity scatter
    * comparison_chart — Plotly grouped bars of regional metrics
    * time_series    — Plotly seasonal surface-temperature lines

Functions take the plain dicts produced by floatchat_core and return either a
Plotly Figure or, for the Folium map, an HTML string for st.components.v1.html.
"""

from __future__ import annotations

import plotly.graph_objects as go

COLORS = {
    "warm": "#1D9E75",
    "cool": "#378ADD",
    "anomaly": "#EF9F27",
    "bg_secondary": "#F7F8F7",
    "border_soft": "#EEEFEE",
    "thermocline": "#D85A30",
    "region_a": "#1D9E75",
    "region_b": "#185FA5",
}
_CAT_COLOR = {"warm": COLORS["warm"], "cool": COLORS["cool"],
              "anomaly": COLORS["anomaly"]}


# --------------------------------------------------------------------------- #
# Float map (Folium)
# --------------------------------------------------------------------------- #
def float_map(data: dict, height: int = 300) -> str:
    """Folium map of float positions; returns HTML for st.components.v1.html.

    Falls back to a Plotly scattergeo (as HTML) if folium isn't installed.
    """
    positions = data["positions"]
    lats = [p["lat"] for p in positions]
    lons = [p["lon"] for p in positions]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]

    try:
        import folium  # noqa: WPS433
        fmap = folium.Map(location=center, zoom_start=4, tiles="CartoDB positron")
        for p in positions:
            color = _CAT_COLOR.get(p["category"], COLORS["warm"])
            folium.CircleMarker(
                location=[p["lat"], p["lon"]],
                radius=6, color=color, fill=True, fill_color=color,
                fill_opacity=0.85, weight=1,
                popup=f"{p['temp']:.1f} °C"
                + (f" · {p['psal']:.1f} PSU" if p.get("psal") else ""),
            ).add_to(fmap)
        return fmap._repr_html_()
    except Exception:
        fig = _scattergeo_fallback(data, height)
        return fig.to_html(include_plotlyjs="cdn", full_html=False,
                           config={"displayModeBar": False})


def _scattergeo_fallback(data: dict, height: int) -> go.Figure:
    fig = go.Figure()
    for cat, color in _CAT_COLOR.items():
        pts = [p for p in data["positions"] if p["category"] == cat]
        if pts:
            fig.add_trace(go.Scattergeo(
                lon=[p["lon"] for p in pts], lat=[p["lat"] for p in pts],
                mode="markers", name=cat.title(),
                marker=dict(size=9, color=color, opacity=0.85,
                            line=dict(width=0.5, color="white")),
            ))
    lats = [p["lat"] for p in data["positions"]]
    lons = [p["lon"] for p in data["positions"]]
    fig.update_geos(
        lataxis_range=[min(lats) - 3, max(lats) + 3],
        lonaxis_range=[min(lons) - 3, max(lons) + 3],
        showland=True, landcolor="#EAF3DE", showocean=True, oceancolor="#D4EDFA",
        showcountries=True, countrycolor="#B4B2A9", resolution=50,
    )
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=4, b=0),
                      legend=dict(orientation="h", y=-0.05, font=dict(size=10)),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


# --------------------------------------------------------------------------- #
# Depth profile (Plotly)
# --------------------------------------------------------------------------- #
def depth_profile(data: dict, height: int = 300) -> go.Figure:
    fig = go.Figure()
    band = data.get("profile_band")

    # For many floats, show a mean ± 1σ band instead of individual lines.
    if band and data.get("active_floats", 0) > 5:
        d = band["depths"]
        fig.add_trace(go.Scatter(  # upper bound (invisible line)
            x=band["hi"], y=d, mode="lines", line=dict(width=0),
            showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(  # lower bound + fill to upper
            x=band["lo"], y=d, mode="lines", line=dict(width=0),
            fill="tonextx", fillcolor="rgba(29,158,117,0.18)",
            name="±1σ spread", hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=band["mean"], y=d, mode="lines+markers",
            name=f"Mean of {band['n']:,} obs",
            line=dict(color=COLORS["warm"], width=2.5), marker=dict(size=5)))
    else:
        profiles = data["profiles"]
        depths = profiles["depths"]
        palette = [COLORS["warm"], COLORS["cool"], COLORS["anomaly"]]
        series = [(k, v) for k, v in profiles.items() if k != "depths"]
        for (name, vals), color in zip(series, palette):
            fig.add_trace(go.Scatter(
                x=vals["temp"], y=depths, mode="lines+markers", name=name,
                line=dict(color=color, width=2), marker=dict(size=5),
            ))

    fig.add_hline(y=120, line=dict(color=COLORS["thermocline"], width=1, dash="dash"),
                  annotation_text="thermocline", annotation_position="top right",
                  annotation_font=dict(size=9, color=COLORS["thermocline"]))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=4, b=0),
        xaxis=dict(title=dict(text="Temperature (°C)", font=dict(size=10)),
                   tickfont=dict(size=9), gridcolor=COLORS["border_soft"]),
        yaxis=dict(title=dict(text="Depth (m)", font=dict(size=10)),
                   tickfont=dict(size=9),
                   autorange="reversed", gridcolor=COLORS["border_soft"]),
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        plot_bgcolor=COLORS["bg_secondary"], paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------------------------------------------- #
# T-S diagram (Plotly)
# --------------------------------------------------------------------------- #
def ts_diagram(data: dict, height: int = 320) -> go.Figure:
    """Temperature-salinity scatter colored by depth, per float."""
    profiles = data["profiles"]
    depths = profiles["depths"]
    fig = go.Figure()
    for name, vals in profiles.items():
        if name == "depths" or not vals.get("psal"):
            continue
        fig.add_trace(go.Scatter(
            x=vals["psal"], y=vals["temp"], mode="markers", name=name,
            marker=dict(size=8, color=depths, colorscale="Tealgrn",
                        showscale=False, line=dict(width=0.5, color="white")),
        ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=4, b=0),
        xaxis=dict(title=dict(text="Salinity (PSU)", font=dict(size=10)),
                   tickfont=dict(size=9), gridcolor=COLORS["border_soft"]),
        yaxis=dict(title=dict(text="Temperature (°C)", font=dict(size=10)),
                   tickfont=dict(size=9), gridcolor=COLORS["border_soft"]),
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        plot_bgcolor=COLORS["bg_secondary"], paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------------------------------------------- #
# Comparison chart (Plotly)
# --------------------------------------------------------------------------- #
def comparison_chart(metrics: dict, height: int = 300) -> go.Figure:
    """Grouped bars for numeric metrics shared by two regions."""
    labels, a_vals, b_vals = [], [], []
    for name, a, b in metrics["metrics"]:
        a_num, b_num = _num(a), _num(b)
        if a_num is not None and b_num is not None:
            labels.append(name)
            a_vals.append(a_num)
            b_vals.append(b_num)
    fig = go.Figure()
    fig.add_bar(x=labels, y=a_vals, name=metrics["region_a"],
                marker_color=COLORS["region_a"])
    fig.add_bar(x=labels, y=b_vals, name=metrics["region_b"],
                marker_color=COLORS["region_b"])
    fig.update_layout(
        height=height, barmode="group", margin=dict(l=0, r=0, t=4, b=0),
        xaxis=dict(tickfont=dict(size=9)), yaxis=dict(tickfont=dict(size=9),
                   gridcolor=COLORS["border_soft"]),
        legend=dict(orientation="h", y=-0.18, font=dict(size=9)),
        plot_bgcolor=COLORS["bg_secondary"], paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _num(s: str):
    """Pull a leading float out of a label like '36.5 PSU'; None if not numeric."""
    try:
        return float(str(s).split()[0].replace("°C", "").replace("m", ""))
    except (ValueError, IndexError):
        return None


# --------------------------------------------------------------------------- #
# Time series (Plotly)
# --------------------------------------------------------------------------- #
def time_series(data: dict, regions: list[str], height: int = 280) -> go.Figure:
    ts = data["timeseries"]
    months = ts["months"]
    palette = [COLORS["region_a"], COLORS["region_b"], COLORS["anomaly"]]
    fig = go.Figure()
    for region, color in zip(regions, palette):
        if region in ts:
            fig.add_trace(go.Scatter(
                x=months, y=ts[region], mode="lines+markers", name=region,
                line=dict(color=color, width=2), marker=dict(size=5),
            ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=4, b=0),
        xaxis=dict(tickfont=dict(size=9)),
        yaxis=dict(title=dict(text="Surface temp (°C)", font=dict(size=10)),
                   tickfont=dict(size=9), gridcolor=COLORS["border_soft"]),
        legend=dict(orientation="h", y=-0.2, font=dict(size=9)),
        plot_bgcolor=COLORS["bg_secondary"], paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
