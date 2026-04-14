"""
=============================================================
 Nasty TCG — Set Intelligence Module
=============================================================
Fournit 3 types de données enrichies par set :

1. SET DENSITY      → nb de rares par set (via PokéTCG API)
2. SCARCITY SCORE   → set age, statut OOP, print run estimé
3. SEALED MSRP      → ratio prix marché / MSRP pour booster box

Cache : 7 jours (données stables)
=============================================================
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta

CACHE_FILE = os.path.join(os.path.dirname(__file__), "set_intelligence_cache.json")
CACHE_DAYS = 7

# ─── MSRP des booster boxes par set (USD) ───────────────────────────────────
# Source: prix de détail officiels connus
SET_MSRP = {
    # Scarlet & Violet
    "sv10":      143.64,
    "sv9":       143.64,
    "sv8pt5":    143.64,
    "sv8":       143.64,
    "sv7":       143.64,
    "sv6pt5":    143.64,
    "sv6":       143.64,
    "sv5":       143.64,
    "sv4pt5":    143.64,
    "sv4":       143.64,
    "sv3pt5":    143.64,
    "sv3":       143.64,
    "sv2":       143.64,
    "sv1":       143.64,
    # Sword & Shield
    "swsh12pt5": 143.64,
    "swsh12":    143.64,
    "swsh11":    107.69,
    "swsh10":    107.69,
    "swsh9":     107.69,
    "swsh8":     107.69,
    "swsh7":     107.69,
    "swsh6":     107.69,
    "swsh5":     107.69,
    "swsh4":     107.69,
    "swsh3":     107.69,
    "swsh2":     107.69,
    "swsh1":     107.69,
    "swsh45":    107.69,
    "swsh45sv":  107.69,
    "swsh35":    107.69,
    "pgo":       107.69,
    "cel25":      59.99,
    "me2pt5":     79.99,
}

# ─── Print run estimé (échelle 1-10, 10 = très limité) ───────────────────────
# Basé sur: articles Pokebeach, comportement marché, set age
# 1-3 = mass print (ex: Obsidian Flames), 7-10 = limited (ex: 151, Prismatic)
PRINT_RUN_SCORE = {
    "sv8pt5":    9.5,  # Prismatic Evolutions — extremely limited
    "sv3pt5":    8.5,  # 151 — limited reprint
    "sv6pt5":    7.5,  # Shrouded Fable
    "sv4pt5":    7.0,  # Paldean Fates
    "sv10":      6.0,  # Destined Rivals
    "sv9":       5.5,  # Journey Together
    "sv8":       5.0,  # Surging Sparks
    "sv7":       5.0,  # Stellar Crown
    "sv6":       4.5,  # Twilight Masquerade
    "sv5":       4.0,  # Temporal Forces
    "sv4":       4.0,  # Paradox Rift
    "sv3":       4.5,  # Obsidian Flames — mass print
    "sv2":       5.0,  # Paldea Evolved
    "sv1":       5.5,  # Scarlet & Violet Base
    "swsh12pt5": 7.5,  # Crown Zenith
    "swsh12pt5gg": 7.5,
    "swsh12":    6.0,
    "swsh11":    5.5,
    "swsh10":    5.5,
    "swsh9":     5.0,
    "swsh8":     5.0,
    "swsh7":     5.0,
    "swsh6":     5.0,
    "swsh5":     5.0,
    "swsh4":     5.5,
    "swsh3":     5.0,
    "swsh2":     5.5,
    "swsh1":     6.0,
    "swsh45":    7.0,
    "swsh45sv":  7.5,
    "swsh35":    6.5,
    "pgo":       8.0,  # Pokemon GO — limited window
    "cel25":     9.0,  # Celebrations — very limited
    "me2pt5":    8.5,  # Ascended Heroes — limited
}

def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE) as f:
            c = json.load(f)
        # Vérifier l'expiration
        if "cached_at" in c:
            age = datetime.now() - datetime.fromisoformat(c["cached_at"])
            if age > timedelta(days=CACHE_DAYS):
                return {}
        return c
    except Exception:
        return {}

def _save_cache(data):
    data["cached_at"] = datetime.now().isoformat()
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def _fetch_set_metadata_from_api():
    """Récupère les métadonnées de tous les sets via PokéTCG API."""
    try:
        resp = requests.get(
            "https://api.pokemontcg.io/v2/sets",
            params={"pageSize": 500},
            timeout=15
        )
        if resp.status_code != 200:
            return {}
        sets = resp.json().get("data", [])
        result = {}
        for s in sets:
            sid = s.get("id", "").lower()
            result[sid] = {
                "name":          s.get("name", ""),
                "total":         s.get("total", 0),
                "printed_total": s.get("printedTotal", 0),
                "release_date":  s.get("releaseDate", ""),
                "series":        s.get("series", ""),
            }
        return result
    except Exception:
        return {}

def _get_set_age_score(release_date_str):
    """
    Score de scarcité basé sur l'âge du set.
    Plus le set est vieux → plus rare → score plus élevé.
    OOP automatique après 3 ans.
    """
    if not release_date_str:
        return 5.0, False
    try:
        release = datetime.strptime(release_date_str, "%Y/%m/%d")
        age_days = (datetime.now() - release).days
        age_years = age_days / 365.25

        is_oop = age_years >= 3.0

        if age_years < 0.5:
            score = 3.0   # Très récent, encore en print
        elif age_years < 1.0:
            score = 4.5
        elif age_years < 2.0:
            score = 6.0
        elif age_years < 3.0:
            score = 7.5
        elif age_years < 5.0:
            score = 8.5   # OOP
        else:
            score = 9.5   # Vintage, très rare
        return round(score, 2), is_oop
    except Exception:
        return 5.0, False

def get_sealed_market_ratio(set_id, tcgplayer_box_price_usd=None):
    """
    Ratio prix marché sealed / MSRP.
    > 1.0 = premium (gens paient plus → cartes valent plus)
    < 1.0 = discount (surplus d'offre)
    
    Si on n'a pas le prix marché actuel, on retourne 1.0 (neutre).
    """
    msrp = SET_MSRP.get(set_id.lower(), 0)
    if not msrp or not tcgplayer_box_price_usd:
        # Ratio neutre
        return 1.0
    ratio = tcgplayer_box_price_usd / msrp
    return round(ratio, 3)

def sealed_ratio_to_score(ratio):
    """
    Convertit le ratio sealed en score 1-10.
    ratio 1.0 = 5.0 (neutre)
    ratio 2.0 = 9.0 (très premium)
    ratio 0.5 = 2.0 (discount)
    """
    # Sigmoïde logarithmique
    import math
    if ratio <= 0:
        return 5.0
    log_r = math.log(ratio)  # 0 à neutre, positif = premium
    score = 5.0 + (log_r * 4.0)
    return round(max(1.0, min(10.0, score)), 2)

# ─── Booster box market prices (TCGPlayer, USD) ──────────────────────────────
# Mis à jour manuellement — représente le prix marché actuel des booster boxes
# Source: TCGPlayer market price (mis à jour ~hebdomadaire)
SEALED_MARKET_PRICES = {
    "sv8pt5":    620.00,  # Prismatic Evolutions — massif premium
    "sv3pt5":    210.00,  # 151
    "sv6pt5":    160.00,  # Shrouded Fable
    "sv4pt5":    155.00,  # Paldean Fates
    "sv10":      150.00,  # Destined Rivals
    "sv9":       145.00,  # Journey Together
    "sv8":       140.00,  # Surging Sparks
    "sv7":       135.00,  # Stellar Crown
    "sv6":       130.00,  # Twilight Masquerade
    "sv5":       125.00,  # Temporal Forces
    "sv4":       120.00,  # Paradox Rift
    "sv3":       115.00,  # Obsidian Flames
    "sv2":       120.00,  # Paldea Evolved
    "sv1":       130.00,  # SV Base
    "swsh12pt5": 250.00,  # Crown Zenith
    "swsh12":    180.00,
    "swsh11":    150.00,
    "swsh10":    140.00,
    "swsh9":     130.00,
    "swsh8":     125.00,
    "swsh7":     120.00,
    "swsh6":     115.00,
    "swsh5":     110.00,
    "swsh4":     120.00,
    "swsh3":     115.00,
    "swsh2":     110.00,
    "swsh1":     125.00,
    "swsh45":    160.00,
    "swsh45sv":  180.00,
    "pgo":       200.00,
    "cel25":     350.00,
    "me2pt5":    120.00,
}

# ─── Cache global des métadonnées de sets ─────────────────────────────────────
_SET_META_CACHE = None

# ─── Dates de sortie connues (statique — pas besoin d'API) ──────────────────
SET_RELEASE_DATES = {
    "sv10":      "2025/05/30", "sv9": "2025/02/07", "sv8pt5": "2025/01/17",
    "sv8":       "2024/11/08", "sv7": "2024/09/13", "sv6pt5": "2024/08/02",
    "sv6":       "2024/05/24", "sv5": "2024/03/22", "sv4pt5": "2024/01/26",
    "sv4":       "2023/11/03", "sv3pt5": "2023/09/22", "sv3": "2023/08/11",
    "sv2":       "2023/06/09", "sv1": "2023/03/31",
    "swsh12pt5": "2023/01/20", "swsh12": "2022/11/11", "swsh11": "2022/09/09",
    "swsh10":    "2022/07/01", "swsh9": "2022/02/25", "swsh8": "2021/11/12",
    "swsh7":     "2021/08/27", "swsh6": "2021/06/18", "swsh5": "2021/03/19",
    "swsh4":     "2020/11/13", "swsh3": "2020/08/14", "swsh2": "2020/05/01",
    "swsh1":     "2020/02/07", "swsh45": "2021/02/19", "swsh45sv": "2021/02/19",
    "swsh35":    "2020/09/25", "pgo": "2022/07/01", "cel25": "2021/10/08",
    "me2pt5":    "2025/03/28",
}

def get_all_set_intelligence():
    """
    Retourne un dict {set_id: {...scores...}} pour tous les sets.
    100% statique — pas d'appel API au démarrage.
    Cache en mémoire pour éviter recalculs.
    """
    global _SET_META_CACHE
    if _SET_META_CACHE is not None:
        return _SET_META_CACHE

    all_sids = set(list(SET_MSRP.keys()) + list(PRINT_RUN_SCORE.keys()) + list(SET_RELEASE_DATES.keys()))
    result = {}

    for sid in all_sids:
        release_date      = SET_RELEASE_DATES.get(sid, "")
        age_score, is_oop_flag = _get_set_age_score(release_date)
        print_run         = PRINT_RUN_SCORE.get(sid, 5.0)
        mkt_price         = SEALED_MARKET_PRICES.get(sid)
        sealed_ratio      = get_sealed_market_ratio(sid, mkt_price)
        sealed_score      = sealed_ratio_to_score(sealed_ratio)
        oop_bonus         = 2.0 if is_oop_flag else 0.0
        scarcity          = round(0.40 * age_score + 0.40 * print_run + 0.20 * (7.0 + oop_bonus), 2)
        scarcity          = max(1.0, min(10.0, scarcity))

        result[sid] = {
            "name":         sid,
            "release_date": release_date,
            "age_score":    age_score,
            "is_oop":       is_oop_flag,
            "print_run":    print_run,
            "sealed_ratio": sealed_ratio,
            "sealed_score": sealed_score,
            "density":      1.0,
            "scarcity":     scarcity,
        }

    _SET_META_CACHE = result
    return result

def get_scarcity_score(set_id):
    """Score de rareté/offre pour un set donné (1-10)."""
    intel = get_all_set_intelligence()
    s = intel.get(set_id.lower(), {})
    return s.get("scarcity", 5.0)

def get_sealed_score(set_id):
    """Score basé sur le ratio sealed market / MSRP (1-10)."""
    intel = get_all_set_intelligence()
    s = intel.get(set_id.lower(), {})
    return s.get("sealed_score", 5.0)

def get_set_density_score(set_id):
    """
    Score de consistance du set (inverse de la densité).
    Peu de rares = chaque carte individuelle a plus de valeur.
    """
    intel = get_all_set_intelligence()
    s = intel.get(set_id.lower(), {})
    density = s.get("density", 1.0)
    # Moins de rares = meilleur score de consistance
    score = 10.0 - (density * 5.0)
    return round(max(1.0, min(10.0, score)), 2)

def is_oop(set_id):
    """Retourne True si le set est Out of Print."""
    intel = get_all_set_intelligence()
    s = intel.get(set_id.lower(), {})
    return s.get("is_oop", False)
