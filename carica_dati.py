"""
Bootstrap del database: carica i dati dai file NDJSON in MongoDB e crea gli indici.
 
Popola le collezioni `film` e `persone` del database `movie_database` a partire
dai file versionati nella repo, poi crea tutti gli indici usati dall'applicazione.
Con un solo comando chi clona la repo ottiene un database pronto all'uso, senza
importare nulla a mano da Compass e senza chiave TMDB.
 
Prerequisiti:
    - MongoDB attivo su localhost:27017
    - pip install pymongo
    - i file film.ndjson e persone.ndjson nella stessa cartella
    - connessione.py nella stessa cartella
 
Uso:
    python carica_dati.py
    python carica_dati.py --film dati/film.ndjson --persone dati/persone.ndjson
 
Lo script è ripetibile: usa l'upsert sull'_id (id TMDB), quindi rilanciarlo
aggiorna i documenti esistenti senza crearne di duplicati.
"""
 
import argparse
import json
import os
 
from pymongo import ASCENDING, DESCENDING, ReplaceOne
 
from connessione import get_db
 
 
def carica_collezione(coll, percorso, batch=1000):
    """Carica un file NDJSON nella collezione con upsert sull'_id, a blocchi."""
    if not os.path.exists(percorso):
        raise FileNotFoundError(f"File non trovato: {percorso}")
 
    operazioni = []
    totale = 0
    with open(percorso, encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if not riga:
                continue
            doc = json.loads(riga)
            operazioni.append(ReplaceOne({"_id": doc["_id"]}, doc, upsert=True))
            if len(operazioni) >= batch:
                coll.bulk_write(operazioni, ordered=False)
                totale += len(operazioni)
                operazioni = []
                if totale % 25000 == 0:
                    print(f"    ...{totale} documenti")
    if operazioni:
        coll.bulk_write(operazioni, ordered=False)
        totale += len(operazioni)
    return totale
 
 
def crea_indici(db):
    """Crea gli indici dell'applicazione (idempotente)."""
    # collezione film
    db["film"].create_index([("titolo", ASCENDING)], name="idx_titolo")
    db["film"].create_index([("generi", ASCENDING), ("rating.tmdb_media", DESCENDING)], name="idx_genere_rating")
    db["film"].create_index([("anno_uscita", ASCENDING)], name="idx_anno")
    db["film"].create_index([("rating.tmdb_media", DESCENDING)], name="idx_rating")
    db["film"].create_index([("keyword", ASCENDING)], name="idx_keyword")
    # collezione persone
    db["persone"].create_index([("reparto_principale", ASCENDING)], name="idx_reparto")
    db["persone"].create_index([("nome", ASCENDING)], name="idx_nome")
    # collezione utenti: nessun indice (letture per _id, gia' indicizzato)
 
 
def main():
    parser = argparse.ArgumentParser(description="Carica i dati NDJSON in MongoDB e crea gli indici.")
    parser.add_argument("--film", default="film.ndjson", help="Percorso di film.ndjson")
    parser.add_argument("--persone", default="persone.ndjson", help="Percorso di persone.ndjson")
    parser.add_argument("--batch", type=int, default=1000, help="Dimensione dei blocchi di scrittura")
    args = parser.parse_args()
 
    db = get_db()
    db.command("ping")
    print(f"Connesso al database '{db.name}'.")
 
    print("1) Carico i film...")
    n_film = carica_collezione(db["film"], args.film, args.batch)
    print(f"   film: {n_film} documenti")
 
    print("2) Carico le persone...")
    n_persone = carica_collezione(db["persone"], args.persone, args.batch)
    print(f"   persone: {n_persone} documenti")
 
    print("3) Creo gli indici...")
    crea_indici(db)
    for nome in ["film", "persone"]:
        indici = [i["name"] for i in db[nome].list_indexes()]
        print(f"   {nome}: {', '.join(indici)}")
 
    print("\nFatto. Database pronto all'uso.")
 
 
if __name__ == "__main__":
    main()