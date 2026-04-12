"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (avec PokéTCG.io Live)
=============================================================
Lance avec : streamlit run streamlit_app.py
=============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
import io
import time

# ─── Config page ───
st.set_page_config(
    page_title="Nasty TCG Fair Value",
    page_icon="🎴",
    layout="wide"
)

st.markdown("""
<style>
    .stMetric { background: #1e1e2e; border-radius: 10px; padding: 8px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FONCTIONS MODÈLE
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
        df["scarcity"]             * w1 +
        df["character_tier_norm"]  * w2 +
        df["art_score_norm"]       * w3 +
        df["meta_relevance_norm"]  * w4 +
        df["psa10_ratio_norm"]     * w5 +
        df["hype_score_norm"]      * w6
    ) * price_multiplier

    df["Alpha"] = (df["Vt"] - df["market_price"]) / df["market_price"]
    df["Alpha_pct"] = (df["Alpha"] * 100).round(1)
    df["Signal"] = df["Alpha"].apply(
        lambda x: "🟢 GEM" if x > gem_thresh else ("🔴 OVERVALUED" if x < over_thresh else "🟡 FAIR")
    )
    return df

def simulate_data(n=50):
    np.random.seed(42)
    names = [
        "Charizard ex SIR", "Umbreon ex SIR", "Mewtwo ex SIR",
        "Pikachu ex FA", "Lugia V Alt Art", "Rayquaza VMAX Alt",
        "Gardevoir ex SIR", "Gengar ex IR", "Eevee Full Art", "Mew ex SIR",
        "Blastoise ex SIR", "Venusaur ex FA", "Jolteon ex SIR",
        "Sylveon V Alt Art", "Greninja ex FA", "Snorlax V FA",
        "Espeon ex SIR", "Vaporeon ex FA", "Togekiss ex SIR", "Alakazam ex IR"
    ] + [f"Card #{i}" for i in range(30)]
    rarity_map = {
        "SIR":     {"pull_rate": 1/1440, "art_score": 10},
        "Alt Art":  {"pull_rate": 1/720,  "art_score": 9},
        "FA":       {"pull_rate": 1/288,  "art_score": 7},
        "IR":       {"pull_rate": 1/144,  "art_score": 6},
        "SR":       {"pull_rate": 1/72,   "art_score": 5},
        "Rare":     {"pull_rate": 1/10,   "art_score": 3},
    }
    rarities = np.random.choice(list(rarity_map.keys()), n)
    return pd.DataFrame({
        "name":              names[:n],
        "rarity":            rarities,
        "pull_rate_per_pack": [rarity_map[r]["pull_rate"] for r in rarities],
        "character_tier":    np.random.randint(1, 11, n),
        "art_score":         [min(10, max(1, rarity_map[r]["art_score"] + np.random.uniform(-1, 1))) for r in rarities],
        "meta_relevance":    np.random.uniform(0, 10, n),
        "psa10_ratio":       np.random.uniform(0, 10, n),
        "hype_score":        np.random.uniform(0, 10, n),
        "market_price":      np.random.uniform(5, 500, n),
    })


# ─────────────────────────────────────────────
# FETCH LIVE (PokéTCG.io)
# ─────────────────────────────────────────────

RARITY_METADATA = {
    "Special Illustration Rare": (1/1440, 10),
    "Hyper Rare":                 (1/360,  9),
    "Illustration Rare":          (1/144,  8),
    "Ultra Rare":                 (1/72,   7),
    "Double Rare":                (1/48,   6),
    "Rare Holo VMAX":             (1/36,   7),
    "Rare Holo V":                (1/24,   6),
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

def get_tier(name):
    for tier, names in TIER_MAP.items():
        if any(n in name.lower() for n in names):
            return tier
    return 3

PRESET_QUERIES = {
    "🌟 Special Illustration Rare (toutes)":    'rarity:"Special Illustration Rare"',
    "✨ Illustration Rare (toutes)":             'rarity:"Illustration Rare"',
    "💎 Hyper Rare (toutes)":                   'rarity:"Hyper Rare"',
    "🔥 Top Raretés (SIR + IR + Hyper)":        '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" OR rarity:"Hyper Rare")',
    "🃏 Prismatic Evolutions":                  'set.name:"Prismatic Evolutions"',
    "⚡ Scarlet & Violet — Top Rares":          'set.series:"Scarlet & Violet" rarity:"Special Illustration Rare"',
    "🐉 Charizard (toutes versions)":           'name:charizard',
}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_live_data(query: str, max_cards: int, api_key: str = "") -> pd.DataFrame:
    """Fetche les cartes depuis PokéTCG.io et retourne un DataFrame."""
    import requests

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    all_rows = []
    page = 1
    fetched = 0

    while fetched < max_cards:
        size = min(100, max_cards - fetched)
        params = {"q": query, "page": page, "pageSize": size, "orderBy": "-set.releaseDate"}

        try:
            resp = requests.get("https://api.pokemontcg.io/v2/cards", headers=headers, params=params, timeout=15)
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
                "name":              card.get("name", "?"),
                "set":               card.get("set", {}).get("name", "?"),
                "rarity":            rarity,
                "pull_rate_per_pack": pull_rate,
                "character_tier":    get_tier(card.get("name", "")),
                "art_score":         min(10, max(1, art_base)),
                "meta_relevance":    meta,
                "psa10_ratio":       psa10,
                "hype_score":        hype,
                "market_price":      round(market_price, 2),
                "tcgplayer_url":     tcgplayer.get("url", ""),
                "image_url":         card.get("images", {}).get("small", ""),
            })

        fetched += len(cards)
        if len(cards) < size:
            break
        page += 1
        time.sleep(0.1)

    if not all_rows:
        return pd.DataFrame()

    return pd.DataFrame(all_rows)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────

st.title("🎴 Nasty TCG — Fair Value Model")
st.caption("Identify undervalued Pokémon cards with a quantitative edge • Powered by PokéTCG.io")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Paramètres")

    # --- Source de données ---
    st.subheader("📡 Source de Données")
    data_source = st.radio("", ["🌐 Live API (PokéTCG.io)", "📂 Mon CSV", "🎲 Simulation"], label_visibility="collapsed")

    if data_source == "🌐 Live API (PokéTCG.io)":
        preset_label = st.selectbox("Preset", list(PRESET_QUERIES.keys()))
        custom_query = st.text_input("Ou query custom", placeholder='name:charizard rarity:"Special Illustration Rare"')
        max_cards    = st.slider("Nombre max de cartes", 10, 250, 100, 10)
        api_key      = st.text_input("Clé API (optionnel)", type="password", help="Augmente le rate limit à 20k req/jour")
        fetch_btn    = st.button("🔄 Fetch les cartes", type="primary")

    st.divider()

    # --- Poids ---
    st.subheader("🎚️ Poids des Variables")
    w1 = st.slider("w1 — Scarcity",       0.0, 1.0, 0.30, 0.01)
    w2 = st.slider("w2 — Char. Tier",     0.0, 1.0, 0.25, 0.01)
    w3 = st.slider("w3 — Art Score",      0.0, 1.0, 0.15, 0.01)
    w4 = st.slider("w4 — Meta",           0.0, 1.0, 0.15, 0.01)
    w5 = st.slider("w5 — Grading Ratio",  0.0, 1.0, 0.08, 0.01)
    w6 = st.slider("w6 — Hype",           0.0, 1.0, 0.07, 0.01)
    total_w = round(w1+w2+w3+w4+w5+w6, 2)
    color = "green" if abs(total_w - 1.0) < 0.05 else "red"
    st.markdown(f"**Total : :{color}[{total_w}]**")

    st.divider()
    st.subheader("📐 Calibration & Seuils")
    price_multiplier = st.slider("Price Multiplier", 10.0, 1000.0, 200.0, 10.0)
    gem_thresh  = st.slider("Seuil GEM (α >)",        0.0,  1.0,  0.20, 0.01)
    over_thresh = st.slider("Seuil OVERVALUED (α <)", -1.0, 0.0, -0.20, 0.01)


# ── Chargement des données ──
df_raw = pd.DataFrame()

if data_source == "🌐 Live API (PokéTCG.io)":
    if "live_df" not in st.session_state:
        st.session_state.live_df = pd.DataFrame()

    if fetch_btn:
        query = custom_query.strip() if custom_query.strip() else PRESET_QUERIES[preset_label]
        with st.spinner(f"⏳ Fetching '{query}'..."):
            st.session_state.live_df = fetch_live_data(query, max_cards, api_key)
        if st.session_state.live_df.empty:
            st.warning("Aucune carte retournée. Essaie une autre query.")
        else:
            st.success(f"✅ {len(st.session_state.live_df)} cartes chargées depuis PokéTCG.io")

    df_raw = st.session_state.live_df

    if df_raw.empty:
        st.info("👈 Clique sur **Fetch les cartes** pour charger les données live.")
        st.stop()

elif data_source == "📂 Mon CSV":
    uploaded = st.file_uploader("Charge ton fichier CSV", type=["csv"])
    if uploaded:
        df_raw = pd.read_csv(uploaded)
        st.success(f"✅ {len(df_raw)} cartes chargées")
    else:
        st.info("En attente du fichier CSV... (utilise `template_cartes.csv` comme modèle)")
        st.stop()

else:
    df_raw = simulate_data()
    st.info("🎲 Mode simulation — 50 cartes générées aléatoirement.")


# ── Calculs ──
df = compute_scarcity(df_raw)
df = compute_fair_value(df, w1, w2, w3, w4, w5, w6, price_multiplier, gem_thresh, over_thresh)

# ── Métriques ──
gems  = df[df["Signal"] == "🟢 GEM"]
overs = df[df["Signal"] == "🔴 OVERVALUED"]
fair  = df[df["Signal"] == "🟡 FAIR"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("📦 Total Cartes", len(df))
col2.metric("🟢 GEMs",         len(gems))
col3.metric("🟡 FAIR",         len(fair))
col4.metric("🔴 Overvalued",   len(overs))

st.divider()

# ── Top Gems ──
st.subheader("🏆 Top Buy — GEMs Identifiés")

if len(gems) > 0:
    gems_sorted = gems.sort_values("Alpha_pct", ascending=False)

    # Affichage avec images si dispo
    if "image_url" in gems_sorted.columns and "tcgplayer_url" in gems_sorted.columns:
        cols_per_row = 4
        rows = [gems_sorted.iloc[i:i+cols_per_row] for i in range(0, min(len(gems_sorted), 12), cols_per_row)]
        for row_df in rows:
            cols = st.columns(cols_per_row)
            for idx, (_, card) in enumerate(row_df.iterrows()):
                with cols[idx]:
                    if card.get("image_url"):
                        st.image(card["image_url"], width=120)
                    st.markdown(f"**{card['name']}**")
                    st.markdown(f"💰 `${card['market_price']:.2f}`")
                    st.markdown(f"📈 Alpha: `{card['Alpha_pct']:+.1f}%`")
                    if card.get("tcgplayer_url"):
                        st.markdown(f"[TCGPlayer ↗]({card['tcgplayer_url']})")
    else:
        display_cols = ["name", "rarity", "market_price", "Vt", "Alpha_pct", "Signal"]
        st.dataframe(gems_sorted[display_cols].rename(columns={
            "name": "Carte", "rarity": "Rareté",
            "market_price": "Prix ($)", "Vt": "Fair Value ($)", "Alpha_pct": "Alpha (%)", "Signal": "Signal"
        }), use_container_width=True, hide_index=True)
else:
    st.warning("Aucun GEM avec les paramètres actuels. Ajuste les curseurs dans le sidebar.")

st.divider()

# ── Graphiques ──
st.subheader("📊 Analyse Visuelle")
tab1, tab2, tab3 = st.tabs(["Vt vs Prix Marché", "Distribution Alpha", "Top 20 Alpha"])

colors_map = {"🟢 GEM": "#2ecc71", "🔴 OVERVALUED": "#e74c3c", "🟡 FAIR": "#f39c12"}

with tab1:
    fig, ax = plt.subplots(figsize=(9, 5))
    for signal, group in df.groupby("Signal"):
        ax.scatter(group["market_price"], group["Vt"],
                   label=signal, color=colors_map.get(signal, "gray"), alpha=0.75, s=80)
    max_val = max(df["market_price"].max(), df["Vt"].max())
    ax.plot([0, max_val], [0, max_val], "k--", lw=0.8, label="Vt = Pm")
    ax.set_xlabel("Prix Marché ($)")
    ax.set_ylabel("Fair Value Vt ($)")
    ax.set_title("Fair Value vs Prix Marché")
    ax.legend()
    st.pyplot(fig)

with tab2:
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.hist(df["Alpha"], bins=25, color="#3498db", edgecolor="white", alpha=0.85)
    ax.axvline(gem_thresh,  color="#2ecc71", ls="--", label=f"GEM (>{gem_thresh:.2f})")
    ax.axvline(over_thresh, color="#e74c3c", ls="--", label=f"Overvalued (<{over_thresh:.2f})")
    ax.axvline(0, color="black", lw=0.5)
    ax.set_xlabel("Alpha")
    ax.set_title("Distribution des Alpha")
    ax.legend()
    st.pyplot(fig)

with tab3:
    top20 = df.nlargest(20, "Alpha")
    fig, ax = plt.subplots(figsize=(9, 6))
    bar_colors = [colors_map.get(s, "gray") for s in top20["Signal"]]
    ax.barh(top20["name"], top20["Alpha"], color=bar_colors)
    ax.axvline(0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("Alpha")
    ax.set_title("Top 20 cartes par Alpha")
    ax.invert_yaxis()
    st.pyplot(fig)

st.divider()

# ── Export ──
st.subheader("📥 Export")
export_cols = [c for c in ["name", "set", "rarity", "market_price", "Vt", "Alpha_pct", "Signal", "tcgplayer_url"] if c in df.columns]
csv_buf = io.StringIO()
df[export_cols].sort_values("Alpha_pct", ascending=False).to_csv(csv_buf, index=False)
st.download_button("⬇️ Télécharger le rapport (CSV)", csv_buf.getvalue(), "fair_value_report.csv", "text/csv")

# ── Table complète ──
with st.expander("🔍 Voir toutes les cartes"):
    disp_cols = [c for c in ["name", "set", "rarity", "market_price", "Vt", "Alpha_pct", "Signal"] if c in df.columns]
    st.dataframe(df[disp_cols].sort_values("Alpha_pct", ascending=False), use_container_width=True, hide_index=True)
