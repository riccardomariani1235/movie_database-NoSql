"""
Modulo di connessione condiviso a MongoDB.

Importato da tutti i moduli del progetto (query film, persone, utente) e dai
notebook. Centralizza qui la connessione, così un'eventuale modifica si fa in
un punto solo.

Uso:
    from connessione import get_db
    db = get_db()
    film = db["film"].find_one({"_id": 27205})
"""

from pymongo import MongoClient

URI = "mongodb://localhost:27017"
NOME_DB = "movie_database"

# client riusato tra le chiamate (una sola connessione per processo)
_client = None


def get_client():
    """Restituisce il MongoClient condiviso, creandolo alla prima chiamata."""
    global _client
    if _client is None:
        _client = MongoClient(URI)
    return _client


def get_db():
    """Restituisce il database del progetto (`movie_database`)."""
    return get_client()[NOME_DB]


# piccola verifica manuale: `python connessione.py`
if __name__ == "__main__":
    db = get_db()
    # ping: solleva un'eccezione se il server non risponde
    db.command("ping")
    print(f"Connesso a '{NOME_DB}' su {URI}")
    for nome in ["film", "persone", "utenti"]:
        print(f"  {nome}: {db[nome].count_documents({})} documenti")
