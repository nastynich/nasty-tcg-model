"""
Nasty TCG Dashboard — v12 (Clean screener UI)
"""
import streamlit as st
import pandas as pd
import numpy as np
import requests
import time
import sys, os

sys.path.insert(0, os.path.dirname(__file__))

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="The Nasty Model", page_icon="🎴", layout="wide")

AVATAR_URL = "https://base44.app/api/apps/69dae320409ba22186ac9552/files/mp/public/69dae320409ba22186ac9552/fb5969149_60b86a1b8_NastyPP_07.png"

# ── FX ────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_usd_to_cad():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        return r.json()["rates"]["CAD"]
    except:
        return 1.39

@st.cache_data(ttl=3600, show_spinner=False)
def get_eur_to_cad():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)
        return r.json()["rates"]["CAD"]
    except:
        return 1.52

FX     = get_usd_to_cad()
FX_EUR = get_eur_to_cad()

def fmt_cad(v): return f"C${v:.2f}"

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }

/* ── App background ── */
.stApp { background: #0a0a0f !important; }
.block-container { background: #0a0a0f !important; padding-top: 1.5rem !important; max-width: 1200px !important; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d0d16 !important;
    border-right: 1px solid #1e1e30 !important;
}
section[data-testid="stSidebar"] > div { padding-top: 0 !important; }

/* ── Hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar avatar block ── */
.sb-profile {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 28px 16px 20px;
    border-bottom: 1px solid #1e1e30;
    margin-bottom: 8px;
}
.sb-avatar {
    width: 68px; height: 68px;
    border-radius: 50%;
    border: 2px solid #d4a017;
    object-fit: cover;
    margin-bottom: 10px;
}
.sb-name {
    font-size: 15px; font-weight: 800;
    color: #ffffff; letter-spacing: 0.3px;
    margin-bottom: 3px;
}
.sb-sub {
    font-size: 10px; color: #5a5a7a;
    letter-spacing: 0.5px;
}
.sb-rate {
    font-size: 11px; color: #d4a017;
    margin-top: 4px; font-weight: 600;
}

/* ── Header ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 14px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #1e1e30;
}
.page-header img {
    width: 44px; height: 44px;
    border-radius: 50%; border: 2px solid #d4a017;
    object-fit: cover;
}
.page-title {
    font-size: 22px; font-weight: 800;
    color: #ffffff; letter-spacing: -0.3px;
}
.page-sub {
    font-size: 11px; color: #5a5a7a; margin-top: 2px;
}

/* ── Stats bar ── */
.stats-bar {
    display: flex; gap: 12px;
    margin-bottom: 18px;
}
.stat-pill {
    background: #12121e;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px; color: #8888aa;
    display: flex; align-items: center; gap: 6px;
}
.stat-pill b { color: #fff; font-size: 15px; font-weight: 700; }
.stat-pill.gold b { color: #d4a017; }
.stat-pill.green b { color: #22c55e; }
.stat-pill.red b { color: #ef4444; }

/* ── Search bar ── */
.stTextInput input {
    background: #12121e !important;
    border: 1px solid #2a2a40 !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-size: 13px !important;
    padding: 8px 14px !important;
}
.stTextInput input:focus {
    border-color: #d4a017 !important;
    box-shadow: 0 0 0 2px rgba(212,160,23,0.15) !important;
}

/* ── Table header ── */
.table-header {
    display: grid;
    grid-template-columns: 44px 80px 1fr 110px 110px 110px 110px;
    gap: 0;
    padding: 8px 16px;
    background: #0d0d16;
    border: 1px solid #1e1e30;
    border-radius: 10px 10px 0 0;
    margin-bottom: 1px;
    align-items: center;
}
.th {
    font-size: 10px; font-weight: 700;
    color: #5a5a7a; text-transform: uppercase;
    letter-spacing: 0.8px;
    cursor: pointer;
    user-select: none;
    padding: 2px 4px;
}
.th:hover { color: #d4a017; }
.th.active { color: #d4a017; }
.th-right { text-align: right; }
.th-center { text-align: center; }

/* ── Table row ── */
.tcg-row {
    display: grid;
    grid-template-columns: 44px 80px 1fr 110px 110px 110px 110px;
    gap: 0;
    padding: 8px 16px;
    background: #0f0f1a;
    border: 1px solid #1a1a28;
    border-top: none;
    align-items: center;
    transition: background 0.12s;
}
.tcg-row:hover { background: #14142a; border-color: #d4a01722; }
.tcg-row:last-child { border-radius: 0 0 10px 10px; }

/* ── Row cells ── */
.cell-rank {
    font-size: 12px; font-weight: 700;
    color: #3a3a55;
    text-align: center;
}
.cell-rank.top1 { color: #ffd700; }
.cell-rank.top2 { color: #c0c0c0; }
.cell-rank.top3 { color: #cd7f32; }

.cell-img { display: flex; align-items: center; }
.cell-img img {
    width: 64px; border-radius: 6px;
    border: 1px solid #1e1e30;
    transition: transform 0.2s;
}
.tcg-row:hover .cell-img img { transform: scale(1.06); }

.cell-info { padding: 0 8px; min-width: 0; }
.cell-name {
    font-size: 14px; font-weight: 700;
    color: #ffffff; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
}
.cell-sub {
    font-size: 10px; color: #5a5a7a;
    white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; margin-top: 2px;
}

.cell-num {
    font-size: 14px; font-weight: 600;
    color: #ccccdd; text-align: right;
    padding-right: 8px;
}
.cell-num.price { color: #ffffff; font-weight: 700; }

.cell-demand { text-align: right; padding-right: 8px; }
.demand-bar {
    width: 100%; height: 4px;
    background: #1e1e30; border-radius: 2px;
    margin-top: 3px;
}
.demand-fill {
    height: 4px; border-radius: 2px;
    background: linear-gradient(90deg, #d4a017, #f5cc50);
}
.demand-pct {
    font-size: 12px; font-weight: 700;
    color: #d4a017; text-align: right;
}

.cell-signal { text-align: center; }
.sig-gem  { display: inline-block; padding: 3px 10px; border-radius: 20px;
            background: #052e1c; color: #22c55e; border: 1px solid #22c55e44;
            font-size: 10px; font-weight: 700; letter-spacing: 0.4px; }
.sig-over { display: inline-block; padding: 3px 10px; border-radius: 20px;
            background: #2e0508; color: #ef4444; border: 1px solid #ef444444;
            font-size: 10px; font-weight: 700; letter-spacing: 0.4px; }
.sig-fair { display: inline-block; padding: 3px 10px; border-radius: 20px;
            background: #1a1a2e; color: #8888cc; border: 1px solid #8888cc44;
            font-size: 10px; font-weight: 700; letter-spacing: 0.4px; }

.cell-gap { text-align: right; padding-right: 4px; }
.gap-pos { font-size: 14px; font-weight: 700; color: #22c55e; }
.gap-neg { font-size: 14px; font-weight: 700; color: #ef4444; }
.gap-neu { font-size: 14px; font-weight: 600; color: #5a5a7a; }

/* ── Price range inline ── */
.price-range-wrap {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #12121e;
    border: 1px solid #1e1e30;
    border-radius: 8px;
    padding: 6px 14px;
    margin-left: auto;
    white-space: nowrap;
}
.price-range-label {
    font-size: 10px; font-weight: 700;
    color: #5a5a7a; text-transform: uppercase;
    letter-spacing: 0.6px;
}
.price-range-val {
    font-size: 13px; font-weight: 700;
    color: #d4a017;
}
.price-range-sep { color: #3a3a55; font-size: 12px; }

/* ── Load more ── */
.stButton > button {
    background: #12121e !important;
    border: 1px solid #2a2a40 !important;
    color: #8888aa !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    width: 100%;
    padding: 8px !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    border-color: #d4a017 !important;
    color: #d4a017 !important;
    background: #12120a !important;
}

/* ── Divider ── */
hr { border-color: #1e1e30 !important; margin: 8px 0 !important; }

</style>
""", unsafe_allow_html=True)

# ── DONNÉES / SCORING ─────────────────────────────────────────────────────────

from pokemon_popularity import get_popularity_score
from meta_scores import get_meta_score

RARITY_PACKS = {
    "Special Illustration Rare": 180,
    "Illustration Rare":          90,
    "Hyper Rare":                200,
    "Ultra Rare":                 72,
    "Double Rare":                18,
    "ACE SPEC Rare":              72,
    "Shiny Rare":                 54,
    "Shiny Ultra Rare":          180,
}

SET_META = {
    "sv9":    (10, 15, 5, 20, "main",    4.5),
    "sv8pt5": (20, 30, 8, 25, "special", 5.5),
    "sv8":    (12, 20, 6, 18, "main",    4.5),
    "sv7":    (10, 18, 5, 18, "main",    4.5),
    "sv6pt5": (15, 22, 6, 20, "special", 5.5),
    "sv6":    (10, 16, 5, 16, "main",    4.5),
    "sv5":    (10, 16, 5, 16, "main",    4.5),
    "sv4pt5": (18, 26, 7, 22, "special", 5.5),
    "sv4":    (12, 18, 5, 18, "main",    4.5),
    "sv3pt5": (20, 30, 8, 25, "special", 5.5),
    "sv3":    (14, 22, 5, 18, "main",    4.5),
    "sv2":    (12, 18, 5, 16, "main",    4.5),
    "sv1":    (10, 16, 5, 15, "main",    4.0),
    "svp":    (0,  0,  0,  0, "promo",   0.0),
    "swsh12pt5": (15, 22, 6, 20, "special", 5.0),
    "swsh12":    (10, 18, 5, 18, "main",    4.0),
    "swsh11":    (10, 16, 5, 16, "main",    4.0),
    "swsh10":    (8,  14, 4, 14, "main",    4.0),
    "swsh9":     (8,  14, 4, 14, "main",    4.0),
    "swsh8":     (8,  12, 4, 12, "main",    4.0),
    "swsh7":     (6,  10, 4, 10, "main",    4.0),
    "swsh6":     (6,  10, 3, 10, "main",    4.0),
    "swsh5":     (6,   8, 3,  8, "main",    4.0),
    "swsh4":     (6,   8, 3,  8, "main",    4.0),
    "swsh35":    (8,  12, 4, 10, "special", 5.0),
    "swsh3":     (5,   8, 3,  8, "main",    4.0),
    "swsh2":     (5,   8, 3,  8, "main",    4.0),
    "swsh1":     (4,   6, 3,  6, "main",    4.0),
    "swshp":     (0,   0, 0,  0, "promo",   0.0),
    "mcd19":     (0,   0, 0,  0, "promo",   0.0),
    "mcd20":     (0,   0, 0,  0, "promo",   0.0),
    "mcd21":     (0,   0, 0,  0, "promo",   0.0),
    "mcd22":     (0,   0, 0,  0, "promo",   0.0),
}
DEFAULT_META = (10, 15, 5, 15, "main", 4.5)

SET_HYPE = {
    "sv8pt5": 9.5, "sv3pt5": 8.5, "sv6pt5": 8.0, "sv4pt5": 7.5,
    "sv9": 8.0, "sv8": 7.5, "sv7": 7.0, "sv6": 7.0, "sv5": 7.5,
    "sv4": 7.0, "sv3": 7.0, "sv2": 6.5, "sv1": 6.5,
    "swsh12pt5": 8.5, "swsh12": 7.0, "swsh11": 6.5, "swsh10": 6.5,
    "swsh9": 6.0, "swsh8": 6.0, "swsh7": 5.5, "swsh6": 5.5,
    "swsh5": 5.0, "swsh4": 5.0, "swsh35": 6.0, "swsh3": 5.0,
    "swsh2": 4.5, "swsh1": 4.5,
}

GEM_RATE = {
    "Special Illustration Rare": 0.62,
    "Illustration Rare": 0.68,
    "Hyper Rare": 0.55,
    "Ultra Rare": 0.72,
    "Double Rare": 0.78,
    "ACE SPEC Rare": 0.70,
    "Shiny Rare": 0.65,
    "Shiny Ultra Rare": 0.58,
}

def set_hype_score(sid): return SET_HYPE.get(sid, 5.0)
def get_set_meta(sid): return SET_META.get(sid, DEFAULT_META)

def desirability_score(card_name, sid, card_number=""):
    pop  = get_popularity_score(card_name)
    sid_upper = sid.upper().replace("SV", "SV").replace("SWSH", "SWSH")
    meta = get_meta_score(sid_upper, card_number)
    hype = set_hype_score(sid)
    return round(float(np.clip(0.45*pop + 0.45*hype + 0.10*meta, 1.0, 10.0)), 2)

def pull_cost_score(rarity, sid):
    base_packs = RARITY_PACKS.get(rarity, 72)
    meta       = get_set_meta(sid)
    nb_same    = {"SIR": meta[0], "IR": meta[1], "UR": meta[2], "DR": meta[3]}.get(
        {"Special Illustration Rare":"SIR","Hyper Rare":"SIR","Shiny Ultra Rare":"SIR",
         "Illustration Rare":"IR","Shiny Rare":"IR",
         "Ultra Rare":"UR","ACE SPEC Rare":"UR",
         "Double Rare":"DR"}.get(rarity, "DR"), max(meta[2], 1))
    specific_pull = base_packs * max(nb_same, 1)
    pack_price    = meta[5] if meta[5] > 0 else 4.5
    is_special    = 1.3 if meta[4] == "special" else 1.0
    raw_cost      = (specific_pull * pack_price * is_special) * FX
    return round(float(np.clip(np.log1p(raw_cost) / np.log1p(30000) * 10, 1.0, 10.0)), 2)

RARITY_GROUPS = {
    "SIR":  ["Special Illustration Rare", "Hyper Rare", "Shiny Ultra Rare"],
    "IR":   ["Illustration Rare", "Shiny Rare"],
    "UR":   ["Ultra Rare", "ACE SPEC Rare"],
    "DR":   ["Double Rare"],
}
def rarity_group(rar):
    for g, members in RARITY_GROUPS.items():
        if rar in members: return g
    return "DR"

QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield" OR set.series:"Mega Evolution") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)

def pokeid_to_tcgdex(sid):
    mapping = {
        "sv9":"sv09","sv8pt5":"sv08pt5","sv8":"sv08","sv7":"sv07","sv6pt5":"sv06pt5",
        "sv6":"sv06","sv5":"sv05","sv4pt5":"sv04pt5","sv4":"sv04","sv3pt5":"sv03pt5",
        "sv3":"sv03","sv2":"sv02","sv1":"sv01",
    }
    return mapping.get(sid, sid)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(_v=19):
    rows, seen, page = [], set(), 1
    while True:
        try:
            r = requests.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"q": QUERY, "page": page, "pageSize": 250, "orderBy": "-set.releaseDate"},
                timeout=30
            )
            r.raise_for_status()
            cards = r.json().get("data", [])
        except Exception as e:
            st.error(f"Erreur API: {e}")
            break
        if not cards:
            break
        for c in cards:
            cid = c.get("id", "")
            if cid in seen:
                continue
            seen.add(cid)
            tcp    = c.get("tcgplayer", {})
            prices = tcp.get("prices", {})
            mkt    = None
            price_source = "tcgplayer"

            for pt in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
                if pt in prices and prices[pt].get("market"):
                    mkt = prices[pt]["market"] * FX
                    break

            if mkt is None:
                cmu = c.get("cardmarket", {}).get("prices", {})
                avg30 = cmu.get("avg30") or cmu.get("averageSellPrice")
                if avg30:
                    mkt = avg30 * FX_EUR
                    price_source = "cardmarket"

            if not mkt or mkt < 1.0:
                continue

            sid     = c.get("set", {}).get("id", "")
            series  = c.get("set", {}).get("series", "")
            rarity  = c.get("rarity", "")
            name    = c.get("name", "")
            num     = c.get("number", "")

            rows.append({
                "id":           cid,
                "name":         name,
                "set":          c.get("set", {}).get("name", ""),
                "set_id":       sid,
                "series":       series,
                "rarity":       rarity,
                "number":       num,
                "market_price": round(mkt, 2),
                "price_source": price_source,
                "tcgplayer_url": tcp.get("url", ""),
                "image_url":    c.get("images", {}).get("small", ""),
            })
        if len(cards) < 250:
            break
        page += 1
        time.sleep(0.15)

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["name", "set"])
    return df


def run_screener(df: pd.DataFrame):
    if df.empty:
        return df

    df = df.copy()
    df["pull_cost"]    = df.apply(lambda r: pull_cost_score(r["rarity"], r["set_id"]), axis=1)
    df["desirability"] = df.apply(lambda r: desirability_score(r["name"], r["set_id"], r.get("number", "")), axis=1)
    df["gem_rate"]     = df["rarity"].map(GEM_RATE).fillna(0.65)
    df["rarity_grp"]   = df["rarity"].apply(rarity_group)

    # Percentile intra-rareté
    def percentile_rank(series):
        return series.rank(pct=True)

    df["score_raw"] = (
        0.45 * df["desirability"] +
        0.35 * df["pull_cost"] +
        0.20 * (df["gem_rate"] * 10)
    )

    df["demand_pct"] = df.groupby("rarity_grp")["score_raw"].transform(percentile_rank)
    df["price_pct"]  = df.groupby("rarity_grp")["market_price"].transform(percentile_rank)

    # Potentiel = gap de percentiles * 100 → affiché en %
    df["value_gap"]   = (df["demand_pct"] - df["price_pct"]).round(4)  # garde pour signal
    df["upside_pct"]  = ((df["demand_pct"] - df["price_pct"]) * 100).round(1)

    # Signal
    def signal(row):
        vg = row["value_gap"]
        if vg > 0.20:
            return "gem"
        elif vg < -0.20:
            return "over"
        return "fair"

    df["Signal"] = df.apply(signal, axis=1)
    # Ordre logique pour le tri: gem=0, fair=1, over=2
    signal_order = {"gem": 0, "fair": 1, "over": 2}
    df["signal_sort"] = df["Signal"].map(signal_order)
    return df


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    ss = st.session_state
    if "sort_by"  not in ss: ss.sort_by  = "upside_pct"
    if "sort_asc" not in ss: ss.sort_asc = False
    if "lb_limit" not in ss: ss.lb_limit = 50
    if "search_q" not in ss: ss.search_q = ""
    if "price_min"  not in ss: ss.price_min = 0
    if "price_max"  not in ss: ss.price_max = 9999

    ALL_SERIES = ["Scarlet & Violet", "Sword & Shield", "Mega Evolution"]
    ALL_RARITY = ["Special Illustration Rare", "Illustration Rare", "Hyper Rare",
                  "Ultra Rare", "Double Rare", "ACE SPEC Rare", "Shiny Rare", "Shiny Ultra Rare"]

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div class="sb-profile">
            <img class="sb-avatar" src="{AVATAR_URL}">
            <div class="sb-name">The Nasty Model</div>
            <div class="sb-sub">SCREENER TCG · POKÉMON</div>
            <div class="sb-rate">1 USD = {FX:.4f} C$</div>
        </div>
        """, unsafe_allow_html=True)

    # ── LOAD DATA ─────────────────────────────────────────────────────────────
    with st.spinner("Chargement des cartes..."):
        fetched = fetch_data(_v=19)

    if fetched.empty:
        st.error("Aucune carte chargée — vérifier la connexion API.")
        return

    df = run_screener(fetched)

    # ── HEADER ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="page-header">
        <img src="{AVATAR_URL}">
        <div>
            <div class="page-title">The Nasty Model</div>
            <div class="page-sub">Screener TCG · Ranking intra-rareté · Valeurs en C$</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── STATS BAR ────────────────────────────────────────────────────────────
    price_floor = int(df["market_price"].min()) if not df.empty else 0
    price_ceil  = int(df["market_price"].max()) + 1 if not df.empty else 9999
    if ss.price_max == 9999: ss.price_max = price_ceil
    n_total = len(df)
    n_gem   = (df["Signal"] == "gem").sum()
    n_over  = (df["Signal"] == "over").sum()
    n_fair  = (df["Signal"] == "fair").sum()

    # Stats pills + price range sur la même ligne
    cols_bar = st.columns([1, 1, 1, 1, 0.1, 1.4])
    with cols_bar[0]:
        st.markdown(f'<div class="stat-pill gold"><b>{n_total}</b> cartes</div>', unsafe_allow_html=True)
    with cols_bar[1]:
        st.markdown(f'<div class="stat-pill green"><b>{n_gem}</b> sous-évaluées</div>', unsafe_allow_html=True)
    with cols_bar[2]:
        st.markdown(f'<div class="stat-pill red"><b>{n_over}</b> surévaluées</div>', unsafe_allow_html=True)
    with cols_bar[3]:
        st.markdown(f'<div class="stat-pill"><b>{n_fair}</b> prix juste</div>', unsafe_allow_html=True)
    with cols_bar[4]:
        st.markdown('<div style="height:36px;border-left:1px solid #1e1e30;margin-top:2px;"></div>', unsafe_allow_html=True)
    with cols_bar[5]:
        st.markdown('<div class="price-range-label" style="margin-bottom:2px;">Prix C$</div>', unsafe_allow_html=True)
        pr_cols = st.columns([1, 0.2, 1])
        with pr_cols[0]:
            new_min = st.number_input("", min_value=0, max_value=price_ceil, value=ss.price_min,
                                      step=5, key="ni_min", label_visibility="collapsed")
        with pr_cols[1]:
            st.markdown('<div style="text-align:center;color:#3a3a55;padding-top:6px;">—</div>', unsafe_allow_html=True)
        with pr_cols[2]:
            new_max = st.number_input("", min_value=0, max_value=price_ceil, value=ss.price_max,
                                      step=5, key="ni_max", label_visibility="collapsed")
        if new_min != ss.price_min or new_max != ss.price_max:
            ss.price_min = new_min
            ss.price_max = new_max
            ss.lb_limit  = 50
            st.rerun()

    # ── SEARCH ───────────────────────────────────────────────────────────────
    search_q = st.text_input("", placeholder="🔍  Rechercher une carte, un set...", key="ti_search", label_visibility="collapsed")
    ss.search_q = search_q

    # ── FILTER & SORT ────────────────────────────────────────────────────────
    df_f = df[df["series"].isin(ALL_SERIES) & df["rarity"].isin(ALL_RARITY)].copy()
    df_f = df_f[(df_f["market_price"] >= ss.price_min) & (df_f["market_price"] <= ss.price_max)]
    if search_q:
        q = search_q.lower()
        df_f = df_f[df_f["name"].str.lower().str.contains(q) | df_f["set"].str.lower().str.contains(q)]

    df_f = df_f.sort_values(ss.sort_by, ascending=ss.sort_asc)

    total = len(df_f)
    limit = min(ss.lb_limit, total)

    # ── TABLE HEADER avec colonnes cliquables ─────────────────────────────────
    COLUMNS = [
        ("",           None,         ""),
        ("",           None,         ""),
        ("Carte",      None,         ""),
        ("Prix C$",    "market_price","th-right"),
        ("Demande",    "demand_pct",  "th-right"),
        ("Signal",     "signal_sort", "th-center"),
        ("Potentiel",  "upside_pct",  "th-right"),
    ]

    # Build header as columns
    col_widths = [0.4, 0.7, 3, 1, 1, 1, 1]
    header_cols = st.columns(col_widths)

    sort_labels = {
        "market_price": "Prix C$",
        "demand_pct":   "Demande",
        "Signal":       "Signal",
        "upside_pct":   "Potentiel",
    }

    for i, (hcol, (label, field, cls)) in enumerate(zip(header_cols, COLUMNS)):
        with hcol:
            if field is None:
                st.markdown(f'<div class="th {cls}">{label}</div>', unsafe_allow_html=True)
            else:
                is_active = (ss.sort_by == field)
                arrow = (" ▲" if ss.sort_asc else " ▼") if is_active else ""
                active_cls = "active" if is_active else ""
                btn_style = "color:#d4a017;" if is_active else "color:#5a5a7a;"
                if st.button(f"{label}{arrow}", key=f"hdr_{field}", use_container_width=True):
                    if ss.sort_by == field:
                        ss.sort_asc = not ss.sort_asc
                    else:
                        ss.sort_by  = field
                        ss.sort_asc = False
                    ss.lb_limit = 50
                    st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── ROWS ─────────────────────────────────────────────────────────────────
    for rank, (_, row) in enumerate(df_f.head(limit).iterrows(), 1):
        cols = st.columns(col_widths)

        # Rank
        rank_cls = {1: "top1", 2: "top2", 3: "top3"}.get(rank, "")
        with cols[0]:
            st.markdown(f'<div class="cell-rank {rank_cls}">{rank}</div>', unsafe_allow_html=True)

        # Image
        with cols[1]:
            if row.get("image_url"):
                st.image(row["image_url"], width=64)
            else:
                st.markdown('<div style="width:64px;height:89px;background:#12121e;border-radius:6px;"></div>', unsafe_allow_html=True)

        # Info
        with cols[2]:
            src_badge = ' <span style="font-size:9px;color:#3a3a55;background:#12121e;padding:1px 5px;border-radius:3px;border:1px solid #2a2a40;">CardMarket</span>' if row.get("price_source") == "cardmarket" else ""
            st.markdown(f"""
            <div style="padding: 4px 0;">
                <div class="cell-name">{row["name"]}{src_badge}</div>
                <div class="cell-sub">{row["set"]} · {row["rarity"]}</div>
            </div>
            """, unsafe_allow_html=True)

        # Prix
        with cols[3]:
            st.markdown(f'<div class="cell-num price" style="padding-top:8px;">C${row["market_price"]:.2f}</div>', unsafe_allow_html=True)

        # Demande
        with cols[4]:
            dp = row["demand_pct"]
            bar_w = int(dp * 100)
            color = "#d4a017" if dp >= 0.7 else ("#8888cc" if dp >= 0.4 else "#3a3a55")
            st.markdown(f"""
            <div style="padding-top:6px;">
                <div class="demand-pct" style="color:{color};">{int(dp*100)}%</div>
                <div class="demand-bar"><div class="demand-fill" style="width:{bar_w}%;background:{color};"></div></div>
            </div>
            """, unsafe_allow_html=True)

        # Signal
        with cols[5]:
            sig = row["Signal"]
            if sig == "gem":
                badge = '<span class="sig-gem">SOUS-ÉV.</span>'
            elif sig == "over":
                badge = '<span class="sig-over">SUR-ÉV.</span>'
            else:
                badge = '<span class="sig-fair">JUSTE</span>'
            st.markdown(f'<div style="padding-top:8px;text-align:center;">{badge}</div>', unsafe_allow_html=True)

        # Value Gap
        with cols[6]:
            vg = row["value_gap"]
            if vg > 0.05:
                vg_html = f'<span class="gap-pos">+{vg:.2f}</span>'
            elif vg < -0.05:
                vg_html = f'<span class="gap-neg">{vg:.2f}</span>'
            else:
                vg_html = f'<span class="gap-neu">{vg:.2f}</span>'
            st.markdown(f'<div style="padding-top:8px;text-align:right;">{vg_html}</div>', unsafe_allow_html=True)

        st.markdown('<hr style="margin:2px 0;">', unsafe_allow_html=True)

    # ── LOAD MORE ─────────────────────────────────────────────────────────────
    if limit < total:
        remaining = total - limit
        c1, c2, c3 = st.columns([2, 3, 2])
        with c2:
            if st.button(f"Voir {min(50, remaining)} de plus  ({remaining} restantes)", use_container_width=True):
                ss.lb_limit += 50
                st.rerun()
    else:
        st.markdown(f'<p style="text-align:center;color:#3a3a55;font-size:11px;padding:12px 0;">— {total} cartes affichées —</p>', unsafe_allow_html=True)


main()
