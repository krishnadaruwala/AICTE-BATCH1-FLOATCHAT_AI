# 🌊 FloatChat

A conversational assistant for exploring **Argo** ocean-float data — ask about
temperature, salinity, depth profiles, float tracks, and regional anomalies in
natural language and get back narrative answers with inline maps and charts.

> The current build ships with **mock Argo data** so the UI runs with zero
> external services. Swap in a live ERDDAP / `argopy` backend when ready (see
> [Going live](#going-live)).

## Project layout

```
floatchat/
├── notebooks/
│   └── FloatChat_Development.ipynb   # exploration & prototyping
├── src/
│   ├── floatchat_core.py             # NLP intent parsing + data fetching
│   ├── floatchat_viz.py              # all Plotly visualizations
│   └── floatchat_app.py              # Streamlit UI
├── data/                             # cached .nc files (gitignored)
├── requirements.txt
└── README.md
```

The three `src` modules are layered: `floatchat_app` (presentation) depends on
`floatchat_viz` (charts) and `floatchat_core` (data + NLP). The core and viz
layers have no Streamlit dependency, so they're reusable from the notebook.

## Quickstart

```bash
cd floatchat
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
streamlit run src/floatchat_app.py
```

Then open the URL Streamlit prints (default http://localhost:8501).

## Usage

The chat is seeded with an example conversation. Try prompts like:

- `Show me temperature profiles in the Arabian Sea at 100–500m, Jan 2023`
- `Compare Arabian Sea and Bay of Bengal salinity`
- `Float tracks in the Indian Ocean`

`floatchat_core.parse_query` routes each prompt to an intent
(`overview` / `compare` / `help`) and extracts region entities.

## Going live

Replace the mock bodies in `floatchat_core.py` with real queries — the
`fetch_erddap` stub shows the intended `argopy` pattern:

```python
from argopy import DataFetcher
ds = DataFetcher().region([55, 78, 5, 26, 0, 500, '2023-01', '2023-02']).to_xarray()
```

Cache downloaded NetCDF files into `./data` (gitignored). For natural-language
parsing beyond keywords, set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) — `parse_query`
and `generate_insight` will call Google Gemini and keep the same
`Query` return shape so the UI is unaffected.
