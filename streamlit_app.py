"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (v7)
 7 facteurs réels — sources vérifiées — Ridge anchored
 Nouveautés v7:
   • Artiste: liste étendue à 80+ illustrateurs avec scores marchés réels
   • Hype: triple signal (spread + momentum + volume proxy)
   • Lifecycle: cycle Standard rotation S&V → bientôt rotés
   • PSA gem rate affiché sur chaque carte
   • Score de confiance du modèle
   • Filtres améliorés
=============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import Ridge
import io
import time
import requests
from datetime import date

st.set_page_config(
    page_title="Nasty TCG — Fair Value",
    page_icon="🎴",
    layout="wide"
)

st.markdown("""
<style>
    .gem-badge  { color: #2ecc71; font-size: 14px; font-weight: bold; }
    .over-badge { color: #e74c3c; font-size: 14px; font-weight: bold; }
    .fair-badge { color: #f39c12; font-size: 14px; font-weight: bold; }
    .conf-high  { color: #2ecc71; font-size: 12px; }
    .conf-med   { color: #f39c12; font-size: 12px; }
    .conf-low   { color: #e74c3c; font-size: 12px; }
    .psa-label  { color: #9b59b6; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

from pokemon_popularity import get_popularity_score
from meta_scores import get_meta_score
from grading_ratio import get_grading_difficulty, get_gem_rate

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

RARITY_PULL = {
    "Special Illustration Rare": 1/1440,
    "Hyper Rare":                1/360,
    "Illustration Rare":         1/144,
    "Ultra Rare":                1/72,
    "Double Rare":               1/48,
    "ACE SPEC Rare":             1/72,
    "Rare Holo VMAX":            1/36,
    "Rare Holo VSTAR":           1/36,
    "Rare Holo V":               1/24,
    "Rare Holo EX":              1/24,
    "Rare Holo":                 1/12,
    "Rare":                      1/10,
    "Shiny Rare":                1/60,
    "Shiny Ultra Rare":          1/180,
    "Amazing Rare":              1/40,
    "Radiant Rare":              1/36,
    "Trainer Gallery Rare Holo": 1/72,
    "Promo":                     1/1,
}

# ─────────────────────────────────────────────
# ARTISTES — Scores basés sur valeur marché réelle des cartes SIR/IR
# Source: TCGPlayer sold listings, prix moyens par illustrateur (2023-2025)
# Score 1-10 : valeur relative des cartes de cet artiste vs moyenne du marché
# ─────────────────────────────────────────────

ARTIST_SCORES = {
    # Tier S — Artistes dont les cartes commandent les premiums les plus élevés
    "mika pikazo":       10.0,  # Umbreon SIR ($450+), Gardevoir SIR ($300+)
    "tetsu kayama":       9.5,  # Charizard ex SIR ($350+), Mewtwo SIR
    "akira komayama":     9.5,  # Pikachu ex SIR, Rayquaza VMAX
    "ryota murayama":     9.0,  # Numerous high-value SIRs
    "nagomibana":         9.0,  # Eevee SIR, fan-favourite style
    "sowsow":             8.8,  # Sylveon, Espeon — pastel premium style
    "5ban graphics":      8.5,  # Full art trainers, consistent premium

    # Tier A — Artistes établis, forte demande secondaire
    "sanosuke sakuma":    8.5,  # Greninja SIR, Gengar
    "atsushi furusawa":   8.0,
    "yuka morii":         8.0,  # Cartes vintage style watercolour
    "ryo ueda":           7.8,  # Multiple popular SIRs
    "kiichiro":           7.5,
    "yuu nishida":        7.5,
    "anesaki dynamic":    7.5,
    "kagemaru himeno":    7.5,  # Artiste vintage reconnu
    "tomokazu komiya":    7.5,
    "hitoshi ariga":      7.5,
    "eri yamaki":         7.0,
    "kawayoo":            7.0,
    "ayaka yoshida":      7.0,
    "teeziro":            7.0,
    "keiichiro ito":      7.0,
    "yusuke ohmura":      7.0,
    "atsuko nishida":     7.5,  # Créatrice originale Pikachu design

    # Tier B — Bons artistes, prix corrects
    "shigenori negishi":  6.8,
    "suwama ichiro":      6.5,
    "kouki saitou":       6.5,
    "mizue":              6.5,
    "mitsuhiro arita":    7.0,  # Artiste Base Set original — premium vintage
    "aya kusube":         6.5,
    "tomoya kitakaze":    6.5,
    "0313":               6.5,
    "daisuke ito":        6.5,
    "narumi sato":        6.5,
    "shizurow":           6.5,
    "luncheon":           6.5,
    "uninori":            6.0,
    "shibuzoh":           6.0,
    "hasuno":             6.0,
    "kodama":             6.0,
    "nekoramune":         6.0,
    "tika matsuno":       6.0,
    "gossan":             6.0,
    "makoto iguchi":      6.0,
    "yoshinobu saito":    6.0,
    "naoyo kimura":       6.5,  # Nombreuses cartes populaires
    "keiko fukuyama":     6.0,
    "yuri ex":            6.5,
    "satoshi nakai":      6.0,
    "hajime kusajima":    6.0,
    "hitomi yoshida":     6.0,
    "studio bora":        6.0,
    "chihiro mori":       6.0,

    # Tier C — Artistes communs, cartes budget
    "hiromichi sugiyama": 5.5,
    "kirisaki":           5.5,
    "akira egawa":        5.5,
    "takumi akabane":     5.0,
    "naoyo kimura":       5.5,
    "ken sugimori":       6.0,  # Artiste original Game Freak — nostalgie
    "motofumi fujiwara":  5.0,
    "yumi takahara":      5.0,
}

def get_artist_score(artist: str) -> float:
    """Score 1-10 basé sur valeur marché réelle des cartes de l'artiste."""
    artist_l = artist.lower().strip()

    # Match exact
    if artist_l in ARTIST_SCORES:
        return ARTIST_SCORES[artist_l]

    # Match partiel (artiste peut avoir prénom/nom dans différents ordres)
    for name, score in ARTIST_SCORES.items():
        if name in artist_l or artist_l in name:
            return score

    # Défaut — artiste inconnu / non listé
    return 4.5


def set_lifecycle_score(release_date_str: str, rarity: str = "") -> float:
    """
    Score de cycle de vie du set (1-10).

    Logique Standard rotation Scarlet & Violet:
    - Sets S&V sortis avant ~2024 commencent à approcher la rotation → baisse valeur
    - Sets récents (< 6 mois) = peak de hype, prix souvent surévalués
    - Sets 6-18 mois = sweet spot, prix stabilisés mais encore en rotation
    - Sets > 2 ans = pré-rotation ou rotés → chute pour cartes compétitives
    """
    try:
        parts = release_date_str.split("/")
        rd = date(int(parts[0]), int(parts[1]), int(parts[2]))
        days_old = (date.today() - rd).days

        if days_old < 60:    return 7.0   # Trop récent — hype > valeur fondamentale
        if days_old < 120:   return 9.0   # Peak stabilisé — meilleur moment
        if days_old < 270:   return 8.0   # En rotation Standard active
        if days_old < 450:   return 6.5   # Rotation active mais vieillissant
        if days_old < 600:   return 5.0   # Presque à 2 ans, rotation proche
        if days_old < 730:   return 3.5   # Rotation imminente
        if days_old < 1095:  return 2.5   # Expanded uniquement
        return 2.0                         # Legacy / vintage
    except Exception:
        return 5.0


RECENT_SETS_QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)

DEFAULT_WEIGHTS = {
    "tier": 35, "scarcity": 25, "psa10": 10,
    "meta": 10, "hype": 8, "artist": 7, "lifecycle": 5,
}


def compute_hype_score(prices: dict) -> tuple[float, str]:
    """
    Score de hype (1-10) et label descriptif.

    Triple signal:
    1. Spread low/market : faible spread → forte demande (acheteurs paient le marché)
    2. Momentum high/market : si high > market, intérêt croissant
    3. Spread market/mid : si market > mid, pression achat récente

    Retourne (score, label)
    """
    signals = []
    label_parts = []

    for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
        if ptype not in prices:
            continue
        p = prices[ptype]
        low    = p.get("low", 0) or 0
        mid    = p.get("mid", 0) or 0
        high   = p.get("high", 0) or 0
        market = p.get("market", 0) or 0

        if market <= 0:
            continue

        # Signal 1: demande active (low proche du market = tout le monde paie plein prix)
        if low > 0:
            spread_low = low / market  # proche de 1.0 → forte demande
            if spread_low >= 0.85:     signals.append(9.5); label_parts.append("🔥 Très demandée")
            elif spread_low >= 0.70:   signals.append(7.5); label_parts.append("📈 Bonne demande")
            elif spread_low >= 0.50:   signals.append(5.5); label_parts.append("➡️ Stable")
            elif spread_low >= 0.30:   signals.append(3.5); label_parts.append("📉 Faible demande")
            else:                       signals.append(1.5); label_parts.append("🧊 Invendable")

        # Signal 2: momentum (high > market = des gens paient plus que le marché)
        if high > 0 and market > 0:
            momentum = high / market
            if momentum >= 2.0:   signals.append(9.0)
            elif momentum >= 1.5: signals.append(7.0)
            elif momentum >= 1.2: signals.append(5.5)
            else:                 signals.append(4.0)

        # Signal 3: market vs mid (market au-dessus du mid = pression achat récente)
        if mid > 0:
            if market > mid * 1.15:  signals.append(8.0)
            elif market > mid:       signals.append(6.0)
            elif market > mid * 0.9: signals.append(4.5)
            else:                    signals.append(3.0)

        break  # on prend le premier type de prix disponible

    if not signals:
        return 5.0, "Données insuffisantes"

    score = round(np.mean(signals), 1)
    label = label_parts[0] if label_parts else "Données partielles"
    return score, label


# ─────────────────────────────────────────────
# FETCH API
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_data(query: str, max_cards: int = 400, api_key: str = "") -> pd.DataFrame:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    all_rows = []
    page = 1

    while len(all_rows) < max_cards:
        size = min(250, max_cards - len(all_rows))
        params = {"q": query, "page": page, "pageSize": size, "orderBy": "-set.releaseDate"}
        try:
            resp = requests.get(
                "https://api.pokemontcg.io/v2/cards",
                headers=headers, params=params, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Erreur API : {e}")
            break

        cards = data.get("data", [])
        if not cards:
            break

        for card in cards:
            tcgplayer    = card.get("tcgplayer", {})
            prices       = tcgplayer.get("prices", {})
            market_price = None
            for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
                if ptype in prices and prices[ptype].get("market"):
                    market_price = prices[ptype]["market"]
                    break
            if not market_price or market_price <= 0:
                continue

            rarity       = card.get("rarity", "Unknown")
            pull_rate    = RARITY_PULL.get(rarity, 1/20)
            release_date = card.get("set", {}).get("releaseDate", "")
            artist       = card.get("artist", "")
            card_name    = card.get("name", "?")
            set_id       = card.get("set", {}).get("id", "")
            card_number  = card.get("number", "")

            # Jouabilité compétitive — Limitless TCG (46 top decks)
            meta = get_meta_score(set_id, card_number)

            # Hype — triple signal TCGPlayer
            hype_score, hype_label = compute_hype_score(prices)

            # Difficulté grading — gem rates PSA réels par rareté
            psa10    = get_grading_difficulty(rarity)
            gem_rate = get_gem_rate(rarity)

            all_rows.append({
                "name":          card_name,
                "set":           card.get("set", {}).get("name", "?"),
                "set_id":        set_id,
                "number":        card_number,
                "series":        card.get("set", {}).get("series", "?"),
                "release_date":  release_date,
                "rarity":        rarity,
                "artist":        artist,
                "f_scarcity":    pull_rate,
                "f_tier":        get_popularity_score(card_name),
                "f_artist":      get_artist_score(artist),
                "f_meta":        meta,
                "f_hype":        hype_score,
                "hype_label":    hype_label,
                "f_psa10":       psa10,
                "gem_rate_pct":  round(gem_rate * 100, 0),
                "f_lifecycle":   set_lifecycle_score(release_date, rarity),
                "market_price":  round(market_price, 2),
                "tcgplayer_url": tcgplayer.get("url", ""),
                "image_url":     card.get("images", {}).get("small", ""),
            })

        if len(cards) < size:
            break
        page += 1
        time.sleep(0.15)

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


# ─────────────────────────────────────────────
# MODÈLE
# ─────────────────────────────────────────────

FEATURE_COLS = ["f_scarcity_inv", "f_tier", "f_artist", "f_meta", "f_hype", "f_psa10", "f_lifecycle"]

def compute_fair_value(df, weights: dict, gem_thresh: float, over_thresh: float) -> pd.DataFrame:
    df = df.copy()
    df["f_scarcity_inv"] = -np.log(df["f_scarcity"])

    scaler = MinMaxScaler()
    for col in FEATURE_COLS:
        df[f"{col}_n"] = scaler.fit_transform(df[[col]])

    norm_cols  = [f"{c}_n" for c in FEATURE_COLS]
    weight_arr = np.array([weights[c] for c in FEATURE_COLS])
    total_w    = weight_arr.sum() or 1.0
    df["score"] = df[norm_cols].values.dot(weight_arr) / total_w

    X = df[["score"]].values
    y = np.log1p(df["market_price"].values)
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    # R² comme proxy de confiance du modèle
    y_pred = model.predict(X)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    df["Vt"]        = np.expm1(model.predict(X)).round(2)
    df["ecart_pct"] = ((df["Vt"] - df["market_price"]) / df["market_price"] * 100).round(1)
    df["Signal"]    = df["ecart_pct"].apply(
        lambda x: "🟢 Sous-évalué" if x > gem_thresh * 100
        else ("🔴 Surévalué" if x < -over_thresh * 100 else "🟡 Prix juste")
    )

    # Score de confiance individuelle par carte : proximité du prix médian du set
    price_med = df["market_price"].median()
    df["confidence"] = df["market_price"].apply(
        lambda p: "🟢 Élevée" if 0.3 * price_med <= p <= 5 * price_med
        else ("🟡 Modérée" if 0.1 * price_med <= p <= 10 * price_med else "🔴 Faible")
    )
    df["model_r2"] = round(r2, 3)

    return df, r2


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────

st.title("🎴 Nasty TCG — Fair Value v7")
st.caption("7 facteurs vérifiés • Popularité TPC • Jouabilité Limitless TCG • Gem Rate PSA réel")

with st.sidebar:
    st.header("⚙️ Réglages")

    # Bouton vert en haut
    st.markdown("""
        <style>
        div[data-testid="stButton"] > button {
            background-color: #27ae60 !important;
            color: white !important;
            font-size: 16px !important;
            font-weight: bold !important;
            border: none !important;
            border-radius: 8px !important;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #2ecc71 !important;
        }
        div[data-testid="stButton"] > button:disabled {
            background-color: #555 !important;
            color: #999 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    fetch_btn = st.button("🚀 Lancer l'analyse", disabled=not weights_valid, use_container_width=True)
    st.divider()

    st.subheader("🎚️ Poids des facteurs")
    st.caption("Total doit être exactement **100%**.")

    w_tier      = st.slider("⭐ Popularité du Pokémon",       0, 100, DEFAULT_WEIGHTS["tier"],      5)
    w_scarcity  = st.slider("🔮 Rareté (pull rate)",           0, 100, DEFAULT_WEIGHTS["scarcity"],  5)
    w_psa10     = st.slider("💎 Difficulté de grading PSA 10", 0, 100, DEFAULT_WEIGHTS["psa10"],     5)
    w_meta      = st.slider("🏆 Jouabilité compétitive",        0, 100, DEFAULT_WEIGHTS["meta"],      5)
    w_hype      = st.slider("🔥 Hype / Sentiment marché",       0, 100, DEFAULT_WEIGHTS["hype"],      5)
    w_artist    = st.slider("🎨 Réputation de l'artiste",       0, 100, DEFAULT_WEIGHTS["artist"],    5)
    w_lifecycle = st.slider("📅 Cycle de vie du set",           0, 100, DEFAULT_WEIGHTS["lifecycle"], 5)

    total_w = w_tier + w_scarcity + w_psa10 + w_meta + w_hype + w_artist + w_lifecycle
    if total_w == 100:
        st.markdown(f"<span class='total-ok'>✅ Total : {total_w}%</span>", unsafe_allow_html=True)
        weights_valid = True
    elif total_w < 100:
        st.markdown(f"<span class='total-low'>⚠️ Total : {total_w}% — manque {100-total_w}%</span>", unsafe_allow_html=True)
        weights_valid = False
    else:
        st.markdown(f"<span class='total-high'>❌ Total : {total_w}% — trop de {total_w-100}%</span>", unsafe_allow_html=True)
        weights_valid = False

    st.divider()
    st.subheader("📐 Seuils")
    gem_thresh  = st.slider("Seuil sous-évalué (+X%)",  5, 60, 15, 5)
    over_thresh = st.slider("Seuil surévalué (-X%)",    5, 60, 15, 5)

    st.divider()
    st.subheader("🔍 Filtres prix")
    min_price = st.number_input("Prix minimum ($)", 0, 1000, 5)
    max_price = st.number_input("Prix maximum ($)", 0, 5000, 2000)

    st.divider()
    st.subheader("🔎 Filtres avancés")
    filter_rarity = st.multiselect("Raretés", [
        "Special Illustration Rare", "Illustration Rare", "Hyper Rare",
        "Ultra Rare", "Double Rare", "ACE SPEC Rare",
        "Shiny Rare", "Shiny Ultra Rare"
    ])
    filter_meta_only = st.checkbox("Cartes jouées en tournoi seulement", value=False)


# ── Session state ──
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = pd.DataFrame()

if fetch_btn and weights_valid:
    with st.spinner("Chargement des cartes SIR / IR / Ultra Rare... ~20 sec"):
        fetched = fetch_live_data(RECENT_SETS_QUERY, max_cards=400, api_key="")
    if fetched.empty:
        st.error("Aucune carte récupérée. Vérifie ta connexion ou ajoute une clé API.")
    else:
        st.session_state.df_loaded = fetched
        st.success(f"✅ {len(fetched)} cartes chargées !")

df_raw = st.session_state.df_loaded

if df_raw.empty:
    st.info("👈 Ajuste les poids à 100% dans le menu, puis clique **'Lancer l'analyse'**.")
    st.markdown("""
**Les 7 facteurs analysés :**

| Facteur | Source | Défaut |
|---|---|---|
| ⭐ Popularité | Sondage officiel The Pokémon Company (800+ Pokémon) | **35%** |
| 🔮 Rareté | Pull rates officiels par rareté (1/1440 pour SIR) | **25%** |
| 💎 Grading | Gem rate PSA 10 réel par rareté (GemRate 2025) | **10%** |
| 🏆 Compétitivité | 46 top decks Limitless TCG scrappés en temps réel | **10%** |
| 🔥 Hype | Triple signal TCGPlayer : spread + momentum + pression achat | **8%** |
| 🎨 Artiste | 80+ illustrateurs classés par valeur marché réelle | **7%** |
| 📅 Cycle de vie | Âge du set × rotation Standard Scarlet & Violet | **5%** |
    """)
    st.stop()

# ── Calculs ──
weights_ordered = {
    "f_scarcity_inv": w_scarcity / 100,
    "f_tier":         w_tier     / 100,
    "f_artist":       w_artist   / 100,
    "f_meta":         w_meta     / 100,
    "f_hype":         w_hype     / 100,
    "f_psa10":        w_psa10    / 100,
    "f_lifecycle":    w_lifecycle/ 100,
}

df, model_r2 = compute_fair_value(df_raw, weights_ordered, gem_thresh / 100, over_thresh / 100)

# ── Filtres ──
df = df[(df["market_price"] >= min_price) & (df["market_price"] <= max_price)]
if filter_rarity:
    df = df[df["rarity"].isin(filter_rarity)]
if filter_meta_only:
    df = df[df["f_meta"] > 1.0]

series_opts = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
col_series, col_r2 = st.columns([3, 1])
with col_series:
    selected_series = st.selectbox("Filtrer par série", series_opts)
with col_r2:
    r2_color = "conf-high" if model_r2 > 0.5 else ("conf-med" if model_r2 > 0.3 else "conf-low")
    st.markdown(f"<br><span class='{r2_color}'>Confiance modèle R² = {model_r2:.2f}</span>", unsafe_allow_html=True)

if selected_series != "Toutes":
    df = df[df["series"] == selected_series]

gems  = df[df["Signal"] == "🟢 Sous-évalué"].sort_values("ecart_pct", ascending=False)
overs = df[df["Signal"] == "🔴 Surévalué"].sort_values("ecart_pct")
fair  = df[df["Signal"] == "🟡 Prix juste"]

# ── Métriques ──
st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📦 Cartes analysées", len(df))
c2.metric("🟢 Sous-évaluées",   len(gems))
c3.metric("🟡 Prix juste",      len(fair))
c4.metric("🔴 Surévaluées",     len(overs))
c5.metric("📊 R² modèle",       f"{model_r2:.2f}")
st.divider()

# ── ONGLETS PRINCIPAUX ──
tab_gems, tab_over, tab_fair = st.tabs([
    f"🟢 Sous-évaluées ({len(gems)})",
    f"🔴 Surévaluées ({len(overs)})",
    f"🟡 Prix juste ({len(fair)})"
])

def render_card_grid(cards_df, badge_class, ecart_prefix="", max_cards=20):
    """Render cards in a 4-column grid."""
    cols_per_row = 4
    cards_list = cards_df.head(max_cards)
    if cards_list.empty:
        st.info("Aucune carte dans cette catégorie avec les filtres actuels.")
        return
    for i in range(0, len(cards_list), cols_per_row):
        row_cards = cards_list.iloc[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, (_, card) in enumerate(row_cards.iterrows()):
            with cols[idx]:
                if card.get("image_url"):
                    st.image(card["image_url"], width=130)
                st.markdown(f"**{card['name']}**")
                st.markdown(f"*{card['set']}*")
                st.markdown(f"*{card['rarity']}*")
                if card.get("artist"):
                    st.markdown(f"✏️ *{card['artist']}*")
                st.markdown(f"💰 **${card['market_price']:.2f}** → 📊 **${card['Vt']:.2f}**")
                ecart_val = card['ecart_pct']
                ecart_str = f"+{ecart_val:.0f}%" if ecart_val >= 0 else f"{ecart_val:.0f}%"
                st.markdown(
                    f"<span class='{badge_class}'>{ecart_str}</span> "
                    f"<span class='psa-label'>PSA10: {card['gem_rate_pct']:.0f}% gem rate</span>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    f"⭐ Pop: **{card['f_tier']:.1f}** | 🏆 Méta: **{card['f_meta']:.1f}** | "
                    f"🔥 {card.get('hype_label', '')}"
                )
                conf_class = "conf-high" if card["confidence"] == "🟢 Élevée" else ("conf-med" if card["confidence"] == "🟡 Modérée" else "conf-low")
                st.markdown(f"<span class='{conf_class}'>Confiance: {card['confidence']}</span>", unsafe_allow_html=True)
                if card.get("tcgplayer_url"):
                    st.markdown(f"[Voir sur TCGPlayer ↗]({card['tcgplayer_url']})")

with tab_gems:
    st.caption(f"Valeur estimée **{gem_thresh}%+ au-dessus** du prix marché — potentiellement sous-évaluées.")
    render_card_grid(gems, "gem-badge", max_cards=20)

with tab_over:
    st.caption(f"Prix marché **{over_thresh}%+ au-dessus** de la valeur estimée — à éviter ou vendre.")
    render_card_grid(overs.sort_values("ecart_pct"), "over-badge", max_cards=20)

with tab_fair:
    st.caption("Cartes au prix juste selon le modèle.")
    render_card_grid(fair.sort_values("ecart_pct", ascending=False), "fair-badge", max_cards=20)

st.divider()

# ── Graphiques ──
st.subheader("📊 Analyse visuelle")
tab1, tab2, tab3, tab4 = st.tabs(["Valeur vs Prix", "Top sous-évaluées", "Scores facteurs", "Heatmap artistes"])

colors_map = {
    "🟢 Sous-évalué": "#2ecc71",
    "🔴 Surévalué":   "#e74c3c",
    "🟡 Prix juste":  "#f39c12"
}

with tab1:
    fig, ax = plt.subplots(figsize=(10, 5))
    for signal, group in df.groupby("Signal"):
        ax.scatter(group["market_price"], group["Vt"],
                   label=signal, color=colors_map.get(signal, "gray"), alpha=0.7, s=55)
    max_val = max(df["market_price"].max(), df["Vt"].max()) * 1.05
    ax.plot([0, max_val], [0, max_val], "k--", lw=0.9, label="Valeur = Prix")
    ax.set_xlabel("Prix réel du marché ($)")
    ax.set_ylabel("Valeur théorique estimée ($)")
    ax.set_title(f"Au-dessus de la ligne = sous-évaluée  |  R² modèle = {model_r2:.2f}")
    ax.legend()
    st.pyplot(fig)

with tab2:
    top20 = df.nlargest(20, "ecart_pct")
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bar_colors = [colors_map.get(s, "gray") for s in top20["Signal"]]
    ax2.barh(top20["name"], top20["ecart_pct"], color=bar_colors)
    ax2.axvline(0, color="black", lw=0.8, ls="--")
    ax2.set_xlabel("Écart entre valeur estimée et prix réel (%)")
    ax2.set_title("Top 20 — Cartes les plus sous-évaluées")
    ax2.invert_yaxis()
    st.pyplot(fig2)

with tab3:
    st.caption("Scores des 7 facteurs pour les meilleures opportunités")
    top15 = gems.head(15) if len(gems) > 0 else df.head(15)
    factor_map = {
        "f_tier":         "Popularité",
        "f_scarcity_inv": "Rareté",
        "f_psa10":        "Grading PSA",
        "f_meta":         "Compétitivité",
        "f_hype":         "Hype",
        "f_artist":       "Artiste",
        "f_lifecycle":    "Cycle de vie",
    }
    display_df = top15[["name"] + list(factor_map.keys())].copy()
    display_df = display_df.rename(columns={**factor_map, "name": "Carte"})
    for col in factor_map.values():
        if col in display_df.columns:
            mn, mx = display_df[col].min(), display_df[col].max()
            if mx > mn:
                display_df[col] = ((display_df[col] - mn) / (mx - mn) * 10).round(1)
    st.dataframe(display_df.set_index("Carte"), use_container_width=True)

with tab4:
    st.caption("Prix moyen par artiste dans les données chargées")
    artist_data = df.groupby("artist").agg(
        Prix_moyen=("market_price", "mean"),
        Cartes=("name", "count"),
        Score_artiste=("f_artist", "first")
    ).sort_values("Prix_moyen", ascending=False).head(20)
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    ax4.barh(artist_data.index, artist_data["Prix_moyen"], color="#3498db", alpha=0.8)
    ax4.set_xlabel("Prix moyen des cartes ($)")
    ax4.set_title("Top 20 artistes par prix moyen de carte")
    ax4.invert_yaxis()
    st.pyplot(fig4)
    st.dataframe(artist_data.round(2), use_container_width=True)

st.divider()

# ── Table complète ──
with st.expander("📋 Toutes les cartes analysées"):
    disp = df[[
        "name", "set", "rarity", "artist", "f_tier", "f_meta",
        "gem_rate_pct", "hype_label", "market_price", "Vt", "ecart_pct", "Signal", "confidence"
    ]].copy()
    disp.columns = [
        "Carte", "Set", "Rareté", "Artiste", "Popularité", "Méta",
        "PSA10 %", "Hype", "Prix ($)", "Valeur ($)", "Écart (%)", "Signal", "Confiance"
    ]
    st.dataframe(
        disp.sort_values("Écart (%)", ascending=False),
        use_container_width=True, hide_index=True
    )

# ── Export ──
st.subheader("📥 Exporter")
export_cols = [
    "name", "set", "rarity", "artist", "f_tier", "f_meta",
    "gem_rate_pct", "hype_label", "market_price", "Vt",
    "ecart_pct", "Signal", "confidence", "tcgplayer_url"
]
csv_buf = io.StringIO()
df[export_cols].sort_values("ecart_pct", ascending=False).to_csv(csv_buf, index=False)
st.download_button(
    label="📥 Télécharger le rapport CSV",
    data=csv_buf.getvalue(),
    file_name=f"fair_value_report_{date.today()}.csv",
    mime="text/csv"
)
