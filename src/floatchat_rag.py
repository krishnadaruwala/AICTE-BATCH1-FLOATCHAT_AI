"""
floatchat_rag — retrieval-augmented answering over an oceanography knowledge base.

Pipeline:
    embed curated docs (Gemini embeddings) -> cosine vector store (cached to
    ./data) -> retrieve top-k for a question -> Gemini answers using ONLY the
    retrieved context and cites sources inline ([1], [2], ...).

Everything degrades gracefully:
    * No API key  -> lexical (keyword-overlap) retrieval + extractive answer.
    * Embeddings fail -> same lexical fallback.
So the module is import-safe and runnable offline.
"""

from __future__ import annotations

import json
import math
import os
import re

import floatchat_core as core  # reuse client, MODEL, retry, _chunk, _is_transient

EMBED_MODEL = "text-embedding-004"
_BASE = os.path.dirname(__file__)
_INDEX_PATH = os.path.join(_BASE, "..", "data", "rag_index.json")
DOCS_DIR = os.path.join(_BASE, "..", "docs")  # drop your own .txt/.md here
TOP_K = 3
_CHUNK_CHARS = 900  # target characters per chunk

# --------------------------------------------------------------------------- #
# Knowledge base — concise, well-established oceanography facts with sources.
# (Standard textbook / program-documentation knowledge, not novel claims.)
# --------------------------------------------------------------------------- #
DOCS: list[dict] = [
    {"id": "argo-overview", "title": "What Argo floats are",
     "source": "Argo Program, argo.ucsd.edu",
     "text": "Argo is a global array of ~4000 autonomous profiling floats that "
             "drift with ocean currents. A float typically parks at ~1000 m, "
             "descends to ~2000 m, then rises to the surface every ~10 days, "
             "measuring temperature, salinity and pressure along the way and "
             "transmitting the profile via satellite."},
    {"id": "thermocline", "title": "Thermocline",
     "source": "Talley et al., Descriptive Physical Oceanography",
     "text": "The thermocline is the depth zone where temperature decreases "
             "rapidly with depth, separating warm surface water from cold deep "
             "water. It is identified as the depth of maximum vertical "
             "temperature gradient. A strong (sharp) thermocline indicates "
             "stable stratification and limited vertical mixing."},
    {"id": "mixed-layer", "title": "Mixed layer depth",
     "source": "NOAA / WHOI ocean education",
     "text": "The surface mixed layer is the near-surface region kept nearly "
             "uniform in temperature and salinity by wind and convective "
             "mixing. Mixed layer depth (MLD) is commonly defined as the depth "
             "where temperature drops about 0.2 C below the surface value. A "
             "shallow mixed layer implies strong stratification near the "
             "surface."},
    {"id": "salinity-psu", "title": "Salinity and PSU",
     "source": "UNESCO Practical Salinity Scale",
     "text": "Salinity measures dissolved salt content, reported on the "
             "Practical Salinity Scale in PSU (practical salinity units). Open "
             "ocean salinity is typically 34-37 PSU. Evaporation and ice "
             "formation raise salinity; precipitation, river runoff and ice "
             "melt lower it."},
    {"id": "ts-diagram", "title": "Temperature-salinity (T-S) diagrams",
     "source": "Talley et al., Descriptive Physical Oceanography",
     "text": "A T-S diagram plots temperature against salinity for a profile. "
             "Because water masses have characteristic temperature-salinity "
             "signatures, T-S diagrams are used to identify and trace water "
             "masses and mixing between them. Lines of constant density "
             "(isopycnals) are often overlaid."},
    {"id": "water-mass", "title": "Water masses",
     "source": "Talley et al., Descriptive Physical Oceanography",
     "text": "A water mass is a body of water with a common formation history "
             "and a distinctive range of temperature and salinity. Water "
             "masses form at the surface, then sink and spread along surfaces "
             "of constant density, retaining their T-S signature far from their "
             "origin."},
    {"id": "arabian-sea", "title": "Arabian Sea characteristics",
     "source": "Indian Ocean physical oceanography literature",
     "text": "The Arabian Sea is highly saline (often >36.5 PSU) due to strong "
             "evaporation and limited freshwater input, and hosts a pronounced "
             "oxygen minimum zone. Monsoon winds drive seasonal upwelling and a "
             "relatively deep, well-developed mixed layer."},
    {"id": "bay-of-bengal", "title": "Bay of Bengal characteristics",
     "source": "Indian Ocean physical oceanography literature",
     "text": "The Bay of Bengal receives large freshwater input from monsoon "
             "rainfall and major rivers, making surface waters relatively fresh "
             "(often 33 PSU or lower). This creates a shallow, strongly "
             "stratified mixed layer and a barrier layer that suppresses "
             "vertical mixing."},
    {"id": "thermocline-vs-mld", "title": "Thermocline vs mixed layer",
     "source": "NOAA ocean education",
     "text": "The mixed layer sits above the thermocline. The mixed layer is "
             "vertically uniform; the thermocline immediately below it is where "
             "temperature falls steeply. A shallow mixed layer is usually "
             "paired with a shallow, sharp thermocline."},
    {"id": "argo-qc", "title": "Argo data quality and delayed mode",
     "source": "Argo Data Management",
     "text": "Argo profiles carry quality-control flags. Real-time data pass "
             "automated checks; delayed-mode data are adjusted by experts for "
             "sensor drift, especially salinity. Fill values (NaN) mark missing "
             "or rejected measurements and should be excluded from analysis."},
    {"id": "ohc", "title": "Ocean heat content",
     "source": "IPCC / NOAA climate indicators",
     "text": "Ocean heat content is the integrated thermal energy stored in a "
             "column of seawater, computed from temperature profiles. Argo's "
             "global coverage made robust upper-ocean heat content estimates "
             "possible, a key indicator of global warming."},
    {"id": "upwelling", "title": "Upwelling",
     "source": "NOAA ocean facts",
     "text": "Upwelling is the wind-driven rise of cold, nutrient-rich deep "
             "water to the surface. It lowers surface temperature, shoals the "
             "thermocline, and fuels biological productivity. The Arabian Sea "
             "experiences strong monsoon-driven coastal upwelling."},
]


# --------------------------------------------------------------------------- #
# User documents — drop .txt / .md files into ./docs to extend the knowledge base
# --------------------------------------------------------------------------- #
def _chunk_text(text: str) -> list[str]:
    """Split text into ~_CHUNK_CHARS chunks on paragraph boundaries."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) + 2 > _CHUNK_CHARS:
            chunks.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        chunks.append(buf)
    return chunks


def _title_for(text: str, fname: str, i: int) -> str:
    """Use a leading markdown heading if present, else filename + chunk number."""
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    heading = first.lstrip("#").strip()
    if first.startswith("#") and heading:
        return heading[:80]
    base = os.path.splitext(os.path.basename(fname))[0].replace("_", " ")
    return f"{base} (part {i + 1})"


def load_user_docs() -> list[dict]:
    """Read and chunk every .txt/.md file in ./docs into doc records."""
    out: list[dict] = []
    if not os.path.isdir(DOCS_DIR):
        return out
    for fname in sorted(os.listdir(DOCS_DIR)):
        if not fname.lower().endswith((".txt", ".md")):
            continue
        if fname.lower() == "readme.md":  # instructions, not knowledge
            continue
        path = os.path.join(DOCS_DIR, fname)
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except Exception:
            continue
        for i, chunk in enumerate(_chunk_text(text)):
            out.append({
                "id": f"user::{fname}::{i}",
                "title": _title_for(chunk, fname, i),
                "source": fname,
                "text": chunk,
            })
    return out


def get_corpus() -> list[dict]:
    """Curated docs plus any user-provided documents from ./docs."""
    return DOCS + load_user_docs()


# --------------------------------------------------------------------------- #
# Query routing
# --------------------------------------------------------------------------- #
_CONCEPT_TRIGGERS = (
    "what is", "what are", "what's", "what causes", "why", "how does",
    "how do", "how are", "explain", "define", "definition", "meaning of",
    "difference between", "tell me about", "describe", "concept",
)


def is_rag_query(prompt: str) -> bool:
    """True for conceptual/explanatory questions (vs. data-retrieval queries)."""
    p = prompt.lower().strip()
    return any(t in p for t in _CONCEPT_TRIGGERS)


def rag_available() -> bool:
    """RAG always works (lexical fallback); True signals the feature is on."""
    return True


# --------------------------------------------------------------------------- #
# Embeddings + vector store
# --------------------------------------------------------------------------- #
def _docs_signature() -> str:
    return str(hash(tuple(d["id"] + d["text"] for d in get_corpus())))


def _embed(texts: list[str]) -> list[list[float]] | None:
    """Embed texts with Gemini; None if unavailable."""
    client = core.get_client()
    if client is None:
        return None
    try:
        resp = client.models.embed_content(model=EMBED_MODEL, contents=texts)
        return [list(e.values) for e in resp.embeddings]
    except Exception:
        return None


_INDEX: list[dict] | None = None  # [{doc, vec}]
_INDEX_SIG: str | None = None      # corpus signature the index was built for


def _load_cache() -> list[dict] | None:
    try:
        with open(_INDEX_PATH, encoding="utf-8") as fh:
            blob = json.load(fh)
        if blob.get("signature") == _docs_signature() \
                and blob.get("model") == EMBED_MODEL:
            return blob["entries"]
    except Exception:
        pass
    return None


def _save_cache(entries: list[dict]) -> None:
    try:
        os.makedirs(os.path.dirname(_INDEX_PATH), exist_ok=True)
        with open(_INDEX_PATH, "w", encoding="utf-8") as fh:
            json.dump({"signature": _docs_signature(), "model": EMBED_MODEL,
                       "entries": entries}, fh)
    except Exception:
        pass


def _ensure_index() -> list[dict] | None:
    """Build/load the embedded vector store, rebuilding if the corpus changed."""
    global _INDEX, _INDEX_SIG
    sig = _docs_signature()
    if _INDEX is not None and _INDEX_SIG == sig:
        return _INDEX

    cached = _load_cache()
    if cached:
        _INDEX, _INDEX_SIG = cached, sig
        return _INDEX

    corpus = get_corpus()
    vecs = _embed([d["text"] for d in corpus])
    if not vecs:
        return None  # lexical fallback (no embeddings available)
    _INDEX = [{"doc": d, "vec": v} for d, v in zip(corpus, vecs)]
    _INDEX_SIG = sig
    _save_cache(_INDEX)
    return _INDEX


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


_STOPWORDS = {
    "the", "what", "why", "how", "does", "are", "and", "for", "with", "explain",
    "define", "tell", "about", "between", "difference", "this", "that", "from",
    "into", "you", "can", "show", "give", "describe", "meaning", "concept",
}


def _terms(text: str) -> set:
    return {w for w in re.findall(r"[a-z]{3,}", text.lower())
            if w not in _STOPWORDS}


def _lexical_score(query: str, doc: dict) -> float:
    q = _terms(query)
    if not q:
        return 0.0
    # Title matches count double — they're the strongest topical signal.
    title = _terms(doc["title"])
    body = _terms(doc["text"])
    return (2 * len(q & title) + len(q & body)) / len(q)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Top-k docs by embedding cosine similarity, else lexical overlap."""
    index = _ensure_index()
    if index:
        qv = _embed([query])
        if qv:
            scored = sorted(index, key=lambda e: _cosine(qv[0], e["vec"]),
                            reverse=True)
            return [e["doc"] for e in scored[:k]]
    scored = sorted(get_corpus(), key=lambda d: _lexical_score(query, d),
                    reverse=True)
    return scored[:k]


# --------------------------------------------------------------------------- #
# Answering
# --------------------------------------------------------------------------- #
_ANSWER_SYSTEM = (
    "You are FloatChat, an oceanography tutor. Answer the user's question using "
    "ONLY the numbered context passages provided. Cite the passages you use "
    "inline as [1], [2], etc. If the context does not cover the question, say "
    "so briefly. Be concise (2-4 sentences). No markdown headers."
)


def _context_block(hits: list[dict]) -> str:
    return "\n\n".join(f"[{i + 1}] {d['title']}: {d['text']}"
                       for i, d in enumerate(hits))


def _fallback_answer(prompt: str, hits: list[dict]) -> str:
    top = hits[0]
    return (f"{top['text']} [1]\n\n*(Offline mode: showing the most relevant "
            "knowledge-base entry. Set GEMINI_API_KEY for synthesized, "
            "multi-source answers.)*")


def stream_answer(prompt: str, context: str, result: dict):
    """Generator yielding the answer live; populates result['sources']."""
    hits = retrieve(prompt, TOP_K)
    result["sources"] = [f"{d['title']} — {d['source']}" for d in hits]

    client = core.get_client()
    if client is None:
        yield from core._chunk(_fallback_answer(prompt, hits))
        return

    from google.genai import types  # noqa: WPS433
    contents = (f"Context passages:\n{_context_block(hits)}\n\n"
                + (f"Conversation so far:\n{context}\n\n" if context else "")
                + f"Question: {prompt}")
    config = types.GenerateContentConfig(
        system_instruction=_ANSWER_SYSTEM, max_output_tokens=400)
    try:
        any_text = False
        stream = client.models.generate_content_stream(
            model=core.MODEL, contents=contents, config=config)
        for ck in stream:
            if not ck.candidates:
                continue
            for p in (ck.candidates[0].content.parts or []):
                if getattr(p, "text", None):
                    any_text = True
                    yield p.text
        if not any_text:
            yield from core._chunk(_fallback_answer(prompt, hits))
    except Exception:
        yield from core._chunk(_fallback_answer(prompt, hits))


def answer_ocean_question(prompt: str, context: str = "") -> dict:
    """Non-streaming convenience wrapper. Returns {answer, sources}."""
    result: dict = {"sources": []}
    answer = "".join(stream_answer(prompt, context, result))
    return {"answer": answer, "sources": result["sources"]}
