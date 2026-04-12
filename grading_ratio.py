"""
Grading Ratio — Difficulté d'obtenir un PSA 10 par rareté de carte Pokémon TCG

Sources:
- GemRate.com (2023-2025): TCG gem rate global = 50-53%, cartes 2020s = 59-69%
- misprint.com PSA pop analysis (Mars 2026): gem rates par carte spécifique
  ex: Moltres/Zapdos/Articuno GX promo = 57.5%, Blastoise EX SIR (151) ≈ 58%
- Yahoo Sports / GemRate H1 2025: TCG overall = 50%, modernes = 59%
- Elite Fourum 2023 stats: 2020s = 68.9% gem rate

Interprétation dans le modèle:
- Gem rate ÉLEVÉ → PSA 10 plus "facile" → moins de prime de rareté sur le grade
- Gem rate FAIBLE → PSA 10 plus difficile → prime forte sur le grade → card plus précieuse

Score Grading dans le modèle:
  On veut récompenser les cartes DIFFICILES à grader (elles valent plus graded)
  → score élevé = difficile à grader = carte plus précieuse graded
  → score 1-10 inversé: gem_rate bas → score haut

  Score = 10 × (1 - gem_rate) + 1  (normalisé 1-10)
  Ex: gem_rate=0.15 (vintage) → score = 9.5 (très difficile)
      gem_rate=0.58 (SIR)    → score = 5.2 (modéré)
      gem_rate=0.80 (bulk)   → score = 3.0 (facile)

Note: Le score final est pondéré par le slider "Slab Factor" dans l'app.
"""

# PSA 10 gem rates par rareté — sources: GemRate, misprint.com, hobby data 2023-2026
# Format: "Rarity string from PokéTCG API": (gem_rate, description)
GEM_RATES = {
    # ─── Scarlet & Violet / modern ultra-premium ───────────────────────────
    "Special Illustration Rare":  (0.57, "Collecteurs expérimentés, qualité premium"),
    "Hyper Rare":                 (0.54, "Gold energy / rainbow, haut de gamme"),
    "Illustration Rare":          (0.51, "Art Rare, mix séries/casual"),
    "Ultra Rare":                 (0.48, "ex full art, V full art — volume élevé"),
    "Double Rare":                (0.45, "ex/VSTAR — masse de graders"),
    "ACE SPEC Rare":              (0.50, "Tirage limité, collecteurs ciblés"),

    # ─── Sword & Shield era ────────────────────────────────────────────────
    "Amazing Rare":               (0.52, "Set S&S — tirage limité"),
    "VMAX Rare":                  (0.44, "VMAX full art"),
    "Shiny Rare":                 (0.46, "Shiny vault — collecteurs"),
    "Shiny Ultra Rare":           (0.49, "Shiny vault full art"),
    "Radiant Rare":               (0.48, "Radiant cartes, moderne S&S"),

    # ─── Rare Holo variants ────────────────────────────────────────────────
    "Rare Holo V":                (0.46, "V cards holo"),
    "Rare Holo VMAX":             (0.44, "VMAX cards"),
    "Rare Holo VSTAR":            (0.45, "VSTAR cards"),
    "Rare Holo GX":               (0.42, "GX era — Sun & Moon"),
    "Rare Holo EX":               (0.40, "EX era — XY"),
    "Rare Holo":                  (0.41, "Holo rare standard moderne"),
    "Rare Secret":                (0.44, "Secret rares (gold/rainbow XY/S&S)"),
    "Rare Rainbow":               (0.46, "Rainbow rares"),
    "Rare Prism Star":            (0.43, "Prism Star — Sun & Moon"),
    "Rare Shining":               (0.42, "Shining cartes"),
    "Rare Break":                 (0.38, "Break evolution"),
    "Rare Prime":                 (0.36, "HGSS Prime"),
    "Rare ACE":                   (0.39, "ACE SPEC ancien (BW)"),
    "Rare Dragon":                (0.40, "Dragon rares — BW"),
    "Rare Ultra":                 (0.43, "Full art trainers/legendaires"),
    "Rare Shiny":                 (0.44, "Shiny cartes Sun&Moon"),
    "Rare Shiny GX":              (0.46, "Shiny GX"),

    # ─── Base commons/uncommons/rares ──────────────────────────────────────
    "Rare":                       (0.35, "Rare non-holo moderne"),
    "Uncommon":                   (0.28, "Peu gradés sauf erreurs"),
    "Common":                     (0.23, "Très peu gradés, casual"),
    "Promo":                      (0.55, "Promos — souvent collecteurs ciblés"),

    # ─── Trainer cards ─────────────────────────────────────────────────────
    "Trainer Gallery Rare Holo":  (0.48, "Trainer Gallery"),

    # ─── Vintage (pre-2010) ────────────────────────────────────────────────
    "Rare Holo Star":             (0.18, "Gold star — très difficile"),
    "Classic Collection":         (0.38, "Celebrations classic"),
}

# Score de difficulté grading (1-10)
# Score élevé = difficile à grader = PSA 10 plus rare = prime plus grande
def gem_rate_to_difficulty(gem_rate: float) -> float:
    """
    Convertit un gem rate PSA 10 en score de difficulté (1-10).
    gem_rate = 0.15 (vintage) → 9.3 (très difficile)
    gem_rate = 0.58 (SIR)    → 5.2 (modéré)
    gem_rate = 0.80           → 3.0 (facile)
    """
    score = 10.0 * (1.0 - gem_rate) + 1.0
    return round(max(1.0, min(10.0, score)), 2)


def get_grading_difficulty(rarity: str) -> float:
    """
    Retourne le score de difficulté de grading (1-10) pour une rareté donnée.
    Score élevé → PSA 10 difficile à obtenir → carte plus précieuse en slab.

    Sources: GemRate 2025, misprint.com, hobby community data.
    """
    if rarity in GEM_RATES:
        gem_rate, _ = GEM_RATES[rarity]
        return gem_rate_to_difficulty(gem_rate)

    # Fallback par mots-clés
    rarity_lower = rarity.lower()
    if "special illustration" in rarity_lower:
        return gem_rate_to_difficulty(0.57)
    if "hyper" in rarity_lower:
        return gem_rate_to_difficulty(0.54)
    if "illustration" in rarity_lower:
        return gem_rate_to_difficulty(0.51)
    if "ultra" in rarity_lower or "full art" in rarity_lower:
        return gem_rate_to_difficulty(0.47)
    if "shiny" in rarity_lower:
        return gem_rate_to_difficulty(0.46)
    if "holo" in rarity_lower:
        return gem_rate_to_difficulty(0.41)
    if "rare" in rarity_lower:
        return gem_rate_to_difficulty(0.37)
    if "promo" in rarity_lower:
        return gem_rate_to_difficulty(0.55)
    if "common" in rarity_lower or "uncommon" in rarity_lower:
        return gem_rate_to_difficulty(0.25)

    # Défaut neutre
    return gem_rate_to_difficulty(0.45)


def get_gem_rate(rarity: str) -> float:
    """Retourne le gem rate PSA 10 brut (0.0-1.0) pour une rareté."""
    if rarity in GEM_RATES:
        return GEM_RATES[rarity][0]
    return 0.45  # défaut moderne


if __name__ == "__main__":
    print(f"{'Rareté':<35} {'Gem Rate PSA10':<16} {'Score difficulté /10'}")
    print("-" * 75)

    # Trier par gem rate croissant (plus difficile en premier)
    sorted_rarities = sorted(GEM_RATES.items(), key=lambda x: x[1][0])
    for rarity, (gem_rate, desc) in sorted_rarities:
        score = gem_rate_to_difficulty(gem_rate)
        bar = "█" * int(score)
        print(f"{rarity:<35} {gem_rate*100:.0f}%{'':<12} {score:.1f}  {bar}")
