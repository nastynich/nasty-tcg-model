"""
=============================================================
 Nasty TCG Dashboard — Streamlit App (v4)
 7 facteurs, valeur estimee ancree sur le prix reel
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
    .gem-badge  { color: #2ecc71; font-size: 15px; font-weight: bold; }
    .over-badge { color: #e74c3c; font-size: 15px; font-weight: bold; }
    .fair-badge { color: #f39c12; font-size: 15px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────

# Pull rates approximatifs par rareté (1 carte sur X packs)
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

# Tier du Pokémon (popularité / mascotte)
TIER_MAP = {
    10: ["charizard", "umbreon", "mewtwo", "rayquaza", "lugia"],
    9:  ["pikachu", "eevee", "mew", "gengar", "snorlax", "espeon", "vaporeon"],
    8:  ["jolteon", "flareon", "sylveon", "gardevoir", "blastoise", "venusaur"],
    7:  ["greninja", "lucario", "togekiss", "alakazam", "dragonite"],
    6:  ["gyarados", "arcanine", "ninetales", "absol", "flygon"],
}

# Réputation des artistes illustrateurs (connus dans la communauté TCG)
ARTIST_TIER = {
    10: ["mika pikazo", "tetsu kayama", "akira komayama"],
    9:  ["ryota murayama", "nagomibana", "sowsow", "5ban graphics"],
    8:  ["atsushi furusawa", "yuka morii", "sanosuke sakuma"],
    7:  ["ryo ueda", "kiichiro", "yuu nishida"],
    6:  ["kawayoo", "eri yamaki"],
}

RECENT_SETS_QUERY = (
    '(set.series:"Scarlet & Violet" OR set.series:"Sword & Shield") '
    '(rarity:"Special Illustration Rare" OR rarity:"Illustration Rare" '
    'OR rarity:"Hyper Rare" OR rarity:"Ultra Rare" OR rarity:"Double Rare")'
)

def get_tier(name: str) -> int:
    name = name.lower()
    for tier, names in TIER_MAP.items():
        if any(n in name for n in names):
            return tier
    return 3

def get_artist_score(artist: str) -> float:
    artist = artist.lower()
    for score, names in ARTIST_TIER.items():
        if any(n in artist for n in names):
            return float(score)
    return 4.0  # artiste inconnu = score moyen-bas

def set_lifecycle_score(release_date_str: str) -> float:
    """
    Score de 1 a 10 base sur l'age du set.
    Set recent (<6 mois) = score eleve (encore en print, hype active)
    Set vieux (>2 ans) = score bas (out of print, marche stabilise)
    """
    try:
        parts = release_date_str.split("/")
        rd = date(int(parts[0]), int(parts[1]), int(parts[2]))
        days_old = (date.today() - rd).days
        if days_old < 90:    return 9.0   # tout neuf
        if days_old < 180:   return 8.0   # recent
        if days_old < 365:   return 6.5   # milieu de vie
        if days_old < 548:   return 5.0   # 1-1.5 ans
        if days_old < 730:   return 3.5   # 1.5-2 ans
        return 2.0                         # 2 ans+, out of print / stabilise
    except Exception:
        return 5.0


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
            tcgplayer  = card.get("tcgplayer", {})
            prices     = tcgplayer.get("prices", {})
            market_price = None
            for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
                if ptype in prices and prices[ptype].get("market"):
                    market_price = prices[ptype]["market"]
                    break
            if not market_price or market_price <= 0:
                continue

            rarity       = card.get("rarity", "Unknown")
            pull_rate    = RARITY_PULL.get(rarity, 1/20)
            legalities   = card.get("legalities", {})
            release_date = card.get("set", {}).get("releaseDate", "")
            artist       = card.get("artist", "")

            # Compétitivité (meta relevance)
            if legalities.get("standard") == "Legal":
                meta = 9.0
            elif legalities.get("expanded") == "Legal":
                meta = 5.0
            else:
                meta = 1.0

            # Social Sentiment / Hype — proxy: vitesse de vente (low/mid/high TCGPlayer)
            # On utilise le spread entre listed et market comme proxy d'urgence d'achat
            hype = 5.0  # baseline
            for ptype in ["holofoil", "reverseHolofoil", "normal"]:
                if ptype in prices:
                    low = prices[ptype].get("low", 0)
                    mkt = prices[ptype].get("market", 0)
                    if low and mkt and mkt > 0:
                        # Si low << market => demande forte => hype elevee
                        ratio = low / mkt
                        if ratio < 0.5:   hype = 9.0
                        elif ratio < 0.7: hype = 7.0
                        elif ratio < 0.9: hype = 5.5
                        else:             hype = 3.5
                    break

            # PSA10 Slab Factor — proxy base sur la rareté + prix
            # Les SIR sont notoriement difficiles a grader (bords, texture)
            slab_difficulty = {
                "Special Illustration Rare": 8.5,
                "Illustration Rare":         7.0,
                "Hyper Rare":                6.0,
                "Ultra Rare":                5.0,
                "Double Rare":               4.0,
            }
            psa10 = slab_difficulty.get(rarity, 4.0)

            all_rows.append({
                "name":          card.get("name", "?"),
                "set":           card.get("set", {}).get("name", "?"),
                "series":        card.get("set", {}).get("series", "?"),
                "release_date":  release_date,
                "rarity":        rarity,
                "artist":        artist,
                # 7 facteurs
                "f_scarcity":    pull_rate,           # pull rate brut (inversé = rareté)
                "f_tier":        float(get_tier(card.get("name", ""))),
                "f_artist":      get_artist_score(artist),
                "f_meta":        meta,
                "f_hype":        hype,
                "f_psa10":       psa10,
                "f_lifecycle":   set_lifecycle_score(release_date),
                # Prix
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
# MODELE
# ─────────────────────────────────────────────

FEATURE_COLS = ["f_scarcity_inv", "f_tier", "f_artist", "f_meta", "f_hype", "f_psa10", "f_lifecycle"]

def compute_fair_value(df, weights: dict, gem_thresh: float, over_thresh: float) -> pd.DataFrame:
    df = df.copy()

    # Scarcity: inverser (pull rate petit = rare = bonne chose)
    df["f_scarcity_inv"] = -np.log(df["f_scarcity"])

    # Normaliser tous les facteurs en 0-1
    scaler = MinMaxScaler()
    for col in FEATURE_COLS:
        df[f"{col}_n"] = scaler.fit_transform(df[[col]])

    # Score composite pondéré (0-1)
    norm_cols  = [f"{c}_n" for c in FEATURE_COLS]
    weight_arr = np.array([weights[c] for c in FEATURE_COLS])
    total_w    = weight_arr.sum() or 1.0

    df["score"] = df[norm_cols].values.dot(weight_arr) / total_w

    # Regression Ridge: score -> log(prix reel)
    # => valeur estimee toujours dans la bonne plage de prix
    X = df[["score"]].values
    y = np.log1p(df["market_price"].values)
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    df["Vt"]       = np.expm1(model.predict(X)).round(2)
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
st.caption("7 facteurs analysés • Prix ancrés sur le marché réel • Scarlet & Violet + Sword & Shield")

with st.sidebar:
    st.header("⚙️ Réglages")

    st.subheader("📡 Données")
    api_key = st.text_input(
        "Clé API PokéTCG (optionnel)", type="password",
        help="Sans clé : 1 000 req/jour. Clé gratuite sur pokemontcg.io/dev"
    )
    fetch_btn = st.button("🔄 Charger les cartes récentes", type="primary")

    st.divider()
    st.subheader("🎚️ Poids de chaque facteur")
    st.caption("Ajuste l'importance de chaque variable dans le calcul.")

    w_scarcity  = st.slider("🔮 Rareté (pull rate)",            0.0, 1.0, 0.25, 0.05)
    w_tier      = st.slider("⭐ Popularité du Pokémon",          0.0, 1.0, 0.20, 0.05)
    w_artist    = st.slider("🎨 Réputation de l'artiste",        0.0, 1.0, 0.10, 0.05)
    w_meta      = st.slider("🏆 Jouabilité compétitive",         0.0, 1.0, 0.15, 0.05)
    w_hype      = st.slider("🔥 Hype / Sentiment social",        0.0, 1.0, 0.15, 0.05)
    w_psa10     = st.slider("💎 Difficulté de grading (PSA 10)", 0.0, 1.0, 0.10, 0.05)
    w_lifecycle = st.slider("📅 Cycle de vie du set",            0.0, 1.0, 0.05, 0.05)

    total_w = round(w_scarcity + w_tier + w_artist + w_meta + w_hype + w_psa10 + w_lifecycle, 2)
    color = "green" if abs(total_w - 1.0) < 0.08 else "orange"
    st.markdown(f"**Total : :{color}[{total_w}]** *(idéalement = 1.0)*")

    st.divider()
    st.subheader("📐 Seuils")
    gem_thresh  = st.slider("Seuil sous-évalué (+X%)",  0.05, 0.60, 0.15, 0.05)
    over_thresh = st.slider("Seuil surévalué (-X%)",   -0.60, -0.05, -0.15, 0.05)

    st.divider()
    st.subheader("🔍 Filtres prix")
    min_price = st.number_input("Prix minimum ($)", 0, 1000, 5)
    max_price = st.number_input("Prix maximum ($)", 0, 5000, 2000)

# ── Session state ──
if "df_loaded" not in st.session_state:
    st.session_state.df_loaded = pd.DataFrame()

if fetch_btn:
    with st.spinner("Chargement des cartes SIR / IR / Ultra Rare... ~20 sec"):
        fetched = fetch_live_data(RECENT_SETS_QUERY, max_cards=400, api_key=api_key)
    if fetched.empty:
        st.error("Aucune carte récupérée. Vérifie ta connexion ou ajoute une clé API.")
    else:
        st.session_state.df_loaded = fetched
        st.success(f"✅ {len(fetched)} cartes chargées !")

df_raw = st.session_state.df_loaded

if df_raw.empty:
    st.info("👈 Clique sur **'Charger les cartes récentes'** dans le menu à gauche pour commencer.")
    st.markdown("""
**Les 7 facteurs analysés :**
| Facteur | Description |
|---|---|
| 🔮 Rareté | Probabilité de pull dans un pack (1/1440 pour SIR) |
| ⭐ Popularité | Mascotte vs Pokémon bulk — Charizard > Lickitung |
| 🎨 Artiste | Réputation de l'illustrateur dans la communauté |
| 🏆 Compétitivité | Utilisé dans les top decks de tournoi ? |
| 🔥 Hype | Demande actuelle — vitesse de vente sur TCGPlayer |
| 💎 Grading | Difficulté d'obtenir un PSA 10 (SIR = très difficile) |
| 📅 Cycle de vie | Le set est encore en impression ou déjà retiré ? |
    """)
    st.stop()

# ── Calculs ──
weights = {
    "f_scarcity_inv_n": w_scarcity,
    "f_tier_n":         w_tier,
    "f_artist_n":       w_artist,
    "f_meta_n":         w_meta,
    "f_hype_n":         w_hype,
    "f_psa10_n":        w_psa10,
    "f_lifecycle_n":    w_lifecycle,
}

# On passe les poids dans l'ordre de FEATURE_COLS
weights_ordered = {
    "f_scarcity_inv": w_scarcity,
    "f_tier":         w_tier,
    "f_artist":       w_artist,
    "f_meta":         w_meta,
    "f_hype":         w_hype,
    "f_psa10":        w_psa10,
    "f_lifecycle":    w_lifecycle,
}

df = compute_fair_value(df_raw, weights_ordered, gem_thresh, over_thresh)
df = df[(df["market_price"] >= min_price) & (df["market_price"] <= max_price)]

# Filtre série
series_opts = ["Toutes"] + sorted(df["series"].dropna().unique().tolist())
selected_series = st.selectbox("Filtrer par série", series_opts)
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
st.caption("Valeur théorique nettement supérieure au prix du marché — cartes potentiellement sous-évaluées.")

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
                if card.get("artist"):
                    st.markdown(f"✏️ *{card['artist']}*")
                st.markdown(f"💰 Prix actuel : **${card['market_price']:.2f}**")
                st.markdown(f"📊 Valeur estimée : **${card['Vt']:.2f}**")
                st.markdown(
                    f"<span class='gem-badge'>+{card['ecart_pct']:.0f}% sous le prix réel</span>",
                    unsafe_allow_html=True
                )
                if card.get("tcgplayer_url"):
                    st.markdown(f"[Voir sur TCGPlayer]({card['tcgplayer_url']})")
else:
    st.info("Aucune bonne affaire détectée avec ces réglages. Essaie de baisser le seuil sous-évalué.")

st.divider()

# ── OVERVALUED ──
with st.expander(f"🔴 Cartes surévaluées ({len(overs)}) — à éviter"):
    st.caption("Prix du marché nettement supérieur à la valeur théorique.")
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
                f"<span class='over-badge'>-{abs(card['ecart_pct']):.0f}%</span>",
                unsafe_allow_html=True
            )

st.divider()

# ── Graphiques ──
st.subheader("📊 Vue d'ensemble")
tab1, tab2, tab3 = st.tabs(["Valeur vs Prix", "Top sous-évaluées", "Facteurs par carte"])

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
    ax.set_title("Au-dessus de la ligne = sous-évaluée | En-dessous = surévaluée")
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
    st.caption("Scores normalisés (0-10) par facteur pour les 15 meilleures opportunités")
    top15 = gems.head(15) if len(gems) > 0 else df.head(15)
    factor_labels = {
        "f_scarcity_inv": "Rareté",
        "f_tier":         "Popularité",
        "f_artist":       "Artiste",
        "f_meta":         "Compétitivité",
        "f_hype":         "Hype",
        "f_psa10":        "Grading PSA",
        "f_lifecycle":    "Cycle de vie",
    }
    display_df = top15[["name"] + list(factor_labels.keys())].copy()
    display_df = display_df.rename(columns={**factor_labels, "name": "Carte"})
    # Normaliser pour affichage
    for col in factor_labels.values():
        if col in display_df.columns:
            mn, mx = display_df[col].min(), display_df[col].max()
            if mx > mn:
                display_df[col] = ((display_df[col] - mn) / (mx - mn) * 10).round(1)
    st.dataframe(display_df.set_index("Carte"), use_container_width=True)

st.divider()

# ── Table complète ──
with st.expander("📋 Toutes les cartes analysées"):
    disp = df[["name", "set", "rarity", "artist", "market_price", "Vt", "ecart_pct", "Signal"]].copy()
    disp.columns = ["Carte", "Set", "Rareté", "Artiste", "Prix ($)", "Valeur estimée ($)", "Écart (%)", "Verdict"]
    st.dataframe(disp.sort_values("Écart (%)", ascending=False), use_container_width=True, hide_index=True)

# ── Export ──
st.subheader("📥 Exporter")
export_cols = ["name", "set", "rarity", "artist", "market_price", "Vt", "ecart_pct", "Signal", "tcgplayer_url"]
csv_buf = io.StringIO()
df[export_cols].sort_values("ecart_pct", ascending=False).to_csv(csv_buf, index=False)
st.download_button(
    label="Telecharger le rapport CSV",
    data=csv_buf.getvalue(),
    file_name="fair_value_report.csv",
    mime="text/csv"
)
