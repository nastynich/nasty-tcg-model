"""
=============================================================
 Nasty TCG — Google Trends Art Quality / Hype Scraper
=============================================================
Utilise pytrends pour mesurer l'intérêt Google pour chaque set
et les cartes individuelles → proxy pour Art Quality & Hype.

Cache: 7 jours (Google Trends limite les requêtes)
=============================================================
"""

import time
import json
import os
from datetime import datetime, timedelta

CACHE_FILE = os.path.join(os.path.dirname(__file__), "trends_cache.json")
CACHE_DAYS = 7

# Mapping set_id → terme de recherche Google
SET_SEARCH_TERMS = {
    "sv8pt5":    "Prismatic Evolutions Pokemon",
    "sv3pt5":    "Pokemon 151",
    "sv6pt5":    "Shrouded Fable Pokemon",
    "sv4pt5":    "Paldean Fates Pokemon",
    "sv10":      "Destined Rivals Pokemon",
    "sv9":       "Journey Together Pokemon",
    "sv8":       "Surging Sparks Pokemon",
    "sv7":       "Stellar Crown Pokemon",
    "sv6":       "Twilight Masquerade Pokemon",
    "sv5":       "Temporal Forces Pokemon",
    "sv4":       "Paradox Rift Pokemon",
    "sv3":       "Obsidian Flames Pokemon",
    "sv2":       "Paldea Evolved Pokemon",
    "sv1":       "Scarlet Violet Pokemon cards",
    "swsh12pt5": "Crown Zenith Pokemon",
    "swsh12":    "Silver Tempest Pokemon",
    "swsh11":    "Lost Origin Pokemon",
    "swsh10":    "Pokemon Go TCG",
    "swsh9":     "Brilliant Stars Pokemon",
    "swsh8":     "Fusion Strike Pokemon",
    "swsh7":     "Evolving Skies Pokemon",
    "swsh6":     "Chilling Reign Pokemon",
    "swsh5":     "Battle Styles Pokemon",
    "swsh4":     "Vivid Voltage Pokemon",
    "swsh3":     "Darkness Ablaze Pokemon",
    "swsh2":     "Rebel Clash Pokemon",
    "swsh1":     "Sword Shield Pokemon cards",
    "swsh45":    "Shining Fates Pokemon",
    "swsh45sv":  "Shining Fates Pokemon",
    "swsh35":    "Champion's Path Pokemon",
    "pgo":       "Pokemon Go TCG cards",
    "cel25":     "Celebrations Pokemon 25th",
    "me2pt5":    "Ascended Heroes Pokemon",
    "me2":       "Phantasmal Flames Pokemon",
}

def _load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE) as f:
            c = json.load(f)
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

def _fetch_trends_score(keyword, timeframe="today 12-m"):
    """
    Retourne un score 0-10 basé sur l'intérêt moyen Google Trends
    sur les 12 derniers mois.
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=2, backoff_factor=0.5)
        pt.build_payload([keyword], cat=0, timeframe=timeframe, geo="", gprop="")
        df = pt.interest_over_time()
        if df is None or df.empty:
            return 5.0
        avg = df[keyword].mean()
        # Google Trends retourne 0-100 → normaliser à 1-10
        score = 1.0 + (avg / 100.0) * 9.0
        return round(float(score), 2)
    except Exception:
        return 5.0

def get_set_trends_scores(set_ids=None):
    """
    Retourne un dict {set_id: trends_score} pour les sets demandés.
    Utilise le cache si disponible.
    """
    cache = _load_cache()
    scores = cache.get("scores", {})

    if set_ids is None:
        set_ids = list(SET_SEARCH_TERMS.keys())

    missing = [sid for sid in set_ids if sid not in scores]

    if missing:
        for sid in missing:
            keyword = SET_SEARCH_TERMS.get(sid)
            if not keyword:
                scores[sid] = 5.0
                continue
            scores[sid] = _fetch_trends_score(keyword)
            time.sleep(1.5)  # Rate limit Google Trends

        cache["scores"] = scores
        _save_cache(cache)

    return scores

def get_trends_score(set_id):
    """Retourne le score Google Trends pour un set (1-10)."""
    cache = _load_cache()
    scores = cache.get("scores", {})
    if set_id in scores:
        return scores[set_id]

    # Fetch juste ce set
    keyword = SET_SEARCH_TERMS.get(set_id.lower())
    if not keyword:
        return 5.0

    score = _fetch_trends_score(keyword)
    scores[set_id] = score
    cache["scores"] = scores
    _save_cache(cache)
    return score

# ─── Fallback statique si pytrends est bloqué ────────────────────────────────
# Scores basés sur la popularité relative connue des sets
FALLBACK_TRENDS = {
    "sv8pt5":    9.8,  # Prismatic — viral
    "sv3pt5":    9.2,  # 151 — très populaire
    "sv6pt5":    7.5,  # Shrouded Fable
    "sv4pt5":    8.0,  # Paldean Fates
    "sv10":      6.5,
    "sv9":       6.0,
    "sv8":       7.0,  # Surging Sparks — Pikachu SIR
    "sv7":       6.0,
    "sv6":       6.5,
    "sv5":       5.5,
    "sv4":       6.0,
    "sv3":       5.5,
    "sv2":       5.5,
    "sv1":       6.0,
    "swsh12pt5": 8.5,  # Crown Zenith
    "swsh12":    6.0,
    "swsh11":    5.5,
    "swsh10":    6.5,
    "swsh9":     7.0,  # Brilliant Stars — Arceus
    "swsh8":     6.0,
    "swsh7":     8.0,  # Evolving Skies — Rayquaza
    "swsh6":     5.5,
    "swsh5":     5.0,
    "swsh4":     5.0,
    "swsh3":     5.5,
    "swsh2":     4.5,
    "swsh1":     5.0,
    "swsh45":    8.0,  # Shining Fates
    "swsh45sv":  8.0,
    "swsh35":    7.0,  # Champion's Path — Charizard
    "pgo":       7.5,
    "cel25":     8.5,
    "me2pt5":    7.0,
    "me2":       7.5,
}

def get_hype_score(set_id):
    """
    Score de hype combiné: essaie Google Trends, fallback sur statique.
    Retourne 1-10.
    """
    try:
        score = get_trends_score(set_id.lower())
        if score and score != 5.0:
            return score
    except Exception:
        pass
    return FALLBACK_TRENDS.get(set_id.lower(), 5.0)
