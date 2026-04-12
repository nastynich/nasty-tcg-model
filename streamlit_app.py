"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (v3)
 Valeur estimee ancree sur le prix reel via regression
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

st.set_page_config(
    page_title="Nasty TCG — Fair Value",
    page_icon="🎴",
    layout="wide"
)

st.markdown("""
<style>
    .gem-badge  { color: #2ecc71; font-size: 16px; font-weight: bold; }
    .over-badge { color: #e74c3c; font-size: 16px; font-weight: bold; }
    .fair-badge { color: #f39c12; font-size: 16px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

RARITY_PULL = {
    "Special Illustration Rare": 1/1440,
    "Hyper Rare":                1/360,
    "Illustration Rare":         1/144,
    "Ultra Rare":                1/72,
    "Double Rare":               1/48,
    "Rare Holo VMAX":            1/36,
    "Rare Holo VSTAR":           1/36,
    "Rare Holo V":               1/24,
    "Rare Holo EX":              1/24,
    "Rare Holo":                 1/12,
    "Rare":                      1/10,
}

TIER_MAP = {
    10: ["charizard", "umbreon", "mewtwo", "rayquaza", "lugia"],
    9:  ["pikachu", "eevee", "mew", "gengar", "snorlax", "espeon", "vaporeon"],
    8:  ["jolteon", "flareon", "sylveon", "gardevoir", "blastoise", "venusaur"],
    7:  ["greninja", "lucario", "togekiss", "alakazam", "dragonite"],
    6:  ["gyarados", "arcanine", "ninetales", "absol", "flygon"],
}

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
            st.error(f"Erreur API : {e}")
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
            pull_rate = RARITY_PULL.get(rarity, 1/20)
            legalities = card.get("legalities", {})
            meta = 3.0 if legalities.get("standard") == "Legal" else (2.0 if legalities.get("expanded") == "Legal" else 1.0)

            all_rows.append({
                "name":               card.get("name", "?"),
                "set":                card.get("set", {}).get("name", "?"),
                "series":             card.get("set", {}).get("series", "?"),
                "release_date":       card.get("set", {}).get("releaseDate", ""),
                "rarity":             rarity,
                "pull_rate":          pull_rate,
                "character_tier":     get_tier(card.get("name", "")),
                "meta_relevance":     meta,
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
# MODELE — ancrage sur le prix reel
# ─────────────────────────────────────────────

def compute_fair_value(df, w_scarcity, w_tier, w_meta, gem_thresh, over_thresh):
    """
    Approche: on construit un score composite par carte,
    puis on calibre ce score pour qu'il predit le log(prix) reel.
    La valeur estimee est donc toujours dans la bonne plage de prix.
    """
    df = df.copy()

    # Features brutes
    df["log_scarcity"] = -np.log(df["pull_rate"])          # plus rare = plus grand
    df["log_price"]    = np.log1p(df["market_price"])

    # Normalisation 0-1
    scaler = MinMaxScaler()
    df["scarcity_n"] = scaler.fit_transform(df[["log_scarcity"]])
    df["tier_n"]     = scaler.fit_transform(df[["character_tier"]])
    df["meta_n"]     = scaler.fit_transform(df[["meta_relevance"]])

    # Score composite pondere (0-1)
    total_w = w_scarcity + w_tier + w_meta
    if total_w == 0:
        total_w = 1
    df["score"] = (
        df["scarcity_n"] * w_scarcity +
        df["tier_n"]     * w_tier +
        df["meta_n"]     * w_meta
    ) / total_w

    # Regression Ridge: score -> log(prix)
    # Ca calibre la valeur estimee pour coller a la distribution reelle des prix
    X = df[["score"]].values
    y = df["log_price"].values
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    df["log_Vt"] = model.predict(X)
    df["Vt"]     = np.expm1(df["log_Vt"]).round(2)

    # Ecart en %
    df["ecart_pct"] = ((df["Vt"] - df["market_price"]) / df["market_price"] * 100).round(1)

    df["Signal"] = df["ecart_pct"].apply(
        lambda x: "🟢 Sous-évalué" if x > gem_thresh * 100
        else ("🔴 Surévalué" if x < over_thresh * 100 else "🟡 Prix juste")
    )
    df["Ecart_label"] = df["ecart_pct"].apply(
        lambda x: f"+{x:.0f}% sous le prix réel" if x > 0 else f"{abs(x):.0f}% au-dessus du prix réel"
    )
    return df


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────

st.title("🎴 Nasty TCG — Détecteur de cartes sous-évaluées")
st.caption("Compare le prix réel du marché à la valeur théorique. Trouve les bonnes affaires.")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Réglages")

    st.subheader("📡 Données")
    api_key = st.text_input(
        "Clé API PokéTCG (optionnel)", type="password",
        help="Sans clé : 1 000 req/jour. Clé gratuite sur pokemontcg.io/dev → 20 000/jour"
    )
    fetch_btn = st.button(
        "🔄 Charger les cartes récentes", type="primary",
        help="Charge ~300-500 cartes SIR/IR/Ultra Rare de Scarlet & Violet + Sword & Shield"
    )

    st.divider()
    st.subheader("🎚️ Importance de chaque facteur")
    w_scarcity = st.slider("🔮 Rareté (pull rate)",      0.0, 1.0, 0.50, 0.05)
    w_tier     = st.slider("⭐ Popularité du Pokémon",   0.0, 1.0, 0.35, 0.05)
    w_meta     = st.slider("🏆 Utilisé en tournoi",      0.0, 1.0, 0.15, 0.05)

    st.divider()
    st.subheader("📐 Seuils de décision")
    gem_thresh  = st.slider("Seuil sous-évalué (ex: 0.15 = +15%)",  0.05, 0.60, 0.15, 0.05)
    over_thresh = st.slider("Seuil surévalué (ex: -0.15 = -15%)", -0.60, -0.05, -0.15, 0.05)

    st.divider()
    st.subheader("🔍 Filtres")
    min_price = st.number_input("Prix minimum ($)", 0, 1000, 5)
    max_price = st.number_input("Prix maximum ($)", 0, 5000, 2000)


# ── Session state ──
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = pd.DataFrame()

if fetch_btn:
    with st.spinner("Chargement des cartes SIR / IR / Ultra Rare... ~20 sec"):
        df_fetched = fetch_live_data(RECENT_SETS_QUERY, max_cards=400, api_key=api_key)
    if df_fetched.empty:
        st.error("Aucune carte récupérée. Vérifie ta connexion ou ajoute une clé API.")
    else:
        st.session_state.df_loaded = df_fetched
        st.success(f"✅ {len(df_fetched)} cartes chargées !")

df_raw = st.session_state.df_loaded

if df_raw.empty:
    st.info("👈 Clique sur **'Charger les cartes récentes'** dans le menu à gauche pour commencer.")
    st.markdown("""
**Comment ça marche :**
- Charge les cartes Pokémon les plus précieuses des 3 dernières années
- Calcule une **valeur théorique** basée sur la rareté, la popularité et l'utilisation en tournoi
- Compare cette valeur au **prix réel du marché**
- 🟢 Si la valeur estimée est nettement au-dessus → potentiellement sous-évaluée
- 🔴 Si le prix du marché est nettement au-dessus → potentiellement surévaluée
    """)
    st.stop()

# ── Calculs ──
df = compute_fair_value(df_raw, w_scarcity, w_tier, w_meta, gem_thresh, over_thresh)
df = df[(df["market_price"] >= min_price) & (df["market_price"] <= max_price)]

# Filtre série
series_options = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
selected_series = st.selectbox("Filtrer par série", series_options)
if selected_series != "Toutes":
    df = df[df["series"] == selected_series]

gems  = df[df["Signal"] == "🟢 Sous-évalué"].sort_values("ecart_pct", ascending=False)
overs = df[df["Signal"] == "🔴 Surévalué"].sort_values("ecart_pct")
fair  = df[df["Signal"] == "🟡 Prix juste"]

# ── Métriques ──
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Cartes analysées", len(df))
c2.metric("🟢 Sous-évaluées",   len(gems))
c3.metric("🟡 Prix juste",      len(fair))
c4.metric("🔴 Surévaluées",     len(overs))
st.divider()

# ── GEMS ──
st.subheader("🟢 Bonnes affaires potentielles")
st.caption("Cartes dont la valeur théorique dépasse le prix du marché — potentiellement sous-évaluées.")

if len(gems) > 0:
    cols_per_row = 4
    for i in range(0, min(len(gems), 20), cols_per_row):
        row_cards = gems.iloc[i:i+cols_per_row]
        cols = st.columns(cols_per_row)
        for idx, (_, card) in enumerate(row_cards.iterrows()):
            with cols[idx]:
                if card.get("image_url"):
                    st.image(card["image_url"], width=130)
                st.markdown(f"**{card['name']}**")
                st.markdown(f"*{card['set']}*")
                st.markdown(f"*{card['rarity']}*")
                st.markdown(f"💰 Prix actuel : **${card['market_price']:.2f}**")
                st.markdown(f"📊 Valeur estimée : **${card['Vt']:.2f}**")
                st.markdown(
                    f"<span class='gem-badge'>+{card['ecart_pct']:.0f}% sous le prix réel</span>",
                    unsafe_allow_html=True
                )
                if card.get("tcgplayer_url"):
                    st.markdown(f"[Voir sur TCGPlayer]({card['tcgplayer_url']})")
else:
    st.info("Aucune bonne affaire détectée. Essaie de baisser le seuil 'sous-évalué' dans le menu.")

st.divider()

# ── OVERVALUED ──
with st.expander(f"🔴 Cartes surévaluées ({len(overs)})"):
    st.caption("Ces cartes coûtent plus cher que ce que le modèle estime leur valeur réelle.")
    for _, card in overs.head(10).iterrows():
        ca, cb = st.columns([1, 4])
        with ca:
            if card.get("image_url"):
                st.image(card["image_url"], width=60)
        with cb:
            st.markdown(f"**{card['name']}** — *{card['set']}*")
            st.markdown(
                f"Prix actuel : **${card['market_price']:.2f}** | "
                f"Valeur estimée : **${card['Vt']:.2f}** | "
                f"<span class='over-badge'>{card['ecart_pct']:.0f}%</span>",
                unsafe_allow_html=True
            )

st.divider()

# ── Graphiques ──
st.subheader("📊 Vue d'ensemble")
tab1, tab2 = st.tabs(["Valeur estimée vs Prix réel", "Top sous-évaluées"])

colors_map = {
    "🟢 Sous-évalué": "#2ecc71",
    "🔴 Surévalué":   "#e74c3c",
    "🟡 Prix juste":  "#f39c12"
}

with tab1:
    fig, ax = plt.subplots(figsize=(10, 5))
    for signal, group in df.groupby("Signal"):
        ax.scatter(
            group["market_price"], group["Vt"],
            label=signal, color=colors_map.get(signal, "gray"),
            alpha=0.7, s=55
        )
    max_val = max(df["market_price"].max(), df["Vt"].max()) * 1.05
    ax.plot([0, max_val], [0, max_val], "k--", lw=0.9, label="Valeur = Prix")
    ax.set_xlabel("Prix réel du marché ($)")
    ax.set_ylabel("Valeur théorique estimée ($)")
    ax.set_title("Chaque point = une carte. Au-dessus de la ligne = sous-évaluée.")
    ax.legend()
    st.pyplot(fig)
    st.caption("Les points **au-dessus** de la ligne = valeur estimée > prix du marché → potentiellement sous-évaluées.")

with tab2:
    top20 = df.nlargest(20, "ecart_pct")
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bar_colors = [colors_map.get(s, "gray") for s in top20["Signal"]]
    ax2.barh(top20["name"], top20["ecart_pct"], color=bar_colors)
    ax2.axvline(0, color="black", lw=0.8, ls="--")
    ax2.set_xlabel("Ecart entre valeur estimée et prix réel (%)")
    ax2.set_title("Top 20 — Cartes les plus sous-évaluées")
    ax2.invert_yaxis()
    st.pyplot(fig2)

st.divider()

# ── Table complète ──
with st.expander("📋 Toutes les cartes analysées"):
    disp = df[["name", "set", "rarity", "market_price", "Vt", "ecart_pct", "Signal"]].copy()
    disp.columns = ["Carte", "Set", "Rareté", "Prix ($)", "Valeur estimée ($)", "Écart (%)", "Verdict"]
    st.dataframe(disp.sort_values("Écart (%)", ascending=False), use_container_width=True, hide_index=True)

# ── Export ──
st.subheader("📥 Exporter")
export_cols = ["name", "set", "rarity", "market_price", "Vt", "ecart_pct", "Signal", "tcgplayer_url"]
csv_buf = io.StringIO()
df[export_cols].sort_values("ecart_pct", ascending=False).to_csv(csv_buf, index=False)
st.download_button(
    label="Telecharger le rapport CSV",
    data=csv_buf.getvalue(),
    file_name="fair_value_report.csv",
    mime="text/csv"
)
