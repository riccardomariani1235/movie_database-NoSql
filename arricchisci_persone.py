#!/usr/bin/env python3
"""
Arricchisce la collezione `persone` con i dati anagrafici (biografia, data di
nascita, luogo di nascita, ecc.) SOLO per il cast principale e i registi che
compaiono nella collezione `film`.

Perché solo un sottoinsieme: /person/{id} richiede una chiamata per persona.
Arricchire tutte le 70k+ persone marcate "Acting"/"Directing" richiederebbe ore
per figure che nell'app non compaiono mai in primo piano. Qui si prendono solo
i primi attori per ordine di locandina (top N) più i registi.

Lettura ID persone -> da MongoDB (collezione `film`)
Anagrafiche        -> da TMDB (endpoint /person/{id})
Scrittura          -> MongoDB (collezione `persone`, campo per campo)

Credenziali TMDB (una via variabile d'ambiente):
  TMDB_BEARER    token v4        oppure    TMDB_API_KEY   chiave v3
Connessione MongoDB:
  MONGO_URI      (default mongodb://localhost:27017)

Prerequisiti:
  pip install pymongo requests

Uso consigliato (prima conta, poi scarica):
  python3 arricchisci_persone.py --dry-run           # mostra quante persone
  python3 arricchisci_persone.py                     # esegue l'arricchimento

Lo script è ripetibile: salta le persone già arricchite (campo `arricchito`).
"""

import argparse
import os
import sys
import time

import requests
from pymongo import MongoClient, UpdateOne

BASE_URL = "https://api.themoviedb.org/3"

GENERE = {0: "non specificato", 1: "femminile", 2: "maschile", 3: "non binario"}


# --------------------------------------------------------------------------
# Sessione TMDB con autenticazione e retry
# --------------------------------------------------------------------------
def costruisci_sessione():
    session = requests.Session()
    bearer = os.environ.get("TMDB_BEARER")
    api_key = os.environ.get("TMDB_API_KEY")
    if bearer:
        session.headers.update({"Authorization": f"Bearer {bearer}"})
        session.auth_mode = "bearer"
    elif api_key:
        session.auth_mode = "api_key"
        session.api_key = api_key
    else:
        sys.exit("Nessuna credenziale TMDB. Imposta TMDB_BEARER o TMDB_API_KEY.")
    session.headers.update({"Accept": "application/json"})
    return session


def tmdb_get(session, path, params=None, max_tentativi=5):
    params = dict(params or {})
    if getattr(session, "auth_mode", None) == "api_key":
        params["api_key"] = session.api_key
    url = f"{BASE_URL}{path}"
    for tentativo in range(1, max_tentativi + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
        except requests.RequestException as e:
            attesa = 2 ** tentativo
            print(f"  errore di rete ({e}); riprovo tra {attesa}s", file=sys.stderr)
            time.sleep(attesa)
            continue
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            attesa = int(resp.headers.get("Retry-After", 2)) + 1
            time.sleep(attesa)
            continue
        if resp.status_code == 404:
            return None
        if 500 <= resp.status_code < 600:
            time.sleep(2 ** tentativo)
            continue
        raise RuntimeError(f"TMDB {resp.status_code} su {path}: {resp.text[:200]}")
    return None


# --------------------------------------------------------------------------
# Selezione delle persone da arricchire (dai film)
# --------------------------------------------------------------------------
def raccogli_id_da_arricchire(coll_film, cast_top):
    """
    Restituisce l'insieme degli id_persona che compaiono, in almeno un film,
    tra i primi `cast_top` attori per ordine di locandina oppure come regista.
    """
    ids = set()
    proiezione = {"cast": 1, "troupe": 1}
    for film in coll_film.find({}, proiezione):
        for c in film.get("cast", []):
            if c.get("ordine") is not None and c["ordine"] < cast_top and c.get("id_persona"):
                ids.add(c["id_persona"])
        for t in film.get("troupe", []):
            if t.get("ruolo") == "Director" and t.get("id_persona"):
                ids.add(t["id_persona"])
    return ids


# --------------------------------------------------------------------------
# Costruzione del documento anagrafico (funzione pura, testabile offline)
# --------------------------------------------------------------------------
def costruisci_anagrafica(raw):
    return {
        "biografia": raw.get("biography") or None,
        "data_nascita": raw.get("birthday") or None,
        "data_morte": raw.get("deathday") or None,
        "luogo_nascita": raw.get("place_of_birth") or None,
        "genere": GENERE.get(raw.get("gender", 0), "non specificato"),
        "imdb_id": raw.get("imdb_id") or None,
        "alias": raw.get("also_known_as") or [],
        "popolarita": raw.get("popularity"),
        "arricchito": True,
    }


# --------------------------------------------------------------------------
# Programma principale
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Arricchisce cast principale e registi con le anagrafiche TMDB.")
    parser.add_argument("--cast-top", type=int, default=10, help="Quanti attori per film (per ordine di locandina). Default 10")
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
    parser.add_argument("--db", default="cinelog")
    parser.add_argument("--dry-run", action="store_true", help="Conta soltanto le persone da arricchire, senza chiamare l'API")
    parser.add_argument("--delay", type=float, default=0.25, help="Pausa in secondi tra le chiamate")
    parser.add_argument("--batch", type=int, default=200, help="Ogni quante scritture svuotare il buffer su MongoDB")
    parser.add_argument("--fallback-en", action="store_true", default=True, help="Biografia in inglese quando manca in italiano")
    args = parser.parse_args()

    client = MongoClient(args.mongo_uri)
    db = client[args.db]
    coll_film = db["film"]
    coll_persone = db["persone"]

    print(f"Seleziono cast principale (top {args.cast_top}) e registi dai film...")
    ids = raccogli_id_da_arricchire(coll_film, args.cast_top)
    print(f"  persone candidate: {len(ids)}")

    # quante sono già arricchite (per la ripresa)
    gia_fatte = coll_persone.count_documents({"_id": {"$in": list(ids)}, "arricchito": True})
    da_fare = len(ids) - gia_fatte
    print(f"  già arricchite: {gia_fatte} | da arricchire ora: {da_fare}")

    stima_min = da_fare * args.delay / 60
    print(f"  tempo minimo stimato: ~{stima_min:.1f} minuti (senza retry)")

    if args.dry_run:
        print("\n--dry-run: nessuna chiamata API effettuata. Rilancia senza --dry-run per procedere.")
        return

    session = costruisci_sessione()
    operazioni = []
    fatte = 0

    for pid in ids:
        # salta chi è già stato arricchito
        doc = coll_persone.find_one({"_id": pid}, {"arricchito": 1})
        if doc and doc.get("arricchito"):
            continue

        raw = tmdb_get(session, f"/person/{pid}", {"language": "it-IT"})
        if not raw:
            continue

        if args.fallback_en and not raw.get("biography"):
            en = tmdb_get(session, f"/person/{pid}", {"language": "en-US"})
            if en and en.get("biography"):
                raw["biography"] = en["biography"]

        operazioni.append(UpdateOne({"_id": pid}, {"$set": costruisci_anagrafica(raw)}))
        fatte += 1

        if len(operazioni) >= args.batch:
            coll_persone.bulk_write(operazioni, ordered=False)
            operazioni.clear()
            print(f"  {fatte}/{da_fare} anagrafiche aggiornate")

        time.sleep(args.delay)

    if operazioni:
        coll_persone.bulk_write(operazioni, ordered=False)

    print(f"\nFatto. Anagrafiche aggiornate in questa esecuzione: {fatte}.")
    print("Le persone arricchite hanno ora biografia, data di nascita, luogo di nascita, ecc.")


if __name__ == "__main__":
    main()