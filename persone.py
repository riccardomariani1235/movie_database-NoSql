"""
Modulo di query su persone e collegamenti film <-> persone.

Versione importabile dall'app Streamlit (pagina persona) e dai notebook.

    from persone import persona_per_id, cerca_persone, filmografia

Le funzioni lavorano in lettura sulle collezioni `persone` e `film`.
Il legame tra le due vive negli array embedded `cast` e `troupe` dei film:
ogni elemento porta un `id_persona` che coincide con `_id` in `persone`.

Nota indici: la filmografia interroga gli array annidati, quindi questo
modulo aggiunge due indici multikey (`idx_cast_persona`, `idx_troupe_persona`)
a quelli del notebook condiviso. Da concordare con chi possiede gli indici.
"""

import re

from pymongo import ASCENDING, DESCENDING

from connessione import get_db

_db = get_db()
persone = _db["persone"]
film = _db["film"]

# reparti mostrati nella ricerca: attori e registi, non la troupe tecnica
REPARTI_RICERCA = ["Acting", "Directing"]

# campi restituiti nelle liste di persone (documento leggero)
PROIEZIONE_PERSONA = {"nome": 1, "reparto_principale": 1, "foto_url": 1, "arricchito": 1}

# campi del film che servono in una filmografia (niente cast/troupe interi)
PROIEZIONE_FILM = {"titolo": 1, "anno_uscita": 1, "locandina_url": 1, "rating.tmdb_media": 1}


def crea_indici():
    """Indici multikey sugli array embedded, per le query di filmografia."""
    film.create_index([("cast.id_persona", ASCENDING)], name="idx_cast_persona")
    film.create_index([("troupe.id_persona", ASCENDING)], name="idx_troupe_persona")


# --------------------------------------------------------------------------
# Letture di base sulla collezione `persone`
# --------------------------------------------------------------------------
def persona_per_id(id_persona):
    """Documento completo di una persona dato il suo id, o None.

    L'anagrafica (biografia, date, luogo) c'è solo se `arricchito: true`:
    chi consuma il risultato deve gestire i campi mancanti.
    """
    return persone.find_one({"_id": id_persona})


def cerca_persone(testo, limite=20, solo_reparti=REPARTI_RICERCA):
    """Persone il cui nome inizia con `testo` (maiuscole ignorate).

    Di default restringe ad attori e registi (`reparto_principale`).
    Ordina per popolarità decrescente, così i nomi noti (arricchiti)
    escono per primi; chi non ha il campo finisce in coda.
    """
    filtro = {"nome": {"$regex": "^" + re.escape(testo), "$options": "i"}}
    if solo_reparti:
        filtro["reparto_principale"] = {"$in": solo_reparti}
    return list(
        persone.find(filtro, PROIEZIONE_PERSONA)
        .sort([("popolarita", DESCENDING), ("nome", ASCENDING)])
        .limit(limite)
    )


# --------------------------------------------------------------------------
# Filmografia: i film in cui la persona compare nel cast o nella troupe
# --------------------------------------------------------------------------
def filmografia(id_persona):
    """Film in cui la persona ha lavorato, dal più recente.

    Aggregation in due passi: $match sui film che contengono l'id negli
    array embedded, poi $project con $filter per estrarre SOLO gli elementi
    di cast/troupe relativi alla persona (personaggio interpretato, ruolo
    in troupe) senza trascinare gli array interi.
    """
    pipeline = [
        {"$match": {"$or": [
            {"cast.id_persona": id_persona},
            {"troupe.id_persona": id_persona},
        ]}},
        {"$project": {
            **PROIEZIONE_FILM,
            "come_attore": {"$filter": {
                "input": "$cast", "as": "c",
                "cond": {"$eq": ["$$c.id_persona", id_persona]},
            }},
            "come_troupe": {"$filter": {
                "input": "$troupe", "as": "t",
                "cond": {"$eq": ["$$t.id_persona", id_persona]},
            }},
        }},
        {"$sort": {"anno_uscita": DESCENDING}},
    ]
    return list(film.aggregate(pipeline))


def descrivi_ruoli(voce):
    """Etichetta leggibile dei ruoli in un film della filmografia.

    Es. "Cobb" per un attore, "Director" per un regista, o entrambi
    se la persona compare sia nel cast sia nella troupe.
    """
    parti = []
    for c in voce.get("come_attore", []):
        parti.append(c.get("personaggio") or "Attore")
    for t in voce.get("come_troupe", []):
        if t.get("ruolo"):
            parti.append(t["ruolo"])
    return " · ".join(parti)


# --------------------------------------------------------------------------
# Aggregazioni sul legame film <-> persone
# --------------------------------------------------------------------------
def co_attori(id_persona, limite=10):
    """Attori che hanno recitato più spesso con la persona.

    $match sui film in cui compare nel cast, $unwind del cast, esclusione
    della persona stessa, $group per contare le collaborazioni.
    Il cast embedded porta già nome e foto: nessun $lookup necessario.
    """
    pipeline = [
        {"$match": {"cast.id_persona": id_persona}},
        {"$unwind": "$cast"},
        {"$match": {"cast.id_persona": {"$ne": id_persona}}},
        {"$group": {
            "_id": "$cast.id_persona",
            "nome": {"$first": "$cast.nome"},
            "foto_url": {"$first": "$cast.foto_url"},
            "film_insieme": {"$sum": 1},
        }},
        {"$sort": {"film_insieme": DESCENDING, "nome": ASCENDING}},
        {"$limit": limite},
    ]
    return list(film.aggregate(pipeline))


def registi_di(id_persona, limite=10):
    """Registi con cui la persona ha lavorato più spesso (come attore).

    Qui serve un $lookup: la `troupe` embedded non porta la foto, quindi
    dopo il $group si aggancia la collezione `persone` per recuperarla.
    """
    pipeline = [
        {"$match": {"cast.id_persona": id_persona}},
        {"$unwind": "$troupe"},
        {"$match": {
            "troupe.ruolo": "Director",
            "troupe.id_persona": {"$ne": id_persona},
        }},
        {"$group": {
            "_id": "$troupe.id_persona",
            "nome": {"$first": "$troupe.nome"},
            "film_insieme": {"$sum": 1},
        }},
        {"$sort": {"film_insieme": DESCENDING, "nome": ASCENDING}},
        {"$limit": limite},
        {"$lookup": {
            "from": "persone", "localField": "_id",
            "foreignField": "_id", "as": "dettagli",
        }},
        {"$set": {"foto_url": {"$first": "$dettagli.foto_url"}}},
        {"$unset": "dettagli"},
    ]
    return list(film.aggregate(pipeline))


def piu_presenti_nel_catalogo(reparto=None, limite=10):
    """Le persone che compaiono in più film del catalogo.

    $unwind del cast su tutti i film, $group per persona, $lookup su
    `persone` per il reparto (per l'eventuale filtro attori/registi).
    """
    pipeline = [
        {"$unwind": "$cast"},
        {"$group": {
            "_id": "$cast.id_persona",
            "nome": {"$first": "$cast.nome"},
            "foto_url": {"$first": "$cast.foto_url"},
            "n_film": {"$sum": 1},
        }},
        {"$sort": {"n_film": DESCENDING}},
    ]
    if reparto:
        pipeline += [
            {"$lookup": {
                "from": "persone", "localField": "_id",
                "foreignField": "_id", "as": "dettagli",
            }},
            {"$match": {"dettagli.reparto_principale": reparto}},
            {"$unset": "dettagli"},
        ]
    pipeline.append({"$limit": limite})
    return list(film.aggregate(pipeline))
