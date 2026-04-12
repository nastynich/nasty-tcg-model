"""
Scores de compétitivité — Source: Limitless TCG (scrape live)
Basé sur 46 decks compétitifs top-tier (Régionaux, Internationaux, Worlds)
Score 1-10 calculé depuis: présence dans X decks + % moyen d'utilisation
"""

# Format: "SET-NUMBER": meta_score (1.0-10.0)
# Uniquement les cartes présentes dans des decks de tournoi
META_SCORES = {
    "ASC-142": 10.00,  # 19 decks, avg 94.3% — Gardevoir, Miraidon
    "MEG-114": 8.71,  # 23 decks, avg 47.6% — Miraidon, Charizard
    "MEG-119": 8.27,  # 15 decks, avg 79.2% — Gardevoir, Dragapult
    "MEG-131": 7.84,  # 18 decks, avg 55.1% — Gardevoir, Miraidon
    "ASC-196": 7.56,  # 20 decks, avg 39.2% — Gardevoir, Raging Bolt
    "TWM-163": 7.22,  # 7 decks, avg 98.2% — Gardevoir, Froslass Munkidori
    "SVI-181": 6.97,  # 12 decks, avg 67.7% — Gardevoir, Miraidon
    "TWM-141": 6.81,  # 5 decks, avg 99.8% — Miraidon, Bloodmoon Ursaluna
    "TEF-144": 6.76,  # 12 decks, avg 63.3% — Charizard, Dragapult
    "ASC-39": 6.51,  # 4 decks, avg 98.7% — Festival Lead, Mega Absol Box
    "TWM-95": 6.43,  # 10 decks, avg 66.7% — Gardevoir, Dragapult
    "TWM-64": 6.32,  # 3 decks, avg 100.0% — Flareon, Tera Box
    "MEG-74": 6.30,  # 3 decks, avg 99.5% — Gholdengo, Bloodmoon Ursaluna
    "TEF-157": 6.20,  # 3 decks, avg 97.5% — Miraidon, Raging Bolt
    "DRI-10": 6.20,  # 3 decks, avg 97.5% — Froslass Munkidori, Ethan&#039;s Typhlosion
    "PAR-70": 6.07,  # 2 decks, avg 100.0% — Miraidon, Joltik Box
    "PAR-56": 6.07,  # 2 decks, avg 100.0% — Miraidon, Okidogi
    "WHT-86": 6.07,  # 2 decks, avg 100.0% — Greninja, Rocket&#039;s Honchkrow
    "SCR-118": 6.07,  # 2 decks, avg 100.0% — Flareon, Tera Box
    "DRI-87": 6.07,  # 2 decks, avg 100.0% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "DRI-178": 6.07,  # 2 decks, avg 100.0% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "DRI-182": 6.07,  # 2 decks, avg 100.0% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "MEG-10": 6.07,  # 2 decks, avg 100.0% — Mega Venusaur, Ogerpon Meganium
    "SVI-81": 6.04,  # 2 decks, avg 99.3% — Miraidon, Joltik Box
    "SCR-115": 5.99,  # 2 decks, avg 98.3% — Flareon, Tera Box
    "SCR-142": 5.99,  # 2 decks, avg 98.3% — Flareon, Tera Box
    "PAR-163": 5.97,  # 12 decks, avg 47.1% — Gardevoir, Gholdengo
    "SSP-185": 5.95,  # 2 decks, avg 97.4% — Mega Absol Box, Mega Kangaskhan
    "OBF-186": 5.91,  # 9 decks, avg 61.0% — Gardevoir, Froslass Munkidori
    "SSP-57": 5.91,  # 2 decks, avg 96.5% — Tera Box, Joltik Box
    "TWM-167": 5.88,  # 2 decks, avg 96.0% — Okidogi, Ceruledge
    "MEW-151": 5.87,  # 5 decks, avg 80.5% — Gardevoir, Miraidon
    "SVI-86": 5.83,  # 1 decks, avg 100.0% — Gardevoir
    "PAL-65": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "MEG-45": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "SSP-59": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "BLK-34": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "SVI-170": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "MEG-130": 5.83,  # 1 decks, avg 100.0% — Miraidon
    "PAL-189": 5.83,  # 1 decks, avg 100.0% — Gholdengo
    "TWM-106": 5.83,  # 1 decks, avg 100.0% — Greninja
    "SCR-136": 5.83,  # 1 decks, avg 100.0% — Greninja
    "PRE-54": 5.83,  # 1 decks, avg 100.0% — Bloodmoon Ursaluna
    "SSP-169": 5.83,  # 1 decks, avg 100.0% — Bloodmoon Ursaluna
    "PAL-174": 5.83,  # 1 decks, avg 100.0% — Bloodmoon Ursaluna
    "TWM-111": 5.83,  # 1 decks, avg 100.0% — Okidogi
    "PFL-14": 5.83,  # 1 decks, avg 100.0% — Okidogi
    "TWM-112": 5.83,  # 1 decks, avg 100.0% — Okidogi
    "OBF-80": 5.83,  # 1 decks, avg 100.0% — Okidogi
    "SVI-174": 5.83,  # 1 decks, avg 100.0% — Okidogi
    "SSP-36": 5.83,  # 1 decks, avg 100.0% — Ceruledge
    "PRE-14": 5.83,  # 1 decks, avg 100.0% — Flareon
    "SCR-132": 5.83,  # 1 decks, avg 100.0% — Flareon
    "MEW-132": 5.83,  # 1 decks, avg 100.0% — Tera Box
    "SFA-47": 5.83,  # 1 decks, avg 100.0% — Slowking
    "SFA-54": 5.83,  # 1 decks, avg 100.0% — Slowking
    "SCR-50": 5.83,  # 1 decks, avg 100.0% — Joltik Box
    "DRI-134": 5.83,  # 1 decks, avg 100.0% — Marnie&#039;s Grimmsnarl
    "DRI-135": 5.83,  # 1 decks, avg 100.0% — Marnie&#039;s Grimmsnarl
    "DRI-32": 5.83,  # 1 decks, avg 100.0% — Ethan&#039;s Typhlosion
    "DRI-33": 5.83,  # 1 decks, avg 100.0% — Ethan&#039;s Typhlosion
    "DRI-165": 5.83,  # 1 decks, avg 100.0% — Ethan&#039;s Typhlosion
    "JTG-156": 5.83,  # 1 decks, avg 100.0% — Ethan&#039;s Typhlosion
    "DRI-39": 5.83,  # 1 decks, avg 100.0% — Ho-Oh Armarouge
    "WHT-20": 5.83,  # 1 decks, avg 100.0% — Ho-Oh Armarouge
    "TWM-149": 5.83,  # 1 decks, avg 100.0% — Festival Lead
    "DRI-19": 5.83,  # 1 decks, avg 100.0% — Rocket&#039;s Mewtwo
    "DRI-20": 5.83,  # 1 decks, avg 100.0% — Rocket&#039;s Mewtwo
    "DRI-81": 5.83,  # 1 decks, avg 100.0% — Rocket&#039;s Mewtwo
    "MEG-86": 5.83,  # 1 decks, avg 100.0% — Mega Absol Box
    "MEG-1": 5.83,  # 1 decks, avg 100.0% — Mega Venusaur
    "MEG-2": 5.83,  # 1 decks, avg 100.0% — Mega Venusaur
    "MEG-3": 5.83,  # 1 decks, avg 100.0% — Mega Venusaur
    "PFL-94": 5.83,  # 1 decks, avg 100.0% — Alakazam
    "SSP-191": 5.83,  # 1 decks, avg 100.0% — Alakazam
    "PFL-60": 5.83,  # 1 decks, avg 100.0% — Mega Sharpedo
    "PFL-61": 5.83,  # 1 decks, avg 100.0% — Mega Sharpedo
    "PFL-67": 5.83,  # 1 decks, avg 100.0% — Mega Sharpedo
    "PFL-68": 5.83,  # 1 decks, avg 100.0% — Mega Sharpedo
    "PRE-95": 5.83,  # 1 decks, avg 100.0% — Mega Sharpedo
    "DRI-127": 5.83,  # 1 decks, avg 100.0% — Rocket&#039;s Honchkrow
    "SSP-183": 5.83,  # 1 decks, avg 100.0% — Rocket&#039;s Honchkrow
    "TWM-143": 5.80,  # 2 decks, avg 94.4% — Mega Venusaur, Ogerpon Meganium
    "PAR-86": 5.80,  # 1 decks, avg 99.5% — Gardevoir
    "JTG-97": 5.80,  # 1 decks, avg 99.4% — N&#039;s Zoroark
    "JTG-98": 5.80,  # 1 decks, avg 99.4% — N&#039;s Zoroark
    "TWM-128": 5.80,  # 1 decks, avg 99.4% — Dragapult
    "TWM-129": 5.78,  # 1 decks, avg 99.1% — Dragapult
    "DRI-176": 5.77,  # 2 decks, avg 93.8% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "SFA-62": 5.76,  # 1 decks, avg 98.7% — Crustle
    "TEF-25": 5.76,  # 1 decks, avg 98.6% — Joltik Box
    "MEG-58": 5.73,  # 1 decks, avg 97.9% — Gardevoir
    "DRI-11": 5.70,  # 1 decks, avg 97.4% — Crustle
    "PAR-166": 5.70,  # 1 decks, avg 97.4% — Crustle
    "SVI-118": 5.68,  # 1 decks, avg 97.0% — Dragapult
    "SSP-76": 5.67,  # 7 decks, avg 66.4% — Miraidon, Raging Bolt
    "SVI-182": 5.63,  # 1 decks, avg 96.0% — Ceruledge
    "TWM-145": 5.59,  # 2 decks, avg 90.0% — Miraidon, Ceruledge
    "MEG-59": 5.58,  # 1 decks, avg 94.8% — Gardevoir
    "PFL-91": 5.51,  # 2 decks, avg 88.4% — Crustle, Mega Kangaskhan
    "PAL-185": 5.49,  # 12 decks, avg 37.3% — Gardevoir, Charizard
    "PRE-6": 5.48,  # 1 decks, avg 92.9% — Flareon
    "SSP-177": 5.46,  # 2 decks, avg 87.5% — Ethan&#039;s Typhlosion, Mega Sharpedo
    "DRI-170": 5.46,  # 2 decks, avg 87.5% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "SFA-39": 5.46,  # 2 decks, avg 87.5% — Mega Absol Box, Mega Sharpedo
    "MEG-116": 5.35,  # 5 decks, avg 69.9% — Gholdengo, Bloodmoon Ursaluna
    "PAR-160": 5.29,  # 7 decks, avg 58.6% — Gardevoir, Dragapult
    "DRI-153": 5.22,  # 1 decks, avg 87.5% — Rocket&#039;s Honchkrow
    "DRI-173": 5.16,  # 2 decks, avg 81.2% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "MEG-124": 5.13,  # 1 decks, avg 85.7% — Mega Lucario
    "OBF-164": 5.05,  # 1 decks, avg 84.0% — Charizard
    "PAR-179": 5.03,  # 2 decks, avg 78.7% — Mega Absol Box, Mega Kangaskhan
    "SCR-133": 5.01,  # 6 decks, avg 58.0% — Raging Bolt, Okidogi
    "MEG-54": 4.96,  # 1 decks, avg 82.1% — Alakazam
    "TWM-130": 4.94,  # 1 decks, avg 81.8% — Dragapult
    "SVI-186": 4.91,  # 6 decks, avg 55.9% — Froslass Munkidori, Okidogi
    "PAL-188": 4.90,  # 4 decks, avg 65.9% — Gardevoir, Miraidon
    "SVI-183": 4.88,  # 3 decks, avg 70.5% — Okidogi, Mega Absol Box
    "DRI-171": 4.86,  # 2 decks, avg 75.0% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "DRI-177": 4.86,  # 2 decks, avg 75.0% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "OBF-56": 4.85,  # 1 decks, avg 80.0% — Greninja
    "ASC-198": 4.82,  # 9 decks, avg 38.7% — Dragapult, Froslass Munkidori
    "TEF-161": 4.82,  # 2 decks, avg 74.3% — Crustle, Mega Absol Box
    "SSP-97": 4.81,  # 1 decks, avg 79.2% — Gholdengo
    "JTG-56": 4.75,  # 3 decks, avg 67.8% — Gardevoir, Tera Box
    "SFA-57": 4.75,  # 3 decks, avg 67.8% — Greninja, Okidogi
    "ASC-181": 4.67,  # 7 decks, avg 45.9% — Gholdengo, Froslass Munkidori
    "MEG-117": 4.64,  # 2 decks, avg 70.6% — Mega Venusaur, Ogerpon Meganium
    "PAR-171": 4.63,  # 4 decks, avg 60.3% — Gholdengo, N&#039;s Zoroark
    "TWM-14": 4.61,  # 1 decks, avg 75.0% — Festival Lead
    "TWM-25": 4.59,  # 4 decks, avg 59.5% — Raging Bolt, Tera Box
    "PFL-85": 4.54,  # 2 decks, avg 68.6% — Ethan&#039;s Typhlosion, Alakazam
    "MEE-2": 4.45,  # 7 decks, avg 41.4% — Charizard, Dragapult
    "PRE-75": 4.43,  # 1 decks, avg 71.4% — Flareon
    "ASC-155": 4.42,  # 1 decks, avg 71.2% — N&#039;s Zoroark
    "PAL-173": 4.37,  # 6 decks, avg 44.7% — Gardevoir, Froslass Munkidori
    "PFL-87": 4.33,  # 2 decks, avg 64.3% — Mega Venusaur, Alakazam
    "WHT-80": 4.25,  # 2 decks, avg 62.5% — Ethan&#039;s Typhlosion, Festival Lead
    "DRI-174": 4.25,  # 2 decks, avg 62.5% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "ASC-46": 4.22,  # 2 decks, avg 62.1% — Froslass Munkidori, Marnie&#039;s Grimmsnarl
    "ASC-216": 4.18,  # 3 decks, avg 56.2% — Froslass Munkidori, Okidogi
    "PAR-178": 4.17,  # 1 decks, avg 66.0% — Gardevoir
    "MEE-1": 4.12,  # 9 decks, avg 24.3% — Raging Bolt, Flareon
    "PAL-171": 4.01,  # 5 decks, avg 42.4% — Gardevoir, Gholdengo
    "MEE-7": 4.00,  # 9 decks, avg 22.0% — Gardevoir, Froslass Munkidori
    "TWM-15": 4.00,  # 1 decks, avg 62.5% — Festival Lead
    "DRI-154": 4.00,  # 1 decks, avg 62.5% — Rocket&#039;s Honchkrow
    "DRI-51": 3.94,  # 2 decks, avg 56.2% — Rocket&#039;s Mewtwo, Rocket&#039;s Honchkrow
    "MEG-104": 3.92,  # 2 decks, avg 55.7% — Mega Absol Box, Mega Kangaskhan
    "TWM-57": 3.88,  # 1 decks, avg 60.0% — Greninja
    "MEE-6": 3.86,  # 6 decks, avg 34.3% — Gholdengo, Raging Bolt
    "TEF-145": 3.80,  # 1 decks, avg 58.3% — Slowking
    "PRE-36": 3.77,  # 2 decks, avg 52.7% — Dragapult, Greninja
    "MEG-125": 3.76,  # 6 decks, avg 32.3% — Gardevoir, Charizard
    "MEG-77": 3.74,  # 1 decks, avg 57.1% — Mega Lucario
    "PAR-177": 3.70,  # 2 decks, avg 51.4% — Froslass Munkidori, Marnie&#039;s Grimmsnarl
    "OBF-196": 3.67,  # 2 decks, avg 50.7% — Okidogi, Crustle
    "PRE-35": 3.67,  # 2 decks, avg 50.6% — Dragapult, Greninja
    "JTG-143": 3.65,  # 2 decks, avg 50.3% — Flareon, N&#039;s Zoroark
    "SCR-131": 3.63,  # 4 decks, avg 39.7% — Raging Bolt, Flareon
    "PAL-191": 3.43,  # 2 decks, avg 45.9% — Dragapult, Froslass Munkidori
    "ASC-16": 3.36,  # 4 decks, avg 34.2% — Dragapult, Greninja
    "MEG-75": 3.26,  # 3 decks, avg 37.2% — Gholdengo, Bloodmoon Ursaluna
    "DRI-12": 3.26,  # 1 decks, avg 47.4% — Crustle
    "SCR-114": 3.25,  # 2 decks, avg 42.0% — Flareon, Tera Box
    "PAL-190": 3.21,  # 4 decks, avg 31.0% — Charizard, Ceruledge
    "JTG-159": 3.20,  # 1 decks, avg 46.0% — Crustle
    "MEG-115": 3.14,  # 3 decks, avg 34.7% — Tera Box, Rocket&#039;s Mewtwo
    "PAL-169": 3.12,  # 2 decks, avg 39.5% — Miraidon, Ceruledge
    "JTG-155": 3.12,  # 2 decks, avg 39.5% — Miraidon, Ceruledge
    "MEE-4": 3.11,  # 5 decks, avg 24.0% — Miraidon, Raging Bolt
    "MEG-76": 3.04,  # 1 decks, avg 42.9% — Mega Lucario
    "PAR-170": 3.03,  # 1 decks, avg 42.7% — Raging Bolt
    "TWM-53": 2.90,  # 2 decks, avg 34.9% — Froslass Munkidori, Marnie&#039;s Grimmsnarl
    "PAR-139": 2.83,  # 1 decks, avg 38.6% — Gholdengo
    "TWM-148": 2.80,  # 2 decks, avg 32.8% — Crustle, Alakazam
    "ASC-127": 2.78,  # 1 decks, avg 37.5% — Rocket&#039;s Honchkrow
    "PRE-127": 2.78,  # 1 decks, avg 37.5% — Rocket&#039;s Honchkrow
    "MEE-5": 2.75,  # 5 decks, avg 16.6% — Gardevoir, Dragapult
    "SVI-41": 2.58,  # 1 decks, avg 33.3% — Ho-Oh Armarouge
    "WHT-84": 2.47,  # 2 decks, avg 26.1% — Greninja, Alakazam
    "MEG-55": 2.34,  # 1 decks, avg 28.6% — Alakazam
    "SCR-119": 2.17,  # 1 decks, avg 25.0% — Mega Kangaskhan
    "MEE-8": 2.00,  # 3 decks, avg 11.4% — Gholdengo, Tera Box
    "SSP-143": 2.00,  # 1 decks, avg 21.4% — Flareon
    "MEG-88": 2.00,  # 1 decks, avg 21.4% — Mega Absol Box
    "TWM-18": 1.97,  # 1 decks, avg 20.8% — Festival Lead
    "MEE-3": 1.94,  # 3 decks, avg 10.2% — Greninja, Flareon
    "DRI-34": 1.93,  # 1 decks, avg 20.0% — Ethan&#039;s Typhlosion
    "MEG-9": 1.82,  # 2 decks, avg 12.7% — Mega Venusaur, Ogerpon Meganium
    "TEF-129": 1.82,  # 1 decks, avg 17.9% — Alakazam
    "PRE-37": 1.73,  # 2 decks, avg 10.9% — Dragapult, Greninja
    "WHT-44": 1.71,  # 1 decks, avg 15.5% — Gardevoir
    "MEG-56": 1.65,  # 1 decks, avg 14.3% — Alakazam
    "PRE-21": 1.56,  # 1 decks, avg 12.5% — Festival Lead
    "SCR-58": 1.36,  # 1 decks, avg 8.3% — Slowking
    "TWM-44": 1.36,  # 1 decks, avg 8.3% — Festival Lead
    "SVI-197": 1.36,  # 1 decks, avg 8.3% — Festival Lead
    "DRI-169": 1.28,  # 1 decks, avg 6.7% — Marnie&#039;s Grimmsnarl
    "PAL-192": 1.21,  # 1 decks, avg 5.3% — Crustle
    "ASC-191": 1.09,  # 1 decks, avg 2.9% — Joltik Box
    "JTG-153": 1.09,  # 1 decks, avg 2.8% — N&#039;s Zoroark
    "PAF-7": 1.05,  # 1 decks, avg 2.0% — Charizard
    "PFL-12": 1.05,  # 1 decks, avg 2.0% — Charizard
    "DRI-136": 1.02,  # 1 decks, avg 1.4% — Marnie&#039;s Grimmsnarl
    "SFA-2": 1.02,  # 1 decks, avg 1.4% — Joltik Box
    "TWM-153": 1.01,  # 1 decks, avg 1.2% — Dragapult
    "TEF-123": 1.01,  # 1 decks, avg 1.1% — Raging Bolt
    "OBF-125": 1.00,  # 1 decks, avg 1.0% — Charizard
}

TOTAL_DECKS_ANALYZED = 46

def get_meta_score(set_id: str, card_number: str) -> float:
    """
    Retourne le score méta (1-10) pour une carte TCG.
    Basé sur présence dans les top decks compétitifs Limitless TCG.
    Cartes non jouées en tournoi → 1.0
    """
    key = f"{set_id}-{card_number}"
    return META_SCORES.get(key, 1.0)


if __name__ == "__main__":
    top = sorted(META_SCORES.items(), key=lambda x: x[1], reverse=True)[:20]
    print("Top 20 cartes compétitives:")
    for card_id, score in top:
        print(f"  {card_id:<15} {score:.2f}")