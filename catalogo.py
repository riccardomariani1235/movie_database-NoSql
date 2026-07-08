"""
Modulo di query del catalogo film.

Versione consolidata delle funzioni sviluppate nei notebook, importabile
dall'app Streamlit e da altri moduli.

    from catalogo import cerca_film, scheda_film
"""

from connessione import get_db

_db = get_db()
film = _db["film"]

# soglia minima di voti per le classifiche (tarata sul catalogo)
SOGLIA_VOTI = 1000

# campi restituiti nelle liste (documento leggero)
PROIEZIONE = {
    "titolo": 1, "anno_uscita": 1, "generi": 1,
    "locandina_url": 1, "rating.tmdb_media": 1, "rating.tmdb_voti": 1,
}


def cerca_per_titolo(testo, limite=20):
    """Film il cui titolo inizia con `testo` (maiuscole ignorate)."""
    import re
    filtro = {"titolo": {"$regex": "^" + re.escape(testo), "$options": "i"}}
    return list(film.find(filtro, PROIEZIONE).sort("titolo", 1).limit(limite))


def scheda_film(id_film):
    """Documento completo di un film dato il suo id, o None."""
    return film.find_one({"_id": id_film})


def film_piu_votati(limite=20):
    """I migliori film del catalogo, con almeno SOGLIA_VOTI voti."""
    filtro = {"rating.tmdb_voti": {"$gte": SOGLIA_VOTI}}
    return list(film.find(filtro, PROIEZIONE).sort("rating.tmdb_media", -1).limit(limite))


def film_per_genere(genere, limite=20):
    """Film di un genere, dal più votato, con almeno SOGLIA_VOTI voti."""
    filtro = {"generi": genere, "rating.tmdb_voti": {"$gte": SOGLIA_VOTI}}
    return list(film.find(filtro, PROIEZIONE).sort("rating.tmdb_media", -1).limit(limite))


def film_per_anni(anno_min=None, anno_max=None, limite=20):
    """Film in un intervallo di anni, dal più recente. Estremi opzionali."""
    intervallo = {}
    if anno_min is not None:
        intervallo["$gte"] = anno_min
    if anno_max is not None:
        intervallo["$lte"] = anno_max
    filtro = {"anno_uscita": intervallo} if intervallo else {}
    return list(film.find(filtro, PROIEZIONE).sort("anno_uscita", -1).limit(limite))


def cerca_film(genere=None, anno_min=None, anno_max=None,
               voti_min=SOGLIA_VOTI, ordina_per="rating.tmdb_media",
               decrescente=True, limite=20):
    """Ricerca del catalogo con filtri combinati opzionali."""
    filtro = {}
    if genere:
        filtro["generi"] = genere
    intervallo = {}
    if anno_min is not None:
        intervallo["$gte"] = anno_min
    if anno_max is not None:
        intervallo["$lte"] = anno_max
    if intervallo:
        filtro["anno_uscita"] = intervallo
    if voti_min:
        filtro["rating.tmdb_voti"] = {"$gte": voti_min}
    direzione = -1 if decrescente else 1
    return list(film.find(filtro, PROIEZIONE).sort(ordina_per, direzione).limit(limite))


# --- helper per popolare i controlli dell'interfaccia ---

def generi_disponibili():
    """Elenco ordinato dei generi presenti nel catalogo."""
    return sorted(film.distinct("generi"))


def intervallo_anni():
    """(anno minimo, anno massimo) presenti nel catalogo."""
    solo_con_anno = {"anno_uscita": {"$ne": None}}
    piu_vecchio = film.find(solo_con_anno).sort("anno_uscita", 1).limit(1)
    piu_recente = film.find(solo_con_anno).sort("anno_uscita", -1).limit(1)
    return piu_vecchio[0]["anno_uscita"], piu_recente[0]["anno_uscita"]
