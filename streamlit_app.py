"""
Nasty TCG Dashboard — v11 (PokeDataDadGuy model)

Architecture:
  Supply  → Pull Cost Score   (pack cost to pull a specific card)
  Demand  → Desirability Index (weighted: Character 45% + Art/Hype 45% + Universal 10%)
  Model   → Ridge regression log(price) ~ pull_cost + desirability
  Output  → Expected Price vs Market Price → Under/Overvalued signal
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge
import time, requests, re
from datetime import date

# ── FX ───────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_usd_to_cad():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        return r.json()["rates"]["CAD"]
    except:
        return 1.38

@st.cache_data(ttl=3600, show_spinner=False)
def get_eur_to_cad():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)
        return r.json()["rates"]["CAD"]
    except:
        return 1.62

st.set_page_config(page_title="The Nasty Model", page_icon="🎴", layout="wide")
AVATAR_URL = "https://base44.app/api/apps/69dae320409ba22186ac9552/files/mp/public/69dae320409ba22186ac9552/fb5969149_60b86a1b8_NastyPP_07.png"

FX     = get_usd_to_cad()
FX_EUR = get_eur_to_cad()

def fmt_cad(cad: float) -> str:
    return f"C${cad:.2f}"

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, * { font-family: 'Inter', sans-serif !important; }

section[data-testid="stSidebar"] { background:#0d0d1a !important; }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.stApp, .block-container { background:#0f0f1e !important; color:#e2e8f0; }
h1,h2,h3,h4 { color:#fff !important; }

.card-box {
    background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
    border:1px solid #2d2d50; border-radius:16px; padding:16px;
    margin-bottom:14px; display:flex; gap:14px; align-items:flex-start;
    transition:border-color .2s;
}
.card-box:hover { border-color:#7c3aed; }
.card-img { width:90px; border-radius:8px; flex-shrink:0; }
.card-body { flex:1; min-width:0; }
.card-name { font-size:15px; font-weight:700; color:#fff; margin-bottom:2px; }
.card-sub  { font-size:11px; color:#8892b0; margin-bottom:6px; }
.card-price { font-size:22px; font-weight:800; color:#fff; }
.card-vt   { font-size:13px; color:#a0aec0; margin-top:2px; }
.pill {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:11px; font-weight:700; letter-spacing:.5px; margin-top:6px;
}
.pill-gem  { background:#064e3b; color:#34d399; border:1px solid #34d399; }
.pill-over { background:#4c0519; color:#fb7185; border:1px solid #fb7185; }
.pill-fair { background:#1e1b4b; color:#a5b4fc; border:1px solid #a5b4fc; }
.pill-source { background:#1e293b; color:#64748b; border:1px solid #334155;
               font-size:9px; padding:2px 7px; margin-left:4px; }

.sidebar-avatar { text-align:center; padding:12px 0 4px; }
.sidebar-avatar img { width:72px; height:72px; border-radius:50%;
    border:2px solid #7c3aed; object-fit:cover; }
.sidebar-title { text-align:center; font-size:16px; font-weight:800;
    color:#fff; margin:6px 0 2px; }
.sidebar-sub   { text-align:center; font-size:10px; color:#8892b0; }
.sb-label { font-size:11px; font-weight:600; color:#7c3aed;
    text-transform:uppercase; letter-spacing:.8px; margin:14px 0 4px; }
.metric-box {
    background:#1a1a2e; border:1px solid #2d2d50; border-radius:10px;
    padding:12px 16px; text-align:center;
}
.metric-val { font-size:24px; font-weight:800; color:#7c3aed; }
.metric-lbl { font-size:11px; color:#8892b0; margin-top:2px; }

div[data-testid="stExpander"] { background:#1a1a2e !important;
    border:1px solid #2d2d50 !important; border-radius:10px; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# DATA: Rarity pull rates (packs per hit for rarity tier)
# ═══════════════════════════════════════════════════════════════════
# packs_per_rarity_hit = 1 / pull_rate_for_that_tier
RARITY_PACKS = {
    "Special Illustration Rare": 180,   # ~1 per 180 packs
    "Illustration Rare":          90,   # ~1 per 90 packs
    "Hyper Rare":                200,   # ~1 per 200 packs (gold cards)
    "Ultra Rare":                 72,   # ~1 per 72 packs
    "Double Rare":                18,   # ~1 per 18 packs
    "ACE SPEC Rare":              72,
    "Shiny Rare":                 54,
    "Shiny Ultra Rare":          180,
}

# Number of cards in that rarity tier within the set
# (nb chase cards competing for that slot)
# SET_META: (nb_SIR, nb_IR, nb_UR, nb_DR, prod_type, pack_price_usd)
SET_META = {
    # ── Scarlet & Violet ─────────────────────────────────────────────────
    "sv9":    (10, 15, 5, 20, "main",    4.5),
    "sv8pt5": (20, 30, 8, 25, "special", 5.5),  # Prismatic Evolutions
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
    # ── Sword & Shield ────────────────────────────────────────────────────
    "swsh12pt5": (0, 0, 20, 30, "special", 5.5),  # Crown Zenith
    "swsh12":    (0, 0, 10, 18, "main",    4.0),
    "swsh11":    (0, 0,  8, 15, "main",    4.0),
    "swsh10":    (0, 0,  8, 14, "main",    4.0),
    "swsh9":     (0, 0,  7, 13, "main",    4.0),
    "swsh8":     (0, 0,  6, 11, "main",    4.0),
    "swsh7":     (0, 0,  5, 10, "main",    4.0),
    "swsh6":     (0, 0,  4,  8, "main",    4.0),
    "swsh5":     (0, 0,  4,  8, "main",    4.0),
    "swsh45":    (0, 0, 12, 20, "special", 5.5),  # Shining Fates
    "swsh4":     (0, 0,  3,  7, "main",    4.0),
    "swsh35":    (0, 0,  8, 12, "special", 5.5),  # Champion Path
    "swsh3":     (0, 0,  3,  6, "main",    4.0),
    "swsh2":     (0, 0,  3,  6, "main",    4.0),
    "swsh1":     (0, 0,  3,  5, "main",    4.0),
    "ssp":       (0, 0,  0,  0, "promo",   0.0),
    # ── Mega Evolution ────────────────────────────────────────────────────
    "me1":    (12, 20, 6, 18, "special", 6.5),  # Japanese import
    "me2":    (10, 16, 5, 16, "special", 6.5),
    "me2pt5": (8,  14, 4, 14, "special", 6.5),
    "me3":    (10, 18, 5, 16, "special", 6.5),
}
DEFAULT_META = (10, 15, 5, 15, "main", 4.5)

# ── Set Hype Score (1–10) ────────────────────────────────────────────────────
# Mesure la hype communautaire + valeur perçue du set indépendamment des cartes
# Sources: ventes totales, réputation, demande longue durée, sets "nostalgiques"
SET_HYPE = {
    # Iconic / all-time high demand
    "sv3pt5":    9.8,  # 151 — THE most hyped modern set
    "sv8pt5":    9.5,  # Prismatic Evolutions — sold out worldwide
    "swsh45":    9.0,  # Shining Fates — still heavily sought
    "swsh12pt5": 8.5,  # Crown Zenith — strong chase pool
    "sv4pt5":    8.5,  # Paldean Fates
    "sv6pt5":    8.0,  # Shrouded Fable
    # Strong sets
    "sv9":       8.0,  # Surging Sparks — Pikachu ex hype
    "sv7":       7.5,  # Stellar Crown
    "sv8":       7.0,  # Twilight Masquerade
    "sv6":       7.0,  # Mask of Change
    "sv5":       6.5,  # Temporal Forces
    "sv4":       6.5,  # Paradox Rift
    "sv3":       7.5,  # Obsidian Flames — Charizard ex
    "sv2":       6.5,  # Paldea Evolved
    "sv1":       6.0,  # Scarlet & Violet base
    # SWSH main sets
    "swsh12":    6.5,  # Silver Tempest
    "swsh11":    6.0,  # Lost Origin
    "swsh10":    6.0,  # Astral Radiance
    "swsh9":     5.5,  # Brilliant Stars
    "swsh8":     5.5,  # Fusion Strike
    "swsh7":     5.0,  # Evolving Skies
    "swsh6":     5.0,  # Chilling Reign
    "swsh5":     5.0,  # Battle Styles
    "swsh4":     5.0,  # Vivid Voltage
    "swsh35":    7.0,  # Champion's Path — Charizard V holo
    "swsh3":     4.5,  # Darkness Ablaze
    "swsh2":     4.5,  # Rebel Clash
    "swsh1":     5.0,  # Sword & Shield base
    # Mega Evolution (Japanese import — collector niche)
    "me1":       7.5,
    "me2":       7.0,
    "me2pt5":    7.5,
    "me3":       7.0,
}

def get_set_hype(sid: str) -> float:
    """Set Hype Score 1–10. Default 5.0 pour les sets sans score défini."""
    return SET_HYPE.get(sid, 5.0)

# ── Gem Rate (PSA 10 difficulty) ─────────────────────────────────────────────
# % de cartes de cette rareté qui obtiennent PSA 10 (données population réelles)
# Plus c'est rare d'avoir un 10 → plus la carte gradée vaut une prime
GEM_RATE = {
    "Special Illustration Rare": 0.42,   # Full art textured — difficile
    "Illustration Rare":         0.55,
    "Hyper Rare":                0.38,   # Gold cards — très sensibles aux scratches
    "Ultra Rare":                0.60,
    "Double Rare":               0.65,
    "ACE SPEC Rare":             0.58,
    "Shiny Rare":                0.50,
    "Shiny Ultra Rare":          0.45,
}
def get_gem_rate(rarity: str) -> float:
    """Retourne un score 1–10 : plus le gem rate est BAS, plus le score est HAUT (prime de difficulté)."""
    rate = GEM_RATE.get(rarity, 0.55)
    # Inverser: gem rate 0.38 → score 8.5 | gem rate 0.65 → score 4.0
    score = 10.0 - (rate - 0.30) / (0.70 - 0.30) * 7.0
    return round(float(np.clip(score, 1.0, 10.0)), 2)

# ── Set Age Score ─────────────────────────────────────────────────────────────
def get_set_age_score(release_date: str) -> float:
    """
    Courbe en U : prime de nouveauté + prime de nostalgie, creux à 12-18 mois.
    release_date format: YYYY/MM/DD ou YYYY-MM-DD
    Score 1–10.
    """
    try:
        rd = release_date.replace("/", "-")[:10]
        from datetime import date as _date
        rel = _date.fromisoformat(rd)
        months_old = (date.today() - rel).days / 30.44
    except:
        return 5.0  # fallback

    # Courbe en U : min à ~15 mois
    if months_old <= 3:
        score = 9.0  # tout nouveau — hype launch
    elif months_old <= 12:
        score = 9.0 - (months_old - 3) / 9.0 * 3.5   # 9.0 → 5.5
    elif months_old <= 20:
        score = 5.5 - (months_old - 12) / 8.0 * 1.5  # 5.5 → 4.0 (creux)
    elif months_old <= 36:
        score = 4.0 + (months_old - 20) / 16.0 * 2.5 # 4.0 → 6.5 (nostalgie)
    else:
        score = 6.5 + min(2.0, (months_old - 36) / 24.0 * 2.0)  # 6.5 → 8.5 (vintage)

    return round(float(np.clip(score, 1.0, 10.0)), 2)

def get_set_meta(sid: str):
    return SET_META.get(sid, DEFAULT_META)

def n_cards_in_rarity(sid: str, rarity: str) -> int:
    meta = get_set_meta(sid)
    r = rarity
    if r == "Special Illustration Rare": return max(1, meta[0])
    if r == "Illustration Rare":         return max(1, meta[1])
    if r in ("Hyper Rare", "Ultra Rare", "ACE SPEC Rare"): return max(1, meta[2])
    if r in ("Double Rare", "Shiny Rare", "Shiny Ultra Rare"): return max(1, meta[3])
    return 15

def pack_price_usd(sid: str) -> float:
    meta = get_set_meta(sid)
    return meta[5] if meta[5] > 0 else 4.5

# ── Pull Cost Score ───────────────────────────────────────────────────────────
def pull_cost_score(sid: str, rarity: str) -> float:
    """
    Packs to pull one specific card =
        packs_per_rarity_hit × n_cards_in_rarity_slot

    Then converted to USD cost = packs × pack_price
    Then log-scaled to a 1-10 score.
    """
    packs_per_hit = RARITY_PACKS.get(rarity, 90)
    n_in_slot     = n_cards_in_rarity(sid, rarity)
    avg_packs     = packs_per_hit * n_in_slot
    cost_usd      = avg_packs * pack_price_usd(sid)  # USD cost to pull

    # Log scale to 1–10
    # Reference: cost ~$50 → 1.0 | cost ~$50,000 → 10.0
    score = 1.0 + 9.0 * (np.log1p(cost_usd) - np.log1p(50)) / (np.log1p(50000) - np.log1p(50))
    return round(float(np.clip(score, 1.0, 10.0)), 2)

# ═══════════════════════════════════════════════════════════════════
# DEMAND: Desirability Index
# ═══════════════════════════════════════════════════════════════════
# Import popularity scores
import sys, os
sys.path.insert(0, "/app/tcg_model")
from pokemon_popularity import get_popularity_score   # returns 1–10
from meta_scores import get_meta_score                 # returns 1–10

# Character Premium score (1–10) = popularity in TCG market
# We use the AV Club popularity list as proxy for "market rank"
def character_premium(card_name: str) -> float:
    return get_popularity_score(card_name)   # 1–10

# Art & Hype score (1–10) using TCGPlayer price spread as proxy
def art_hype_score(prices: dict) -> float:
    """
    Uses TCGPlayer low/mid/market spread as proxy for art hype.
    High floor (low ≈ market) → strong demand for this specific art.
    Also checks for Trending signals.
    """
    for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
        if pt not in prices: continue
        p = prices[pt]
        low  = p.get("low",  0) or 0
        mid  = p.get("mid",  0) or 0
        high = p.get("high", 0) or 0
        mkt  = p.get("market", 0) or 0
        if mkt <= 0: continue
        score = 5.0
        if low  > 0: score += 3.0 * (low / mkt - 0.3) / 0.7    # floor ratio
        if high > 0: score += 1.5 * min(1.0, (high/mkt - 1.0))  # ceiling premium
        if mid  > 0: score += 0.5 * (1.0 if mkt >= mid else -0.5)
        return round(float(np.clip(score, 1.0, 10.0)), 2)
    return 5.0   # default when no TCGPlayer data

# Universal Appeal (1–10) using meta score as proxy for Google Trends
def universal_appeal(card_name: str, set_id: str, number: str) -> float:
    meta = get_meta_score(set_id, number)  # 1–10 based on meta relevance
    # Combine meta with a basic popularity signal
    pop  = get_popularity_score(card_name)
    # Universal appeal = mix of meta relevance and broad recognition
    return round(float(np.clip(0.5 * meta + 0.5 * (pop * 0.7 + 3.0 * 0.3), 1.0, 10.0)), 2)

def desirability_index(card_name: str, prices: dict, set_id: str, number: str) -> float:
    """
    Weighted score 1–10:
      45% Character Premium (popularity/market rank)
      45% Art & Hype (art quality + demand signals)
      10% Universal Appeal (meta + broad recognition)
    """
    cp  = character_premium(card_name)
    ah  = art_hype_score(prices)
    ua  = universal_appeal(card_name, set_id, number)
    idx = 0.45 * cp + 0.45 * ah + 0.10 * ua
    return round(float(np.clip(idx, 1.0, 10.0)), 2)

# ═══════════════════════════════════════════════════════════════════
# POKEMONTCG API
# ═══════════════════════════════════════════════════════════════════
def pokeid_to_tcgdex(set_id: str) -> str:
    m = re.match(r'^sv(\d+)pt(\d+)$', set_id)
    if m: return f"sv{int(m.group(1)):02d}.{m.group(2)}"
    m = re.match(r'^sv(\d+)$', set_id)
    if m: return f"sv{int(m.group(1)):02d}"
    m = re.match(r'^swsh(\d+)pt(\d+)$', set_id)
    if m: return f"swsh{m.group(1)}.{m.group(2)}"
    m = re.match(r'^swsh(\d+)$', set_id)
    if m: return f"swsh{m.group(1)}"
    m = re.match(r'^me(\d+)pt(\d+)$', set_id)
    if m: return f"me{int(m.group(1)):02d}.{m.group(2)}"
    m = re.match(r'^me(\d+)$', set_id)
    if m: return f"me{int(m.group(1)):02d}"
    return set_id

QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield" OR set.series:"Mega Evolution") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(_v=14):
    rows, seen, page = [], set(), 1
    while True:
        try:
            r = requests.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"q":QUERY,"page":page,"pageSize":250,"orderBy":"-set.releaseDate"},
                timeout=20
            )
            r.raise_for_status()
            cards = r.json().get("data", [])
        except Exception as e:
            st.error(f"API error: {e}"); break
        if not cards: break
        for c in cards:
            cid = c.get("id","")
            if cid in seen: continue
            seen.add(cid)
            tcp    = c.get("tcgplayer", {})
            prices = tcp.get("prices", {})
            mkt    = None
            price_source = "tcgplayer"

            # TCGPlayer price (USD → CAD)
            for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
                if pt in prices and prices[pt].get("market"):
                    mkt = prices[pt]["market"]; break
            if mkt and mkt > 0:
                mkt = mkt * FX
            else:
                # Fallback: CardMarket via TCGdex (EUR → CAD)
                sid_tmp = c.get("set", {}).get("id", "")
                num_tmp = c.get("number", "")
                tcgdex_id = f"{pokeid_to_tcgdex(sid_tmp)}-{num_tmp}"
                try:
                    r_cm = requests.get(f"https://api.tcgdex.net/v2/en/cards/{tcgdex_id}", timeout=5)
                    if r_cm.status_code == 200:
                        cm = r_cm.json().get("pricing",{}).get("cardmarket",{}) or {}
                        eur = cm.get("avg7-holo") or cm.get("avg7") or cm.get("trend-holo") or cm.get("trend")
                        if eur and eur > 0.5:
                            mkt = eur * FX_EUR
                            price_source = "cardmarket"
                except: pass

            if not mkt or mkt <= 0: continue

            nm  = c.get("name","?")
            rar = c.get("rarity","Unknown")
            sid = c.get("set",{}).get("id","")
            num = c.get("number","")
            rel = c.get("set",{}).get("releaseDate","")

            pc  = pull_cost_score(sid, rar)
            di  = desirability_index(nm, prices, sid, num)
            cp  = character_premium(nm)
            ah  = art_hype_score(prices)
            ua  = universal_appeal(nm, sid, num)
            gr  = get_gem_rate(rar)
            sa  = get_set_age_score(rel)
            # Price velocity: tension buy-side via TCGPlayer spread
            # (market - low) / market → 0 = floor pricing, 1 = strong demand
            pv  = 5.0  # default
            for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
                if pt not in prices: continue
                p_ = prices[pt]
                low_ = p_.get("low", 0) or 0
                mkt_ = p_.get("market", 0) or 0
                if mkt_ > 0 and low_ > 0:
                    ratio = (mkt_ - low_) / mkt_
                    # ratio proche de 0 = floor stable = demande forte
                    # ratio proche de 1 = low très bas = pression vendeuse
                    pv = round(float(np.clip(10.0 - ratio * 8.0, 1.0, 10.0)), 2)
                break

            sh = get_set_hype(sid)
            rows.append({
                "id":           cid,
                "name":         nm,
                "set":          c.get("set",{}).get("name","?"),
                "series":       c.get("set",{}).get("series","?"),
                "release_date": rel,
                "rarity":       rar,
                "artist":       c.get("artist",""),
                "number":       num,
                # ── Model inputs ──
                "pull_cost":    pc,          # 1–10 Supply score
                "desirability": di,          # 1–10 Demand index
                "char_premium": cp,          # 1–10 Character popularity
                "art_hype":     ah,          # 1–10 Art quality/hype
                "univ_appeal":  ua,          # 1–10 Universal appeal
                "set_hype":     sh,          # 1–10 Set hype score
                "gem_rate":     gr,          # 1–10 Grading difficulty (inverse gem%)
                "set_age":      sa,          # 1–10 Set age curve (U-shape)
                "price_vel":    pv,          # 1–10 Price velocity (buy-side tension)
                # ── Market ──
                "market_price": round(mkt, 2),
                "price_source": price_source,
                "tcgplayer_url": tcp.get("url",""),
                "image_url":    c.get("images",{}).get("small",""),
                "tcgdex_id":    f"{pokeid_to_tcgdex(sid)}-{num}",
            })
        if len(cards) < 250: break
        page += 1
        time.sleep(0.15)

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["name","set"])
    return df

# ═══════════════════════════════════════════════════════════════════
# MODEL: Ridge regression log(price) ~ pull_cost + desirability
# ═══════════════════════════════════════════════════════════════════
# ── Rarity groups for intra-rarity modeling ──────────────────────────────────
RARITY_GROUPS = {
    "SIR":   ["Special Illustration Rare", "Hyper Rare", "Shiny Ultra Rare"],
    "IR":    ["Illustration Rare", "Shiny Rare"],
    "UR":    ["Ultra Rare", "ACE SPEC Rare"],
    "DR":    ["Double Rare"],
}
def rarity_group(rar: str) -> str:
    for g, members in RARITY_GROUPS.items():
        if rar in members: return g
    return "DR"

def run_model(df: pd.DataFrame, w_pull: float, w_demand: float):
    """
    Ridge regression PER RARITY GROUP: log(price) ~ pull_cost + desirability
    
    Why intra-rarity? A global regression is dominated by bulk Double Rares
    ($5-20), making all premium SIR ($200-500) look "overvalued".
    Fitting within each rarity tier anchors predictions to realistic peers.
    """
    df = df.copy()
    df["rarity_group"] = df["rarity"].apply(rarity_group)
    df["expected_price"] = np.nan

    all_r2, all_cp, all_cd, all_n = [], [], [], []

    for grp, sub_idx in df.groupby("rarity_group").groups.items():
        sub = df.loc[sub_idx]
        if len(sub) < 5:
            # Not enough data — use median as expected
            med = sub["market_price"].median()
            df.loc[sub_idx, "expected_price"] = med
            continue

        X = sub[["pull_cost","desirability","set_hype","gem_rate","set_age","price_vel"]].values
        y = np.log1p(sub["market_price"].values)

        model = Ridge(alpha=1.0)
        model.fit(X, y)

        preds = np.expm1(model.predict(X))
        df.loc[sub_idx, "expected_price"] = preds.round(2)

        yp = model.predict(X)
        ss_res = np.sum((y - yp)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r2_grp = max(0.0, 1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0
        all_r2.append(r2_grp * len(sub))
        all_n.append(len(sub))
        all_cp.append(np.expm1(model.coef_[0]) * 100)
        all_cd.append(np.expm1(model.coef_[1]) * 100)
        # coef[2] = set_hype (informatif seulement)

    # Gap % = (expected - market) / market
    df["gap_pct"] = ((df["expected_price"] - df["market_price"]) / df["market_price"] * 100).round(1)
    df["gap_pct"] = df["gap_pct"].clip(-85, 250)

    def signal(row):
        g = row["gap_pct"]
        if   g >  w_demand * 100: return "gem"
        elif g < -w_pull   * 100: return "over"
        else:                      return "fair"
    df["Signal"] = df.apply(signal, axis=1)

    # Weighted R² across groups
    r2 = round(sum(all_r2) / sum(all_n), 3) if all_n else 0.0
    coef_pull   = round(np.mean(all_cp), 1) if all_cp else 0.0
    coef_demand = round(np.mean(all_cd), 1) if all_cd else 0.0

    return df, r2, coef_pull, coef_demand

# ═══════════════════════════════════════════════════════════════════
# CARD HTML
# ═══════════════════════════════════════════════════════════════════
def card_html(c, sig):
    gap = c["gap_pct"]
    gap_str = f"+{gap:.0f}%" if gap >= 0 else f"{gap:.0f}%"
    pill_cls = {"gem":"pill-gem","over":"pill-over","fair":"pill-fair"}[sig]
    label    = {"gem":"💎 Sous-évaluée","over":"🔴 Surévaluée","fair":"✅ Prix juste"}[sig]

    img = f'<img class="card-img" src="{c["image_url"]}">' if c.get("image_url") else ""
    tcg = (f'<a href="{c["tcgplayer_url"]}" target="_blank" '
           f'style="color:#7c3aed;font-size:11px;">TCGPlayer ↗</a>'
           if c.get("tcgplayer_url") else "")
    src_pill = ('<span class="pill pill-source">CardMarket</span>'
                if c.get("price_source") == "cardmarket" else "")

    # Desirability breakdown bar
    cp = c.get("char_premium", 5)
    ah = c.get("art_hype",     5)
    ua = c.get("univ_appeal",  5)
    pc = c.get("pull_cost",    5)
    di = c.get("desirability", 5)
    sh = c.get("set_hype",     5)
    gr = c.get("gem_rate",     5)
    sa = c.get("set_age",      5)
    pv = c.get("price_vel",    5)

    return f"""
<div class="card-box">
  {img}
  <div class="card-body">
    <div class="card-name">{c['name']}</div>
    <div class="card-sub">{c['set']} · {c['rarity']} · #{c.get('number','')} · {c.get('artist','')}</div>
    <div class="card-price">C${c['market_price']:.2f} {src_pill}</div>
    <div class="card-vt">Expected: C${c['expected_price']:.2f} &nbsp;|&nbsp;
        <span style="color:{'#34d399' if gap>=0 else '#fb7185'};">{gap_str}</span>
    </div>
    <div style="margin-top:6px;">
      <span class="pill {pill_cls}">{label}</span>
    </div>
    <details style="margin-top:10px;">
      <summary style="font-size:11px;color:#7c3aed;cursor:pointer;">Détails du score</summary>
      <div style="font-size:11px;color:#a0aec0;margin-top:6px;line-height:2;">
        <b>Pull Cost Score</b>: {pc:.1f}/10 &nbsp;(supply)<br>
        <b>Set Hype</b>: {sh:.1f}/10 &nbsp;(réputation set)<br>
        <b>Set Age</b>: {sa:.1f}/10 &nbsp;(courbe nouveauté/nostalgie)<br>
        <b>Gem Rate</b>: {gr:.1f}/10 &nbsp;(difficulté PSA 10)<br>
        <b>Price Velocity</b>: {pv:.1f}/10 &nbsp;(tension buy-side)<br>
        <b>Desirability</b>: {di:.1f}/10 &nbsp;(demand composite)<br>
        &nbsp;&nbsp;→ Character Premium: {cp:.1f}/10 (45%)<br>
        &nbsp;&nbsp;→ Art &amp; Hype: {ah:.1f}/10 (45%)<br>
        &nbsp;&nbsp;→ Universal Appeal: {ua:.1f}/10 (10%)<br>
        {tcg}
      </div>
    </details>
  </div>
</div>"""

# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-avatar"><img src="{AVATAR_URL}"></div>
    <div class="sidebar-title">The Nasty Model</div>
    <div class="sidebar-sub">TCG Fair Value Engine · 1 USD = {FX:.4f} C$</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-label">Seuils Signal</div>', unsafe_allow_html=True)
    gem_t  = st.slider("💎 Sous-évaluée si gap > X%", 5, 60, 20, 5) / 100
    over_t = st.slider("🔴 Surévaluée si gap < -X%",  5, 60, 20, 5) / 100

    st.markdown('<div class="sb-label">Filtres</div>', unsafe_allow_html=True)
    signal_filter = st.multiselect("Signal", ["gem","fair","over"],
                                   default=["gem","fair","over"],
                                   format_func=lambda x: {"gem":"💎 Sous-évaluée","fair":"✅ Juste","over":"🔴 Surévaluée"}[x])

    all_series = ["Scarlet & Violet", "Sword & Shield", "Mega Evolution"]
    series_filter = st.multiselect("Série", all_series, default=all_series)

    rarity_opts = ["Special Illustration Rare","Illustration Rare","Hyper Rare",
                   "Ultra Rare","Double Rare","ACE SPEC Rare","Shiny Rare","Shiny Ultra Rare"]
    rarity_filter = st.multiselect("Rareté", rarity_opts, default=rarity_opts)

    min_p, max_p = st.slider("Prix marché (C$)", 0, 2000, (0, 2000), 10)
    search_q = st.text_input("🔍 Recherche", placeholder="Pikachu, Umbreon…")

    st.markdown('<div class="sb-label">Tri</div>', unsafe_allow_html=True)
    sort_by  = st.selectbox("Trier par", ["gap_pct","market_price","desirability","pull_cost","expected_price"])
    sort_asc = st.checkbox("Croissant", value=False)

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
st.markdown("## 🎴 The Nasty Model — Fair Value TCG")

with st.spinner("Chargement des cartes… (~60 sec première fois)"):
    fetched = fetch_data(_v=14)

if fetched.empty:
    st.error("Aucune carte chargée — vérifier la connexion API.")
    st.stop()

df_model, r2, coef_pull, coef_demand = run_model(fetched, gem_t, over_t)

# ── Metrics ──────────────────────────────────────────────────────────────────
n_gem  = (df_model["Signal"] == "gem").sum()
n_over = (df_model["Signal"] == "over").sum()
n_fair = (df_model["Signal"] == "fair").sum()

c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    st.markdown(f'<div class="metric-box"><div class="metric-val">{len(df_model)}</div>'
                f'<div class="metric-lbl">Cartes analysées</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-box"><div class="metric-val" style="color:#34d399;">{n_gem}</div>'
                f'<div class="metric-lbl">💎 Sous-évaluées</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-box"><div class="metric-val" style="color:#fb7185;">{n_over}</div>'
                f'<div class="metric-lbl">🔴 Surévaluées</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-box"><div class="metric-val">{r2:.2f}</div>'
                f'<div class="metric-lbl">R² du modèle</div></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="metric-box"><div class="metric-val" style="color:#a5b4fc;">{coef_demand:+.0f}%</div>'
                f'<div class="metric-lbl">Prix/pt Desirability</div></div>', unsafe_allow_html=True)

# ── Model explainer ───────────────────────────────────────────────────────────
with st.expander("📊 Comment fonctionne le modèle?", expanded=False):
    st.markdown(f"""
**Inspiré de PokeDataDadGuy — deux forces: Supply vs Demand**

**1. Pull Cost Score (Supply)** — *Combien ça coûte de pull cette carte?*
> Packs par hit (rareté) × Nombre de cartes dans ce slot = Packs moyens à pull
> Converti en coût USD puis log-scalé sur 1–10.

**2. Desirability Index (Demand)** — *Combien les gens la veulent?*
> **45% Character Premium** — Popularité du Pokémon (classement AV Club × marché)
> **45% Art & Hype** — Qualité art + signaux de demande (spread TCGPlayer)
> **10% Universal Appeal** — Pertinence meta + reconnaissance générale

**3. Régression Ridge** — *log(prix) ~ pull_cost + desirability*
> +1 pt Pull Cost → **+{coef_pull:.0f}%** sur le prix *(PokeDataDadGuy: ~+19%)*
> +1 pt Desirability → **+{coef_demand:.0f}%** sur le prix *(PokeDataDadGuy: ~+41%)*
> R² = **{r2:.3f}** — proportion de variance expliquée par le modèle

**Signal**: Expected Price vs Market Price → écart positif = sous-évaluée
    """)

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_gem, tab_fair, tab_over, tab_all, tab_chart = st.tabs([
    f"💎 Sous-évaluées ({n_gem})",
    f"✅ Prix Juste ({n_fair})",
    f"🔴 Surévaluées ({n_over})",
    "📋 Tout voir",
    "📊 Graphique"
])

def apply_filters(df):
    df = df[df["series"].isin(series_filter)]
    df = df[df["rarity"].isin(rarity_filter)]
    df = df[(df["market_price"] >= min_p) & (df["market_price"] <= max_p)]
    if search_q:
        q = search_q.lower()
        df = df[df["name"].str.lower().str.contains(q) | df["set"].str.lower().str.contains(q)]
    df = df[df["Signal"].isin(signal_filter)]
    return df.sort_values(sort_by, ascending=sort_asc)

df_filtered = apply_filters(df_model)

def render_cards(df_sub, sig_val=None):
    if df_sub.empty:
        st.info("Aucune carte dans cette catégorie avec les filtres actuels.")
        return
    cols = st.columns(2)
    for i, (_, row) in enumerate(df_sub.iterrows()):
        sig = sig_val if sig_val else row["Signal"]
        cols[i % 2].markdown(card_html(row, sig), unsafe_allow_html=True)

with tab_gem:
    render_cards(df_filtered[df_filtered["Signal"]=="gem"], "gem")

with tab_fair:
    render_cards(df_filtered[df_filtered["Signal"]=="fair"], "fair")

with tab_over:
    render_cards(df_filtered[df_filtered["Signal"]=="over"], "over")

with tab_all:
    disp = df_filtered[[
        "name","set","rarity","market_price","expected_price","gap_pct",
        "pull_cost","desirability","set_hype","gem_rate","set_age","price_vel","Signal"
    ]].copy()
    disp.columns = [
        "Carte","Set","Rareté","Prix (C$)","Expected (C$)","Gap %",
        "Pull Cost","Desirability","Set Hype","Gem Rate","Set Age","Velocity","Signal"
    ]
    def color_gap(val):
        if isinstance(val, (int,float)):
            if val > 15:  return "color:#34d399"
            if val < -15: return "color:#fb7185"
        return "color:#a5b4fc"
    st.dataframe(
        disp.style.map(color_gap, subset=["Gap %"]),
        use_container_width=True, hide_index=True, height=600
    )

with tab_chart:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#0f0f1e")
    for ax in axes:
        ax.set_facecolor("#1a1a2e")
        ax.tick_params(colors="#8892b0")
        for spine in ax.spines.values(): spine.set_color("#2d2d50")

    colors = {"gem":"#34d399","fair":"#a5b4fc","over":"#fb7185"}

    # Scatter: Pull Cost vs Desirability (bubble = market price)
    ax1 = axes[0]
    for sig, grp in df_filtered.groupby("Signal"):
        sizes = np.clip(grp["market_price"] / 5, 20, 400)
        ax1.scatter(grp["pull_cost"], grp["desirability"],
                    c=colors[sig], s=sizes, alpha=0.7, label=sig)
    ax1.set_xlabel("Pull Cost Score (Supply)", color="#8892b0")
    ax1.set_ylabel("Desirability Index (Demand)", color="#8892b0")
    ax1.set_title("Supply vs Demand\n(bulle = prix marché)", color="#fff", fontsize=11)
    ax1.legend(facecolor="#1a1a2e", labelcolor="#e2e8f0")

    # Scatter: Expected vs Market
    ax2 = axes[1]
    for sig, grp in df_filtered.groupby("Signal"):
        ax2.scatter(grp["market_price"], grp["expected_price"],
                    c=colors[sig], alpha=0.7, s=40, label=sig)
    mv = max(df_filtered["market_price"].max(), df_filtered["expected_price"].max()) * 1.05
    ax2.plot([0, mv], [0, mv], "--", color="#475569", linewidth=1, label="y = x (juste)")
    ax2.set_xlabel("Prix Marché (C$)", color="#8892b0")
    ax2.set_ylabel("Prix Attendu (C$)", color="#8892b0")
    ax2.set_title("Marché vs Modèle", color="#fff", fontsize=11)
    ax2.legend(facecolor="#1a1a2e", labelcolor="#e2e8f0")

    plt.tight_layout()
    st.pyplot(fig)

    # Distribution des gaps
    fig2, ax3 = plt.subplots(figsize=(10, 3))
    fig2.patch.set_facecolor("#0f0f1e")
    ax3.set_facecolor("#1a1a2e")
    ax3.tick_params(colors="#8892b0")
    for s in ax3.spines.values(): s.set_color("#2d2d50")
    ax3.hist(df_filtered["gap_pct"].clip(-100,200), bins=40, color="#7c3aed", alpha=0.8)
    ax3.axvline(0, color="#fb7185", linewidth=1.5, linestyle="--")
    ax3.set_xlabel("Gap % (Expected - Market)", color="#8892b0")
    ax3.set_title("Distribution des écarts", color="#fff", fontsize=10)
    st.pyplot(fig2)

