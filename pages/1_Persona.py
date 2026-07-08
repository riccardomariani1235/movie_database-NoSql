"""
Pagina Streamlit della persona (attore o regista).

Fa parte dell'app multipagina: si avvia sempre con `streamlit run app.py`,
questa pagina risponde su /Persona. Segue la convenzione condivisa: legge
`persona_id` dall'URL, come la scheda film legge `film_id`.

Senza `persona_id` mostra la ricerca per nome e i più presenti nel catalogo.
Usa le funzioni del modulo `persone`.
"""

import streamlit as st

import persone

# la configurazione della pagina (titolo, layout) sta nell'entrypoint app.py

# etichette leggibili per i reparti TMDB
REPARTI = {"Acting": "Recitazione", "Directing": "Regia"}


# --- wrapper con cache: le query girano una volta per persona/ricerca ---
@st.cache_data(ttl=600)
def carica_persona(id_persona):
    return persone.persona_per_id(id_persona)


@st.cache_data(ttl=600)
def carica_filmografia(id_persona):
    return persone.filmografia(id_persona)


@st.cache_data(ttl=600)
def carica_co_attori(id_persona):
    return persone.co_attori(id_persona, limite=6)


@st.cache_data(ttl=600)
def carica_registi(id_persona):
    return persone.registi_di(id_persona, limite=6)


@st.cache_data(ttl=600)
def carica_piu_presenti(reparto):
    return persone.piu_presenti_nel_catalogo(reparto=reparto, limite=12)


def link_persona(id_persona, testo):
    """Link markdown alla pagina di una persona (convenzione ?persona_id=)."""
    return f"[{testo}](/Persona?persona_id={id_persona})"


# =========================================================================
# Vista scheda persona
# =========================================================================
def mostra_scheda(id_persona):
    p = carica_persona(id_persona)
    if not p:
        st.error("Persona non trovata.")
        st.markdown("[← Torna alla ricerca](/Persona)")
        return

    st.markdown("[← Torna alla ricerca](/Persona)")

    col_foto, col_info = st.columns([1, 3])
    with col_foto:
        if p.get("foto_url"):
            st.image(p["foto_url"], use_container_width=True)
    with col_info:
        st.title(p.get("nome", "—"))
        reparto = p.get("reparto_principale")
        if reparto:
            st.caption(REPARTI.get(reparto, reparto))

        # anagrafica: presente solo per le persone arricchite
        if p.get("data_nascita"):
            riga = f"**Nascita:** {p['data_nascita']}"
            if p.get("luogo_nascita"):
                riga += f" — {p['luogo_nascita']}"
            st.write(riga)
        if p.get("data_morte"):
            st.write(f"**Morte:** {p['data_morte']}")

        if p.get("biografia"):
            st.write(p["biografia"])
        else:
            st.caption("_Biografia non disponibile._")

    # filmografia: film in cui compare nel cast o nella troupe
    st.subheader("Filmografia")
    filmografia = carica_filmografia(id_persona)
    if not filmografia:
        st.info("Nessun film del catalogo per questa persona.")
    else:
        st.caption(f"{len(filmografia)} film nel catalogo")
        colonne = st.columns(6)
        for i, f in enumerate(filmografia):
            with colonne[i % 6]:
                if f.get("locandina_url"):
                    st.image(f["locandina_url"], use_container_width=True)
                st.markdown(f"**[{f.get('titolo', '—')}](/?film_id={f['_id']})**")
                ruoli = persone.descrivi_ruoli(f)
                st.caption(f"{f.get('anno_uscita', '—')}  ·  {ruoli}" if ruoli
                           else f"{f.get('anno_uscita', '—')}")

    # collaborazioni: ha senso soprattutto per chi recita
    co = carica_co_attori(id_persona)
    if co:
        st.subheader("Ha recitato più spesso con")
        colonne = st.columns(6)
        for i, c in enumerate(co):
            with colonne[i % 6]:
                if c.get("foto_url"):
                    st.image(c["foto_url"], use_container_width=True)
                st.markdown(link_persona(c["_id"], f"**{c['nome']}**"))
                st.caption(f"{c['film_insieme']} film insieme")

    registi = carica_registi(id_persona)
    if registi:
        st.subheader("Registi con cui ha lavorato")
        colonne = st.columns(6)
        for i, r in enumerate(registi):
            with colonne[i % 6]:
                if r.get("foto_url"):
                    st.image(r["foto_url"], use_container_width=True)
                st.markdown(link_persona(r["_id"], f"**{r['nome']}**"))
                st.caption(f"{r['film_insieme']} film insieme")


# =========================================================================
# Vista ricerca
# =========================================================================
def mostra_ricerca():
    st.title("Persone")
    testo = st.text_input("Cerca attori e registi per nome")

    if testo:
        risultati = persone.cerca_persone(testo)
        if not risultati:
            st.info("Nessuna persona trovata con questo nome.")
            return
        st.caption(f"Risultati per «{testo}»")
        colonne = st.columns(6)
        for i, p in enumerate(risultati):
            with colonne[i % 6]:
                if p.get("foto_url"):
                    st.image(p["foto_url"], use_container_width=True)
                st.markdown(link_persona(p["_id"], f"**{p.get('nome', '—')}**"))
                reparto = p.get("reparto_principale")
                st.caption(REPARTI.get(reparto, reparto or ""))
        return

    # senza ricerca: le facce più presenti nel catalogo, per curiosare
    scelta = st.radio("I più presenti nel catalogo", ["Attori", "Registi"],
                      horizontal=True)
    reparto = "Acting" if scelta == "Attori" else "Directing"
    presenti = carica_piu_presenti(reparto)
    colonne = st.columns(6)
    for i, p in enumerate(presenti):
        with colonne[i % 6]:
            if p.get("foto_url"):
                st.image(p["foto_url"], use_container_width=True)
            st.markdown(link_persona(p["_id"], f"**{p['nome']}**"))
            st.caption(f"{p['n_film']} film nel catalogo")


# =========================================================================
# Routing: scheda se c'è persona_id nell'URL, altrimenti la ricerca
# =========================================================================
parametri = st.query_params
if "persona_id" in parametri:
    try:
        mostra_scheda(int(parametri["persona_id"]))
    except ValueError:
        st.error("Identificatore persona non valido.")
else:
    mostra_ricerca()
