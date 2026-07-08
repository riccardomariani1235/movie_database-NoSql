import streamlit as st
import pandas as pd
from gestione_utente import (
    inizializza_utente, registra_visione, modifica_voto_recensione,
    rimuovi_visione, leggi_diario_completo, ottieni_media_e_visioni,
    ottieni_liste_utente, crea_lista, aggiungi_a_lista
)

st.set_page_config(page_title="Profilo Utente - CineLog", layout="wide")

# Assicura la presenza del documento utente all'avvio[cite: 1]
inizializza_utente() 

st.title("📊 Area Personale Utente")

# --- SEZIONE STATISTICHE ---
st.header("Le Mie Statistiche")
stats = ottieni_media_e_visioni()

col1, col2 = st.columns(2)
col1.metric("Totale Visioni", stats["visioni"])
col2.metric("Media Voti Personale", f"{round(stats['media_voti'], 1)} / 10" if stats["media_voti"] else "N/D")

st.divider()

# --- PANNELLO OPERAZIONI ---
st.header("Aggiungi o Gestisci una Visione")
tab_add, tab_edit, tab_liste = st.tabs(["Registra Visione", "Modifica/Elimina", "Gestione Liste"])

with tab_add:
    with st.form("form_registra"):
        id_film = st.number_input("ID Film (TMDB ID)", step=1, value=27205)
        data_v = st.date_input("Data di Visione")
        voto = st.slider("Il tuo Voto", min_value=0, max_value=10, value=7)
        recensione = st.text_area("La tua Recensione", placeholder="Scrivi un commento...")
        
        submit_add = st.form_submit_button("Salva nel Diario")
        if submit_add:
            registra_visione(id_film, data_v, voto, recensione)
            st.success("Visione registrata correttamente!")
            st.rerun()

with tab_edit:
    id_film_mod = st.number_input("Inserisci ID Film da modificare/rimuovere", step=1, key="mod_id")
    
    with st.expander("Modifica Voto e Recensione"):
        nuovo_voto = st.slider("Nuovo Voto", min_value=0, max_value=10, value=8, key="new_v")
        nuova_rec = st.text_area("Nuova Recensione", key="new_rec")
        if st.button("Aggiorna Visione"):
            modifica_voto_recensione(id_film_mod, nuovo_voto, nuova_rec)
            st.success("Visione aggiornata!")
            st.rerun()
            
    if st.button("❌ Elimina definitivamente dal Diario"):
        rimuovi_visione(id_film_mod)
        st.warning("Visione rimossa dal diario.")
        st.rerun()

with tab_liste:
    st.subheader("Le tue Liste a Tema")
    nuova_l = st.text_input("Nome nuova lista")
    if st.button("Crea Lista"):
        if nuova_l:
            crea_lista(nuova_l)
            st.success(f"Lista '{nuova_l}' creata!")
            st.rerun()
            
    liste_attuali = ottieni_liste_utente()
    if liste_attuali:
        nomi_liste = [l["nome"] for l in liste_attuali]
        lista_scelta = st.selectbox("Seleziona Lista", nomi_liste)
        film_da_agg = st.number_input("ID Film da inserire nella lista", step=1)
        if st.button("Aggiungi alla Lista"):
            aggiungi_a_lista(lista_scelta, film_da_agg)
            st.success("Film inserito nella lista!")
            st.rerun()

st.divider()

# --- SEZIONE VISUALIZZAZIONE DIARIO ---
st.header("🎬 Il mio Diario delle Visioni")
diario_completo = leggi_diario_completo()

if diario_completo:
    st.write("I tuoi film visti di recente:")
    
    # Creiamo una griglia o lista interattiva al posto di una tabella statica
    for visione in diario_completo:
        col_testo, col_link = st.columns([4, 1])
        
        with col_testo:
            st.markdown(f"**{visione['titolo']}** ({visione['anno']})")
            st.write(f"⭐ Il tuo voto: {visione['mio_voto']} | 📅 Visto il: {visione['data_visione']}")
            if visione.get("recensione"):
                st.info(f"📝 *{visione['recensione']}*")
                
        with col_link:
            # Sfruttiamo la logica di routing di app.py usando un link HTML/Markdown
            id_f = visione["id_film"]
            st.markdown(f"[:material/movie: Apri Scheda](/?film_id={id_f})", help="Vai alla scheda del film nel Catalogo")
            
        st.divider()
else:
    st.info("Il tuo diario è ancora vuoto. Inserisci una visione nel modulo sopra per iniziare!")
