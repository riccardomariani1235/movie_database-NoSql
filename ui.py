"""
Componenti di presentazione condivisi dell'interfaccia CineLog.

Risolvono il problema dell'allineamento delle griglie: in Streamlit ogni
colonna cresce con il proprio contenuto, quindi un titolo su due righe o
una locandina mancante sfasano tutte le card vicine. Qui ogni elemento
della card ha altezza FISSA:
  - immagine: proporzione 2:3 (il formato dei poster TMDB), con placeholder
    della stessa identica proporzione quando l'immagine manca;
  - titolo: sempre due righe, troncato con ellissi;
  - riga secondaria: sempre una riga, troncata con ellissi.

Ogni pagina chiama `carica_stile()` una volta in cima, poi usa
`card_film` / `card_persona` nelle proprie griglie.

Questo modulo non accede mai al database: solo presentazione.
"""

import html

import streamlit as st

_CSS = """
<style>
/* titolo card: esattamente due righe, ellissi oltre -> card sempre allineate */
.cl-titolo {
    font-weight: 600;
    line-height: 1.3;
    height: 2.6em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    margin: 0.35rem 0 0.1rem 0;
}
.cl-titolo a, .cl-titolo a:visited { color: inherit; text-decoration: none; }
.cl-titolo a:hover { text-decoration: underline; }

/* riga secondaria: esattamente una riga, ellissi oltre */
.cl-sotto {
    opacity: 0.65;
    font-size: 0.8rem;
    height: 1.3em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 0.2rem;
}

/* placeholder con la stessa proporzione dei poster TMDB (2:3):
   occupa lo spazio dell'immagine mancante e la griglia non si scompone */
.cl-placeholder {
    width: 100%;
    aspect-ratio: 2 / 3;
    border-radius: 8px;
    background: rgba(128, 132, 149, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    opacity: 0.8;
    font-size: 0.8rem;
    padding: 0.5rem;
    box-sizing: border-box;
}

/* immagini con gli stessi angoli del placeholder */
.stImage img { border-radius: 8px; }
</style>
"""


def carica_stile():
    """Applica il CSS condiviso. Da chiamare una volta in cima a ogni pagina."""
    st.markdown(_CSS, unsafe_allow_html=True)


def _immagine(url, testo_placeholder):
    """Immagine 2:3, o un placeholder delle stesse dimensioni se manca."""
    if url:
        st.image(url, use_container_width=True)
    else:
        st.markdown(
            f'<div class="cl-placeholder">{html.escape(testo_placeholder)}</div>',
            unsafe_allow_html=True,
        )


def _titolo_link(testo, url=None):
    """Titolo su due righe fisse, cliccabile se c'è un url (stessa scheda)."""
    testo = html.escape(testo)
    interno = f'<a href="{url}" target="_self">{testo}</a>' if url else testo
    st.markdown(f'<div class="cl-titolo">{interno}</div>', unsafe_allow_html=True)


def _sottotitolo(testo):
    """Riga secondaria a una riga fissa (anche vuota: tiene l'allineamento)."""
    st.markdown(f'<div class="cl-sotto">{html.escape(testo) or "&nbsp;"}</div>',
                unsafe_allow_html=True)


def card_film(f, sotto=None):
    """Card di un film per le griglie (catalogo, filmografia).

    `sotto` sostituisce la riga secondaria di default "anno · TMDB voto"
    (la filmografia ci mette ad esempio il ruolo della persona).
    """
    with st.container(border=True):
        titolo = f.get("titolo") or "Titolo sconosciuto"
        _immagine(f.get("locandina_url"), titolo)
        _titolo_link(titolo, f"/?film_id={f['_id']}")
        if sotto is None:
            anno = f.get("anno_uscita")
            voto = (f.get("rating") or {}).get("tmdb_media")
            parti = [str(anno) if anno else None,
                     f"TMDB {voto:.1f}" if isinstance(voto, (int, float)) else None]
            sotto = " · ".join(p for p in parti if p)
        _sottotitolo(sotto)


def card_persona(id_persona, nome, foto_url, sotto=""):
    """Card di una persona per le griglie (cast, collaborazioni, ricerca)."""
    with st.container(border=True):
        nome = nome or "Nome non disponibile"
        _immagine(foto_url, nome)
        url = f"/Persona?persona_id={id_persona}" if id_persona else None
        _titolo_link(nome, url)
        _sottotitolo(sotto)
