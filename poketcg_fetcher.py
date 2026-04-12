"""
=============================================================
 Nasty TCG — PokéTCG.io API Fetcher
=============================================================
Fetche les vraies données de cartes + prix TCGPlayer
via l'API PokéTCG.io (v2).

Utilisation :
    python poketcg_fetcher.py

Ou dans ton pipeline :
    from poketcg_fetcher import fetch_cards_for_model
    df = fetch_cards_for_model(query="rarity:Special Illustration Rare", max_cards=50)
=============================================================
"""

import requests
import pandas as pd
import numpy as np
import time
import os
from typing import Optional

# ─── Clé API (optionnelle — augmente le rate limit) ───
# Sans clé : 1 000 req/jour | Avec clé : 20 000 req/jour
# Mettre ta clé ici ou dans la variable d'env POKETCG_API_KEY
API_KEY = os.environ.get("POKETCG_API_KEY", "")
BASE_URL = "https://api.pokemontcg.io/v2"


# ─────────────────────────────────────────────
# MAPPING RARETÉ → PULL RATE & ART SCORE
# ─────────────────────────────────────────────

RARITY_METADATA = {
    # Format : rarity_string : (pull_rate_per_pack, art_score)
    "Special Illustration Rare": (1 / 1440, 10),
    "Hyper Rare":                 (1 / 360,  9),
    "Illustration Rare":          (1 / 144,  8),
    "Ultra Rare":                 (1 / 72,   7),
    "Double Rare":                (1 / 48,   6),
    "Full Art":                   (1 / 36,   7),
    "Rare Holo V":                (1 / 24,   6),
    "Rare Holo VMAX":             (1 / 36,   7),
    "Rare Holo VSTAR":            (1 / 36,   7),
    "Rare Holo EX":               (1 / 24,   6),
    "Rare Holo":                  (1 / 12,   5),
    "Rare":                       (1 / 10,   4),
    "Uncommon":                   (1 / 3,    2),
    "Common":                     (1 / 1,    1),
}

# Pull rate par défaut si rareté inconnue
DEFAULT_PULL_RATE  = 1 / 20
DEFAULT_ART_SCORE  = 4

# Pokémon Tier 1 (personnages iconiques → character_tier élevé)
TIER_MAP = {
    10: ["charizard", "umbreon", "mewtwo", "rayquaza", "lugia"],
    9:  ["pikachu", "eevee", "mew", "gengar", "snorlax", "espeon", "vaporeon"],
    8:  ["jolteon", "flareon", "sylveon", "gardevoir", "blastoise", "venusaur"],
    7:  ["greninja", "lucario", "togekiss", "alakazam", "dragonite"],
    6:  ["gyarados", "arcanine", "ninetales", "absol", "flygon"],
}

def get_character_tier(name: str) -> int:
    """Retourne le tier du personnage basé sur son nom."""
    name_lower = name.lower()
    for tier, names in TIER_MAP.items():
        if any(n in name_lower for n in names):
            return tier
    return 3  # Tier par défaut


# ─────────────────────────────────────────────
# FETCH CARDS DEPUIS L'API
# ─────────────────────────────────────────────

def _get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-Api-Key"] = API_KEY
    return headers


def fetch_raw_cards(
    query: str = "rarity:Special Illustration Rare",
    page: int = 1,
    page_size: int = 50,
    order_by: str = "-set.releaseDate",
) -> list:
    """
    Fetche une page de cartes depuis PokéTCG.io.

    Exemples de queries utiles :
      "rarity:Special Illustration Rare"
      "rarity:Illustration Rare"
      "rarity:Ultra Rare"
      "set.name:Prismatic Evolutions"
      "name:charizard rarity:Special Illustration Rare"
      "(rarity:Special Illustration Rare OR rarity:Illustration Rare)"
    """
    params = {
        "q":        query,
        "page":     page,
        "pageSize": page_size,
        "orderBy":  order_by,
    }

    print(f"🔍 Fetching: '{query}' — page {page} ({page_size} cartes max)...")

    resp = requests.get(f"{BASE_URL}/cards", headers=_get_headers(), params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    cards = data.get("data", [])
    total = data.get("totalCount", 0)
    print(f"   ✅ {len(cards)} cartes récupérées (total disponible: {total})")
    return cards


def fetch_all_pages(
    query: str,
    max_cards: int = 200,
    page_size: int = 100,
) -> list:
    """Pagine automatiquement jusqu'à max_cards cartes."""
    all_cards = []
    page = 1

    while len(all_cards) < max_cards:
        remaining = max_cards - len(all_cards)
        size = min(page_size, remaining, 250)

        cards = fetch_raw_cards(query=query, page=page, page_size=size)
        if not cards:
            break

        all_cards.extend(cards)
        if len(cards) < size:
            break  # Dernière page atteinte

        page += 1
        time.sleep(0.2)  # Gentle rate limiting

    return all_cards[:max_cards]


# ─────────────────────────────────────────────
# PARSER : JSON API → DataFrame modèle
# ─────────────────────────────────────────────

def parse_card(card: dict) -> Optional[dict]:
    """
    Transforme un objet carte de l'API en ligne pour notre modèle.
    Retourne None si aucun prix disponible.
    """
    # ── Prix marché ──
    tcgplayer = card.get("tcgplayer", {})
    prices    = tcgplayer.get("prices", {})

    market_price = None
    price_type   = None

    # Cherche dans l'ordre de préférence
    for ptype in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil", "unlimitedHolofoil"]:
        if ptype in prices and prices[ptype].get("market"):
            market_price = prices[ptype]["market"]
            price_type   = ptype
            break

    if market_price is None or market_price <= 0:
        return None  # Pas de prix → on skip

    # ── Rareté ──
    rarity      = card.get("rarity", "Unknown")
    pull_rate, art_score_base = RARITY_METADATA.get(rarity, (DEFAULT_PULL_RATE, DEFAULT_ART_SCORE))

    # ── Set info ──
    set_info    = card.get("set", {})
    set_name    = set_info.get("name", "Unknown")
    set_total   = set_info.get("total", 1)
    card_number = card.get("number", "0")

    # ── Character tier ──
    char_tier = get_character_tier(card.get("name", ""))

    # ── Estimation Meta Relevance (basé sur les légalités) ──
    legalities  = card.get("legalities", {})
    if legalities.get("standard") == "Legal":
        meta_rel = 7.0
    elif legalities.get("expanded") == "Legal":
        meta_rel = 4.0
    else:
        meta_rel = 1.0

    # ── PSA10 ratio approximé (on n'a pas les vraies données pop → heuristique) ──
    # Pour l'instant on estime basé sur la rareté et le prix
    # 0 = facile à grader / commun | 10 = pop très basse
    psa10_ratio = min(10, max(0, round((1 / (pull_rate * 1000 + 0.01)) * 0.5 + (market_price / 500) * 3, 1)))

    # ── Hype score (basé sur le prix relatif dans le set) ──
    hype_score  = min(10, max(0, round(np.log1p(market_price) / np.log1p(500) * 10, 1)))

    return {
        "id":                card.get("id", ""),
        "name":              card.get("name", "Unknown"),
        "set":               set_name,
        "rarity":            rarity,
        "card_number":       card_number,
        "pull_rate_per_pack": pull_rate,
        "character_tier":    char_tier,
        "art_score":         min(10, max(1, art_score_base + np.random.uniform(-0.5, 0.5))),
        "meta_relevance":    meta_rel,
        "psa10_ratio":       psa10_ratio,
        "hype_score":        hype_score,
        "market_price":      round(market_price, 2),
        "price_type":        price_type,
        "tcgplayer_url":     tcgplayer.get("url", ""),
        "image_url":         card.get("images", {}).get("small", ""),
    }


def fetch_cards_for_model(
    query: str = "rarity:Special Illustration Rare",
    max_cards: int = 100,
) -> pd.DataFrame:
    """
    Fonction principale : fetche les cartes et retourne un DataFrame
    prêt pour le modèle Fair Value.

    Paramètres :
        query     : Filtre PokéTCG.io (voir exemples ci-dessus)
        max_cards : Nombre max de cartes à récupérer

    Retourne :
        pd.DataFrame avec toutes les colonnes nécessaires au modèle
    """
    raw_cards = fetch_all_pages(query=query, max_cards=max_cards)

    rows = []
    skipped = 0
    for card in raw_cards:
        parsed = parse_card(card)
        if parsed:
            rows.append(parsed)
        else:
            skipped += 1

    if skipped > 0:
        print(f"   ⚠️  {skipped} cartes ignorées (pas de prix disponible)")

    if not rows:
        print("❌ Aucune carte avec prix disponible. Essaie une autre query.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    print(f"\n✅ DataFrame prêt : {len(df)} cartes avec prix")
    return df


# ─────────────────────────────────────────────
# QUERIES PRÉDÉFINIES (helpers)
# ─────────────────────────────────────────────

PRESET_QUERIES = {
    "sir_all":         "rarity:\"Special Illustration Rare\"",
    "ir_all":          "rarity:\"Illustration Rare\"",
    "prismatic_evo":   "set.name:\"Prismatic Evolutions\"",
    "scarlet_violet":  "set.series:\"Scarlet & Violet\" (rarity:\"Special Illustration Rare\" OR rarity:\"Illustration Rare\")",
    "charizard":       "name:charizard",
    "top_rares":       "(rarity:\"Special Illustration Rare\" OR rarity:\"Hyper Rare\" OR rarity:\"Illustration Rare\")",
}

def fetch_preset(preset_name: str, max_cards: int = 100) -> pd.DataFrame:
    """Raccourci pour les queries prédéfinies."""
    if preset_name not in PRESET_QUERIES:
        print(f"❌ Preset inconnu. Options : {list(PRESET_QUERIES.keys())}")
        return pd.DataFrame()
    return fetch_cards_for_model(PRESET_QUERIES[preset_name], max_cards=max_cards)


# ─────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Test du fetcher PokéTCG.io...\n")

    # Fetch les Special Illustration Rares récentes
    df = fetch_cards_for_model(
        query='rarity:"Special Illustration Rare"',
        max_cards=30
    )

    if not df.empty:
        print("\n📋 Aperçu des données récupérées :")
        print(df[["name", "set", "rarity", "market_price", "character_tier"]].to_string(index=False))

        # Export CSV
        df.to_csv("tcg_model/live_cards.csv", index=False)
        print("\n✅ Exporté dans 'tcg_model/live_cards.csv'")
