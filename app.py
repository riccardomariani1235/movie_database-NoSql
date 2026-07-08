"""
Entrypoint dell'app multipagina CineLog.

Avvio:
    streamlit run app.py

Qui si registrano le pagine con st.navigation, che permette titoli in
sidebar indipendenti dai nomi dei file. Gli `url_path` mantengono gli URL
storici (`/` per il catalogo, `/Persona` per la pagina persona), così i
link tra pagine (`?film_id=`, `?persona_id=`) continuano a funzionare.
"""

import streamlit as st

st.set_page_config(page_title="CineLog", layout="wide")

pagine = st.navigation([
    st.Page("pages/ricerca_film.py", title="Ricerca Film", default=True),
    st.Page("pages/1_Persona.py", title="Attori e registi", url_path="Persona"),
    st.Page("pages/3_Profilo_Utente.py", title="Il mio profilo", url_path="Profilo_Utente"),
])
pagine.run()
