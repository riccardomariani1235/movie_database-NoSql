#!/usr/bin/env python3
"""
Esporta le collezioni `film` e `persone` dal database MongoDB verso file NDJSON
aggiornati (un documento per riga), includendo le anagrafiche arricchite.

Da usare DOPO aver completato l'arricchimento, per ottenere i due file completi
da condividere con il gruppo (invio diretto o repository).

Connessione MongoDB:
  MONGO_URI   (default mongodb://localhost:27017)

Prerequisiti:
  pip install pymongo

Uso:
  python3 esporta_ndjson.py --db movie_database
  python3 esporta_ndjson.py --db movie_database --out-dir dati_export
"""

import argparse
import json
import os

from pymongo import MongoClient


def esporta_collezione(coll, percorso):
    n = 0
    with open(percorso, "w", encoding="utf-8") as f:
        for doc in coll.find({}):
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            n += 1
    dimensione_mb = os.path.getsize(percorso) / (1024 * 1024)
    print(f"  {percorso}: {n} documenti ({dimensione_mb:.1f} MB)")
    return n


def main():
    parser = argparse.ArgumentParser(description="Esporta film e persone da MongoDB in NDJSON.")
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGO_URI", "mongodb://localhost:27017"))
    parser.add_argument("--db", default="movie_database")
    parser.add_argument("--out-dir", default=".", help="Cartella di destinazione dei file")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    client = MongoClient(args.mongo_uri)
    db = client[args.db]

    print(f"Esporto da '{args.db}' ({args.mongo_uri})...")
    esporta_collezione(db["film"], os.path.join(args.out_dir, "film.ndjson"))
    esporta_collezione(db["persone"], os.path.join(args.out_dir, "persone.ndjson"))

    # verifica quante persone hanno l'anagrafica arricchita
    arricchite = db["persone"].count_documents({"arricchito": True})
    print(f"\nPersone con anagrafica completa: {arricchite}")
    print("Fatto. I due file sono pronti da condividere.")


if __name__ == "__main__":
    main()