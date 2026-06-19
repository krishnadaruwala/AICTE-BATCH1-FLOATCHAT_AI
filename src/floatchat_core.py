"""
floatchat_core — core logic for FloatChat.

Layers:
    * Gemini client         — lazy, optional (falls back to keyword parsing)
    * Query parser          — natural language -> structured QueryParams
    * Argo data fetcher      — argopy/ERDDAP, optional (falls back to mock data)
    * Insight generator      — natural-language summary of a result

The module is import-safe with no API key and no argopy installed: every
external dependency is lazy and guarded so the Streamlit UI always runs.

Set GEMINI_API_KEY (or GOOGLE_API_KEY) to enable live Gemini parsing/insights.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Literal

# Point Python/aiohttp at the certifi CA bundle so live HTTPS fetches (argopy
# -> ERDDAP) can verify certificates. Fixes the common Windows/macOS
# "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate" error.
try:
    import certifi  # noqa: WPS433
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
except ImportError:
    pass

Intent = Literal["overview", "compare", "timeseries", "ts_diagram", "help"]

MODEL = "gemini-2.5-flash"

# Seconds argopy waits on an ERDDAP request before raising FSTimeoutError.
ARGO_TIMEOUT = 300

# Named regions -> [lon_min, lon_max, lat_min, lat_max]
REGION_PRESETS: dict[str, list[float]] = {
    "Arabian Sea": [55, 78, 5, 26],
    "Bay of Bengal": [78, 99, 5, 23],
    "Indian Ocean": [40, 110, -40, 25],
    "Mediterranean": [-6, 36, 30, 46],
    "Global": [-180, 180, -90, 90],
}

VARIABLES = ["TEMP", "PSAL", "PRES"]  # temperature, salinity, pressure


# --------------------------------------------------------------------------- #
# Structured query
# --------------------------------------------------------------------------- #
@dataclass
class QueryParams:
    """Structured parameters extracted from a natural-language query."""
    intent: Intent = "overview"
    regions: list[str] = field(default_factory=lambda: ["Arabian Sea"])
    depth_range: tuple[int, int] = (0, 500)
    date_range: tuple[str, str] = ("2023-01-01", "2023-01-31")
    variables: list[str] = field(default_factory=lambda: ["TEMP"])
    raw: str = ""

    def bbox(self, region: str | None = None) -> list[float]:
        region = region or self.regions[0]
        return REGION_PRESETS.get(region, REGION_PRESETS["Arabian Sea"])

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Gemini client (lazy / optional)
# --------------------------------------------------------------------------- #
_client = None


def get_client():
    """Return a cached Gemini client, or None if unavailable."""
    global _client
    if _client is not None:
        return _client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai  # noqa: WPS433 (optional dependency)
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Query parser
# --------------------------------------------------------------------------- #
_PARSER_SYSTEM = (
    "You convert a user's natural-language question about Argo ocean-float data "
    "into a JSON object. Respond with ONLY a JSON object, no prose. Schema:\n"
    "{\n"
    '  "intent": one of ["overview","compare","timeseries","ts_diagram","help"],\n'
    '  "regions": array of region names from '
    f"{list(REGION_PRESETS)},\n"
    '  "depth_range": [min_m, max_m],\n'
    '  "date_range": ["YYYY-MM-DD","YYYY-MM-DD"],\n'
    '  "variables": subset of ["TEMP","PSAL","PRES"]\n'
    "}\n"
    "Use 'compare' when two or more regions are mentioned, 'timeseries' for "
    "trends over time, 'ts_diagram' for temperature-salinity relationships, "
    "'help' when the request is unclear."
)


def parse_query(text: str) -> QueryParams:
    """Parse text into QueryParams, via Gemini if available else keywords."""
    client = get_client()
    if client is not None:
        try:
            return _parse_with_gemini(client, text)
        except Exception:
            pass  # fall through to keyword parsing
    return _parse_with_keywords(text)


def _parse_with_gemini(client, text: str) -> QueryParams:
    from google.genai import types  # noqa: WPS433
    resp = client.models.generate_content(
        model=MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=_PARSER_SYSTEM,
            response_mime_type="application/json",
            max_output_tokens=400,
            temperature=0,
        ),
    )
    payload = json.loads(resp.text)
    return QueryParams(
        intent=payload.get("intent", "overview"),
        regions=payload.get("regions") or ["Arabian Sea"],
        depth_range=tuple(payload.get("depth_range", (0, 500))),
        date_range=tuple(payload.get("date_range", ("2023-01-01", "2023-01-31"))),
        variables=payload.get("variables") or ["TEMP"],
        raw=text,
    )


def _parse_with_keywords(text: str) -> QueryParams:
    p = text.lower()
    regions = [name for name in REGION_PRESETS if name.lower() in p]
    if not regions:
        regions = ["Arabian Sea"]

    if any(k in p for k in ("compare", "versus", " vs ")) or len(regions) >= 2:
        intent: Intent = "compare"
    elif any(k in p for k in ("trend", "over time", "time series", "timeseries",
                              "monthly", "seasonal")):
        intent = "timeseries"
    elif any(k in p for k in ("t-s", "t/s", "temperature-salinity", "water mass")):
        intent = "ts_diagram"
    elif any(k in p for k in ("temperature", "temp", "salinity", "profile",
                              "depth", "float", "anomal", "heat", "show")):
        intent = "overview"
    else:
        intent = "help"

    variables = []
    if any(k in p for k in ("temp", "temperature", "thermo")):
        variables.append("TEMP")
    if any(k in p for k in ("sal", "psu", "salinity")):
        variables.append("PSAL")
    if not variables:
        variables = ["TEMP"]

    return QueryParams(intent=intent, regions=regions, variables=variables, raw=text)


# --------------------------------------------------------------------------- #
# Argo data fetcher
# --------------------------------------------------------------------------- #
def fetch_from_params(params: QueryParams, region: str | None = None,
                      source: str = "auto") -> dict:
    """
    Fetch an Argo dataset for the given params. Returns a backend-agnostic dict:

        {
          "region", "period", "active_floats", "data_points",
          "positions": [{"lon","lat","temp","psal","category"}...],
          "profiles":  {"depths":[...], "<float>":{"temp":[...], "psal":[...]}},
          "timeseries":{"months":[...], "<region>":[...]},
          "source": "argo-erddap" | "mock",
        }

    `source` controls the backend:
        "mock" — skip argopy entirely and return mock data.
        "live" — require argopy; record LAST_FETCH_ERROR if it fails.
        "auto" — try argopy, fall back to mock silently-ish (default).
    """
    global LAST_FETCH_ERROR
    region = region or params.regions[0]

    if source == "mock":
        LAST_FETCH_ERROR = None
        return _fetch_mock(params, region)

    try:
        import argopy  # noqa: WPS433
        data = _fetch_argopy(argopy, params, region)
        LAST_FETCH_ERROR = None
        return data
    except ImportError:
        LAST_FETCH_ERROR = ("argopy is not installed — run "
                            "`pip install argopy xarray netCDF4` to enable live "
                            "Argo data.")
    except Exception as exc:  # network / query failure
        name = type(exc).__name__
        if "Timeout" in name:
            LAST_FETCH_ERROR = (
                f"Live Argo query timed out ({name}). The selected area/period is "
                "likely too large — try a specific region (not Global) and a "
                "narrower date range."
            )
        else:
            LAST_FETCH_ERROR = f"Live Argo query failed ({name}): {exc}"
    return _fetch_mock(params, region)


# Reason the last fetch fell back to mock data (None if live succeeded).
LAST_FETCH_ERROR: str | None = None


def _fetch_argopy(argopy, params: QueryParams, region: str) -> dict:
    """Live fetch via argopy. Cache .nc files into ./data when configured."""
    lon0, lon1, lat0, lat1 = params.bbox(region)
    d0, d1 = params.date_range
    z0, z1 = params.depth_range

    # Large bounding boxes (esp. "Global") over a full month return a lot of
    # data, so give ERDDAP a generous timeout to avoid FSTimeoutError.
    try:
        argopy.set_options(api_timeout=ARGO_TIMEOUT)
    except Exception:
        pass

    fetcher = argopy.DataFetcher().region(
        [lon0, lon1, lat0, lat1, z0, z1, d0, d1]
    )
    ds = fetcher.to_xarray()
    profiles_obj = ds.argo.point2profile()

    # Float positions, colored by surface temperature anomaly.
    positions = []
    for _, prof in profiles_obj.groupby("N_PROF"):
        lon = float(prof["LONGITUDE"].values.flat[0])
        lat = float(prof["LATITUDE"].values.flat[0])
        temp = float(prof["TEMP"].values.flat[0])
        psal = float(prof["PSAL"].values.flat[0]) if "PSAL" in prof else None
        positions.append({
            "lon": lon, "lat": lat, "temp": temp, "psal": psal,
            "category": _classify_temp(temp),
        })

    band = _depth_band([float(v) for v in ds["PRES"].values.flat],
                       [float(v) for v in ds["TEMP"].values.flat])

    return {
        "region": region,
        "period": f"{d0} → {d1}",
        "active_floats": len(positions),
        "data_points": int(ds.sizes.get("N_POINTS", len(positions))),
        "positions": positions,
        "profiles": _profiles_from_ds(profiles_obj),
        "profile_band": band,
        "timeseries": _fetch_mock(params, region)["timeseries"],  # placeholder
        "source": "argo-erddap",
    }


# Pressure-bin edges (m) for aggregating many profiles into a mean ± std band.
_BAND_EDGES = [0, 25, 50, 75, 100, 150, 200, 300, 400, 500,
               750, 1000, 1500, 2000]


def _depth_band(pres: list, temp: list) -> dict | None:
    """Aggregate all (pressure, temperature) points into per-depth mean ± std.

    Returns {"depths","mean","lo","hi","n"} or None if too few points. Used to
    summarize hundreds of float profiles in one readable band.
    """
    import math
    import statistics

    pairs = [(p, t) for p, t in zip(pres, temp)
             if math.isfinite(p) and math.isfinite(t)]
    if len(pairs) < 6:
        return None

    depths, mean, lo, hi = [], [], [], []
    for a, b in zip(_BAND_EDGES, _BAND_EDGES[1:]):
        vals = [t for p, t in pairs if a <= p < b]
        if len(vals) < 3:
            continue
        mu = statistics.mean(vals)
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        depths.append((a + b) / 2)
        mean.append(round(mu, 2))
        lo.append(round(mu - sd, 2))
        hi.append(round(mu + sd, 2))

    if len(depths) < 2:
        return None
    return {"depths": depths, "mean": mean, "lo": lo, "hi": hi,
            "n": len(pairs)}


def _profiles_from_ds(profiles_obj) -> dict:
    out: dict = {"depths": []}
    for i, (_, prof) in enumerate(profiles_obj.groupby("N_PROF")):
        if i >= 3:
            break
        depths = [float(v) for v in prof["PRES"].values.flat]
        temp = [float(v) for v in prof["TEMP"].values.flat]
        psal = ([float(v) for v in prof["PSAL"].values.flat]
                if "PSAL" in prof else [])
        out["depths"] = depths
        out[f"Float {i + 1}"] = {"temp": temp, "psal": psal}
    return out


def _classify_temp(temp: float) -> str:
    if temp >= 26:
        return "warm"
    if temp <= 16:
        return "cool"
    return "anomaly"


# --------------------------------------------------------------------------- #
# Mock data (default)
# --------------------------------------------------------------------------- #
_MOCK_POSITIONS = {
    "Arabian Sea": [
        (64.0, 18.0, 27.8), (66.5, 16.0, 27.2), (63.5, 14.0, 26.9),
        (68.0, 19.0, 15.4), (69.5, 16.5, 26.5), (68.5, 13.5, 15.1),
        (62.0, 13.0, 27.0), (66.0, 20.5, 22.0), (65.0, 11.5, 27.4),
        (70.5, 18.0, 26.8), (71.5, 15.5, 15.9), (70.0, 13.0, 21.5),
        (64.5, 17.0, 27.1), (62.5, 12.5, 15.7),
    ],
    "Bay of Bengal": [
        (85.0, 15.0, 28.1), (88.5, 13.0, 27.6), (90.0, 17.0, 28.4),
        (87.0, 11.0, 27.9), (92.0, 14.5, 16.2), (84.0, 18.0, 22.4),
        (89.0, 19.5, 28.0), (91.0, 12.0, 15.8), (86.0, 16.5, 27.5),
        (93.0, 15.0, 21.0),
    ],
}
_MOCK_PSAL = {"Arabian Sea": 36.5, "Bay of Bengal": 33.1}


def _fetch_mock(params: QueryParams, region: str) -> dict:
    raw = _MOCK_POSITIONS.get(region, _MOCK_POSITIONS["Arabian Sea"])
    base_psal = _MOCK_PSAL.get(region, 35.0)
    positions = [
        {"lon": x, "lat": y, "temp": t,
         "psal": round(base_psal + (i % 5) * 0.1, 2),
         "category": _classify_temp(t)}
        for i, (x, y, t) in enumerate(raw)
    ]

    depths = [0, 50, 100, 150, 200, 300, 400, 500]
    profiles = {"depths": depths}
    shifts = [0.0, -0.4, 0.4]
    for i, shift in enumerate(shifts):
        temp = [round(v + shift, 1) for v in
                (28.0, 27.2, 24.5, 19.0, 16.5, 14.2, 13.0, 12.2)]
        psal = [round(base_psal - 0.2 + d / 5000, 2) for d in depths]
        profiles[f"Float 690{2746 + i * 65}"] = {"temp": temp, "psal": psal}

    months = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
    timeseries = {
        "months": months,
        "Arabian Sea": [28.9, 27.8, 26.4, 25.1, 25.6, 27.0],
        "Bay of Bengal": [29.4, 28.6, 27.5, 27.0, 27.4, 28.5],
    }

    # Band from the mock profiles (so the structure matches live data).
    all_pres = [d for _ in range(len(shifts)) for d in depths]
    all_temp = [t for k, v in profiles.items() if k != "depths"
                for t in v["temp"]]
    band = _depth_band(all_pres, all_temp)

    return {
        "region": region,
        "period": "Jan 2023",
        "active_floats": len(positions),
        "data_points": "18.4k" if region == "Arabian Sea" else "9.7k",
        "positions": positions,
        "profiles": profiles,
        "profile_band": band,
        "timeseries": timeseries,
        "source": "mock",
    }


# --------------------------------------------------------------------------- #
# Insight generator
# --------------------------------------------------------------------------- #
_INSIGHT_SYSTEM = (
    "You are FloatChat, an oceanography assistant. Given a JSON summary of Argo "
    "float data, write 2-3 concise, factual sentences highlighting the key "
    "oceanographic insight (temperature structure, thermocline, salinity, "
    "anomalies). No preamble, no markdown headers."
)


def generate_insight(params: QueryParams, data: dict) -> str:
    """Natural-language insight for a result, via Gemini if available."""
    client = get_client()
    if client is not None:
        try:
            from google.genai import types  # noqa: WPS433
            summary = {
                "region": data["region"], "period": data["period"],
                "active_floats": data["active_floats"],
                "sample_positions": data["positions"][:5],
                "intent": params.intent,
            }
            resp = client.models.generate_content(
                model=MODEL,
                contents=json.dumps(summary),
                config=types.GenerateContentConfig(
                    system_instruction=_INSIGHT_SYSTEM,
                    max_output_tokens=300,
                ),
            )
            return resp.text.strip()
        except Exception:
            pass
    return _mock_insight(params, data)


def _mock_insight(params: QueryParams, data: dict) -> str:
    region = data["region"]
    if params.intent == "compare":
        return (
            "The Bay of Bengal has noticeably fresher water due to monsoon river "
            "runoff, a shallower mixed layer (~50 m vs ~80 m), and a weaker "
            "thermocline. Surface temperatures are similar but Bay of Bengal "
            "stratification is more pronounced."
        )
    if params.intent == "timeseries":
        return (
            f"Surface temperature in the {region} follows a clear seasonal cycle, "
            "cooling through the winter monsoon to a January minimum before "
            "warming again into spring."
        )
    return (
        f"Found **{data['active_floats']} active floats** in the {region} basin "
        f"for {data['period']}. Surface temperatures range 24–28 °C with a strong "
        "thermocline between 80–150 m. Deep water below 300 m is stable at "
        "12–15 °C."
    )


# --------------------------------------------------------------------------- #
# Data-grounded metrics — computed from the actual fetched arrays
# --------------------------------------------------------------------------- #
def _r(v, n=1):
    """Round, treating NaN/inf/non-numbers as None (keeps output JSON-safe)."""
    import math
    if isinstance(v, (int, float)) and math.isfinite(v):
        return round(v, n)
    return None


def _clean(values):
    """Drop NaN/inf from a numeric list."""
    import math
    return [v for v in values
            if isinstance(v, (int, float)) and math.isfinite(v)]


def compute_metrics(data: dict) -> dict:
    """Derive real oceanographic metrics from a fetched/mock data dict.

    These numbers are what the LLM reasons over, so insights are grounded in
    the data rather than templated. All outputs are finite or None so the
    result is safe to JSON-serialize back to the model.
    """
    import statistics

    profiles = data.get("profiles", {})
    depths = profiles.get("depths", [])
    series = [v for k, v in profiles.items() if k != "depths"]

    avg_temp: list = []
    for i in range(len(depths)):
        vals = _clean([s["temp"][i] for s in series
                       if i < len(s.get("temp", []))])
        avg_temp.append(statistics.mean(vals) if vals else None)

    surface_t = avg_temp[0] if avg_temp else None
    deep_t = next((t for t in reversed(avg_temp) if t is not None), None)

    # Thermocline = depth of steepest temperature gradient.
    thermo_depth, max_grad = None, 0.0
    for i in range(1, len(depths)):
        if avg_temp[i] is None or avg_temp[i - 1] is None:
            continue
        dz = max(1, depths[i] - depths[i - 1])
        grad = abs(avg_temp[i] - avg_temp[i - 1]) / dz
        if grad > max_grad:
            max_grad, thermo_depth = grad, depths[i]

    # Mixed-layer depth = first depth >0.2 °C cooler than the surface.
    mld = None
    if surface_t is not None:
        for i, d in enumerate(depths):
            if avg_temp[i] is not None and avg_temp[i] < surface_t - 0.2:
                mld = d
                break

    psal_vals = _clean([s for v in series for s in v.get("psal", [])])
    sal_mean = statistics.mean(psal_vals) if psal_vals else None

    cats: dict = {}
    for p in data.get("positions", []):
        cats[p["category"]] = cats.get(p["category"], 0) + 1

    return {
        "region": data["region"], "period": data["period"],
        "source": data["source"], "active_floats": data["active_floats"],
        "surface_temp_c": _r(surface_t), "deep_temp_c": _r(deep_t),
        "thermocline_depth_m": _r(thermo_depth, 0),
        "mixed_layer_depth_m": _r(mld, 0),
        "mean_salinity_psu": _r(sal_mean, 2),
        "warm_floats": cats.get("warm", 0), "cool_floats": cats.get("cool", 0),
        "anomaly_floats": cats.get("anomaly", 0),
    }


def comparison_metrics(data_a: dict | None = None,
                       data_b: dict | None = None) -> dict:
    """Comparison table — computed from real data when two datasets are given."""
    if data_a and data_b:
        ma, mb = compute_metrics(data_a), compute_metrics(data_b)

        def fmt(v, unit):
            return f"{v}{unit}" if v is not None else "—"

        return {
            "region_a": data_a["region"], "region_b": data_b["region"],
            "metrics": [
                ("Mean salinity", fmt(ma["mean_salinity_psu"], " PSU"),
                 fmt(mb["mean_salinity_psu"], " PSU")),
                ("Mixed layer", fmt(ma["mixed_layer_depth_m"], " m"),
                 fmt(mb["mixed_layer_depth_m"], " m")),
                ("Surface temp", fmt(ma["surface_temp_c"], " °C"),
                 fmt(mb["surface_temp_c"], " °C")),
                ("Thermocline depth", fmt(ma["thermocline_depth_m"], " m"),
                 fmt(mb["thermocline_depth_m"], " m")),
            ],
        }
    return {
        "region_a": "Arabian Sea", "region_b": "Bay of Bengal",
        "metrics": [
            ("Salinity", "36.5 PSU", "33.1 PSU"),
            ("Mixed layer", "80m", "50m"),
            ("Surface temp", "27.1°C", "27.8°C"),
            ("Thermocline", "Strong", "Moderate"),
        ],
    }


def today_range() -> tuple[date, date]:
    """Default date pickers range used by the sidebar."""
    return date(2023, 1, 1), date(2023, 1, 31)


# --------------------------------------------------------------------------- #
# Agent: Gemini function-calling + conversational memory
# --------------------------------------------------------------------------- #
_AGENT_SYSTEM = (
    "You are FloatChat, an autonomous oceanography research agent for Argo float "
    "data. Work in multiple steps WITHOUT asking the user for permission:\n"
    "1. Call a tool to fetch the data the question needs (never invent numbers).\n"
    "2. Inspect the returned metrics and especially the 'anomalies' field.\n"
    "3. If anomalies are flagged, or the question is comparative/causal, take a "
    "FOLLOW-UP step on your own: call get_comparison against a contrasting "
    "region (Arabian Sea vs Bay of Bengal are natural contrasts), or "
    "get_time_series / get_ts_diagram to investigate the cause.\n"
    "4. Once you have enough evidence, synthesize a concise answer (2-5 "
    "sentences) that references the ACTUAL values (surface/deep temperature, "
    "thermocline and mixed-layer depth, salinity, float counts), explicitly "
    "calls out any anomaly, and explains it.\n"
    f"Available regions: {list(REGION_PRESETS)}. Use the conversation history to "
    "resolve follow-ups like 'now show that deeper' or 'compare it to X'. "
    "Take at most a few investigative steps. No markdown headers."
)


def _anomaly_notes(m: dict) -> list[str]:
    """Flag noteworthy values in a metrics dict so the agent can react."""
    notes: list[str] = []
    n = m.get("active_floats", 0) or 0
    if m.get("anomaly_floats", 0) >= max(3, 0.1 * n):
        notes.append(f"{m['anomaly_floats']} anomalous floats")
    mld = m.get("mixed_layer_depth_m")
    if mld is not None and mld <= 20:
        notes.append(f"very shallow mixed layer ({mld} m)")
    elif mld is not None and mld >= 120:
        notes.append(f"very deep mixed layer ({mld} m)")
    thermo = m.get("thermocline_depth_m")
    if thermo is not None and thermo <= 40:
        notes.append(f"shallow thermocline ({thermo} m)")
    st = m.get("surface_temp_c")
    if st is not None and st >= 30:
        notes.append(f"very warm surface ({st} °C)")
    elif st is not None and st <= 10:
        notes.append(f"cold surface ({st} °C)")
    sal = m.get("mean_salinity_psu")
    if sal is not None and sal >= 36.5:
        notes.append(f"high salinity ({sal} PSU)")
    elif sal is not None and sal <= 33.5:
        notes.append(f"low salinity ({sal} PSU)")
    return notes


def _artifact_anomalies(artifact: dict) -> list[str]:
    """Anomaly notes for whatever data an artifact carries."""
    if not artifact:
        return []
    if artifact.get("type") == "comparison":
        cm = artifact.get("metrics", {})
        out = []
        for a in _anomaly_notes(compute_metrics(artifact.get("data", {}))):
            out.append(f"{cm.get('region_a', 'A')}: {a}")
        return out
    data = artifact.get("data")
    return _anomaly_notes(compute_metrics(data)) if data else []


def _run_tool(filters: dict, call):
    """Execute one tool call. Returns (artifact, result, step, used_mock)."""
    fn = _TOOL_DISPATCH.get(call.name)
    args = dict(call.args) if call.args else {}
    arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
    if fn is None:
        return None, {"error": f"unknown tool {call.name}"}, \
            f"{call.name}({arg_str})", False
    try:
        artifact, res = fn(filters, **args)
    except Exception as exc:
        return None, {"error": str(exc)}, f"{call.name}({arg_str}) failed", False

    anomalies = _artifact_anomalies(artifact)
    if anomalies:
        res = dict(res)
        res["anomalies"] = anomalies
    used_mock = artifact.get("data", {}).get("source") == "mock"
    step = f"{call.name}({arg_str})"
    if anomalies:
        step += " — flagged " + "; ".join(anomalies)
    return artifact, res, step, used_mock


def _make_params(filters: dict, region: str) -> QueryParams:
    p = QueryParams(regions=[region])
    p.depth_range = tuple(filters["depth"])
    p.date_range = tuple(filters["date_range"])
    p.variables = filters["variables"]
    return p


def _tool_overview(filters, region, **_):
    data = fetch_from_params(_make_params(filters, region), source=filters["source"])
    return {"type": "overview", "data": data}, compute_metrics(data)


def _tool_ts_diagram(filters, region, **_):
    data = fetch_from_params(_make_params(filters, region), source=filters["source"])
    return {"type": "ts_diagram", "data": data}, compute_metrics(data)


def _tool_time_series(filters, regions=None, **_):
    regions = regions or [filters["region"]]
    data = fetch_from_params(_make_params(filters, regions[0]),
                             source=filters["source"])
    return ({"type": "timeseries", "data": data, "regions": regions},
            {"timeseries": data["timeseries"], "regions": regions})


def _tool_comparison(filters, region_a, region_b, **_):
    da = fetch_from_params(_make_params(filters, region_a), source=filters["source"])
    db = fetch_from_params(_make_params(filters, region_b), source=filters["source"])
    cm = comparison_metrics(da, db)
    # Send only plain dicts to the model (the cm table holds tuples, which are
    # not JSON-serializable for the function response).
    return ({"type": "comparison", "metrics": cm, "data": da},
            {"region_a": compute_metrics(da), "region_b": compute_metrics(db)})


_TOOL_DISPATCH = {
    "get_ocean_overview": _tool_overview,
    "get_ts_diagram": _tool_ts_diagram,
    "get_time_series": _tool_time_series,
    "get_comparison": _tool_comparison,
}


def _tool_declarations(types):
    s, t = types.Schema, types.Type
    region = lambda d: s(type=t.STRING, description=d, enum=list(REGION_PRESETS))
    return [types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_ocean_overview",
            description="Fetch float positions and temperature-depth profiles "
                        "for one region, with computed metrics.",
            parameters=s(type=t.OBJECT,
                         properties={"region": region("Ocean region")},
                         required=["region"])),
        types.FunctionDeclaration(
            name="get_ts_diagram",
            description="Fetch data and compute the temperature-salinity "
                        "relationship (water masses) for one region.",
            parameters=s(type=t.OBJECT,
                         properties={"region": region("Ocean region")},
                         required=["region"])),
        types.FunctionDeclaration(
            name="get_time_series",
            description="Fetch the seasonal surface-temperature time series for "
                        "one or more regions.",
            parameters=s(type=t.OBJECT,
                         properties={"regions": s(type=t.ARRAY,
                                                  items=region("Ocean region"))},
                         required=["regions"])),
        types.FunctionDeclaration(
            name="get_comparison",
            description="Compare two regions across salinity, mixed layer, "
                        "surface temperature and thermocline depth.",
            parameters=s(type=t.OBJECT,
                         properties={"region_a": region("First region"),
                                     "region_b": region("Second region")},
                         required=["region_a", "region_b"])),
    ])]


def _note_for(filters: dict, used_mock: bool) -> str | None:
    if filters["source"] == "mock":
        return "Mock sample data — selected in the sidebar."
    if used_mock and LAST_FETCH_ERROR:
        return f"Showing mock data — {LAST_FETCH_ERROR}"
    return None


def _is_transient(exc: Exception) -> bool:
    """True for retryable Gemini errors: 429 rate limit / 503 overloaded."""
    s = str(exc)
    return any(code in s for code in ("429", "503", "RESOURCE_EXHAUSTED",
                                      "UNAVAILABLE", "overloaded", "high demand"))


def _generate_retry(client, **kwargs):
    """Call generate_content, retrying transient 429/503 with backoff."""
    import time
    delay = 1.0
    last = None
    for attempt in range(3):
        try:
            return client.models.generate_content(**kwargs)
        except Exception as exc:
            last = exc
            if not _is_transient(exc) or attempt == 2:
                raise
            time.sleep(delay)
            delay *= 2  # 1s, 2s
    raise last  # pragma: no cover


def run_turn(history: list[dict], filters: dict) -> dict:
    """One assistant turn. Returns {insight, artifacts, note}.

    history: [{"role": "user"|"assistant", "text": str}, ...]
    artifacts: ordered list of render specs, e.g. {"type": "overview", "data": ...}
    """
    client = get_client()
    if client is None:
        return _fallback_turn(history, filters)
    try:
        return _gemini_turn(client, history, filters)
    except Exception as exc:  # any SDK/tool error -> graceful fallback
        res = _fallback_turn(history, filters)
        if _is_transient(exc):
            msg = ("Gemini is busy (rate-limited or overloaded) — showing "
                   "computed results from the data. Try again in a moment.")
        else:
            detail = (str(exc).splitlines()[0][:160] if str(exc)
                      else type(exc).__name__)
            msg = f"AI turn failed: {detail}"
        res["note"] = (res.get("note") + " " if res.get("note") else "") + msg
        return res


def _gemini_turn(client, history: list[dict], filters: dict) -> dict:
    from google.genai import types  # noqa: WPS433

    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["text"])])
        for m in history if m.get("text")
    ]
    config = types.GenerateContentConfig(
        system_instruction=_AGENT_SYSTEM,
        tools=_tool_declarations(types),
        max_output_tokens=800,
    )

    artifacts: list = []
    used_mock = False
    resp = None
    for _ in range(5):  # bounded tool-call rounds
        resp = _generate_retry(
            client, model=MODEL, contents=contents, config=config)
        cand = resp.candidates[0].content
        contents.append(cand)
        calls = [p.function_call for p in (cand.parts or [])
                 if getattr(p, "function_call", None)]
        if not calls:
            break
        for call in calls:
            fn = _TOOL_DISPATCH.get(call.name)
            args = dict(call.args) if call.args else {}
            try:
                artifact, result = fn(filters, **args)
                artifacts.append(artifact)
                if artifact.get("data", {}).get("source") == "mock":
                    used_mock = True
            except Exception as exc:
                result = {"error": str(exc)}
            contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(
                    name=call.name, response={"result": result})]))

    insight = ((resp.text or "").strip() if resp else "") or \
        "Here's what I found from the Argo data."
    return {"insight": insight, "artifacts": artifacts,
            "note": _note_for(filters, used_mock)}


def _fallback_turn(history: list[dict], filters: dict) -> dict:
    """No-API path: keyword parse the last user message into one artifact."""
    last = next((m["text"] for m in reversed(history)
                 if m["role"] == "user"), "")
    params = parse_query(last)
    if (params.regions == ["Arabian Sea"]
            and filters["region"] != "Arabian Sea"):
        params.regions = [filters["region"]]
    params.depth_range = tuple(filters["depth"])
    params.date_range = tuple(filters["date_range"])
    if filters["variables"]:
        params.variables = filters["variables"]

    if params.intent == "help":
        return {"insight": HELP_TEXT, "artifacts": [], "note": None}

    region = params.regions[0]
    data = fetch_from_params(params, source=filters["source"])
    used_mock = data["source"] == "mock"
    artifacts: list = []

    if params.intent == "compare":
        other = "Bay of Bengal" if region != "Bay of Bengal" else "Arabian Sea"
        db = fetch_from_params(_make_params(filters, other),
                               source=filters["source"])
        artifacts.append({"type": "comparison",
                          "metrics": comparison_metrics(data, db), "data": data})
    elif params.intent == "timeseries":
        regions = params.regions if len(params.regions) > 1 \
            else [region, "Bay of Bengal"]
        artifacts.append({"type": "timeseries", "data": data, "regions": regions})
    elif params.intent == "ts_diagram":
        artifacts.append({"type": "ts_diagram", "data": data})
    else:
        artifacts.append({"type": "overview", "data": data})

    return {"insight": _mock_insight(params, data), "artifacts": artifacts,
            "note": _note_for(filters, used_mock)}


# --------------------------------------------------------------------------- #
# Streaming variant — yields text chunks live (for st.write_stream)
# --------------------------------------------------------------------------- #
def _chunk(text: str):
    """Yield a string word-by-word for a typing effect (fallback path)."""
    import time
    for i, word in enumerate(text.split(" ")):
        yield (word if i == 0 else " " + word)
        time.sleep(0.015)


def stream_turn(history: list[dict], filters: dict, result: dict):
    """Generator yielding insight text chunks live.

    `result` is populated in place with {"artifacts", "note"} once known, so
    the caller can render charts after st.write_stream() returns the full text.
    """
    result.setdefault("steps", [])
    client = get_client()
    if client is None:
        r = _fallback_turn(history, filters)
        result["artifacts"], result["note"] = r["artifacts"], r["note"]
        yield from _chunk(r["insight"])
        return
    try:
        yield from _gemini_stream(client, history, filters, result)
    except Exception as exc:  # transient/other -> grounded fallback
        r = _fallback_turn(history, filters)
        result["artifacts"] = r["artifacts"]
        if _is_transient(exc):
            note = ("Gemini is busy (rate-limited or overloaded) — showing "
                    "computed results from the data. Try again in a moment.")
        else:
            detail = (str(exc).splitlines()[0][:160] if str(exc)
                      else type(exc).__name__)
            note = f"AI turn failed: {detail}"
        result["note"] = (r["note"] + " " if r["note"] else "") + note
        yield from _chunk(r["insight"])


def _gemini_stream(client, history: list[dict], filters: dict, result: dict):
    import time
    from google.genai import types  # noqa: WPS433

    contents = [
        types.Content(role="user" if m["role"] == "user" else "model",
                      parts=[types.Part(text=m["text"])])
        for m in history if m.get("text")
    ]
    config = types.GenerateContentConfig(
        system_instruction=_AGENT_SYSTEM,
        tools=_tool_declarations(types),
        max_output_tokens=800,
    )

    artifacts: list = []
    steps: list = []
    used_mock = False
    for _ in range(6):  # bounded agent rounds (plan -> fetch -> follow-up -> ...)
        text_parts: list = []
        fcalls: list = []
        attempt = 0
        while True:  # retry a round only if it fails before emitting text
            yielded = False
            try:
                stream = client.models.generate_content_stream(
                    model=MODEL, contents=contents, config=config)
                for ck in stream:
                    if not ck.candidates:
                        continue
                    for p in (ck.candidates[0].content.parts or []):
                        fc = getattr(p, "function_call", None)
                        if fc:
                            fcalls.append(fc)
                        elif getattr(p, "text", None):
                            text_parts.append(p.text)
                            yielded = True
                            yield p.text
                break
            except Exception as exc:
                if _is_transient(exc) and not yielded and attempt < 2:
                    attempt += 1
                    text_parts, fcalls = [], []
                    time.sleep(2 ** attempt)
                    continue
                raise

        parts = []
        if text_parts:
            parts.append(types.Part(text="".join(text_parts)))
        for fc in fcalls:
            parts.append(types.Part(function_call=fc))
        if parts:
            contents.append(types.Content(role="model", parts=parts))

        if not fcalls:
            break
        for call in fcalls:
            artifact, res, step, mock = _run_tool(filters, call)
            steps.append(step)
            if artifact is not None:
                artifacts.append(artifact)
            used_mock = used_mock or mock
            contents.append(types.Content(role="user", parts=[
                types.Part.from_function_response(
                    name=call.name, response={"result": res})]))

    result["artifacts"] = artifacts
    result["steps"] = steps
    result["note"] = _note_for(filters, used_mock)
