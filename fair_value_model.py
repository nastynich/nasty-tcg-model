"""
=============================================================
 Nasty TCG Fair Value Model — Pokémon Card Pricing Engine
=============================================================
Auteur   : Nasty (pour Nich)
Objectif : Calculer la Valeur Théorique (Vt) d'une carte et
           identifier les cartes sous-évaluées (Gems).

Formule de base :
  Vt = (S * w1) + (C * w2) + (A * w3) + (M * w4) + (G * w5) + (H * w6)
  Alpha = (Vt - Pm) / Pm

Variables :
  S  = Scarcity          (basé sur pull rate, normalisé 0-100)
  C  = Character Tier    (1 à 10)
  A  = Art Score         (1 à 10)
  M  = Meta Relevance    (0 à 10)
  G  = Grading Ratio     (0 à 10, PSA 10 pop / total graded)
  H  = Sentiment/Hype    (0 à 10, vélocité des ventes)
  Pm = Prix marché actuel (en USD)
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# 1. CHARGEMENT / SIMULATION DES DONNÉES
# ─────────────────────────────────────────────

def load_data(filepath: str = None) -> pd.DataFrame:
    """
    Charge un CSV ou génère des données simulées si aucun fichier n'est fourni.
    Colonnes attendues dans le CSV :
        name, set, rarity, pull_rate_per_pack, character_tier,
        art_score, meta_relevance, psa10_ratio, hype_score, market_price
    """
    if filepath:
        df = pd.read_csv(filepath)
        print(f"✅ Données chargées : {len(df)} cartes depuis '{filepath}'")
    else:
        print("⚠️  Aucun fichier fourni — génération de données simulées.")
        df = simulate_data()
    return df


def simulate_data(n: int = 50) -> pd.DataFrame:
    """Génère un dataset simulé pour tester le modèle."""
    np.random.seed(42)

    names = [
        "Charizard ex SIR", "Umbreon ex SIR", "Mewtwo ex SIR",
        "Pikachu ex FA", "Lugia V Alt Art", "Rayquaza VMAX Alt",
        "Gengar ex IR", "Eevee Full Art", "Mew ex SIR", "Snorlax V FA",
        "Blastoise ex SIR", "Venusaur ex FA", "Jolteon ex SIR",
        "Sylveon V Alt Art", "Gardevoir ex SIR", "Greninja ex FA",
        "Togekiss ex SIR", "Alakazam ex IR", "Espeon ex SIR",
        "Vaporeon ex FA"
    ] + [f"Card #{i}" for i in range(30)]

    rarity_map = {
        "SIR": {"pull_rate": 1/1440, "art_score": 10},
        "Alt Art": {"pull_rate": 1/720, "art_score": 9},
        "FA": {"pull_rate": 1/288, "art_score": 7},
        "IR": {"pull_rate": 1/144, "art_score": 6},
        "SR": {"pull_rate": 1/72, "art_score": 5},
        "Rare": {"pull_rate": 1/10, "art_score": 3},
    }

    rarities = np.random.choice(list(rarity_map.keys()), n)

    data = {
        "name": names[:n],
        "rarity": rarities,
        "pull_rate_per_pack": [rarity_map[r]["pull_rate"] for r in rarities],
        "character_tier": np.random.randint(1, 11, n),
        "art_score": [rarity_map[r]["art_score"] + np.random.uniform(-1, 1) for r in rarities],
        "meta_relevance": np.random.uniform(0, 10, n),
        "psa10_ratio": np.random.uniform(0, 10, n),
        "hype_score": np.random.uniform(0, 10, n),
        "market_price": np.random.uniform(5, 500, n),
    }

    return pd.DataFrame(data)


# ─────────────────────────────────────────────
# 2. FEATURE ENGINEERING — CALCUL DE LA SCARCITY
# ─────────────────────────────────────────────

def compute_scarcity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforme le pull rate brut en score de Scarcity normalisé (0 à 100).
    Logique : plus c'est rare (pull rate bas), plus le score est élevé.
    On utilise -log(pull_rate) puis on normalise entre 0 et 100.
    """
    df = df.copy()
    df["scarcity_raw"] = -np.log(df["pull_rate_per_pack"])
    scaler = MinMaxScaler(feature_range=(0, 100))
    df["scarcity"] = scaler.fit_transform(df[["scarcity_raw"]])
    return df


# ─────────────────────────────────────────────
# 3. CALCUL DE LA FAIR VALUE (Vt)
# ─────────────────────────────────────────────

def compute_fair_value(
    df: pd.DataFrame,
    w1: float = 0.30,  # Scarcity
    w2: float = 0.25,  # Character Tier
    w3: float = 0.15,  # Art Score
    w4: float = 0.15,  # Meta Relevance
    w5: float = 0.08,  # Grading Ratio (PSA10)
    w6: float = 0.07,  # Hype/Sentiment
    price_multiplier: float = 100.0,
) -> pd.DataFrame:
    """
    Calcule la Valeur Théorique (Vt) pondérée et l'Alpha.

    Formule :
      Vt_raw = (S*w1 + C_norm*w2 + A_norm*w3 + M_norm*w4 + G_norm*w5 + H_norm*w6)
      Vt     = Vt_raw * price_multiplier  (pour ramener à l'échelle USD)
      Alpha  = (Vt - Pm) / Pm

    Paramètres :
      w1..w6           : Poids de chaque variable (doivent sommer à ~1.0)
      price_multiplier : Facteur d'échelle pour convertir le score en USD
    """
    df = df.copy()

    # Normaliser les variables sur 0-100 pour uniformité
    scaler = MinMaxScaler(feature_range=(0, 100))
    for col in ["character_tier", "art_score", "meta_relevance", "psa10_ratio", "hype_score"]:
        df[f"{col}_norm"] = scaler.fit_transform(df[[col]])

    # Calcul Vt
    df["Vt"] = (
        df["scarcity"]             * w1 +
        df["character_tier_norm"]  * w2 +
        df["art_score_norm"]       * w3 +
        df["meta_relevance_norm"]  * w4 +
        df["psa10_ratio_norm"]     * w5 +
        df["hype_score_norm"]      * w6
    ) * price_multiplier

    # Calcul Alpha
    df["Alpha"] = (df["Vt"] - df["market_price"]) / df["market_price"]

    # Classification
    df["Signal"] = df["Alpha"].apply(
        lambda x: "🟢 GEM" if x > 0.20 else ("🔴 OVERVALUED" if x < -0.20 else "🟡 FAIR")
    )

    return df


# ─────────────────────────────────────────────
# 4. MODÈLE ML — RANDOM FOREST (optionnel)
# ─────────────────────────────────────────────

def train_ml_model(df: pd.DataFrame, model_type: str = "rf") -> dict:
    """
    Entraîne un modèle ML pour prédire le market_price à partir des features.
    Utile pour valider si vos poids manuels font sens.

    model_type : 'rf' (Random Forest) ou 'lr' (Linear Regression)
    """
    features = ["scarcity", "character_tier", "art_score",
                 "meta_relevance", "psa10_ratio", "hype_score"]
    target = "market_price"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    if model_type == "rf":
        model = RandomForestRegressor(n_estimators=100, random_state=42)
    else:
        model = LinearRegression()

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae  = mean_absolute_error(y_test, y_pred)
    r2   = r2_score(y_test, y_pred)

    print(f"\n📊 Modèle {model_type.upper()} — MAE: ${mae:.2f} | R²: {r2:.3f}")

    # Feature importance (RF seulement)
    if model_type == "rf":
        importances = pd.Series(model.feature_importances_, index=features).sort_values(ascending=False)
        print("\n🔍 Feature Importances :")
        print(importances.to_string())

    return {"model": model, "mae": mae, "r2": r2}


# ─────────────────────────────────────────────
# 5. VISUALISATIONS
# ─────────────────────────────────────────────

def plot_results(df: pd.DataFrame, top_n: int = 20):
    """Génère les visualisations clés du modèle."""

    df_top = df.nlargest(top_n, "Alpha")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("🎴 Nasty TCG Fair Value Model — Pokémon", fontsize=16, fontweight="bold")

    # 1. Top Gems par Alpha
    colors = ["#2ecc71" if s == "🟢 GEM" else "#e74c3c" if s == "🔴 OVERVALUED" else "#f39c12"
              for s in df_top["Signal"]]
    axes[0, 0].barh(df_top["name"], df_top["Alpha"], color=colors)
    axes[0, 0].axvline(0, color="black", linewidth=0.8, linestyle="--")
    axes[0, 0].set_title(f"Top {top_n} cartes par Alpha")
    axes[0, 0].set_xlabel("Alpha = (Vt - Pm) / Pm")

    # 2. Scatter Vt vs Pm
    signal_colors = {"🟢 GEM": "#2ecc71", "🔴 OVERVALUED": "#e74c3c", "🟡 FAIR": "#f39c12"}
    for signal, group in df.groupby("Signal"):
        axes[0, 1].scatter(group["market_price"], group["Vt"],
                           label=signal, color=signal_colors.get(signal, "gray"), alpha=0.7)
    max_val = max(df["market_price"].max(), df["Vt"].max())
    axes[0, 1].plot([0, max_val], [0, max_val], "k--", linewidth=0.8, label="Vt = Pm (Fair)")
    axes[0, 1].set_title("Fair Value (Vt) vs Prix Marché (Pm)")
    axes[0, 1].set_xlabel("Prix Marché ($)")
    axes[0, 1].set_ylabel("Fair Value ($)")
    axes[0, 1].legend()

    # 3. Distribution des Alpha
    axes[1, 0].hist(df["Alpha"], bins=20, color="#3498db", edgecolor="white", alpha=0.8)
    axes[1, 0].axvline(0.20, color="#2ecc71", linestyle="--", label="Seuil GEM (+20%)")
    axes[1, 0].axvline(-0.20, color="#e74c3c", linestyle="--", label="Seuil Overvalued (-20%)")
    axes[1, 0].set_title("Distribution des Alpha")
    axes[1, 0].set_xlabel("Alpha")
    axes[1, 0].legend()

    # 4. Signal pie chart
    signal_counts = df["Signal"].value_counts()
    axes[1, 1].pie(
        signal_counts.values,
        labels=signal_counts.index,
        colors=[signal_colors.get(s, "gray") for s in signal_counts.index],
        autopct="%1.0f%%",
        startangle=90
    )
    axes[1, 1].set_title("Répartition des Signaux")

    plt.tight_layout()
    plt.savefig("tcg_model/results.png", dpi=150, bbox_inches="tight")
    plt.show()
    print("✅ Graphiques sauvegardés dans 'tcg_model/results.png'")


# ─────────────────────────────────────────────
# 6. RAPPORT FINAL
# ─────────────────────────────────────────────

def print_report(df: pd.DataFrame):
    """Affiche le classement final des cartes."""
    cols = ["name", "rarity", "market_price", "Vt", "Alpha", "Signal"]
    report = df[cols].sort_values("Alpha", ascending=False)

    print("\n" + "="*70)
    print("  🏆 CLASSEMENT FAIR VALUE — TOP BUY (GEMS)")
    print("="*70)
    gems = report[report["Signal"] == "🟢 GEM"]
    print(gems.to_string(index=False))

    print("\n" + "="*70)
    print("  ⚠️  OVERVALUED — À ÉVITER / SHORTER")
    print("="*70)
    over = report[report["Signal"] == "🔴 OVERVALUED"]
    print(over.to_string(index=False))

    return report


# ─────────────────────────────────────────────
# 7. PIPELINE PRINCIPAL
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Lancement du Nasty TCG Fair Value Model...\n")

    # --- Paramètres ajustables ---
    WEIGHTS = {
        "w1": 0.30,  # Scarcity
        "w2": 0.25,  # Character Tier
        "w3": 0.15,  # Art Score
        "w4": 0.15,  # Meta Relevance
        "w5": 0.08,  # Grading Ratio
        "w6": 0.07,  # Hype/Sentiment
    }
    PRICE_MULTIPLIER = 100.0  # Ajuster selon l'échelle de tes prix

    # --- Pipeline ---
    df = load_data()                        # ou load_data("ton_fichier.csv")
    df = compute_scarcity(df)
    df = compute_fair_value(df, **WEIGHTS, price_multiplier=PRICE_MULTIPLIER)

    # --- Rapport ---
    report = print_report(df)

    # --- ML (optionnel) ---
    # ml = train_ml_model(df, model_type="rf")

    # --- Visualisations ---
    plot_results(df, top_n=20)

    # --- Export ---
    report.to_csv("tcg_model/fair_value_report.csv", index=False)
    print("\n✅ Rapport exporté : 'tcg_model/fair_value_report.csv'")
