#!/usr/bin/env python3
"""
Scarica i film più popolari da TMDB e li salva come documenti pronti per MongoDB.

Cosa produce (NDJSON, un documento per riga):
  - film.ndjson     -> collezione `film`: scheda completa di ogni film
                       (descrizione, cast, troupe, produzione, rating aggregato,
                        keyword, disponibilità streaming in Italia, recensioni,
                        anno di uscita, URL locandina)
  - persone.ndjson  -> collezione `persone`: attori e membri della troupe
                       deduplicati dai credits, per costruire i collegamenti
                       film <-> persona senza chiamate API aggiuntive

Ogni film richiede UNA sola chiamata di dettaglio grazie ad append_to_response,
che unisce in un'unica risposta: credits, keywords, watch/providers, reviews.

Autenticazione (una delle due, via variabile d'ambiente):
  - TMDB_BEARER    token v4 (consigliato)  -> usato come header Authorization
  - TMDB_API_KEY   chiave v3               -> usata come parametro api_key

Prerequisiti:
  pip install requests

Uso:
  export TMDB_BEARER="il_tuo_token_v4"      # oppure TMDB_API_KEY="la_tua_chiave_v3"
  python3 scarica_film_tmdb.py --n 2000

Caricamento in MongoDB:
  mongoimport --db cinelog --collection persone --file persone.ndjson
  mongoimport --db cinelog --collection film    --file film.ndjson

Attribuzione richiesta dai termini d'uso:
  - I dati provengono da TMDB. Questo prodotto usa l'API di TMDB ma non è
    approvato o certificato da TMDB.
  - La disponibilità streaming è fornita da JustWatch e va attribuita a JustWatch.
"""

import argparse
import json
import os
import sys
import time

import requests

BASE_URL = "https://api.themoviedb.org/3"
IMG_BASE = "https://image.tmdb.org/t/p"       # + /w500{poster_path} ecc.
POSTER_SIZE = "w500"
PROFILE_SIZE = "w185"

# --------------------------------------------------------------------------
# Sessione HTTP con autenticazione e retry
# --------------------------------------------------------------------------
def costruisci_sessione():
    """Prepara una sessione requests con l'autenticazione TMDB disponibile."""
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
        sys.exit(
            "Nessuna credenziale trovata. Imposta TMDB_BEARER (token v4) "
            "oppure TMDB_API_KEY (chiave v3) come variabile d'ambiente."
        )
    session.headers.update({"Accept": "application/json"})
    return session


def tmdb_get(session, path, params=None, max_tentativi=5):
    """GET verso TMDB con backoff su 429 (rate limit) e 5xx."""
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
            print(f"  rate limit; attendo {attesa}s", file=sys.stderr)
            time.sleep(attesa)
            continue
        if resp.status_code == 404:
            return None
        if 500 <= resp.status_code < 600:
            attesa = 2 ** tentativo
            print(f"  errore server {resp.status_code}; riprovo tra {attesa}s", file=sys.stderr)
            time.sleep(attesa)
            continue
        # errori non recuperabili (401 credenziali, ecc.)
        raise RuntimeError(f"TMDB {resp.status_code} su {path}: {resp.text[:200]}")

    print(f"  saltato {path} dopo {max_tentativi} tentativi", file=sys.stderr)
    return None


# --------------------------------------------------------------------------
# Raccolta degli ID dei film più popolari
# --------------------------------------------------------------------------
def raccogli_id_popolari(session, n, language, region):
    """
    Restituisce fino a `n` ID di film ordinati per popolarità decrescente,
    usando /discover/movie. Deduplica perché la popolarità può spostare i
    risultati tra una pagina e l'altra.
    """
    visti = []
    gia_presenti = set()
    pagina = 1
    # discover restituisce 20 risultati a pagina, max 500 pagine
    while len(visti) < n and pagina <= 500:
        dati = tmdb_get(session, "/discover/movie", {
            "sort_by": "popularity.desc",
            "include_adult": "false",
            "include_video": "false",
            "language": language,
            "region": region,
            "page": pagina,
            "vote_count.gte": 10,   # filtra i titoli con pochissimi voti / rumore
        })
        if not dati or not dati.get("results"):
            break
        for film in dati["results"]:
            fid = film.get("id")
            if fid and fid not in gia_presenti:
                gia_presenti.add(fid)
                visti.append(fid)
                if len(visti) >= n:
                    break
        print(f"  pagina {pagina}: raccolti {len(visti)}/{n} ID")
        pagina += 1

    return visti[:n]


# --------------------------------------------------------------------------
# Helper di trasformazione
# --------------------------------------------------------------------------
def url_immagine(path, size):
    return f"{IMG_BASE}/{size}{path}" if path else None


def anno_da_data(data_str):
    if data_str and len(data_str) >= 4 and data_str[:4].isdigit():
        return int(data_str[:4])
    return None


def estrai_disponibilita_it(raw, region):
    """Estrae la disponibilità streaming/noleggio/acquisto per la region scelta."""
    blocco = (raw.get("watch/providers") or {}).get("results") or {}
    paese = blocco.get(region)
    if not paese:
        return None
    def nomi(chiave):
        return [p.get("provider_name") for p in paese.get(chiave, []) if p.get("provider_name")]
    return {
        "streaming": nomi("flatrate"),   # in abbonamento
        "noleggio": nomi("rent"),
        "acquisto": nomi("buy"),
        "link_tmdb": paese.get("link"),  # pagina /watch TMDB (attribuzione JustWatch)
    }


def estrai_recensioni(raw, massimo=5, lunghezza_max=1200):
    recensioni = []
    for r in (raw.get("reviews") or {}).get("results", [])[:massimo]:
        dettagli = r.get("author_details") or {}
        testo = (r.get("content") or "")[:lunghezza_max]
        recensioni.append({
            "autore": r.get("author"),
            "voto": dettagli.get("rating"),
            "testo": testo,
            "data": r.get("created_at"),
        })
    return recensioni


def trasforma_film(raw, region, cast_limit, crew_limit):
    """Converte la risposta grezza TMDB nel documento `film` per MongoDB."""
    credits = raw.get("credits") or {}

    cast = []
    for c in credits.get("cast", [])[: cast_limit or None]:
        cast.append({
            "id_persona": c.get("id"),
            "nome": c.get("name"),
            "personaggio": c.get("character"),
            "ordine": c.get("order"),
            "foto_url": url_immagine(c.get("profile_path"), PROFILE_SIZE),
        })

    troupe = []
    crew_items = credits.get("crew", [])
    if crew_limit:
        crew_items = crew_items[:crew_limit]
    for c in crew_items:
        troupe.append({
            "id_persona": c.get("id"),
            "nome": c.get("name"),
            "reparto": c.get("department"),
            "ruolo": c.get("job"),
        })

    keyword = [k.get("name") for k in (raw.get("keywords") or {}).get("keywords", [])]

    return {
        "_id": raw.get("id"),
        "titolo": raw.get("title"),
        "titolo_originale": raw.get("original_title"),
        "anno_uscita": anno_da_data(raw.get("release_date")),
        "data_uscita": raw.get("release_date") or None,
        "descrizione": raw.get("overview") or None,
        "locandina_url": url_immagine(raw.get("poster_path"), POSTER_SIZE),
        "generi": [g.get("name") for g in raw.get("genres", [])],
        "durata_min": raw.get("runtime"),
        "lingua_originale": raw.get("original_language"),
        "rating": {
            "tmdb_media": raw.get("vote_average"),
            "tmdb_voti": raw.get("vote_count"),
            "imdb_id": raw.get("imdb_id"),  # per un eventuale join con i rating IMDb
        },
        "popolarita": raw.get("popularity"),
        "cast": cast,
        "troupe": troupe,
        "produzione": {
            "case": [p.get("name") for p in raw.get("production_companies", [])],
            "paesi": [p.get("iso_3166_1") for p in raw.get("production_countries", [])],
        },
        "keyword": keyword,
        f"disponibile_su_{region}": estrai_disponibilita_it(raw, region),
        "recensioni": estrai_recensioni(raw),
    }


def aggiorna_persone(raw, persone):
    """Accumula attori e troupe (deduplicati per id) nel dizionario `persone`."""
    credits = raw.get("credits") or {}
    for c in credits.get("cast", []) + credits.get("crew", []):
        pid = c.get("id")
        if pid and pid not in persone:
            persone[pid] = {
                "_id": pid,
                "nome": c.get("name"),
                "reparto_principale": c.get("known_for_department"),
                "foto_url": url_immagine(c.get("profile_path"), PROFILE_SIZE),
                # Nota: biografia, data di nascita e luogo richiedono /person/{id}
                # e si possono aggiungere in un secondo momento per un sottoinsieme.
            }


# --------------------------------------------------------------------------
# Programma principale
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Scarica i film più popolari da TMDB per MongoDB.")
    parser.add_argument("--n", type=int, default=2000, help="Numero di film da scaricare (default 2000)")
    parser.add_argument("--language", default="it-IT", help="Lingua dei metadati (default it-IT)")
    parser.add_argument("--region", default="IT", help="Region per la disponibilità streaming (default IT)")
    parser.add_argument("--cast-limit", type=int, default=20, help="Numero massimo di attori per film (0 = tutti)")
    parser.add_argument("--crew-limit", type=int, default=0, help="Numero massimo di membri troupe (0 = tutti)")
    parser.add_argument("--out-dir", default=".", help="Cartella di output")
    parser.add_argument("--delay", type=float, default=0.25, help="Pausa in secondi tra le richieste di dettaglio")
    parser.add_argument("--fallback-en", action="store_true", default=True,
                        help="Recupera descrizione/titolo in inglese quando mancano in italiano")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    percorso_film = os.path.join(args.out_dir, "film.ndjson")
    percorso_persone = os.path.join(args.out_dir, "persone.ndjson")

    session = costruisci_sessione()

    # ripresa: se film.ndjson esiste già, salta gli ID presenti
    gia_scaricati = set()
    if os.path.exists(percorso_film):
        with open(percorso_film, encoding="utf-8") as f:
            for riga in f:
                try:
                    gia_scaricati.add(json.loads(riga)["_id"])
                except (json.JSONDecodeError, KeyError):
                    pass
        if gia_scaricati:
            print(f"Ripresa: {len(gia_scaricati)} film già presenti, verranno saltati.")

    print(f"1) Raccolta dei {args.n} film più popolari...")
    ids = raccogli_id_popolari(session, args.n, args.language, args.region)
    print(f"   ottenuti {len(ids)} ID.")

    print("2) Download dei dettagli (una chiamata per film)...")
    persone = {}
    scritti = 0
    with open(percorso_film, "a", encoding="utf-8") as fout:
        for i, fid in enumerate(ids, 1):
            if fid in gia_scaricati:
                continue

            raw = tmdb_get(session, f"/movie/{fid}", {
                "language": args.language,
                "region": args.region,
                "append_to_response": "credits,keywords,watch/providers,reviews",
            })
            if not raw:
                continue

            # fallback inglese per descrizione/titolo mancanti in italiano
            if args.fallback_en and not raw.get("overview"):
                en = tmdb_get(session, f"/movie/{fid}", {"language": "en-US"})
                if en:
                    raw["overview"] = en.get("overview") or raw.get("overview")
                    if not raw.get("title"):
                        raw["title"] = en.get("title")

            documento = trasforma_film(raw, args.region, args.cast_limit, args.crew_limit)
            aggiorna_persone(raw, persone)

            fout.write(json.dumps(documento, ensure_ascii=False) + "\n")
            fout.flush()
            scritti += 1

            if i % 50 == 0 or i == len(ids):
                print(f"   {i}/{len(ids)} film elaborati")
            time.sleep(args.delay)

    print(f"3) Scrittura di {len(persone)} persone deduplicate...")
    with open(percorso_persone, "w", encoding="utf-8") as fp:
        for p in persone.values():
            fp.write(json.dumps(p, ensure_ascii=False) + "\n")

    print(f"\nFatto. Film nuovi scritti: {scritti}. Persone: {len(persone)}.")
    print(f"  {percorso_film}")
    print(f"  {percorso_persone}")


if __name__ == "__main__":
    main()