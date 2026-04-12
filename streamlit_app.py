"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (v8)
 UI dark cards, dedup, infos clés condensées
=============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import Ridge
import io, time, requests
from datetime import date

st.set_page_config(page_title="Nasty TCG — Fair Value", page_icon="🎴", layout="wide")

st.markdown("""
<style>
/* ── Card UI ─────────────────────────────────────────── */
.tcg-card {
    background: #1a1a2e;
    border-radius: 14px;
    padding: 14px 12px 16px 12px;
    margin-bottom: 10px;
    border: 1px solid #2a2a4a;
    transition: border 0.2s;
}
.tcg-card:hover { border: 1px solid #4a90e2; }

.card-name {
    font-size: 15px; font-weight: 700;
    color: #ffffff; margin: 8px 0 2px 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.card-set   { font-size: 11px; color: #8888aa; margin-bottom: 6px; }
.card-rarity { font-size: 11px; color: #6677bb; margin-bottom: 8px; }

.price-row {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 6px;
}
.price-market { font-size: 13px; color: #aaaacc; }
.price-fair   { font-size: 16px; font-weight: 700; color: #4af0c4; }

.badge-gem  {
    display: inline-block; background: #0d3d25;
    color: #2ecc71; font-size: 13px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
}
.badge-over {
    display: inline-block; background: #3d0d0d;
    color: #e74c3c; font-size: 13px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
}
.badge-fair {
    display: inline-block; background: #2d2500;
    color: #f39c12; font-size: 13px; font-weight: 700;
    padding: 3px 10px; border-radius: 20px; margin-bottom: 8px;
}

.meta-row {
    font-size: 11px; color: #7788aa;
    display: flex; flex-wrap: wrap; gap: 6px;
    margin-bottom: 6px;
}
.meta-pill {
    background: #22223a; border-radius: 8px;
    padding: 2px 7px; white-space: nowrap;
}
.psa-row  { font-size: 11px; color: #9966cc; margin-bottom: 6px; }
.artist-row { font-size: 11px; color: #556677; margin-bottom: 8px; }

.tcg-link a {
    font-size: 12px; color: #4a90e2;
    text-decoration: none;
}
.tcg-link a:hover { text-decoration: underline; }

/* ── Sidebar button ──────────────────────────────────── */
div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #27ae60, #2ecc71) !important;
    color: white !important; font-size: 15px !important;
    font-weight: 700 !important; border: none !important;
    border-radius: 10px !important; padding: 10px !important;
}
div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #2ecc71, #1abc9c) !important;
}
div[data-testid="stButton"] > button:disabled {
    background: #333 !important; color: #666 !important;
}
.total-ok   { color: #2ecc71; font-size: 18px; font-weight: bold; }
.total-low  { color: #e67e22; font-size: 18px; font-weight: bold; }
.total-high { color: #e74c3c; font-size: 18px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

from pokemon_popularity import get_popularity_score
from meta_scores import get_meta_score
from grading_ratio import get_grading_difficulty, get_gem_rate

# ─── Constantes ───────────────────────────────────────────────
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

ARTIST_SCORES = {
    "mika pikazo": 10.0, "tetsu kayama": 9.5, "akira komayama": 9.5,
    "ryota murayama": 9.0, "nagomibana": 9.0, "sowsow": 8.8,
    "5ban graphics": 8.5, "sanosuke sakuma": 8.5, "atsushi furusawa": 8.0,
    "yuka morii": 8.0, "ryo ueda": 7.8, "kiichiro": 7.5,
    "yuu nishida": 7.5, "anesaki dynamic": 7.5, "kagemaru himeno": 7.5,
    "tomokazu komiya": 7.5, "hitoshi ariga": 7.5, "eri yamaki": 7.0,
    "kawayoo": 7.0, "ayaka yoshida": 7.0, "teeziro": 7.0,
    "keiichiro ito": 7.0, "yusuke ohmura": 7.0, "atsuko nishida": 7.5,
    "mitsuhiro arita": 7.0, "shigenori negishi": 6.8, "suwama ichiro": 6.5,
    "kouki saitou": 6.5, "mizue": 6.5, "aya kusube": 6.5,
    "tomoya kitakaze": 6.5, "0313": 6.5, "daisuke ito": 6.5,
    "narumi sato": 6.5, "shizurow": 6.5, "luncheon": 6.5,
    "uninori": 6.0, "shibuzoh": 6.0, "hasuno": 6.0,
    "kodama": 6.0, "nekoramune": 6.0, "tika matsuno": 6.0,
    "gossan": 6.0, "makoto iguchi": 6.0, "yoshinobu saito": 6.0,
    "naoyo kimura": 6.5, "keiko fukuyama": 6.0, "yuri ex": 6.5,
    "satoshi nakai": 6.0, "hajime kusajima": 6.0, "hitomi yoshida": 6.0,
    "studio bora": 6.0, "chihiro mori": 6.0, "hiromichi sugiyama": 5.5,
    "kirisaki": 5.5, "akira egawa": 5.5, "takumi akabane": 5.0,
    "ken sugimori": 6.0, "motofumi fujiwara": 5.0, "yumi takahara": 5.0,
    "aky cg works": 6.5,
}

def get_artist_score(artist: str) -> float:
    a = artist.lower().strip()
    if a in ARTIST_SCORES: return ARTIST_SCORES[a]
    for name, score in ARTIST_SCORES.items():
        if name in a or a in name: return score
    return 4.5

def set_lifecycle_score(release_date_str: str) -> float:
    try:
        parts = release_date_str.split("/")
        rd = date(int(parts[0]), int(parts[1]), int(parts[2]))
        days = (date.today() - rd).days
        if days < 60:   return 7.0
        if days < 120:  return 9.0
        if days < 270:  return 8.0
        if days < 450:  return 6.5
        if days < 600:  return 5.0
        if days < 730:  return 3.5
        if days < 1095: return 2.5
        return 2.0
    except: return 5.0

def compute_hype_score(prices: dict) -> tuple:
    signals = []
    label = "Données insuffisantes"
    for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
        if ptype not in prices: continue
        p = prices[ptype]
        low, mid, high, market = (p.get(k, 0) or 0 for k in ["low","mid","high","market"])
        if market <= 0: continue
        if low > 0:
            ratio = low / market
            if ratio >= 0.85:   signals.append(9.5); label = "🔥 Très demandée"
            elif ratio >= 0.70: signals.append(7.5); label = "📈 Bonne demande"
            elif ratio >= 0.50: signals.append(5.5); label = "➡️ Stable"
            elif ratio >= 0.30: signals.append(3.5); label = "📉 Faible demande"
            else:                signals.append(1.5); label = "🧊 Peu d'intérêt"
        if high > 0:
            m = high / market
            signals.append(9.0 if m>=2.0 else 7.0 if m>=1.5 else 5.5 if m>=1.2 else 4.0)
        if mid > 0:
            signals.append(8.0 if market > mid*1.15 else 6.0 if market > mid else 4.5 if market > mid*0.9 else 3.0)
        break
    return (round(np.mean(signals), 1) if signals else 5.0, label)

RECENT_SETS_QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare" '
    'OR rarity:"ACE SPEC Rare" OR rarity:"Shiny Rare" OR rarity:"Shiny Ultra Rare")'
)

DEFAULT_WEIGHTS = {"tier":35,"scarcity":25,"psa10":10,"meta":10,"hype":8,"artist":7,"lifecycle":5}
FEATURE_COLS = ["f_scarcity_inv","f_tier","f_artist","f_meta","f_hype","f_psa10","f_lifecycle"]

# ─── Fetch ────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_data(query: str, max_cards: int = 400) -> pd.DataFrame:
    all_rows = []
    seen_ids = set()
    page = 1
    while len(all_rows) < max_cards:
        size = min(250, max_cards - len(all_rows))
        params = {"q": query, "page": page, "pageSize": size, "orderBy": "-set.releaseDate"}
        try:
            resp = requests.get("https://api.pokemontcg.io/v2/cards",
                                params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"Erreur API : {e}"); break

        cards = data.get("data", [])
        if not cards: break

        for card in cards:
            card_id = card.get("id", "")
            if card_id in seen_ids: continue   # ← dédoublonnage
            seen_ids.add(card_id)

            tcgplayer = card.get("tcgplayer", {})
            prices    = tcgplayer.get("prices", {})
            market_price = None
            for ptype in ["holofoil","reverseHolofoil","normal","1stEditionHolofoil"]:
                if ptype in prices and prices[ptype].get("market"):
                    market_price = prices[ptype]["market"]; break
            if not market_price or market_price <= 0: continue

            rarity      = card.get("rarity", "Unknown")
            artist      = card.get("artist", "")
            card_name   = card.get("name", "?")
            set_id      = card.get("set", {}).get("id", "")
            card_number = card.get("number", "")
            release_date= card.get("set", {}).get("releaseDate", "")

            hype_score, hype_label = compute_hype_score(prices)

            all_rows.append({
                "id":           card_id,
                "name":         card_name,
                "set":          card.get("set", {}).get("name", "?"),
                "series":       card.get("set", {}).get("series", "?"),
                "release_date": release_date,
                "rarity":       rarity,
                "artist":       artist,
                "f_scarcity":   RARITY_PULL.get(rarity, 1/20),
                "f_tier":       get_popularity_score(card_name),
                "f_artist":     get_artist_score(artist),
                "f_meta":       get_meta_score(set_id, card_number),
                "f_hype":       hype_score,
                "hype_label":   hype_label,
                "f_psa10":      get_grading_difficulty(rarity),
                "gem_rate_pct": round(get_gem_rate(rarity) * 100, 0),
                "f_lifecycle":  set_lifecycle_score(release_date),
                "market_price": round(market_price, 2),
                "tcgplayer_url":tcgplayer.get("url", ""),
                "image_url":    card.get("images", {}).get("small", ""),
            })

        if len(cards) < size: break
        page += 1
        time.sleep(0.15)

    df = pd.DataFrame(all_rows) if all_rows else pd.DataFrame()
    # dedup supplémentaire sur nom+set au cas où
    if not df.empty:
        df = df.drop_duplicates(subset=["name", "set"])
    return df

# ─── Modèle ───────────────────────────────────────────────────
def compute_fair_value(df, weights, gem_thresh, over_thresh):
    df = df.copy()
    df["f_scarcity_inv"] = -np.log(df["f_scarcity"])
    scaler = MinMaxScaler()
    for col in FEATURE_COLS:
        df[f"{col}_n"] = scaler.fit_transform(df[[col]])
    norm_cols  = [f"{c}_n" for c in FEATURE_COLS]
    weight_arr = np.array([weights[c] for c in FEATURE_COLS])
    df["score"] = df[norm_cols].values.dot(weight_arr) / (weight_arr.sum() or 1)

    X, y = df[["score"]].values, np.log1p(df["market_price"].values)
    model = Ridge(alpha=1.0); model.fit(X, y)
    y_pred = model.predict(X)
    ss_res = np.sum((y - y_pred)**2); ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0

    df["Vt"]        = np.expm1(y_pred).round(2)
    df["ecart_pct"] = ((df["Vt"] - df["market_price"]) / df["market_price"] * 100).round(1)
    df["Signal"]    = df["ecart_pct"].apply(
        lambda x: "gem" if x > gem_thresh*100 else ("over" if x < -over_thresh*100 else "fair")
    )
    price_med = df["market_price"].median()
    df["confidence"] = df["market_price"].apply(
        lambda p: "Élevée" if 0.3*price_med <= p <= 5*price_med
        else ("Modérée" if 0.1*price_med <= p <= 10*price_med else "Faible")
    )
    df["model_r2"] = round(r2, 3)
    return df, r2

# ─── Render card ──────────────────────────────────────────────
def render_card_html(card, badge_class):
    ecart = card["ecart_pct"]
    ecart_str = f"+{ecart:.0f}%" if ecart >= 0 else f"{ecart:.0f}%"
    conf_colors = {"Élevée": "#2ecc71", "Modérée": "#f39c12", "Faible": "#e74c3c"}
    conf_col = conf_colors.get(card["confidence"], "#aaa")
    hype = card.get("hype_label", "")
    tcg_link = f'<div class="tcg-link"><a href="{card["tcgplayer_url"]}" target="_blank">Voir sur TCGPlayer ↗</a></div>' if card.get("tcgplayer_url") else ""

    html = f"""
    <div class="tcg-card">
      <div class="card-name" title="{card['name']}">{card['name']}</div>
      <div class="card-set">{card['set']}</div>
      <div class="card-rarity">{card['rarity']}</div>
      <div class="artist-row">✏️ {card['artist']}</div>
      <div class="price-row">
        <span class="price-market">${card['market_price']:.2f}</span>
        <span class="price-fair">${card['Vt']:.2f} FV</span>
      </div>
      <div><span class="{badge_class}">{ecart_str}</span>
      <span class="psa-row"> &nbsp;PSA10: {card['gem_rate_pct']:.0f}% gem</span></div>
      <div class="meta-row">
        <span class="meta-pill">⭐ {card['f_tier']:.1f}</span>
        <span class="meta-pill">🏆 {card['f_meta']:.1f}</span>
        <span class="meta-pill">{hype}</span>
      </div>
      <div style="font-size:11px; color:{conf_col}; margin-bottom:6px;">● Confiance {card['confidence']}</div>
      {tcg_link}
    </div>"""
    return html

def render_grid(cards_df, badge_class, max_cards=24):
    cards_df = cards_df.head(max_cards)
    if cards_df.empty:
        st.info("Aucune carte dans cette catégorie.")
        return
    cols_per_row = 4
    for i in range(0, len(cards_df), cols_per_row):
        row = cards_df.iloc[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, (_, card) in enumerate(row.iterrows()):
            with cols[idx]:
                if card.get("image_url"):
                    st.image(card["image_url"], use_container_width=True)
                st.markdown(render_card_html(card, badge_class), unsafe_allow_html=True)

# ─── UI ───────────────────────────────────────────────────────
st.title("🎴 Nasty TCG — Fair Value")
st.caption("7 facteurs • Popularité TPC • Limitless TCG • Gem Rate PSA réel")

with st.sidebar:
    st.header("⚙️ Réglages")

    st.subheader("🎚️ Poids des facteurs")
    st.caption("Total doit être exactement **100%**.")

    w_tier      = st.slider("⭐ Popularité",         0, 100, DEFAULT_WEIGHTS["tier"],      5)
    w_scarcity  = st.slider("🔮 Rareté (pull rate)", 0, 100, DEFAULT_WEIGHTS["scarcity"],  5)
    w_psa10     = st.slider("💎 Grading PSA 10",     0, 100, DEFAULT_WEIGHTS["psa10"],     5)
    w_meta      = st.slider("🏆 Compétitivité",       0, 100, DEFAULT_WEIGHTS["meta"],      5)
    w_hype      = st.slider("🔥 Hype marché",         0, 100, DEFAULT_WEIGHTS["hype"],      5)
    w_artist    = st.slider("🎨 Artiste",             0, 100, DEFAULT_WEIGHTS["artist"],    5)
    w_lifecycle = st.slider("📅 Cycle de vie",        0, 100, DEFAULT_WEIGHTS["lifecycle"], 5)

    total_w = w_tier + w_scarcity + w_psa10 + w_meta + w_hype + w_artist + w_lifecycle
    if total_w == 100:
        st.markdown(f"<span class='total-ok'>✅ {total_w}%</span>", unsafe_allow_html=True)
        weights_valid = True
    elif total_w < 100:
        st.markdown(f"<span class='total-low'>⚠️ {total_w}% — manque {100-total_w}%</span>", unsafe_allow_html=True)
        weights_valid = False
    else:
        st.markdown(f"<span class='total-high'>❌ {total_w}% — trop de {total_w-100}%</span>", unsafe_allow_html=True)
        weights_valid = False

    st.divider()
    fetch_btn = st.button("🚀 Lancer l'analyse", disabled=not weights_valid, use_container_width=True)

    st.divider()
    st.subheader("📐 Seuils")
    st.caption("Écart minimum pour classer une carte comme sous/surévaluée.")
    gem_thresh  = st.slider("🟢 Sous-évalué si Vt dépasse le prix de +X%", 5, 60, 15, 5)
    over_thresh = st.slider("🔴 Surévalué si prix dépasse Vt de +X%",      5, 60, 15, 5)

    st.divider()
    st.subheader("🔍 Filtres")
    min_price = st.number_input("Prix min ($)", 0, 1000, 5)
    max_price = st.number_input("Prix max ($)", 0, 5000, 2000)
    filter_rarity = st.multiselect("Raretés", [
        "Special Illustration Rare","Illustration Rare","Hyper Rare",
        "Ultra Rare","Double Rare","ACE SPEC Rare","Shiny Rare","Shiny Ultra Rare"
    ])
    filter_meta_only = st.checkbox("Tournoi seulement", value=False)

# ── Session state ──
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = pd.DataFrame()

if fetch_btn and weights_valid:
    with st.spinner("Chargement des cartes... ~20 sec"):
        fetched = fetch_live_data(RECENT_SETS_QUERY, max_cards=400)
    if fetched.empty:
        st.error("Aucune carte. Vérifie ta connexion.")
    else:
        st.session_state.df_loaded = fetched
        st.success(f"✅ {len(fetched)} cartes chargées !")

df_raw = st.session_state.df_loaded

if df_raw.empty:
    st.info("👈 Ajuste les poids à 100% puis clique **Lancer l'analyse**.")
    st.markdown("""
| Facteur | Source | Défaut |
|---|---|---|
| ⭐ Popularité | Sondage officiel TPC | **35%** |
| 🔮 Rareté | Pull rates officiels | **25%** |
| 💎 Grading | Gem rate PSA réel (GemRate 2025) | **10%** |
| 🏆 Compétitivité | Limitless TCG top 46 decks | **10%** |
| 🔥 Hype | Triple signal TCGPlayer | **8%** |
| 🎨 Artiste | 80+ illustrateurs classés marché | **7%** |
| 📅 Cycle de vie | Âge set × rotation Standard | **5%** |
    """)
    st.stop()

# ── Calculs ──
weights_ordered = {
    "f_scarcity_inv": w_scarcity/100, "f_tier": w_tier/100,
    "f_artist": w_artist/100, "f_meta": w_meta/100,
    "f_hype": w_hype/100, "f_psa10": w_psa10/100, "f_lifecycle": w_lifecycle/100,
}
df, model_r2 = compute_fair_value(df_raw, weights_ordered, gem_thresh/100, over_thresh/100)

# ── Filtres ──
df = df[(df["market_price"] >= min_price) & (df["market_price"] <= max_price)]
if filter_rarity: df = df[df["rarity"].isin(filter_rarity)]
if filter_meta_only: df = df[df["f_meta"] > 1.0]

series_opts = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
col_s, col_r = st.columns([3,1])
with col_s:
    selected_series = st.selectbox("Série", series_opts)
with col_r:
    r2_col = "#2ecc71" if model_r2 > 0.5 else ("#f39c12" if model_r2 > 0.3 else "#e74c3c")
    st.markdown(f'<br><span style="color:{r2_col}; font-size:13px;">R² = {model_r2:.2f}</span>', unsafe_allow_html=True)

if selected_series != "Toutes":
    df = df[df["series"] == selected_series]

gems  = df[df["Signal"] == "gem"].sort_values("ecart_pct", ascending=False)
overs = df[df["Signal"] == "over"].sort_values("ecart_pct")
fair  = df[df["Signal"] == "fair"].sort_values("ecart_pct", ascending=False)

# ── Métriques ──
st.divider()
c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("📦 Analysées", len(df))
c2.metric("🟢 Sous-évaluées", len(gems))
c3.metric("🟡 Prix juste", len(fair))
c4.metric("🔴 Surévaluées", len(overs))
c5.metric("R²", f"{model_r2:.2f}")
st.divider()

# ── Onglets principaux ──
tab_gems, tab_over, tab_fair, tab_charts = st.tabs([
    f"🟢 Sous-évaluées ({len(gems)})",
    f"🔴 Surévaluées ({len(overs)})",
    f"🟡 Prix juste ({len(fair)})",
    "📊 Graphiques",
])

with tab_gems:
    st.caption(f"Valeur estimée **{gem_thresh}%+** au-dessus du prix marché.")
    render_grid(gems, "badge-gem")

with tab_over:
    st.caption(f"Prix marché **{over_thresh}%+** au-dessus de la valeur estimée.")
    render_grid(overs, "badge-over")

with tab_fair:
    st.caption("Cartes au prix juste selon le modèle.")
    render_grid(fair, "badge-fair")

with tab_charts:
    colors_map = {"gem":"#2ecc71","over":"#e74c3c","fair":"#f39c12"}
    t1, t2 = st.tabs(["Valeur vs Prix", "Top sous-évaluées"])

    with t1:
        fig, ax = plt.subplots(figsize=(10,5), facecolor="#0e0e1a")
        ax.set_facecolor("#0e0e1a")
        for sig, grp in df.groupby("Signal"):
            ax.scatter(grp["market_price"], grp["Vt"],
                       color=colors_map.get(sig,"gray"), alpha=0.7, s=50, label=sig)
        mv = max(df["market_price"].max(), df["Vt"].max()) * 1.05
        ax.plot([0,mv],[0,mv],"w--",lw=0.8,label="Vt = Prix")
        ax.set_xlabel("Prix marché ($)", color="#aaa")
        ax.set_ylabel("Fair Value ($)", color="#aaa")
        ax.tick_params(colors="#aaa")
        ax.legend(facecolor="#1a1a2e", labelcolor="white")
        ax.set_title(f"Fair Value vs Prix  |  R² = {model_r2:.2f}", color="white")
        st.pyplot(fig)

    with t2:
        top20 = df.nlargest(20,"ecart_pct")
        fig2, ax2 = plt.subplots(figsize=(10,6), facecolor="#0e0e1a")
        ax2.set_facecolor("#0e0e1a")
        ax2.barh(top20["name"], top20["ecart_pct"],
                 color=[colors_map.get(s,"gray") for s in top20["Signal"]])
        ax2.axvline(0,color="white",lw=0.7,ls="--")
        ax2.set_xlabel("Écart (%)", color="#aaa")
        ax2.tick_params(colors="#aaa")
        ax2.invert_yaxis()
        ax2.set_title("Top 20 sous-évaluées", color="white")
        st.pyplot(fig2)

st.divider()
# ── Table & Export ──
with st.expander("📋 Toutes les cartes"):
    disp = df[["name","set","rarity","artist","f_tier","f_meta","gem_rate_pct",
               "hype_label","market_price","Vt","ecart_pct","Signal","confidence"]].copy()
    disp.columns = ["Carte","Set","Rareté","Artiste","Pop","Méta","PSA10%",
                    "Hype","Prix($)","FV($)","Écart(%)","Signal","Confiance"]
    st.dataframe(disp.sort_values("Écart(%)",ascending=False), use_container_width=True, hide_index=True)

csv_buf = io.StringIO()
df.sort_values("ecart_pct",ascending=False).to_csv(csv_buf, index=False)
st.download_button("📥 Exporter CSV", csv_buf.getvalue(),
                   f"fair_value_{date.today()}.csv", "text/csv")
