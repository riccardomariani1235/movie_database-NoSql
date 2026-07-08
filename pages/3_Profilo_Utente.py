import streamlit as st
import pandas as pd
from gestione_utente import (
    inizializza_utente, registra_visione, modifica_voto_recensione,
    rimuovi_visione, leggi_diario_completo, ottieni_media_e_visioni,
    ottieni_generi_preferiti, ottieni_liste_utente, crea_lista, aggiungi_a_lista
)

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

# Carichiamo il diario subito, così lo usiamo per rendere intelligenti i menu a tendina
diario_completo = leggi_diario_completo()

# --- PANNELLO OPERAZIONI (USABILITY UPGRADE) ---
st.header("Aggiungi o Gestisci una Visione")
tab_add, tab_edit, tab_liste = st.tabs(["Registra Visione", "Modifica/Elimina", "Gestione Liste"])

with tab_add:
    st.markdown("Cerca un film nel **Catalogo**, copia il suo ID e incollalo qui sotto per registrarlo!")
    with st.form("form_registra"):
        id_film = st.number_input("ID Film (TMDB ID)", step=1, value=None, placeholder="Es. 514999 (F9 - The Fast Saga)")
        data_v = st.date_input("Data di Visione")
        voto = st.slider("Il tuo Voto", min_value=0, max_value=10, value=7)
        recensione = st.text_area("La tua Recensione", placeholder="Un quarto di miglio alla volta... Scrivi qui cosa ne pensi del film!")
        
        submit_add = st.form_submit_button("Salva nel Diario")
        if submit_add:
            if id_film is None:
                st.error("⚠️ Attenzione: devi inserire l'ID del film per poterlo salvare!")
            else:
                registra_visione(id_film, data_v, voto, recensione)
                st.success("Visione registrata correttamente!")
                st.rerun()

with tab_edit:
    if not diario_completo:
        st.info("Non hai ancora film nel diario da modificare o rimuovere.")
    else:
        # SUPER UX: Invece dell'ID, l'utente seleziona il TITOLO dal suo diario
        opzioni_modifica = {f"{v['titolo']} ({v['anno']})": v for v in diario_completo}
        titolo_scelto = st.selectbox("Seleziona il film dal tuo diario:", list(opzioni_modifica.keys()))
        
        # Recuperiamo la visione corrispondente per pre-compilare i campi
        visione_corrente = opzioni_modifica[titolo_scelto]
        id_film_mod = visione_corrente["id_film"]
        
        with st.expander("Modifica o Cancella", expanded=True):
            # Pre-compiliamo lo slider e l'area di testo con i dati già salvati dall'utente
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
        nuova_l = st.text_input("Nome lista (es. 'Migliori finali' o 'Cybersecurity')")
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
            film_da_agg = st.number_input("ID Film da inserire", step=1, value=None)
            
            if st.button("Aggiungi"):
                if film_da_agg is None:
                    st.error("⚠️ Inserisci l'ID del film!")
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
