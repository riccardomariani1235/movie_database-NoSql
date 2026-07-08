"""
Pagina Streamlit del catalogo film.

Avvio:
    streamlit run app.py

Usa le funzioni del modulo `catalogo`. La navigazione tra elenco e scheda
avviene tramite un parametro nell'URL (`film_id`), la stessa convenzione con
cui, nell'app completa, la scheda si collegherà alla pagina persona.
"""

import streamlit as st

import catalogo

st.set_page_config(page_title="CineLog — Catalogo", layout="wide")


# --- dati per i controlli, calcolati una volta e messi in cache ---
@st.cache_data(ttl=600)
def generi_disponibili():
    return catalogo.generi_disponibili()


@st.cache_data(ttl=600)
def intervallo_anni():
    return catalogo.intervallo_anni()


# =========================================================================
# Vista scheda film
# =========================================================================
def mostra_scheda(id_film):
    f = catalogo.scheda_film(id_film)
    if not f:
        st.error("Film non trovato.")
        if st.button("← Torna al catalogo"):
            st.query_params.clear()
            st.rerun()
        return

    if st.button("← Torna al catalogo"):
        st.query_params.clear()
        st.rerun()

    col_poster, col_info = st.columns([1, 2])
    with col_poster:
        if f.get("locandina_url"):
            st.image(f["locandina_url"], use_container_width=True)
    with col_info:
        st.title(f.get("titolo", "—"))
        if f.get("titolo_originale") and f["titolo_originale"] != f.get("titolo"):
            st.caption(f["titolo_originale"])
        st.write(f"**Anno:** {f.get('anno_uscita', '—')}  ·  "
                 f"**Durata:** {f.get('durata_min', '—')} min")
        if f.get("generi"):
            st.write("**Generi:** " + ", ".join(f["generi"]))
        r = f.get("rating", {})
        st.write(f"**Rating TMDB:** {r.get('tmdb_media', '—')} "
                 f"({r.get('tmdb_voti', '—')} voti)")
        registi = [t["nome"] for t in f.get("troupe", []) if t.get("ruolo") == "Director"]
        if registi:
            st.write("**Regia:** " + ", ".join(registi))
        st.write(f.get("descrizione") or "_Nessuna descrizione disponibile._")

        disp = f.get("disponibile_su_IT") or {}
        if disp.get("streaming"):
            st.success("In streaming: " + ", ".join(disp["streaming"]))
        if disp.get("noleggio"):
            st.info("A noleggio: " + ", ".join(disp["noleggio"]))

    # cast
    st.subheader("Cast")
    cast = f.get("cast", [])[:12]
    if cast:
        colonne = st.columns(6)
        for i, c in enumerate(cast):
            with colonne[i % 6]:
                if c.get("foto_url"):
                    st.image(c["foto_url"], use_container_width=True)
                st.markdown(f"**{c.get('nome', '')}**")
                st.caption(c.get("personaggio", ""))
                # Punto di integrazione con la pagina persona (modulo del compagno):
                # qui ogni attore diventerà un link a ?persona_id=c["id_persona"].

    case = f.get("produzione", {}).get("case", [])
    if case:
        st.caption("Produzione: " + ", ".join(case))


# =========================================================================
# Vista elenco (ricerca, filtri, scoperta)
# =========================================================================
def mostra_griglia(risultati):
    if not risultati:
        st.info("Nessun film trovato con questi criteri.")
        return
    colonne = st.columns(4)
    for i, f in enumerate(risultati):
        with colonne[i % 4]:
            if f.get("locandina_url"):
                st.image(f["locandina_url"], use_container_width=True)
            st.markdown(f"**{f.get('titolo', '—')}**")
            voto = f.get("rating", {}).get("tmdb_media", "—")
            st.caption(f"{f.get('anno_uscita', '—')}  ·  ⭐ {voto}")
            if st.button("Apri", key=f"apri_{f['_id']}"):
                st.query_params["film_id"] = str(f["_id"])
                st.rerun()


def mostra_catalogo():
    st.title("Catalogo film")

    st.sidebar.header("Ricerca e filtri")
    testo = st.sidebar.text_input("Cerca per titolo")

    generi = ["(tutti)"] + generi_disponibili()
    genere = st.sidebar.selectbox("Genere", generi)

    anno_min, anno_max = intervallo_anni()
    intervallo = st.sidebar.slider("Anni", anno_min, anno_max, (anno_min, anno_max))

    voti_min = st.sidebar.number_input(
        "Voti minimi", min_value=0, max_value=50000,
        value=catalogo.SOGLIA_VOTI, step=500)

    limite = st.sidebar.slider("Numero di risultati", 4, 40, 20, step=4)

    if testo:
        # la ricerca per titolo ha la precedenza sui filtri
        risultati = catalogo.cerca_per_titolo(testo, limite)
        st.caption(f"Risultati per «{testo}»")
    else:
        risultati = catalogo.cerca_film(
            genere=None if genere == "(tutti)" else genere,
            anno_min=intervallo[0],
            anno_max=intervallo[1],
            voti_min=voti_min,
            limite=limite,
        )

    mostra_griglia(risultati)


# =========================================================================
# Routing: scheda se c'è film_id nell'URL, altrimenti il catalogo
# =========================================================================
parametri = st.query_params
if "film_id" in parametri:
    try:
        mostra_scheda(int(parametri["film_id"]))
    except ValueError:
        st.error("Identificatore film non valido.")
else:
    mostra_catalogo()
