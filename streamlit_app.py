"""
Nasty TCG Dashboard — v10
"""
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import Ridge
import io, time, requests
from datetime import date

@st.cache_data(ttl=3600, show_spinner=False)
def get_usd_to_cad():
    try:
        r = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
        return r.json()["rates"]["CAD"]
    except:
        return 1.38  # fallback

st.set_page_config(page_title="The Nasty Model", page_icon="🎴", layout="wide")

AVATAR_URL = "https://base44.app/api/apps/69dae320409ba22186ac9552/files/mp/public/69dae320409ba22186ac9552/fb5969149_60b86a1b8_NastyPP_07.png"

FX = get_usd_to_cad()  # USD → CAD taux en temps réel

def to_cad(usd: float) -> str:
    """Convertit USD en CAD et formate."""
    return f"C${usd * FX:.2f}"

def to_cad_raw(usd: float) -> float:
    return round(usd * FX, 2)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, * { font-family: 'Inter', sans-serif !important; }

/* ══ SIDEBAR ══ */
section[data-testid="stSidebar"] {
    background: #0d0d1a !important;
    border-right: 1px solid #1a1a30 !important;
}
section[data-testid="stSidebar"] header { display:none !important; }

.sidebar-hero {
    display:flex; align-items:center; gap:12px;
    padding:20px 16px 16px 16px;
    border-bottom:1px solid #1a1a30;
    margin-bottom:16px;
}
.sidebar-hero img {
    width:52px; height:52px; border-radius:50%;
    border:2px solid #7c3aed; object-fit:cover;
}
.sidebar-title { font-size:17px; font-weight:800; color:#fff; line-height:1.2; }
.sidebar-sub   { font-size:11px; color:#6655aa; }

.sb-label {
    font-size:10px; font-weight:700; letter-spacing:1.5px;
    color:#5544aa; text-transform:uppercase;
    margin:18px 0 8px 0; padding-left:2px;
}
.sb-div { border:none; border-top:1px solid #1a1a30; margin:14px 0; }

/* Slider purple accent */
section[data-testid="stSidebar"] [data-testid="stSlider"] > div > div > div {
    background: #7c3aed !important;
}
section[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {
    background: #a855f7 !important;
    border: 2px solid #fff !important;
}

/* Total pill */
.total-pill {
    display:inline-flex; align-items:center; gap:6px;
    padding:6px 14px; border-radius:99px;
    font-size:13px; font-weight:700; margin:8px 0 14px 0;
    width:100%; justify-content:center;
}
.pill-ok   { background:#0d2e1a; color:#22c55e; border:1px solid #166534; }
.pill-low  { background:#2d1a00; color:#f59e0b; border:1px solid #92400e; }
.pill-high { background:#2d0a0a; color:#ef4444; border:1px solid #7f1d1d; }

/* Launch button */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #6d28d9, #7c3aed) !important;
    color: #fff !important; font-weight:700 !important;
    font-size:14px !important; border:none !important;
    border-radius:10px !important; padding:12px !important;
    width:100% !important;
}
div[data-testid="stButton"] > button:hover { opacity:.85 !important; }
div[data-testid="stButton"] > button:disabled {
    background:#1a1a2e !important; color:#444 !important;
}

/* ══ MAIN ══ */
.main-hero {
    display:flex; align-items:center; gap:16px;
    padding:24px 0 8px 0;
}
.main-hero img {
    width:64px; height:64px; border-radius:50%;
    border:3px solid #7c3aed; object-fit:cover;
}
.main-title { font-size:32px; font-weight:800; color:#fff; letter-spacing:-.5px; }
.main-sub   { font-size:13px; color:#6655aa; margin-top:2px; }

/* ══ CARD ══ */
.card-wrap {
    background:#12122a; border:1px solid #1e1e3f;
    border-radius:14px; overflow:hidden; margin-bottom:14px;
    transition:border-color .2s, transform .15s, box-shadow .2s;
}
.card-wrap:hover {
    border-color:#7c3aed; transform:translateY(-3px);
    box-shadow:0 8px 24px rgba(124,58,237,.2);
}
.card-img { width:100%; display:block; }
.card-body { padding:10px 12px 12px 12px; }
.card-name {
    font-size:15px; font-weight:700; color:#eeeeff;
    margin:0 0 2px 0; white-space:nowrap;
    overflow:hidden; text-overflow:ellipsis;
}
.card-set { font-size:11px; color:#5566aa; margin-bottom:8px; }
.price-block {
    display:flex; justify-content:space-between; align-items:flex-end;
    margin-bottom:8px;
}
.price-market { font-size:12px; color:#7788aa; }
.price-mnum   { font-size:14px; font-weight:600; color:#aabbdd; }
.price-fv-lbl { font-size:10px; color:#6644aa; text-align:right; }
.price-fv-num { font-size:18px; font-weight:800; color:#a855f7; line-height:1; text-align:right; }
.ecart-pill {
    display:inline-block; padding:3px 10px;
    border-radius:99px; font-size:13px; font-weight:700; margin-bottom:8px;
}
.pill-gem  { background:#0a2e1a; color:#22c55e; }
.pill-over { background:#2e0a0a; color:#ef4444; }
.pill-fair { background:#2e2200; color:#f59e0b; }
details { margin-top:4px; }
summary { font-size:11px; color:#7c3aed; cursor:pointer; list-style:none; padding:2px 0; }
summary::-webkit-details-marker { display:none; }
.detail-body {
    margin-top:6px; padding:8px; background:#0a0a20;
    border-radius:8px; font-size:11px; color:#7788aa; line-height:1.9;
}

/* Metrics */
[data-testid="stMetric"] {
    background:#12122a; border:1px solid #1e1e3f;
    border-radius:12px; padding:12px 16px !important;
}
[data-testid="stMetricLabel"] { font-size:11px !important; color:#6655aa !important; }
[data-testid="stMetricValue"] { font-size:22px !important; font-weight:700 !important; color:#fff !important; }
</style>
""", unsafe_allow_html=True)

from pokemon_popularity import get_popularity_score
from meta_scores import get_meta_score
from grading_ratio import get_grading_difficulty, get_gem_rate

# ─── Constantes ───────────────────────────────────────────────
# Pull rate de BASE par rareté (taux de drop de la CATÉGORIE dans un booster)
RARITY_PULL = {
    "Special Illustration Rare":1/1440,"Hyper Rare":1/360,
    "Illustration Rare":1/144,"Ultra Rare":1/72,"Double Rare":1/48,
    "ACE SPEC Rare":1/72,"Rare Holo VMAX":1/36,"Rare Holo VSTAR":1/36,
    "Rare Holo V":1/24,"Rare Holo EX":1/24,"Rare Holo":1/12,
    "Rare":1/10,"Shiny Rare":1/60,"Shiny Ultra Rare":1/180,
    "Amazing Rare":1/40,"Radiant Rare":1/36,
    "Trainer Gallery Rare Holo":1/72,"Promo":1/1,
}

# ── SET METADATA : Dilution & Accessibilité ──────────────────────────────────
# Données par set_id (source: Limitless, Bulbapedia, communauté)
# Format: {set_id: (nb_SIR, nb_chase_total, type_prod, print_vol_mult)}
#   nb_SIR         = nombre de SIR dans le set
#   nb_chase_total = nb SIR + Hyper Rare + Gold dans le set
#   type_prod      = "special" | "main" | "mini"
#     special = pas de booster box (coffrets uniquement) → accessibilité réduite
#     mini    = tirage limité
#   print_vol_mult = multiplicateur volume impression (1.0=normal, 0.6=limité, 1.4=grand set)
SET_META = {
    # ── Scarlet & Violet ──────────────────────────────────────────────────
    "sv8pt5": (20, 32, "special", 0.55),  # Prismatic Evolutions - coffrets uniquement, méga dilution
    "sv8":    (15, 28, "main",    1.2),   # Surging Sparks
    "sv7":    (15, 27, "main",    1.1),   # Stellar Crown
    "sv6pt5": (12, 20, "mini",    0.7),   # Shrouded Fable - mini set
    "sv6":    (13, 24, "main",    1.1),   # Twilight Masquerade
    "sv5":    (16, 26, "main",    1.0),   # Temporal Forces
    "sv4pt5": (12, 22, "mini",    0.65),  # Paldean Fates - shiny vault
    "sv4":    (14, 25, "main",    1.0),   # Paradox Rift
    "sv3pt5": (10, 18, "mini",    0.7),   # Pokemon 151 - spécial, très demandé
    "sv3":    (14, 24, "main",    1.0),   # Obsidian Flames
    "sv2":    (12, 20, "main",    0.9),   # Paldea Evolved
    "sv1":    (10, 18, "main",    0.85),  # Scarlet & Violet Base
    "svp":    (0,  0,  "promo",   1.0),   # SVP Promos
    # ── Sword & Shield ────────────────────────────────────────────────────
    "swsh12pt5": (30, 45, "special", 0.6), # Crown Zenith - spécial, dense
    "swsh12":    (10, 18, "main",    1.0), # Silver Tempest
    "swsh11":    (8,  15, "main",    1.0), # Lost Origin
    "swsh10":    (8,  14, "main",    0.9), # Astral Radiance
    "swsh9":     (7,  13, "main",    0.9), # Brilliant Stars
    "swsh8":     (6,  11, "main",    0.85),# Fusion Strike
    "swsh7":     (5,  10, "main",    0.8), # Evolving Skies
    "swsh6":     (4,   8, "main",    0.8), # Chilling Reign
    "swsh5":     (4,   8, "main",    0.8), # Battle Styles
    "swsh45":    (0,  12, "mini",    0.6), # Shining Fates - spécial shiny
    "swsh4":     (3,   7, "main",    0.75),# Vivid Voltage
    "swsh35":    (0,   8, "special", 0.65),# Champion Path
    "swsh3":     (3,   6, "main",    0.75),# Darkness Ablaze
    "swsh2":     (3,   6, "main",    0.7), # Rebel Clash
    "swsh1":     (3,   5, "main",    0.7), # Sword & Shield Base
    "ssp":       (0,   0, "promo",   1.0), # Promo S&S
    # Nouveau set Destined Rivals (sv9)
    "sv9":       (14, 25, "main",    1.1),
}

# Accessibilité produit : coût relatif d'obtenir un booster (vs booster box standard)
PROD_ACCESS = {
    "special": 1.6,  # coffrets uniquement → packs 60-80% plus chers
    "main":    1.0,  # booster box normal
    "mini":    1.35, # mini set ou shiny vault
    "promo":   0.5,  # promos gratuites
}

def get_set_meta(set_id: str):
    """Retourne (nb_SIR, nb_chase, prod_type, print_vol) avec fallback."""
    if set_id in SET_META:
        return SET_META[set_id]
    # Fallback par série
    if set_id.startswith("sv"):  return (12, 20, "main", 1.0)
    if set_id.startswith("swsh"):return (5,  10, "main", 0.9)
    return (8, 15, "main", 1.0)

def specific_pull_rate(base_pull: float, nb_chase: int) -> float:
    """
    Rs = taux_drop_categorie / nb_cartes_dans_categorie
    Ex: SIR Prismatic = (1/1440) / 20 = 1/28800 → hyper-rare individuellement
    """
    if nb_chase <= 0: return base_pull
    return base_pull / max(nb_chase, 1)

ARTIST_SCORES = {
    "mika pikazo":10.0,"tetsu kayama":9.5,"akira komayama":9.5,
    "ryota murayama":9.0,"nagomibana":9.0,"sowsow":8.8,"5ban graphics":8.5,
    "sanosuke sakuma":8.5,"atsushi furusawa":8.0,"yuka morii":8.0,
    "ryo ueda":7.8,"kiichiro":7.5,"yuu nishida":7.5,"anesaki dynamic":7.5,
    "kagemaru himeno":7.5,"tomokazu komiya":7.5,"hitoshi ariga":7.5,
    "eri yamaki":7.0,"kawayoo":7.0,"ayaka yoshida":7.0,"teeziro":7.0,
    "keiichiro ito":7.0,"yusuke ohmura":7.0,"atsuko nishida":7.5,
    "mitsuhiro arita":7.0,"shigenori negishi":6.8,"suwama ichiro":6.5,
    "kouki saitou":6.5,"mizue":6.5,"aya kusube":6.5,"tomoya kitakaze":6.5,
    "0313":6.5,"daisuke ito":6.5,"narumi sato":6.5,"shizurow":6.5,
    "luncheon":6.5,"uninori":6.0,"shibuzoh":6.0,"hasuno":6.0,
    "kodama":6.0,"nekoramune":6.0,"gossan":6.0,"makoto iguchi":6.0,
    "naoyo kimura":6.5,"yuri ex":6.5,"studio bora":6.0,"aky cg works":6.5,
    "ken sugimori":6.0,"kirisaki":5.5,"yumi takahara":5.0,
}

def get_artist_score(a):
    a = a.lower().strip()
    if a in ARTIST_SCORES: return ARTIST_SCORES[a]
    for n, s in ARTIST_SCORES.items():
        if n in a or a in n: return s
    return 4.5

def lifecycle(rel):
    try:
        p = rel.split("/")
        days = (date.today() - date(int(p[0]), int(p[1]), int(p[2]))).days
        if days < 60:   return 7.0
        if days < 120:  return 9.0
        if days < 270:  return 8.0
        if days < 450:  return 6.5
        if days < 600:  return 5.0
        if days < 730:  return 3.5
        if days < 1095: return 2.5
        return 2.0
    except: return 5.0

def hype(prices):
    sigs, lbl = [], "-"
    for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
        if pt not in prices: continue
        p = prices[pt]
        low = p.get("low", 0) or 0
        mid = p.get("mid", 0) or 0
        high = p.get("high", 0) or 0
        mkt = p.get("market", 0) or 0
        if mkt <= 0: continue
        if low > 0:
            r = low / mkt
            if r >= .85:   sigs.append(9.5); lbl = "🔥 Très demandée"
            elif r >= .70: sigs.append(7.5); lbl = "📈 Bonne demande"
            elif r >= .50: sigs.append(5.5); lbl = "➡️ Stable"
            elif r >= .30: sigs.append(3.5); lbl = "📉 Faible"
            else:          sigs.append(1.5); lbl = "🧊 Peu d'intérêt"
        if high > 0:
            m = high / mkt
            sigs.append(9.0 if m>=2 else 7.0 if m>=1.5 else 5.5 if m>=1.2 else 4.0)
        if mid > 0:
            sigs.append(8.0 if mkt>mid*1.15 else 6.0 if mkt>mid else 4.5 if mkt>mid*.9 else 3.0)
        break
    return (round(np.mean(sigs), 1) if sigs else 5.0, lbl)

# ── Mapping pokemontcg.io set ID → TCGdex set ID ─────────────────────────
def pokeid_to_tcgdex(set_id: str) -> str:
    import re
    m = re.match(r'^sv(\d+)pt(\d+)$', set_id)
    if m: return f"sv{int(m.group(1)):02d}.{int(m.group(2))}"
    m = re.match(r'^sv(\d+)$', set_id)
    if m: return f"sv{int(m.group(1)):02d}"
    m = re.match(r'^swsh(\d+)pt(\d+)$', set_id)
    if m: return f"swsh{m.group(1)}.{m.group(2)}"
    return set_id

@st.cache_data(ttl=7200, show_spinner=False)
def fetch_price_history(tcgdex_card_id: str) -> dict:
    try:
        r = requests.get(f"https://api.tcgdex.net/v2/en/cards/{tcgdex_card_id}", timeout=6)
        if r.status_code != 200: return {}
        cm = r.json().get("pricing", {}).get("cardmarket", {}) or {}
        avg1, avg7, avg30 = cm.get("avg1"), cm.get("avg7"), cm.get("avg30")
        if not avg7 or not avg30: return {}
        vel_7_30 = round((avg7 - avg30) / avg30 * 100, 1)
        vel_1_7  = round((avg1 - avg7)  / avg7  * 100, 1) if avg1 else None
        return {"avg7": avg7, "avg30": avg30, "vel_7_30": vel_7_30, "vel_1_7": vel_1_7}
    except: return {}

QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)
DEFAULTS = {"tier":35,"scarcity":25,"psa10":10,"meta":10,"hype":8,"artist":7,"lifecycle":5}
FCOLS = ["f_scarcity_inv","f_tier","f_artist","f_meta","f_hype","f_psa10","f_lifecycle"]

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(max_cards=9999, _v=7):  # _v=7 : fetch complet sans limite
    rows, seen, page = [], set(), 1
    while len(rows) < max_cards:
        size = min(250, max_cards - len(rows))
        try:
            r = requests.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"q":QUERY,"page":page,"pageSize":size,"orderBy":"-set.releaseDate"},
                timeout=20
            )
            r.raise_for_status()
            cards = r.json().get("data", [])
        except Exception as e:
            st.error(f"API : {e}"); break
        if not cards: break
        for c in cards:
            cid = c.get("id", "")
            if cid in seen: continue
            seen.add(cid)
            tcp = c.get("tcgplayer", {})
            prices = tcp.get("prices", {})
            mkt = None
            for pt in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
                if pt in prices and prices[pt].get("market"):
                    mkt = prices[pt]["market"]; break
            if not mkt or mkt <= 0: continue
            mkt = mkt * get_usd_to_cad()  # Convertir en CAD dès le fetch
            rar = c.get("rarity", "Unknown")
            art = c.get("artist", "")
            nm  = c.get("name", "?")
            sid = c.get("set", {}).get("id", "")
            num = c.get("number", "")
            rel = c.get("set", {}).get("releaseDate", "")
            hs, hl = hype(prices)
            nb_sir, nb_chase, prod_type, print_vol = get_set_meta(sid)
            base_pull = RARITY_PULL.get(rar, 1/20)
            rs = specific_pull_rate(base_pull, nb_chase)
            rows.append({
                "id": cid, "name": nm,
                "set": c.get("set", {}).get("name", "?"),
                "series": c.get("set", {}).get("series", "?"),
                "release_date": rel, "rarity": rar, "artist": art,
                "f_scarcity": RARITY_PULL.get(rar, 1/20),
                "f_specific_pull": rs,           # Rs : pull rate individuel
                "f_chase_density": nb_chase,     # Dset : nb chase cards du set
                "f_accessibility": PROD_ACCESS.get(prod_type, 1.0),  # Aprod
                "f_print_vol": print_vol,        # Vprint
                "prod_type": prod_type,
                "f_tier": get_popularity_score(nm),
                "f_artist": get_artist_score(art),
                "f_meta": get_meta_score(sid, num),
                "f_hype": hs, "hype_label": hl,
                "f_psa10": get_grading_difficulty(rar),
                "gem_rate": round(get_gem_rate(rar) * 100),
                "f_lifecycle": lifecycle(rel),
                "market_price": round(mkt, 2),
                "tcgplayer_url": tcp.get("url", ""),
                "image_url": c.get("images", {}).get("small", ""),
                "tcgdex_id": f"{pokeid_to_tcgdex(sid)}-{num}",
                "f_velocity": 5.0,
            })
        if len(cards) < size: break
        page += 1
        time.sleep(0.15)
    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not df.empty:
        df = df.drop_duplicates(subset=["name", "set"])
    return df

def run_model(df, w, gt, ot):
    """
    Moteur v5 — Score qualitatif intra-rareté UNIQUEMENT.

    Architecture :
    - Les variables de dilution (Rs, Dset, Aprod, Vprint) font partie du contexte
      DÉJÀ reflété dans le prix marché. On n'en a pas besoin pour gonfler le score.
    - Ce qui compte : est-ce que CETTE carte est sous/surévaluée vs ses pairs de même rareté?
    - Score = 7 facteurs qualitatifs pondérés par l'utilisateur
    - Rank = percentile intra-rareté du score (Umbreon vs autres SIR, pas vs Ultra Rare)
    - Vt = prix_marché × multiplicateur(rank)
      rank 0.0 → ×0.5 | rank 0.5 → ×1.0 | rank 1.0 → ×1.9
      courbe non-linéaire douce, sans plafond artificiel
    """
    df = df.copy()
    # Rareté individuelle = pull rate catégorie ÷ nb de SIR dans le set
    df["f_scarcity_inv"] = -np.log(df["f_specific_pull"].clip(lower=1e-9))

    # ── Score qualitatif pondéré ──────────────────────────────────────────
    sc = MinMaxScaler()
    for c in FCOLS:
        df[f"{c}_n"] = sc.fit_transform(df[[c]])
    wa = np.array([w[c] for c in FCOLS])
    df["score_q"] = df[[f"{c}_n" for c in FCOLS]].values.dot(wa) / (wa.sum() or 1)

    # ── Percentile rank INTRA-RARETÉ ─────────────────────────────────────
    # Chaque carte est jugée uniquement vs ses pairs de même rareté
    # Umbreon SIR Prismatic vs autres SIR — pas vs Ultra Rare à $10
    df["qual_rank"] = df.groupby("rarity")["score_q"].rank(pct=True)

    # ── Multiplicateur Fair Value ─────────────────────────────────────────
    # Courbe en deux segments :
    #   rank 0.0 → 0.50x  (très surévaluée pour sa rareté)
    #   rank 0.5 → 1.00x  (au prix juste = médiane de sa rareté)
    #   rank 0.75 → 1.40x
    #   rank 1.0 → ~1.90x (meilleure carte de sa rareté)
    # Pas de plafond — les cartes PEUVENT être très sous/surévaluées
    def rank_to_mult(r):
        if r <= 0.5:
            # Linéaire descendant : 0.50 → 1.00
            return 0.50 + 0.50 * (r / 0.5)
        else:
            # Non-linéaire ascendant : 1.00 → ~1.90
            t = (r - 0.5) / 0.5  # 0→1
            return 1.0 + 0.9 * (t ** 1.4)  # légèrement convexe

    df["mult"] = df["qual_rank"].apply(rank_to_mult)
    df["Vt"]   = (df["market_price"] * df["mult"]).round(2)
    df["ecart"]= ((df["Vt"] - df["market_price"]) / df["market_price"] * 100).round(1)

    # ── Signal ───────────────────────────────────────────────────────────
    def sig(r):
        if r["ecart"] > gt * 100:  return "gem"
        if r["ecart"] < -ot * 100: return "over"
        return "fair"
    df["Signal"] = df.apply(sig, axis=1)

    # ── R² (informatif — score_q vs log-price par rareté) ────────────────
    try:
        from sklearn.linear_model import Ridge as _R
        _m = _R(alpha=1.0)
        _m.fit(df[["score_q"]], np.log1p(df["market_price"]))
        yp = _m.predict(df[["score_q"]])
        y  = np.log1p(df["market_price"].values)
        r2 = max(0, 1 - np.sum((y-yp)**2) / np.sum((y-np.mean(y))**2))
    except:
        r2 = 0.0

    df.drop(columns=[c for c in ["score_q","qual_rank","mult"] if c in df.columns],
            inplace=True)
    return df, round(r2, 3)


def _vel_label(tcgdex_id: str, default: float = 5.0) -> str:
    """Fetch vélocité pour UNE carte (via cache) et retourne un label HTML."""
    hist = fetch_price_history(tcgdex_id) if tcgdex_id else {}
    v30  = hist.get("vel_7_30")
    v7   = hist.get("vel_1_7")
    score = default
    if v30 is not None: score += min(2.5, max(-2.5, v30 / 6.0))
    if v7  is not None: score += min(1.5, max(-1.5, v7  / 10.0))
    score = round(min(10.0, max(0.0, score)), 1)
    if   score >= 7.5: return f"🚀 +{score}/10  ({f'+{v30:.1f}%' if v30 else ''})"
    elif score >= 6.0: return f"📈 {score}/10  ({f'+{v30:.1f}%' if v30 else ''})"
    elif score >= 4.0: return f"➡️  {score}/10  (stable)"
    elif score >= 2.5: return f"📉 {score}/10  ({f'{v30:.1f}%' if v30 else ''})"
    else:              return f"🧊 {score}/10  (chute)"

def card_html(c, sig):
    e = c["ecart"]
    es = f"+{e:.0f}%" if e >= 0 else f"{e:.0f}%"
    pc = {"gem":"pill-gem","over":"pill-over","fair":"pill-fair"}[sig]
    img = f'<img class="card-img" src="{c["image_url"]}">' if c.get("image_url") else ""
    tcg = f'<a href="{c["tcgplayer_url"]}" target="_blank" style="color:#7c3aed;font-size:11px;">TCGPlayer ↗</a>' if c.get("tcgplayer_url") else ""
    return f"""
<div class="card-wrap">
  {img}
  <div class="card-body">
    <div class="card-name" title="{c['name']}">{c['name']}</div>
    <div class="card-set">{c['set']}</div>
    <div class="price-block">
      <div>
        <div class="price-market">Marché</div>
        <div class="price-mnum">C${c['market_price']:.2f}</div>
      </div>
      <div>
        <div class="price-fv-lbl">Fair Value</div>
        <div class="price-fv-num">C${c['Vt']:.2f}</div>
      </div>
    </div>
    <div><span class="ecart-pill {pc}">{es}</span></div>
    <details>
      <summary>▾ Détails</summary>
      <div class="detail-body">
        <b>Rareté:</b> {c['rarity']}<br>
        <b>Artiste:</b> {c['artist']}<br>
        <b>Pop:</b> {c['f_tier']:.1f}/10 &nbsp;·&nbsp;
        <b>Méta:</b> {c['f_meta']:.1f}/10 &nbsp;·&nbsp;
        <b>Hype:</b> {c['hype_label']}<br>
        <b>Vélocité 30j:</b> {_vel_label(c.get("tcgdex_id",""), c.get("f_velocity",5))}<br>
        <b>PSA 10 gem rate:</b> {c['gem_rate']:.0f}%<br>
        {tcg}
      </div>
    </details>
  </div>
</div>"""

def grid(df_c, sig, n=24):
    df_c = df_c.head(n)
    if df_c.empty:
        st.info("Aucune carte dans cette catégorie."); return
    for i in range(0, len(df_c), 4):
        row = df_c.iloc[i:i+4]
        cols = st.columns(4)
        for j, (_, c) in enumerate(row.iterrows()):
            with cols[j]:
                st.markdown(card_html(c, sig), unsafe_allow_html=True)

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-hero">
      <img src="{AVATAR_URL}">
      <div>
        <div class="sidebar-title">The Nasty Model</div>
        <div class="sidebar-sub">TCG Fair Value Engine · 1 USD = {FX:.4f} C$</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-label">Poids des facteurs</div>', unsafe_allow_html=True)
    w_tier      = st.slider("⭐ Popularité",    0, 100, DEFAULTS["tier"],      5)
    w_scarcity  = st.slider("🔮 Rareté",         0, 100, DEFAULTS["scarcity"],  5)
    w_psa10     = st.slider("💎 Grading PSA",    0, 100, DEFAULTS["psa10"],     5)
    w_meta      = st.slider("🏆 Compétitivité",  0, 100, DEFAULTS["meta"],      5)
    w_hype      = st.slider("🔥 Hype marché",    0, 100, DEFAULTS["hype"],      5)
    w_artist    = st.slider("🎨 Artiste",         0, 100, DEFAULTS["artist"],    5)
    w_lifecycle = st.slider("📅 Cycle de vie",   0, 100, DEFAULTS["lifecycle"], 5)

    total = w_tier + w_scarcity + w_psa10 + w_meta + w_hype + w_artist + w_lifecycle
    if total == 100:
        st.markdown('<div class="total-pill pill-ok">✅ 100% — Prêt</div>', unsafe_allow_html=True)
        ok = True
    elif total < 100:
        st.markdown(f'<div class="total-pill pill-low">⚠️ {total}% — manque {100-total}%</div>', unsafe_allow_html=True)
        ok = False
    else:
        st.markdown(f'<div class="total-pill pill-high">❌ {total}% — trop de {total-100}%</div>', unsafe_allow_html=True)
        ok = False

    fetch_btn = st.button("🚀 Lancer l'analyse", disabled=not ok, use_container_width=True)
    if st.button("🗑️ Vider le cache", use_container_width=True):
        st.cache_data.clear()
        st.session_state.df = pd.DataFrame()
        st.rerun()

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">Seuils</div>', unsafe_allow_html=True)
    gem_t  = st.slider("🟢 Sous-évalué si +X%", 5, 60, 15, 5)
    over_t = st.slider("🔴 Surévalué si -X%",   5, 60, 15, 5)

    st.markdown('<hr class="sb-div">', unsafe_allow_html=True)
    st.markdown('<div class="sb-label">Filtres</div>', unsafe_allow_html=True)
    min_p_cad = st.number_input("Prix min (C$)", 0, 2000, 5)
    max_p_cad = st.number_input("Prix max (C$)", 0, 8000, 2000)
    min_p = round(min_p_cad / FX, 2)
    max_p = round(max_p_cad / FX, 2)
    filt_rar = st.multiselect("Raretés", [
        "Special Illustration Rare","Illustration Rare","Hyper Rare",
        "Ultra Rare","Double Rare","ACE SPEC Rare","Shiny Rare","Shiny Ultra Rare"
    ])
    filt_meta = st.checkbox("Tournoi seulement", False)

# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════
st.markdown(f"""
<div class="main-hero">
  <img src="{AVATAR_URL}">
  <div>
    <div class="main-title">The Nasty Model</div>
    <div class="main-sub">7 facteurs · Popularité TPC · Limitless TCG · PSA Gem Rate</div>
  </div>
</div>
""", unsafe_allow_html=True)

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()

if fetch_btn and ok:
    with st.spinner("Chargement... ~45 sec (1275 cartes)"):
        fetched = fetch_data(_v=7)
    if fetched.empty:
        st.error("Aucune carte. Vérifie ta connexion.")
    else:
        st.session_state.df = fetched
        st.success(f"✅ {len(fetched)} cartes chargées !")

df_raw = st.session_state.df

if df_raw.empty:
    st.markdown("""
| Facteur | Source | Défaut |
|---|---|---|
| ⭐ Popularité | Sondage officiel TPC | **35%** |
| 🔮 Rareté | Pull rates officiels | **25%** |
| 💎 Grading | Gem rate PSA réel | **10%** |
| 🏆 Compétitivité | Limitless TCG | **10%** |
| 🔥 Hype | Triple signal TCGPlayer | **8%** |
| 🎨 Artiste | 80+ illustrateurs classés | **7%** |
| 📅 Cycle de vie | Âge set / rotation | **5%** |
    """)
    st.stop()

W = {
    "f_scarcity_inv": w_scarcity/100, "f_tier": w_tier/100,
    "f_artist": w_artist/100, "f_meta": w_meta/100,
    "f_hype": w_hype/100, "f_psa10": w_psa10/100, "f_lifecycle": w_lifecycle/100,
}
try:
    df, r2 = run_model(df_raw, W, gem_t/100, over_t/100)
except Exception as _e:
    st.error(f"Erreur modèle : {_e}")
    st.stop()

df = df[(df["market_price"] >= min_p) & (df["market_price"] <= max_p)]
if filt_rar: df = df[df["rarity"].isin(filt_rar)]
if filt_meta: df = df[df["f_meta"] > 1.0]

series_list = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
col_s, col_r = st.columns([4, 1])
with col_s:
    sel = st.selectbox("Série", series_list, label_visibility="collapsed")
with col_r:
    col = "#22c55e" if r2 > .5 else ("#f59e0b" if r2 > .3 else "#ef4444")
    st.markdown(f'<div style="padding-top:8px;font-size:12px;color:{col};">R² {r2:.2f}</div>', unsafe_allow_html=True)
if sel != "Toutes":
    df = df[df["series"] == sel]

# ── Recherche par nom de carte ─────────────────────────────────────────────
search_q = st.text_input(
    "🔍 Rechercher une carte",
    placeholder="Ex: Umbreon ex, Charizard, Pikachu...",
    label_visibility="collapsed"
)
if search_q.strip():
    mask = df["name"].str.contains(search_q.strip(), case=False, na=False)
    df = df[mask]
    if df.empty:
        st.warning(f"Aucune carte trouvée pour « {search_q} »")
        st.stop()

gems  = df[df["Signal"] == "gem"].sort_values("ecart", ascending=False)
overs = df[df["Signal"] == "over"].sort_values("ecart")
fair  = df[df["Signal"] == "fair"].sort_values("ecart", ascending=False)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📦 Analysées",     len(df))
c2.metric("🟢 Sous-évaluées", len(gems))
c3.metric("🟡 Prix juste",    len(fair))
c4.metric("🔴 Surévaluées",   len(overs))
c5.metric("R²",               f"{r2:.2f}")
st.divider()

t1, t2, t3, t4 = st.tabs([
    f"🟢 Sous-évaluées ({len(gems)})",
    f"🔴 Surévaluées ({len(overs)})",
    f"🟡 Prix juste ({len(fair)})",
    "📊 Graphiques",
])
with t1: grid(gems, "gem")
with t2: grid(overs, "over")
with t3: grid(fair, "fair")
with t4:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), facecolor="#0d0d1a")
    cm = {"gem":"#22c55e","over":"#ef4444","fair":"#f59e0b"}
    for ax in [ax1, ax2]:
        ax.set_facecolor("#12122a"); ax.tick_params(colors="#aaa")
    for sig, grp in df.groupby("Signal"):
        ax1.scatter(grp["market_price"], grp["Vt"],
                    color=cm.get(sig, "gray"), alpha=.7, s=45, label=sig)
    mv = max(df["market_price"].max(), df["Vt"].max()) * 1.05
    ax1.plot([0, mv], [0, mv], "w--", lw=.8)
    ax1.set_xlabel("Prix marché ($)", color="#aaa")
    ax1.set_ylabel("Fair Value ($)", color="#aaa")
    ax1.set_title(f"FV vs Prix  R²={r2:.2f}", color="white")
    ax1.legend(facecolor="#12122a", labelcolor="white")
    top20 = df.nlargest(20, "ecart")
    ax2.barh(top20["name"], top20["ecart"],
             color=[cm.get(s, "gray") for s in top20["Signal"]])
    ax2.axvline(0, color="white", lw=.7, ls="--")
    ax2.set_xlabel("Écart (%)", color="#aaa")
    ax2.set_title("Top 20 sous-évaluées", color="white")
    ax2.invert_yaxis()
    st.pyplot(fig)

st.divider()
with st.expander("📋 Tableau complet"):
    disp = df[["name","set","rarity","market_price","Vt","ecart","Signal"]].copy()
    # prix déjà en CAD depuis le fetch
    disp.columns = ["Carte","Set","Rareté","Prix(C$)","FV(C$)","Écart(%)","Signal"]
    st.dataframe(disp.sort_values("Écart(%)", ascending=False),
                 use_container_width=True, hide_index=True)

buf = io.StringIO()
df.sort_values("ecart", ascending=False).to_csv(buf, index=False)
st.download_button("📥 Exporter CSV", buf.getvalue(),
                   f"nasty_model_{date.today()}.csv", "text/csv")
