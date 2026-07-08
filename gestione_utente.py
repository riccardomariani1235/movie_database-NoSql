from connessione import get_db
from datetime import datetime

# Connessione al database e alle collezioni condivise
db = get_db()
utenti = db["utenti"]
film = db["film"]

# --- SETUP INIZIALE ---
def inizializza_utente():
    """Crea il documento utente fisso (utente_1) se non esiste nel DB[cite: 1]."""
    if not utenti.find_one({"_id": "utente_1"}):
        utenti.insert_one({
            "_id": "utente_1",
            "username": "riccardo",
            "creato_il": "2026-01-15",
            "diario": [],
            "liste": []
        })

# --- GESTIONE DIARIO ---
def registra_visione(id_film, data_visione, voto, recensione):
    """Aggiunge un film in fondo all'array embedded 'diario' con $push[cite: 1]."""
    utenti.update_one(
        {"_id": "utente_1"},
        {"$push": {"diario": {
            "id_film": int(id_film), 
            "data_visione": str(data_visione),
            "voto": int(voto),
            "recensione": recensione
        }}}
    )

def modifica_voto_recensione(id_film, nuovo_voto, nuova_recensione):
    """Modifica voto e recensione di un film già visto usando array_filters[cite: 1]."""
    utenti.update_one(
        {"_id": "utente_1"},
        {"$set": {
            "diario.$[v].voto": int(nuovo_voto),
            "diario.$[v].recensione": nuova_recensione
        }},
        array_filters=[{"v.id_film": int(id_film)}]
    )

def rimuovi_visione(id_film):
    """Rimuove un film dal diario personale utilizzando $pull."""
    utenti.update_one(
        {"_id": "utente_1"},
        {"$pull": {"diario": {"id_film": int(id_film)}}}
    )

# --- GESTIONE LISTE ---
def crea_lista(nome_lista):
    """Crea una nuova lista personalizzata vuota[cite: 1]."""
    utenti.update_one(
        {"_id": "utente_1"},
        {"$push": {"liste": {"nome": nome_lista, "id_film": []}}}
    )

def aggiungi_a_lista(nome_lista, id_film):
    """Aggiunge un film a una lista specifica senza creare duplicati usando $addToSet[cite: 1]."""
    utenti.update_one(
        {"_id": "utente_1"},
        {"$addToSet": {"liste.$[l].id_film": int(id_film)}},
        array_filters=[{"l.nome": nome_lista}]
    )

# --- LETTURA E AGGREGAZIONI ---
def leggi_diario_completo():
    """Esegue un $lookup per unire l'id_film del diario con la collezione film[cite: 1]."""
    pipeline = [
        {"$match": {"_id": "utente_1"}},
        {"$unwind": "$diario"},
        {"$lookup": {
            "from": "film",
            "localField": "diario.id_film",
            "foreignField": "_id",
            "as": "info_film"
        }},
        {"$unwind": "$info_film"},
        {"$project": {
            "_id": 0,
            "id_film": "$diario.id_film",
            "titolo": "$info_film.titolo",
            "anno": "$info_film.anno_uscita",
            "mio_voto": "$diario.voto",
            "data_visione": "$diario.data_visione",
            "recensione": "$diario.recensione"
        }},
        {"$sort": {"data_visione": -1}}
    ]
    return list(utenti.aggregate(pipeline))

def ottieni_media_e_visioni():
    """Calcola la media globale dei voti e il numero totale di visioni[cite: 1]."""
    pipeline = [
        {"$match": {"_id": "utente_1"}},
        {"$unwind": "$diario"},
        {"$group": {
            "_id": None,
            "media_voti": {"$avg": "$diario.voto"},
            "visioni": {"$sum": 1}
        }}
    ]
    risultato = list(utenti.aggregate(pipeline))
    return risultato[0] if risultato else {"media_voti": 0, "visioni": 0}

def ottieni_liste_utente():
    """Recupera le liste correnti dell'utente[cite: 1]."""
    utente = utenti.find_one({"_id": "utente_1"}, {"liste": 1})
    return utente["liste"] if utente and "liste" in utente else []