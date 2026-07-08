# CineLog — Diario personale di film su MongoDB

Progetto per il corso NoSQL (ITS). Applicazione personale per catalogare e loggare film, in stile Letterboxd/IMDb, costruita su **MongoDB** come database documentale. I dati provengono dall'API di TMDB.

Questo documento serve per iniziare a lavorare al progetto: cosa fa, com'è modellato il database, come ottenere i dati, chi fa cosa.

---

## Lo use case

Un'app d'uso personale dove l'utente logga i film visti (con voto, recensione, data), tiene watchlist e liste a tema, e consulta per ogni film la scheda completa: descrizione, cast, troupe, produzione, rating aggregato, disponibilità streaming in Italia, anno e locandina.

L'argomento tecnico che giustifica il database documentale è la **località del dato**. La scheda di un film è un aggregato coeso (titolo, cast con personaggi, troupe per reparto, disponibilità per paese) che l'app legge sempre intero: nel modello documentale quella lettura è una singola read sull'`_id`. La versione relazionale modellerebbe lo stesso aggregato spezzandolo su cinque o sei tabelle e ricomponendolo con join a ogni apertura di scheda. Entrambi funzionano; il documento aderisce alla forma del dominio, il relazionale la spezza e la ricompone. Lo stesso vale per il diario dell'utente, con le visioni embedded lette in una sola operazione.

Nota per la difesa all'esame: i documenti hanno struttura uniforme (solo film), quindi il vantaggio sta nella località, non nella flessibilità di schema. Ammetterlo apertamente rafforza la credibilità sul punto dove il vantaggio sta davvero. Gli array di sotto-oggetti (`cast`, `troupe`, `keyword`) in SQL si modellano con tabelle associative, quindi vanno presentati come attrito e ricomposizione via join, senza dichiararli impossibili in relazionale.

## Cosa viene valutato

La valutazione riguarda la parte **database**: connessione, query, aggregazioni, indici, modellazione dei documenti e motivazione delle scelte. Il frontend Streamlit serve come vetrina per la demo e va mantenuto minimale: mostra le funzionalità del database, senza cura tecnica dell'interfaccia.

---

## Il database

Nome database: `movie_database`. Due collezioni.

### Collezione `film` (2000 documenti)

I 2000 film più popolari su TMDB. Esempio di struttura:

```jsonc
{
  "_id": 27205,                       // id TMDB, usato come chiave in tutto il progetto
  "titolo": "Inception",
  "titolo_originale": "Inception",
  "anno_uscita": 2010,
  "data_uscita": "2010-07-15",
  "descrizione": "...",
  "locandina_url": "https://image.tmdb.org/t/p/w500/....jpg",
  "generi": ["Azione", "Fantascienza"],
  "durata_min": 148,
  "lingua_originale": "en",
  "rating": { "tmdb_media": 8.4, "tmdb_voti": 36000, "imdb_id": "tt1375666" },
  "popolarita": 120.5,
  "cast":  [ { "id_persona": 6193, "nome": "...", "personaggio": "...", "ordine": 0, "foto_url": "..." } ],
  "troupe":[ { "id_persona": 525,  "nome": "...", "reparto": "Directing", "ruolo": "Director" } ],
  "produzione": { "case": ["..."], "paesi": ["US", "GB"] },
  "keyword": ["sogno", "colpo", "subconscio"],
  "disponibile_su_IT": {
      "streaming": ["Netflix"], "noleggio": ["Apple TV"], "acquisto": ["..."],
      "link_tmdb": "https://www.themoviedb.org/movie/27205/watch?locale=IT"
  },
  "recensioni": []
}
```

Nota: `cast` e `troupe` sono array embedded dentro il film, la località del dato da difendere all'esame. Ogni persona qui porta il suo `id_persona`.

### Collezione `persone` (173.702 documenti)

Attori e troupe estratti dai credits dei film. La struttura base:

```jsonc
{
  "_id": 6193,                   // id TMDB, coincide con id_persona nei film
  "nome": "Leonardo DiCaprio",
  "reparto_principale": "Acting",
  "foto_url": "https://image.tmdb.org/t/p/w185/....jpg"
}
```

Per il **cast principale (primi 10 per locandina) e i registi**, in totale 12.303 persone, il documento è arricchito con l'anagrafica completa:

```jsonc
{
  "_id": 6193, "nome": "Leonardo DiCaprio", "reparto_principale": "Acting", "foto_url": "...",
  "biografia": "...", "data_nascita": "1974-11-11", "data_morte": null,
  "luogo_nascita": "Los Angeles, California, USA", "genere": "maschile",
  "imdb_id": "nm0000138", "alias": ["Leo"], "popolarita": 42.1,
  "arricchito": true
}
```

Le altre persone (troupe tecnica, comparse) hanno solo i quattro campi base. La pagina persona deve gestire con eleganza il caso "anagrafica non disponibile".

### Collezione `utente` (da definire insieme)

Il documento utente per il diario e le liste. Direzione proposta: diario delle visioni **embedded** come array nel profilo (una read per l'intero diario), liste come array che referenziano i `_id` dei film. Da concordare in gruppo prima di scrivere il codice.

---

## Come ottenere i dati

I dati stanno in MongoDB, non nella repo. Per popolare il proprio database locale:

1. Installare MongoDB Community e MongoDB Compass.
2. Recuperare i file `film.ndjson` e `persone.ndjson` (link condiviso dal gruppo, fuori dalla repo).
3. In Compass, connettersi a `mongodb://localhost:27017`, creare il database `movie_database` con le collezioni `film` e `persone`.
4. Per ciascuna collezione: **Add Data -> Import JSON**, selezionare il file corrispondente, tipo JSON.

Risultato atteso: 2000 documenti in `film`, 173.702 in `persone`.

Gli script che hanno generato i dati (`scarica_film_tmdb.py`, `arricchisci_persone.py`, `esporta_ndjson.py`) sono nella repo per trasparenza sul percorso dei dati. Per lavorare al progetto **non serve rilanciarli**, né serve una chiave TMDB.

---

## Convenzioni condivise (importanti)

Queste regole fanno funzionare il lavoro in parallelo e i collegamenti tra pagine. Vanno rispettate da tutti.

- **Le chiavi sono gli id TMDB.** `_id` per i film, `_id` / `id_persona` per le persone. Ogni collegamento tra collezioni e tra pagine passa da questi id.
- **Le pagine dell'app si collegano tramite id.** Dalla scheda di un film, ogni attore è un link che apre la pagina persona puntata sul suo `id_persona`. La pagina persona legge l'id e carica i dati.
- **Anagrafica opzionale.** Solo le persone con `arricchito: true` hanno biografia e dati anagrafici. Le pagine gestiscono l'assenza senza rompersi.
- **Un modulo di connessione unico** (`connessione.py`) condiviso da tutti, con `movie_database` come default.
- **Credenziali fuori dalla repo.** Nessuna chiave in chiaro nel codice: si leggono da variabile d'ambiente o da un file `.env` inserito nel `.gitignore`.

---

## Divisione del lavoro

Fondazione condivisa da definire insieme per prima: il modulo `connessione.py`, lo schema del documento `utente`, lo script che crea gli indici. Poi i tre moduli procedono in parallelo su file separati.

**Persona 1 — Catalogo e ricerca.** Query sui film: scheda completa in una read, ricerca full-text su titolo e descrizione, filtri per genere/anno/rating con ordinamento e paginazione, discovery di base. Possiede gli indici e la loro motivazione.

**Persona 2 — Persone e collegamenti.** Query sul legame film <-> persone: filmografia di attori e registi, co-attori, registi con cui un attore ha lavorato, persone più presenti nel catalogo. Aggregation pipeline con `$lookup` e `$unwind`. Possiede la slide delle limitazioni (dove un database a grafo darebbe di più).

**Persona 3 — Utente: diario e liste.** Documento `utente`, registrazione visioni con voto e recensione, watchlist e liste, statistiche personali via aggregation sul diario embedded. Possiede il confronto "questa scheda in SQL" e la motivazione della modellazione.

**Frontend Streamlit**, diviso per pagine: ognuno costruisce la pagina che consuma le proprie query (catalogo/scheda, persona, diario/statistiche), collegate tra loro tramite gli id.

---

## Presentazione (12-15 minuti)

Quattro parti richieste: descrizione del business case e della soluzione, architettura, demo del POC, limitazioni e possibili improvement. Tre relatori, una parte a testa più la demo.

## Attribuzioni

I dati provengono da TMDB. Questo prodotto usa l'API di TMDB e non è approvato o certificato da TMDB. La disponibilità streaming è fornita da JustWatch.
