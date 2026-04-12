"""
Popularité Pokémon — Source principale: AV Club "The 150 Best Pokemon" (Nov 2024)
https://www.avclub.com/the-top-100-pokemon-of-all-time

Scoring:
- Rank 1   → 10.0
- Rank 150 → 4.0
- Hors top 150 (bulk / Trainers) → 2.0

Formula: score = 10.0 - (rank - 1) / 149.0 * 6.0

Note: Certains Pokémon du vrai top 50 ne sont pas dans le HTML statique (page JS).
Leurs rangs sont estimés (* = estimation) basés sur d'autres classements de référence.
"""

# Format: "nom_lowercase": rank (1 = meilleur)
AVCLUB_RANKINGS = {
    # ── TOP 10 ──
    "mewtwo": 1,
    "charizard": 4,
    "rayquaza": 5,
    "gengar": 6,
    "blaziken": 7,
    "mimikyu": 8,
    "greninja": 9,
    "garchomp": 10,

    # ── TOP 11-30 ──
    "decidueye": 12,
    "jigglypuff": 13,
    "metagross": 14,
    "wobbuffet": 15,
    "gyarados": 17,
    "arcanine": 18,
    "deoxys": 19,
    "venusaur": 20,
    "dialga": 21,
    "nidoking": 23,
    "flygon": 25,
    "alakazam": 26,
    "eevee": 27,
    "ampharos": 28,
    "torterra": 29,
    "snorlax": 30,

    # ── TOP 31-60 ──
    "weavile": 31,
    "arceus": 32,
    "aggron": 33,
    "rotom": 34,
    "gardevoir": 36,
    "salamence": 37,
    "mew": 38,
    "luxray": 39,
    "ninetales": 40,
    "sharpedo": 41,
    "ditto": 42,
    "bidoof": 43,
    "giratina": 49,
    "umbreon": 55,
    "empoleon": 57,
    "tyranitar": 60,

    # ── TOP 61-100 ──
    "slowpoke": 61,
    "corviknight": 63,
    "milotic": 64,
    "yveltal": 65,
    "togepi": 66,
    "jolteon": 67,
    "aegislash": 68,
    "typhlosion": 69,
    "espurr": 70,
    "shedinja": 71,
    "bewear": 72,
    "lucario": 73,
    "azumarill": 74,
    "zoroark": 75,
    "kabutops": 76,
    "shuckle": 77,
    "eelektross": 78,
    "sableye": 79,
    "tapu koko": 80,
    "electrode": 81,
    "palossand": 82,
    "camerupt": 83,
    "mudkip": 84,
    "silvally": 85,
    "smeargle": 86,
    "scizor": 88,
    "tyrantrum": 89,
    "machamp": 90,
    "drifloon": 91,
    "absol": 92,
    "houndoom": 93,
    "hariyama": 94,
    "dragapult": 95,
    "escavalier": 96,
    "castform": 97,
    "pangoro": 98,
    "porygon": 99,
    "altaria": 100,

    # ── TOP 101-150 ──
    "incineroar": 101,
    "vikavolt": 102,
    "rillaboom": 103,
    "coalossal": 104,
    "copperajah": 105,
    "toxtricity": 106,
    "rhydon": 107,
    "lugia": 108,
    "heatran": 109,
    "ursaring": 110,
    "crobat": 111,
    "tinkaton": 112,
    "duraludon": 113,
    "squirtle": 114,
    "hydreigon": 115,
    "skarmory": 116,
    "manectric": 117,
    "hatterene": 118,
    "flapple": 119,
    "glalie": 120,
    "litten": 121,
    "wishiwashi": 122,
    "entei": 124,
    "rowlet": 125,
    "snom": 126,
    "yamask": 127,
    "sudowoodo": 128,
    "magnezone": 129,
    "rattata": 130,
    "pachirisu": 131,
    "cinderace": 132,
    "torkoal": 133,
    "croagunk": 134,
    "lapras": 135,
    "wooloo": 136,
    "floatzel": 137,
    "latios": 138,
    "latias": 138,
    "wailord": 139,
    "talonflame": 140,
    "trevenant": 141,
    "amoonguss": 142,
    "miltank": 143,
    "darkrai": 144,
    "ludicolo": 145,
    "bellibolt": 146,
    "garbodor": 147,
    "cramorant": 148,
    "roserade": 149,

    # ── Estimations top 50 (page JS non accessible) ──
    # Basé sur culture TCG + autres classements de référence
    "pikachu": 5,        # mascotte officielle
    "blastoise": 15,
    "sylveon": 20,
    "vaporeon": 22,
    "espeon": 25,
    "kyogre": 30,
    "groudon": 35,
    "glaceon": 40,
    "flareon": 45,
    "suicune": 47,       # confirmé dans le scrape
    "zapdos": 46,
    "heracross": 47,
    "palkia": 55,
    "zacian": 60,
    "raikou": 65,
    "raichu": 70,
    "eternatus": 75,
    "chandelure": 52,
    "blissey": 16,
    "dragonite": 2,      # confirmé #2 dans le scrape
    "ho-oh": 87,
    "runerigus": 127,
    "zamazenta": 62,
    "calyrex": 75,
    "spectrier": 80,
    "inteleon": 97,
    "cinccino": 131,
}

# Aliases pour les noms de cartes TCG (ex: "Charizard ex" → "charizard")
ALIASES = {
    "sirfetch'd": 146,
    "sirfetchd": 146,
    "marowak": 35,
    "alolan marowak": 35,
    "ho oh": 87,
    "porygon-z": 99,
    "porygon z": 99,
    "tapu": 80,
    "rapidash": 123,
    "galarian rapidash": 123,
    "galarian": 35,      # generic galarian = midtier
}

def rank_to_score(rank: int) -> float:
    """Rang 1 → 10.0 | Rang 150 → 4.0"""
    return round(max(4.0, min(10.0, 10.0 - (rank - 1) / 149.0 * 6.0)), 2)

def get_popularity_score(card_name: str) -> float:
    """
    Score de popularité 1-10 basé sur classement AV Club.
    - Dans top 150  → 4.0 à 10.0
    - Hors liste    → 2.0 (bulk, Trainers, inconnus)
    """
    name_lower = card_name.lower().strip()

    # Check aliases
    for alias, rank in ALIASES.items():
        if alias in name_lower:
            return rank_to_score(rank)

    # Exact match
    if name_lower in AVCLUB_RANKINGS:
        return rank_to_score(AVCLUB_RANKINGS[name_lower])

    # Partial match (ex: "Charizard ex" → "charizard", "Gardevoir ex" → "gardevoir")
    best_rank = None
    for poke_name, rank in AVCLUB_RANKINGS.items():
        if poke_name in name_lower:
            if best_rank is None or rank < best_rank:
                best_rank = rank

    if best_rank is not None:
        return rank_to_score(best_rank)

    return 2.0   # hors top 150 = bulk / Trainer card


if __name__ == "__main__":
    tests = [
        "Charizard ex", "Mewtwo ex", "Umbreon ex", "Gardevoir ex",
        "Mimikyu ex", "Rayquaza ex", "Pikachu ex", "Greninja ex",
        "Giratina V", "Ho-Oh V", "Lugia V", "Sylveon ex",
        "Blastoise V", "Suicune V", "Jamming Tower", "Iono",
        "Vaporeon ex", "Eevee", "Dialga ex", "Palkia ex",
    ]
    print(f"{'Carte':<30} {'Score /10'}")
    print("-" * 42)
    for name in tests:
        score = get_popularity_score(name)
        print(f"{name:<30} {score:.1f}")
