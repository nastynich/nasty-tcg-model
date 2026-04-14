"""
PriceCharting scraper — volume de ventes eBay par carte
Doit tourner depuis l'ordi local (IP résidentielle requise).
Cache journalier dans pricecharting_cache.json
"""

import requests
import json
import re
import time
import os
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

CACHE_FILE = os.path.join(os.path.dirname(__file__), "pricecharting_cache.json")
CACHE_TTL_HOURS = 24

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Mapping set_id PokéTCG → slug PriceCharting ──────────────────────────────
SET_SLUG_MAP = {
    "sv3pt5":    "pokemon-151",
    "sv8pt5":    "pokemon-prismatic-evolutions",
    "sv9":       "pokemon-journey-together",
    "sv8":       "pokemon-surging-sparks",
    "sv7":       "pokemon-stellar-crown",
    "sv6pt5":    "pokemon-shrouded-fable",
    "sv6":       "pokemon-twilight-masquerade",
    "sv5":       "pokemon-temporal-forces",
    "sv4pt5":    "pokemon-paldean-fates",
    "sv4":       "pokemon-paradox-rift",
    "sv3":       "pokemon-obsidian-flames",
    "sv2":       "pokemon-paldea-evolved",
    "sv1":       "pokemon-scarlet-violet",
    "swsh12pt5": "pokemon-crown-zenith",
    "swsh12":    "pokemon-silver-tempest",
    "swsh11":    "pokemon-lost-origin",
    "swsh10":    "pokemon-astral-radiance",
    "swsh9":     "pokemon-brilliant-stars",
    "me2pt5":    "pokemon-ascended-heroes",
}

# ── Parsing du volume depuis la page PriceCharting ────────────────────────────
def parse_volume(html: str) -> float:
    """
    Extrait le volume de ventes depuis la page d'une carte PriceCharting.
    Format PriceCharting: "volume: X sale(s) per day/week/month"
    Retourne le volume maximum trouvé (tous grades confondus), en ventes/jour.
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    # Format PriceCharting: "volume: 2 sales per day"
    per_day   = re.findall(r"volume:\s*(\d+(?:\.\d+)?)\s+sales?\s+per\s+day", text, re.IGNORECASE)
    per_week  = re.findall(r"volume:\s*(\d+(?:\.\d+)?)\s+sales?\s+per\s+week", text, re.IGNORECASE)
    per_month = re.findall(r"volume:\s*(\d+(?:\.\d+)?)\s+sales?\s+per\s+month", text, re.IGNORECASE)

    # On prend le max sur tous les grades disponibles
    vol = 0.0
    if per_day:
        vol = max(vol, max(float(x) for x in per_day))
    if per_week:
        vol = max(vol, max(float(x) for x in per_week) / 7)
    if per_month:
        vol = max(vol, max(float(x) for x in per_month) / 30)

    if vol > 0:
        return round(vol, 3)

    # Fallback: compter les sold listings visibles sur la page
    sold_rows = soup.select("table#sold-listings tbody tr, .js-sold-listings tr")
    if sold_rows:
        return round(max(0.05, len(sold_rows) / 30), 3)

    return 0.0


def card_name_to_slug(name: str, number: str) -> str:
    """
    Convertit un nom de carte + numéro en slug PriceCharting.
    Ex: "Charizard ex", "199" → "charizard-ex-199"
    """
    # Nettoyer le nom
    slug_name = name.lower()
    slug_name = re.sub(r"[''']", "", slug_name)       # apostrophes
    slug_name = re.sub(r"[^a-z0-9\s-]", "", slug_name)  # caractères spéciaux
    slug_name = re.sub(r"\s+", "-", slug_name.strip())   # espaces → tirets
    slug_name = re.sub(r"-+", "-", slug_name)             # tirets doubles

    # Numéro sans le "/" (ex: "199/165" → "199")
    num_clean = number.split("/")[0] if number else ""

    if num_clean:
        return f"{slug_name}-{num_clean}"
    return slug_name


def is_list_page(html: str) -> bool:
    """Détecte si la page est une liste de cartes (pas une carte individuelle)."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("title")
    if not title:
        return True
    t = title.text
    # Page de liste: titre contient "List" sans "Prices |" pour un set specifique
    # Ex: "Espeon Ex 162 List" vs "Espeon ex #162 Prices | Pokemon Prismatic Evolutions"
    if "List" in t and "Prices |" not in t:
        return True
    # Si le titre contient "Prices |" avec un set Pokemon, c'est une page individuelle
    if "Prices |" in t and ("Pokemon" in t or "pokemon" in t.lower()):
        return False
    return "List" in t


def find_individual_card_url(html: str, set_slug: str, card_name_base: str) -> str | None:
    """Sur une page de liste, trouve le lien vers la carte individuelle du bon set."""
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select(f'a[href*="/game/{set_slug}/"]')
    for link in links:
        href = link.get("href", "")
        text = link.text.strip()
        # On prend le premier lien dans le bon set avec un nom similaire
        if set_slug in href and text:
            return href
    return None


def fetch_volume_for_card(set_slug: str, card_slug: str, delay: float = 1.5) -> float:
    """
    Scrape la page PriceCharting d'une carte et retourne le volume/jour.
    Gère automatiquement les pages de liste (redirect vers la bonne carte).
    """
    url = f"https://www.pricecharting.com/game/{set_slug}/{card_slug}"
    try:
        time.sleep(delay)
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return 0.0

        # Si c'est une page de liste, chercher la vraie URL
        if is_list_page(r.text):
            card_name_base = card_slug.rsplit("-", 1)[0]  # enlève le numéro
            real_url = find_individual_card_url(r.text, set_slug, card_name_base)
            if real_url:
                time.sleep(delay)
                r2 = requests.get(real_url, headers=HEADERS, timeout=15)
                if r2.status_code == 200 and not is_list_page(r2.text):
                    return parse_volume(r2.text)
            return 0.0

        return parse_volume(r.text)
    except Exception:
        return 0.0


# ── Cache management ──────────────────────────────────────────────────────────

def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
            # Vérifier si le cache est encore valide (24h)
            cache_date = data.get("_date", "")
            if cache_date == str(date.today()):
                return data
        except Exception:
            pass
    return {"_date": str(date.today())}


def save_cache(data: dict):
    data["_date"] = str(date.today())
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ── Fonction principale ───────────────────────────────────────────────────────

def _fetch_one(args: tuple) -> tuple:
    """Worker pour le fetch parallèle. Retourne (card_id, volume)."""
    cid, set_slug, name, number = args
    card_slug = card_name_to_slug(name, number)
    # Délai aléatoire léger pour éviter les bursts simultanés
    import random
    time.sleep(random.uniform(0.8, 1.4))
    vol = fetch_volume_for_card(set_slug, card_slug, delay=0)
    return (cid, vol)


def get_ebay_volumes(
    cards: list[dict],
    force_refresh: bool = False,
    max_workers: int = 4,
    progress_callback=None,
) -> dict:
    """
    Pour chaque carte dans la liste, récupère le volume de ventes eBay depuis PriceCharting.
    Utilise le threading parallèle (max_workers=4) pour accélérer le fetch.

    Args:
        cards: liste de dicts avec au minimum {"id", "name", "set_id", "number"}
        force_refresh: ignore le cache et re-scrape tout
        max_workers: nombre de threads parallèles (défaut 4, recommandé 3-5)
        progress_callback: fonction(done, total) appelée après chaque carte fetchée

    Returns:
        dict: {card_id: volume_per_day (float)}
    """
    cache = {} if force_refresh else load_cache()
    results = {}
    to_fetch = []

    for card in cards:
        cid     = card.get("id", "")
        set_id  = card.get("set_id", "")
        name    = card.get("name", "")
        number  = card.get("number", "")

        set_slug = SET_SLUG_MAP.get(set_id)
        if not set_slug:
            results[cid] = 0.0
            continue

        if cid in cache and not force_refresh:
            results[cid] = cache[cid]
        else:
            to_fetch.append((cid, set_slug, name, number))

    # Fetch parallèle des cartes manquantes
    if to_fetch:
        print(f"[PriceCharting] Fetching {len(to_fetch)} cartes (threads={max_workers})...")
        done_count = 0
        batch_size = 50  # Sauvegarde partielle tous les 50

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_one, args): args[0] for args in to_fetch}
            for future in as_completed(futures):
                try:
                    cid, vol = future.result()
                    results[cid] = vol
                    cache[cid]   = vol
                except Exception:
                    cid = futures[future]
                    results[cid] = 0.0
                    cache[cid]   = 0.0

                done_count += 1
                if progress_callback:
                    progress_callback(done_count, len(to_fetch))
                if done_count % batch_size == 0:
                    save_cache(cache)
                    print(f"[PriceCharting] {done_count}/{len(to_fetch)} — cache partiel sauvegardé")

        save_cache(cache)
        print(f"[PriceCharting] Done. {len(to_fetch)} cartes fetchées.")

    return results


def volume_to_score(vol_per_day: float) -> float:
    """
    Convertit un volume de ventes/jour en score 1-10.
    Calibré sur les données Pokémon TCG:
    - 0 ventes/jour  → score 1.0
    - 0.1 (1/semaine) → ~3.0
    - 0.5            → ~5.5
    - 1.0/jour       → ~7.0
    - 2+/jour        → ~9.0+
    - 5+/jour        → 10.0 (cartes très actives genre Charizard SIR)
    """
    if vol_per_day <= 0:
        return 3.0  # neutre si pas de données (pas 1.0 pour éviter faux négatifs)
    import numpy as np
    # Log scale pour éviter que les cartes ultra-populaires écrasent tout
    score = 1.0 + 9.0 * (np.log1p(vol_per_day) / np.log1p(5.0))
    return round(float(min(10.0, max(1.0, score))), 2)


if __name__ == "__main__":
    # Test rapide sur quelques cartes
    test_cards = [
        {"id": "sv3pt5-199", "name": "Charizard ex",  "set_id": "sv3pt5", "number": "199"},
        {"id": "sv8pt5-1",   "name": "Umbreon ex",    "set_id": "sv8pt5", "number": "1"},
        {"id": "sv3pt5-198", "name": "Blastoise ex",  "set_id": "sv3pt5", "number": "198"},
    ]
    volumes = get_ebay_volumes(test_cards, force_refresh=True)
    for cid, vol in volumes.items():
        score = volume_to_score(vol)
        print(f"  {cid}: {vol:.3f} ventes/jour → score {score}/10")
