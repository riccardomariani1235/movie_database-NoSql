import streamlit as st
import pandas as pd
from gestione_utente import (
    inizializza_utente, registra_visione, modifica_voto_recensione,
    rimuovi_visione, leggi_diario_completo, ottieni_media_e_visioni,
    ottieni_generi_preferiti, ottieni_liste_utente, crea_lista, aggiungi_a_lista
)
# IMPORTIAMO LA RICERCA DAL MODULO DEL TUO COMPAGNO
from catalogo import cerca_per_titolo 

st.set_page_config(page_title="Profilo Utente - CineLog", layout="wide")
inizializza_utente() 

st.title("📊 Area Personale Utente")

# --- SEZIONE STATISTICHE ---
st.header("Le Mie Statistiche")
stats = ottieni_media_e_visioni()
generi = ottieni_generi_preferiti()

col1, col2, col3 = st.columns(3)
col1.metric("Totale Visioni", stats["visioni"])
col2.metric("Media Voti Personale", f"{round(stats['media_voti'], 1)} / 10" if stats["media_voti"] else "N/D")

if generi:
    col3.metric("Genere Preferito", f"{generi[0]['_id']} ({generi[0]['conteggio']} film)")

st.divider()

diario_completo = leggi_diario_completo()

# --- PANNELLO OPERAZIONI ---
st.header("Aggiungi o Gestisci una Visione")
tab_add, tab_edit, tab_liste = st.tabs(["Registra Visione", "Modifica/Elimina", "Gestione Liste"])

with tab_add:
    st.markdown("Cerca il film per titolo per aggiungerlo al tuo diario.")
    
    # 1. Nuova barra di ricerca per nome invece che per ID numerico
    titolo_ricerca = st.text_input("🔍 Cerca film da aggiungere (es. 'Inception', 'Spider-Man')", key="cerca_add")
    
    id_film = None
    if titolo_ricerca:
        risultati = cerca_per_titolo(titolo_ricerca, limite=10) # Usa la query del compagno
        if risultati:
            # Creiamo le opzioni da mostrare nel menu a tendina
            opzioni_film = {f"{r['titolo']} ({r.get('anno_uscita', 'N/D')})": r['_id'] for r in risultati}
            film_scelto = st.selectbox("Seleziona il film corretto dai risultati:", list(opzioni_film.keys()), key="sel_add")
            id_film = opzioni_film[film_scelto] # Estraiamo l'ID di nascosto
        else:
            st.warning("Nessun film trovato con questo titolo nel catalogo.")
            
    with st.form("form_registra"):
        data_v = st.date_input("Data di Visione")
        voto = st.slider("Il tuo Voto", min_value=0, max_value=10, value=7)
        recensione = st.text_area("La tua Recensione", placeholder="Scrivi qui cosa ne pensi del film!")
        
        submit_add = st.form_submit_button("Salva nel Diario")
        if submit_add:
            if id_film is None:
                st.error("⚠️ Attenzione: cerca e seleziona un film per poterlo salvare!")
            else:
                registra_visione(id_film, data_v, voto, recensione)
                st.success("Visione registrata correttamente!")
                st.rerun()

with tab_edit:
    if not diario_completo:
        st.info("Non hai ancora film nel diario da modificare o rimuovere.")
    else:
        opzioni_modifica = {f"{v['titolo']} ({v['anno']})": v for v in diario_completo}
        titolo_scelto = st.selectbox("Seleziona il film dal tuo diario:", list(opzioni_modifica.keys()))
        
        visione_corrente = opzioni_modifica[titolo_scelto]
        id_film_mod = visione_corrente["id_film"]
        
        with st.expander("Modifica o Cancella", expanded=True):
            nuovo_voto = st.slider("Cambia il Voto", min_value=0, max_value=10, value=visione_corrente["mio_voto"], key="new_v")
            nuova_rec = st.text_area("Cambia la Recensione", value=visione_corrente.get("recensione", ""), key="new_rec")
            
            col_btn_mod, col_btn_del = st.columns(2)
            
            if col_btn_mod.button("Aggiorna Visione"):
                modifica_voto_recensione(id_film_mod, nuovo_voto, nuova_rec)
                st.success("Visione aggiornata con successo!")
                st.rerun()
                
            if col_btn_del.button("❌ Elimina dal Diario"):
                rimuovi_visione(id_film_mod)
                st.warning(f"'{visione_corrente['titolo']}' è stato rimosso definitivamente dal diario.")
                st.rerun()

with tab_liste:
    col_crea, col_agg = st.columns(2)
    
    with col_crea:
        st.subheader("Crea una Lista")
        nuova_l = st.text_input("Nome lista (es. 'Da vedere', 'Preferiti')")
        if st.button("Crea"):
            if nuova_l:
                crea_lista(nuova_l)
                st.success(f"Lista '{nuova_l}' creata!")
                st.rerun()
            else:
                st.error("Inserisci un nome valido.")
                
    with col_agg:
        st.subheader("Aggiungi film a una Lista")
        liste_attuali = ottieni_liste_utente()
        if not liste_attuali:
            st.info("Crea prima una lista qui a sinistra.")
        else:
            nomi_liste = [l["nome"] for l in liste_attuali]
            lista_scelta = st.selectbox("In quale lista?", nomi_liste)
            
            # 2. Ricerca per nome anche per le liste
            titolo_ricerca_lista = st.text_input("🔍 Cerca film da aggiungere", key="cerca_list")
            
            film_da_agg = None
            if titolo_ricerca_lista:
                risultati_lista = cerca_per_titolo(titolo_ricerca_lista, limite=10) # Usa la query del compagno
                if risultati_lista:
                    opzioni_lista = {f"{r['titolo']} ({r.get('anno_uscita', 'N/D')})": r['_id'] for r in risultati_lista}
                    film_scelto_lista = st.selectbox("Seleziona il film:", list(opzioni_lista.keys()), key="sel_list")
                    film_da_agg = opzioni_lista[film_scelto_lista]
                else:
                    st.warning("Nessun film trovato.")
            
            if st.button("Aggiungi"):
                if film_da_agg is None:
                    st.error("⚠️ Cerca e seleziona un film!")
                else:
                    aggiungi_a_lista(lista_scelta, film_da_agg)
                    st.success("Film inserito nella lista!")
                    st.rerun()

st.divider()

# --- SEZIONE VISUALIZZAZIONE DIARIO ---
st.header("🎬 Il mio Diario delle Visioni")

if diario_completo:
    for visione in diario_completo:
        col_testo, col_link = st.columns([4, 1])
        
        with col_testo:
            st.markdown(f"**{visione['titolo']}** ({visione['anno']})")
            st.write(f"⭐ Il tuo voto: {visione['mio_voto']} | 📅 Visto il: {visione['data_visione']}")
            if visione.get("recensione"):
                st.info(f"📝 *{visione['recensione']}*")
                
        with col_link:
            st.markdown(f"[:material/movie: Apri Scheda](/?film_id={visione['id_film']})", help="Vai alla scheda del film nel Catalogo")
            
        st.divider()
else:
    st.info("Il tuo diario è ancora vuoto. Registra un film per iniziare!")
