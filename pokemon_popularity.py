"""
Popularité Pokémon — Source: AV Club "The 150 Best Pokémon" (Nov 2024)
https://www.avclub.com/the-top-100-pokemon-of-all-time

Données extraites directement de l'article complet.

Scoring:
- Rank 1  (Mewtwo)   → 10.0
- Rank 150 (Roserade) → 4.0
- Hors top 150        → 2.0 (bulk, Trainers, inconnus)

Formula: score = 10.0 - (rank - 1) / 149.0 * 6.0
"""

# Format: "nom_lowercase": rank (1 = meilleur)
AVCLUB_RANKINGS = {
    "mewtwo": 1,
    "pikachu": 2,
    "suicune": 3,
    "charizard": 4,
    "rayquaza": 5,
    "gengar": 6,
    "blaziken": 7,
    "mimikyu": 8,
    "greninja": 9,
    "garchomp": 10,
    "missingno": 11,
    "decidueye": 12,
    "jigglypuff": 13,
    "metagross": 14,
    "wobbuffet": 15,
    "blissey": 16,
    "gyarados": 17,
    "arcanine": 18,
    "deoxys": 19,
    "venusaur": 20,
    "dialga": 21,
    "toxapex": 22,
    "nidoking": 23,
    "dragonite": 24,
    "flygon": 25,
    "alakazam": 26,
    "eevee": 27,
    "ampharos": 28,
    "torterra": 29,
    "snorlax": 30,
    "weavile": 31,
    "arceus": 32,
    "aggron": 33,
    "rotom": 34,
    "alolan marowak": 35,
    "marowak": 35,
    "gardevoir": 36,
    "salamence": 37,
    "mew": 38,
    "luxray": 39,
    "ninetales": 40,
    "sharpedo": 41,
    "ditto": 42,
    "bidoof": 43,
    "xurkitree": 44,
    "serperior": 45,
    "zapdos": 46,
    "heracross": 47,
    "magcargo": 48,
    "giratina": 49,
    "hawlucha": 50,
    "zygarde": 51,
    "chandelure": 52,
    "tauros": 53,
    "omanyte": 54,
    "umbreon": 55,
    "gliscor": 56,
    "empoleon": 57,
    "vivillon": 58,
    "ferrothorn": 59,
    "tyranitar": 60,
    "slowpoke": 61,
    "steelix": 62,
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
    "ho-oh": 87,
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
    "galarian rapidash": 123,
    "rapidash": 123,
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
    "sirfetch'd": 147,
    "sirfetchd": 147,
    "garbodor": 148,
    "cramorant": 149,
    "roserade": 150,
}

# Aliases supplémentaires pour matcher les noms de cartes TCG
ALIASES = {
    "ho oh": 87,
    "ho-oh": 87,
    "porygon-z": 99,
    "porygon z": 99,
    "porygon2": 99,
    "tapu koko": 80,
    "tapu lele": 80,
    "tapu bulu": 80,
    "tapu fini": 80,
    "alolan": 35,
    "galarian": 61,   # slowpoke region -> midtier
}

def rank_to_score(rank: int) -> float:
    """Rang 1 → 10.0 | Rang 150 → 4.0"""
    return round(max(4.0, min(10.0, 10.0 - (rank - 1) / 149.0 * 6.0)), 2)

def get_popularity_score(card_name: str) -> float:
    """
    Score de popularité 1-10 basé sur classement AV Club (150 Pokémon).
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
        ("Mewtwo ex",       1),
        ("Pikachu ex",      2),
        ("Suicune V",       3),
        ("Charizard ex",    4),
        ("Rayquaza ex",     5),
        ("Gengar ex",       6),
        ("Mimikyu ex",      8),
        ("Greninja ex",     9),
        ("Garchomp ex",     10),
        ("Gardevoir ex",    36),
        ("Umbreon ex",      55),
        ("Lugia V",         108),
        ("Lapras V",        135),
        ("Jamming Tower",   None),
        ("Iono",            None),
        ("Ho-Oh V",         87),
        ("Dialga ex",       21),
        ("Giratina V",      49),
        ("Sylveon ex",      None),  # pas dans la liste -> 2.0
        ("Eevee",           27),
    ]
    print(f"{'Carte':<30} {'Rang AV Club':<15} {'Score /10'}")
    print("-" * 55)
    for name, expected in tests:
        score = get_popularity_score(name)
        tag = "" if expected else "[hors liste]"
        print(f"{name:<30} #{str(expected) if expected else '-':<14} {score:.1f}  {tag}")
