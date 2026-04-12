"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (v2)
=============================================================
Lance avec : streamlit run streamlit_app.py
=============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as st_plt
from sklearn.preprocessing import MinMaxScaler
import io
import time
import requests

# ─── Config page ───
st.set_page_config(
    page_title="Nasty TCG — Fair Value",
    page_icon="🎴",
    layout="wide"
)

st.markdown("""
<style>
    .card-box {
        background: #1a1a2e;
        border-radius: 12px;
        padding: 12px;
        text-align: center;
        margin-bottom: 8px;
    }
    .gem-badge { color: #2ecc71; font-size: 18px; font-weight: bold; }
    .over-badge { color: #e74c3c; font-size: 18px; font-weight: bold; }
    .fair-badge { color: #f39c12; font-size: 18px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 2rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

RARITY_METADATA = {
    "Special Illustration Rare": (1/1440, 10),
    "Hyper Rare":                 (1/360,  9),
    "Illustration Rare":          (1/144,  8),
    "Ultra Rare":                 (1/72,   7),
    "Double Rare":                (1/48,   6),
    "Rare Holo VMAX":             (1/36,   7),
    "Rare Holo VSTAR":            (1/36,   7),
    "Rare Holo V":                (1/24,   6),
    "Rare Holo EX":               (1/24,   6),
    "Rare Holo":                  (1/12,   5),
    "Rare":                       (1/10,   4),
}

TIER_MAP = {
    10: ["charizard", "umbreon", "mewtwo", "rayquaza", "lugia"],
    9:  ["pikachu", "eevee", "mew", "gengar", "snorlax", "espeon", "vaporeon"],
    8:  ["jolteon", "flareon", "sylveon", "gardevoir", "blastoise", "venusaur"],
    7:  ["greninja", "lucario", "togekiss", "alakazam", "dragonite"],
    6:  ["gyarados", "arcanine", "ninetales", "absol", "flygon"],
}

# Séries récentes Scarlet & Violet + Sword & Shield (2022-2025)
RECENT_SETS_QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare")'
)

def get_tier(name):
    for tier, names in TIER_MAP.items():
        if any(n in name.lower() for n in names):
            return tier
    return 3


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
            resp = requests.get("https://api.pokemontcg.io/v2/cards", headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            st.error(f"❌ Erreur API : {e}")
            break

        cards = data.get("data", [])
        if not cards:
            break

        for card in cards:
            tcgplayer = card.get("tcgplayer", {})
            prices    = tcgplayer.get("prices", {})
            market_price = None
            for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
                if ptype in prices and prices[ptype].get("market"):
                    market_price = prices[ptype]["market"]
                    break
            if not market_price or market_price <= 0:
                continue

            rarity = card.get("rarity", "Unknown")
            pull_rate, art_base = RARITY_METADATA.get(rarity, (1/20, 4))
            legalities = card.get("legalities", {})
            meta = 7.0 if legalities.get("standard") == "Legal" else (4.0 if legalities.get("expanded") == "Legal" else 1.0)
            psa10 = min(10, max(0, round(np.log1p(market_price) / np.log1p(500) * 8, 1)))
            hype  = min(10, max(0, round(np.log1p(market_price) / np.log1p(500) * 10, 1)))

            all_rows.append({
                "name":               card.get("name", "?"),
                "set":                card.get("set", {}).get("name", "?"),
                "series":             card.get("set", {}).get("series", "?"),
                "release_date":       card.get("set", {}).get("releaseDate", ""),
                "rarity":             rarity,
                "pull_rate_per_pack": pull_rate,
                "character_tier":     get_tier(card.get("name", "")),
                "art_score":          float(art_base),
                "meta_relevance":     meta,
                "psa10_ratio":        psa10,
                "hype_score":         hype,
                "market_price":       round(market_price, 2),
                "tcgplayer_url":      tcgplayer.get("url", ""),
                "image_url":          card.get("images", {}).get("small", ""),
            })

        if len(cards) < size:
            break
        page += 1
        time.sleep(0.15)

    return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()


# ─────────────────────────────────────────────
# MODÈLE
# ─────────────────────────────────────────────

def compute_scarcity(df):
    df = df.copy()
    df["scarcity_raw"] = -np.log(df["pull_rate_per_pack"])
    scaler = MinMaxScaler(feature_range=(0, 100))
    df["scarcity"] = scaler.fit_transform(df[["scarcity_raw"]])
    return df

def compute_fair_value(df, w1, w2, w3, w4, w5, w6, price_multiplier, gem_thresh, over_thresh):
    df = df.copy()
    scaler = MinMaxScaler(feature_range=(0, 100))
    for col in ["character_tier", "art_score", "meta_relevance", "psa10_ratio", "hype_score"]:
        df[f"{col}_norm"] = scaler.fit_transform(df[[col]])

    df["Vt"] = (
        df["scarcity"]            * w1 +
        df["character_tier_norm"] * w2 +
        df["art_score_norm"]      * w3 +
        df["meta_relevance_norm"] * w4 +
        df["psa10_ratio_norm"]    * w5 +
        df["hype_score_norm"]     * w6
    ) * price_multiplier

    df["Alpha"] = (df["Vt"] - df["market_price"]) / df["market_price"]
    df["Alpha_pct"] = (df["Alpha"] * 100).round(1)
    df["Signal"] = df["Alpha"].apply(
        lambda x: "🟢 Sous-évalué" if x > gem_thresh
        else ("🔴 Surévalué" if x < over_thresh else "🟡 Prix juste")
    )
    df["Ecart_pct"] = df["Alpha_pct"].apply(
        lambda x: f"+{x:.0f}% sous le prix réel" if x > 0 else f"{x:.0f}% au-dessus du prix réel"
    )
    return df


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────

st.title("🎴 Nasty TCG — Détecteur de cartes sous-évaluées")
st.caption("Compare le prix réel du marché à la valeur théorique de chaque carte. Trouve les bonnes affaires.")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Réglages")

    st.subheader("📡 Données")
    api_key = st.text_input("Clé API PokéTCG (optionnel)", type="password",
                             help="Sans clé : 1 000 requêtes/jour. Avec clé gratuite : 20 000/jour → pokemontcg.io/dev")
    fetch_btn = st.button("🔄 Charger toutes les cartes récentes", type="primary",
                           help="Fetch ~300-500 cartes SIR/IR/Ultra Rare des 3 dernières années")

    st.divider()
    st.subheader("🎚️ Importance de chaque facteur")
    st.caption("Ajuste selon ta conviction. Total recommandé = 1.0")

    w1 = st.slider("🔮 Rareté (pull rate)",     0.0, 1.0, 0.30, 0.01)
    w2 = st.slider("⭐ Popularité du Pokémon",  0.0, 1.0, 0.25, 0.01)
    w3 = st.slider("🎨 Qualité de l'illustration", 0.0, 1.0, 0.15, 0.01)
    w4 = st.slider("🏆 Utilisé en tournoi",     0.0, 1.0, 0.15, 0.01)
    w5 = st.slider("📊 Ratio PSA 10",           0.0, 1.0, 0.08, 0.01)
    w6 = st.slider("🔥 Hype / Demande",         0.0, 1.0, 0.07, 0.01)

    total_w = round(w1+w2+w3+w4+w5+w6, 2)
    color = "green" if abs(total_w - 1.0) < 0.05 else "red"
    st.markdown(f"**Total : :{color}[{total_w}]**")

    st.divider()
    st.subheader("📐 Calibration")
    price_multiplier = st.slider("Multiplicateur de prix", 50.0, 1000.0, 250.0, 10.0,
                                  help="Ajuste si les valeurs théoriques semblent trop hautes ou basses")
    gem_thresh  = st.slider("Seuil 'Sous-évalué' (écart min)", 0.05, 0.50, 0.20, 0.01,
                             help="Ex: 0.20 = la carte doit valoir 20% de plus que son prix actuel")
    over_thresh = st.slider("Seuil 'Surévalué' (écart max)",  -0.50, -0.05, -0.20, 0.01)

    st.divider()
    st.subheader("🔍 Filtres")
    min_price = st.number_input("Prix minimum ($)", 0, 1000, 10)
    max_price = st.number_input("Prix maximum ($)", 0, 5000, 1000)


# ── Session state ──
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = pd.DataFrame()

if fetch_btn:
    with st.spinner("⏳ Chargement des cartes SIR / IR / Ultra Rare (2022-2025)... ~20 sec"):
        df_fetched = fetch_live_data(RECENT_SETS_QUERY, max_cards=400, api_key=api_key)
    if df_fetched.empty:
        st.error("❌ Aucune carte récupérée. Réessaie ou ajoute une clé API.")
    else:
        st.session_state.df_loaded = df_fetched
        st.success(f"✅ {len(df_fetched)} cartes chargées !")

df_raw = st.session_state.df_loaded

if df_raw.empty:
    st.info("👈 Clique sur **'Charger toutes les cartes récentes'** dans le menu à gauche pour commencer.")
    st.markdown("""
    **Ce que fait cette app :**
    - Elle charge les cartes Pokémon les plus précieuses des 3 dernières années (SIR, IR, Ultra Rare)
    - Elle calcule pour chaque carte une **valeur théorique** basée sur sa rareté, la popularité du Pokémon, son art, etc.
    - Elle compare cette valeur à son **prix réel sur le marché**
    - Si la valeur théorique est bien au-dessus du prix → 🟢 **Bonne affaire potentielle**
    """)
    st.stop()

# ── Calculs ──
df = compute_scarcity(df_raw)
df = compute_fair_value(df, w1, w2, w3, w4, w5, w6, price_multiplier, gem_thresh, over_thresh)

# Filtre prix
df = df[(df["market_price"] >= min_price) & (df["market_price"] <= max_price)]

# ── Filtre série ──
series_options = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
selected_series = st.selectbox("Filtrer par série", series_options)
if selected_series != "Toutes":
    df = df[df["series"] == selected_series]

gems  = df[df["Signal"] == "🟢 Sous-évalué"]
overs = df[df["Signal"] == "🔴 Surévalué"]
fair  = df[df["Signal"] == "🟡 Prix juste"]

# ── Métriques ──
st.divider()
col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Cartes analysées", len(df))
col2.metric("🟢 Bonnes affaires",  len(gems),  help="Cartes dont la valeur théorique dépasse largement le prix du marché")
col3.metric("🟡 Prix juste",       len(fair),  help="Cartes correctement évaluées")
col4.metric("🔴 Surévaluées",      len(overs), help="Cartes qui coûtent plus cher que ce que le modèle estime")

st.divider()

# ── GEMS ──
st.subheader("🟢 Bonnes affaires détectées")
st.caption("Ces cartes semblent sous-évaluées par rapport à leur valeur théorique. À surveiller.")

if len(gems) > 0:
    gems_sorted = gems.sort_values("Alpha_pct", ascending=False).head(20)
    cols_per_row = 4
    for i in range(0, len(gems_sorted), cols_per_row):
        row_cards = gems_sorted.iloc[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, (_, card) in enumerate(row_cards.iterrows()):
            with cols[idx]:
                if card.get("image_url"):
                    st.image(card["image_url"], width=130)
                st.markdown(f"**{card['name']}**")
                st.markdown(f"*{card['set']}*")
                st.markdown(f"💰 Prix actuel : **${card['market_price']:.2f}**")
                st.markdown(f"📊 Valeur estimée : **${card['Vt']:.2f}**")
                st.markdown(f"<span class='gem-badge'>⬆ {card['Ecart_pct']}</span>", unsafe_allow_html=True)
                if card.get("tcgplayer_url"):
                    st.markdown(f"[Voir sur TCGPlayer ↗]({card['tcgplayer_url']})")
else:
    st.info("Aucune bonne affaire avec les réglages actuels. Essaie de baisser le seuil 'Sous-évalué' dans le menu.")

st.divider()

# ── OVERVALUED ──
with st.expander("🔴 Cartes surévaluées — à éviter"):
    st.caption("Ces cartes coûtent plus cher que ce que le modèle estime leur valeur réelle.")
    if len(overs) > 0:
        overs_sorted = overs.sort_values("Alpha_pct").head(10)
        for _, card in overs_sorted.iterrows():
            col_a, col_b = st.columns([1, 4])
            with col_a:
                if card.get("image_url"):
                    st.image(card["image_url"], width=60)
            with col_b:
                st.markdown(f"**{card['name']}** — *{card['set']}*")
                st.markdown(f"Prix actuel : **${card['market_price']:.2f}** | Valeur estimée : **${card['Vt']:.2f}** | <span class='over-badge'>{card['Ecart_pct']}</span>", unsafe_allow_html=True)
    else:
        st.info("Aucune carte surévaluée détectée.")

st.divider()

# ── Graphique ──
st.subheader("📊 Vue d'ensemble")
tab1, tab2 = st.tabs(["Valeur estimée vs Prix réel", "Classement des écarts"])

colors_map = {"🟢 Sous-évalué": "#2ecc71", "🔴 Surévalué": "#e74c3c", "🟡 Prix juste": "#f39c12"}

with tab1:
    fig, ax = plt.subplots(figsize=(10, 5))
    for signal, group in df.groupby("Signal"):
        ax.scatter(group["market_price"], group["Vt"],
                   label=signal, color=colors_map.get(signal, "gray"), alpha=0.7, s=60)
    max_val = max(df["market_price"].max(), df["Vt"].max())
    ax.plot([0, max_val], [0, max_val], "k--", lw=0.8, label="Valeur = Prix (équilibre)")
    ax.set_xlabel("Prix réel du marché ($)")
    ax.set_ylabel("Valeur théorique estimée ($)")
    ax.set_title("Chaque point = une carte. Au-dessus de la ligne = sous-évaluée.")
    ax.legend()
    st.pyplot(fig)
    st.caption("Les points **au-dessus** de la ligne pointillée sont des cartes dont la valeur estimée dépasse le prix actuel → potentiellement sous-évaluées.")

with tab2:
    top20 = df.nlargest(20, "Alpha_pct")
    fig, ax = plt.subplots(figsize=(10, 6))
    bar_colors = [colors_map.get(s, "gray") for s in top20["Signal"]]
    bars = ax.barh(top20["name"], top20["Alpha_pct"], color=bar_colors)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("Écart entre valeur estimée et prix réel (%)")
    ax.set_title("Top 20 — Cartes les plus sous-évaluées")
    ax.invert_yaxis()
    st.pyplot(fig)

st.divider()

# ── Table complète ──
with st.expander("📋 Voir toutes les cartes analysées"):
    disp = df[["name", "set", "rarity", "market_price", "Vt", "Alpha_pct", "Signal"]].copy()
    disp.columns = ["Carte", "Set", "Rareté", "Prix ($)", "Valeur estimée ($)", "Écart (%)", "Verdict"]
    disp = disp.sort_values("Écart (%)", ascending=False)
    st.dataframe(disp, use_container_width=True, hide_index=True)

# ── Export ──
st.subheader("📥 Exporter les résultats")
export_cols = [c for c in ["name", "set", "rarity", "market_price", "Vt", "Alpha_pct", "Signal", "tcgplayer_url"] if c in df.columns]
csv_buf = io.StringIO()
df[export_cols].sort_values("Alpha_pct", ascending=False).to_csv(csv_buf, index=False)
st.download_button("⬇️ Télécharger le rapport complet (CSV)", csv_buf.getvalue()
