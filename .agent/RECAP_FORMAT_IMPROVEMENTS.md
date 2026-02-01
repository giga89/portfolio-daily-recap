# Migliorie al Formato dei Riassunti AI

## Branch: `feature/improve-ai-recap-format`

## Obiettivo
Migliorare i due riassunti AI (daily e monthly) organizzando i contenuti per tag e argomenti, con un formato più strutturato e visivamente più accattivante.

## Modifiche Implementate

### 1. **Nuovo Formato Organizzato per Argomenti**
Entrambi i recap (giornaliero e mensile) ora seguono una struttura basata su **argomenti/topic**:

#### Struttura del Daily Recap:
```
🌍 MARKET OVERVIEW
📊📈💹 S&P500 Rally
Il S&P 500 è salito dell'1.2% oggi grazie agli utili tech...

🏛️💵🔔 Fed Decision
La Federal Reserve ha tagliato i tassi di 25bps...

💼 PORTFOLIO FOCUS
📦📦📦 $AMZN
Amazon ha annunciato un nuovo sistema logistico AI...

🤖💡🚀 $NVDA
NVIDIA presenta nuovi chip per AI...
```

#### Struttura del Monthly Recap:
```
🌍 MONTHLY MARKET OVERVIEW
🏛️💵🔔 Fed Rate Decision
La Federal Reserve ha tagliato i tassi di 25bps a 4.25-4.50%...

📊📈💹 Market Trends
I mercati globali hanno registrato guadagni solidi a gennaio...

💼 PORTFOLIO IMPACT & OUTLOOK
🤖💡🚀 $NVDA
NVIDIA ha registrato guadagni del 15% questo mese. Prospettive positive per Q1...

⚡🔋🌍 Energy Sector
Il settore energetico ha beneficiato dell'aumento dei prezzi...
```

### 2. **Formato per ogni Topic**
- **3 emoji rilevanti** che rappresentano visivamente il topic
- **Tag eToro** (quando disponibile nel budget globale di 5 tag): `$AMZN`, `$NVDA`, ecc.
- **Titolo breve** del topic
- **1-3 frasi** di descrizione concisa

### 3. **Limiti Implementati**

#### Limiti per Argomento:
- **MAX 5 argomenti** nella sezione MARKET OVERVIEW
- **MAX 5 argomenti** nella sezione PORTFOLIO FOCUS
- Totale: **MAX 10 argomenti** per recap

#### Limiti per Tag:
- **MAX 5 tag globali** in tutto il recap (invariato)
- Logica di **rotazione dei tag** mantenuta (evita ripetizioni)
- I tag sono usati SOLO nella sezione PORTFOLIO FOCUS/IMPACT

#### Limiti di Lunghezza:
- **Daily AI section**: max 2000 caratteri
- **Monthly AI section**: max 2200 caratteri
- **Recap completo**: **MAX 4500 caratteri totali**
- Se il recap supera 4500 caratteri, viene troncato automaticamente

### 4. **File Modificati**

#### `src/ai_news_generator.py`
- **`generate_market_news_recap()`**: Aggiornato prompt per formato topic-based
  - Richiede esplicitamente max 5 topic per sezione
  - Formato emoji + tag standardizzato
  - Esempi chiari nel prompt
  
- **`generate_monthly_ai_recap()`**: Aggiornato prompt per formato topic-based
  - Stessa struttura del daily ma con focus mensile
  - Esempi specifici per il contesto mensile

#### `src/formatter.py`
- **`generate_recap()`**: Aggiunto controllo di lunghezza
  - Verifica che il recap finale non superi 4500 caratteri
  - Tronca con messaggio se necessario
  - Log della lunghezza per debugging

### 5. **Esempi di Output Atteso**

#### Daily Recap - PORTFOLIO FOCUS:
```
💼 PORTFOLIO FOCUS

📦📦📦 $AMZN
Amazon ha lanciato un nuovo sistema di logistica AI che promette di ridurre i tempi di consegna del 30%. Le azioni sono salite del 3.2% sulla notizia.

🤖💡🚀 $NVDA  
NVIDIA ha presentato la nuova architettura Blackwell. Gli analisti alzano il target price a $150.

⚡🔋🌍 Clean Energy Sector
Il settore dell'energia pulita beneficia dei nuovi incentivi governativi. Prospettive positive per Q2.
```

#### Monthly Recap - MONTHLY MARKET OVERVIEW:
```
🌍 MONTHLY MARKET OVERVIEW

🏛️💵🔔 Fed Rate Decision
La Federal Reserve ha tagliato i tassi di 25bps a 4.25-4.50%, segnalando un approccio più accomodante. I mercati hanno reagito positivamente con un rally di fine mese.

📊📈💹 January Market Rally  
Lo S&P 500 ha chiuso gennaio con un guadagno del 4.5%, il miglior inizio d'anno dal 2019. Il Nasdaq ha superato il 6% grazie al settore tech.

🌏🇨🇳📉 China Slowdown
L'economia cinese mostra segni di rallentamento con il PMI manifatturiero in contrazione. Impatto sui mercati asiatici e sulle commodities.
```

## Vantaggi del Nuovo Formato

1. **✨ Maggiore Leggibilità**: Ogni argomento è immediatamente riconoscibile
2. **🎯 Focus Migliorato**: Le informazioni sono organizzate per tema
3. **📱 Ottimizzazione Mobile**: Il formato con emoji è perfetto per Telegram
4. **🔄 Rotazione Tag**: I tag continuano a ruotare evitando ripetizioni
5. **⚖️ Controllo Lunghezza**: Il limite di 4500 caratteri garantisce compatibilità con i limiti di eToro
6. **🎨 Visivamente Accattivante**: Le emoji triplicare creano un header distintivo

## Testing

Per testare le modifiche:

```bash
# Esegui il generatore di recap
python src/main.py

# Oppure tramite GitHub Actions
# Il workflow esistente utilizzerà automaticamente il nuovo formato
```

## Note Tecniche

- Il prompt AI è stato riscritto per essere più prescrittivo sul formato
- Gli esempi nel prompt guidano l'AI a produrre output consistente
- I limiti di caratteri sono applicati sia a livello di AI che di formatter
- La logica di rotazione tag esistente è stata preservata completamente
- Compatibile con entrambi i recap (daily e monthly)

## Prossimi Passi

1. Testare il nuovo formato con una run reale
2. Verificare che i limiti di caratteri siano rispettati
3. Controllare la qualità visiva su Telegram/eToro
4. Eventualmente fare merge su `main` dopo i test
