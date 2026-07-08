"""
Pagina Streamlit del profilo utente: diario delle visioni, voti e liste.

Usa le funzioni del modulo `gestione_utente` (logica e query invariate) e la
ricerca per titolo del modulo `catalogo`. La configurazione della pagina
(titolo, layout) sta nell'entrypoint app.py.
"""

import streamlit as st
from gestione_utente import (
    inizializza_utente, registra_visione, modifica_voto_recensione,
    rimuovi_visione, leggi_diario_completo, ottieni_media_e_visioni,
    ottieni_generi_preferiti, ottieni_liste_utente, crea_lista,
    elimina_lista, aggiungi_a_lista, rimuovi_da_lista, ottieni_dettagli_lista
)
# Importazione della ricerca creata dal compagno
from catalogo import cerca_per_titolo

inizializza_utente()


# --- feedback che sopravvive al rerun -------------------------------------
# st.success seguito subito da st.rerun() sparirebbe prima di essere letto:
# il messaggio si parcheggia in session_state e si mostra al giro successivo.
def segnala(messaggio, tipo="successo"):
    st.session_state["_esito_profilo"] = (tipo, messaggio)


if "_esito_profilo" in st.session_state:
    tipo, messaggio = st.session_state.pop("_esito_profilo")
    if tipo == "successo":
        st.success(messaggio)
    else:
        st.warning(messaggio)


# --- selettore di film riusabile (ricerca per titolo, logica del catalogo) --
def selettore_film(chiave, etichetta="Cerca il film per titolo"):
    """Campo di ricerca + tendina dei risultati. Restituisce l'id scelto o None."""
    testo = st.text_input(etichetta, key=f"cerca_{chiave}",
                          placeholder="Es. Inception")
    if not testo:
        return None
    risultati = cerca_per_titolo(testo, limite=10)
    if not risultati:
        st.info("Nessun film trovato con questo titolo nel catalogo.")
        return None
    opzioni = {f"{r['titolo']} ({r.get('anno_uscita', 'N/D')})": r["_id"]
               for r in risultati}
    scelto = st.selectbox("Risultati", list(opzioni.keys()), key=f"sel_{chiave}")
    return opzioni[scelto]


# ===========================================================================
# Intestazione e statistiche
# ===========================================================================
st.title("Il mio profilo")
st.caption("Il tuo diario delle visioni, i voti e le liste personali.")

stats = ottieni_media_e_visioni()
generi = ottieni_generi_preferiti()

col1, col2, col3 = st.columns(3)
col1.metric("Visioni totali", stats["visioni"])
col2.metric("Media dei tuoi voti",
            f"{round(stats['media_voti'], 1)} / 10" if stats["media_voti"] else "N/D")
col3.metric("Genere preferito",
            f"{generi[0]['_id']}" if generi else "N/D",
            help=f"{generi[0]['conteggio']} film visti" if generi else None)

st.divider()

diario_completo = leggi_diario_completo()

# ===========================================================================
# Diario delle visioni (il contenuto principale della pagina)
# ===========================================================================
st.header("Diario delle visioni")

if not diario_completo:
    st.info("Il tuo diario è ancora vuoto: registra la prima visione qui sotto.")
else:
    st.caption(f"{len(diario_completo)} visioni registrate, dalla più recente.")
    for visione in diario_completo:
        with st.container(border=True):
            col_info, col_azione = st.columns([5, 1], vertical_alignment="center")
            with col_info:
                st.markdown(f"**{visione.get('titolo', 'Titolo non disponibile')}** "
                            f"({visione.get('anno', 'N/D')})")
                st.caption(f"Il tuo voto: {visione['mio_voto']}/10 · "
                           f"Visto il {visione['data_visione']}")
                if visione.get("recensione"):
                    st.markdown(f"_{visione['recensione']}_")
            with col_azione:
                st.markdown(f"[Apri scheda](/?film_id={visione['id_film']})")

st.divider()

# ===========================================================================
# Azioni: registra, modifica, liste
# ===========================================================================
st.header("Gestisci il diario e le liste")
tab_add, tab_edit, tab_liste = st.tabs(
    ["Registra una visione", "Modifica o elimina", "Le mie liste"])

# --- Registra una visione --------------------------------------------------
with tab_add:
    id_film = selettore_film("add", "Cerca il film che hai visto")

    with st.form("form_registra", border=True):
        data_v = st.date_input("Data di visione")
        voto = st.slider("Il tuo voto", min_value=0, max_value=10, value=7)
        recensione = st.text_area("La tua recensione (facoltativa)",
                                  placeholder="Cosa ne pensi del film?")
        submit_add = st.form_submit_button("Salva nel diario", type="primary")
        if submit_add:
            if id_film is None:
                st.error("Prima cerca e seleziona un film qui sopra.")
            else:
                registra_visione(id_film, data_v, voto, recensione)
                segnala("Visione registrata nel diario.")
                st.rerun()

# --- Modifica o elimina ----------------------------------------------------
with tab_edit:
    if not diario_completo:
        st.info("Non hai ancora visioni da modificare o rimuovere.")
    else:
        opzioni_modifica = {f"{v.get('titolo', 'Titolo non disponibile')} "
                            f"({v.get('anno', 'N/D')})": v
                            for v in diario_completo}
        titolo_scelto = st.selectbox("Scegli una visione dal diario",
                                     list(opzioni_modifica.keys()))
        visione_corrente = opzioni_modifica[titolo_scelto]
        id_film_mod = visione_corrente["id_film"]

        with st.container(border=True):
            nuovo_voto = st.slider("Voto", min_value=0, max_value=10,
                                   value=visione_corrente["mio_voto"], key="new_v")
            nuova_rec = st.text_area("Recensione",
                                     value=visione_corrente.get("recensione", ""),
                                     key="new_rec")
            col_btn_mod, col_btn_del = st.columns(2)
            if col_btn_mod.button("Aggiorna la visione", type="primary",
                                  use_container_width=True):
                modifica_voto_recensione(id_film_mod, nuovo_voto, nuova_rec)
                segnala("Visione aggiornata.")
                st.rerun()
            if col_btn_del.button("Elimina dal diario", use_container_width=True):
                rimuovi_visione(id_film_mod)
                segnala(f"«{visione_corrente.get('titolo', '')}» rimosso dal diario.",
                        tipo="avviso")
                st.rerun()

# --- Le mie liste ------------------------------------------------------------
with tab_liste:
    liste_attuali = ottieni_liste_utente()
    col_liste, col_gestione = st.columns([3, 2], gap="large")

    # colonna principale: il contenuto delle liste
    with col_liste:
        st.subheader("Le tue liste")
        if not liste_attuali:
            st.info("Non hai ancora liste: creane una qui a fianco.")
        else:
            nomi_liste = [l["nome"] for l in liste_attuali]
            lista_scelta_vis = st.selectbox("Lista da esplorare", nomi_liste,
                                            key="sel_list_vis")

            dettagli_lista = ottieni_dettagli_lista(lista_scelta_vis)
            film_nella_lista = [f for f in dettagli_lista
                                if f.get("id_film") is not None]

            if not film_nella_lista:
                st.info("Questa lista è ancora vuota: aggiungi un film qui a fianco.")
            else:
                st.caption(f"{len(film_nella_lista)} film in questa lista.")
                for f in film_nella_lista:
                    with st.container(border=True):
                        col_titolo, col_apri, col_del = st.columns(
                            [4, 1, 1], vertical_alignment="center")
                        with col_titolo:
                            st.markdown(f"**{f.get('titolo', 'Titolo non disponibile')}** "
                                        f"({f.get('anno', 'N/D')})")
                        with col_apri:
                            if f.get("id_film"):
                                st.markdown(f"[Apri scheda](/?film_id={f['id_film']})")
                        with col_del:
                            if st.button("Rimuovi",
                                         key=f"del_{lista_scelta_vis}_{f['id_film']}",
                                         help="Rimuovi questo film dalla lista"):
                                rimuovi_da_lista(lista_scelta_vis, f["id_film"])
                                segnala("Film rimosso dalla lista.", tipo="avviso")
                                st.rerun()

            if st.button("Elimina l'intera lista",
                         help="Cancella la lista selezionata e il suo contenuto"):
                elimina_lista(lista_scelta_vis)
                segnala(f"Lista «{lista_scelta_vis}» eliminata.", tipo="avviso")
                st.rerun()

    # colonna secondaria: creare liste e aggiungere film
    with col_gestione:
        st.subheader("Crea una lista")
        nuova_l = st.text_input("Nome della lista",
                                placeholder="Es. Da vedere, Migliori finali")
        if st.button("Crea la lista", type="primary"):
            if nuova_l:
                crea_lista(nuova_l)
                segnala(f"Lista «{nuova_l}» creata.")
                st.rerun()
            else:
                st.error("Inserisci un nome per la lista.")

        st.divider()

        st.subheader("Aggiungi un film")
        if not liste_attuali:
            st.caption("Prima crea una lista.")
        else:
            lista_scelta = st.selectbox("In quale lista?",
                                        [l["nome"] for l in liste_attuali],
                                        key="sel_list_add")
            film_da_agg = selettore_film("lista", "Cerca il film da aggiungere")
            if film_da_agg is not None:
                if st.button("Aggiungi alla lista", type="primary"):
                    aggiungi_a_lista(lista_scelta, film_da_agg)
                    segnala("Film aggiunto alla lista.")
                    st.rerun()
