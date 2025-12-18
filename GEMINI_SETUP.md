# 🔑 Come Ottenere la Google Gemini API Key

Segui questi semplici passaggi per ottenere la tua chiave API gratuita di Google Gemini:

## Passo 1: Vai su Google AI Studio

Apri il browser e vai su: **[Google AI Studio](https://makersuite.google.com/app/apikey)**

## Passo 2: Accedi con il tuo Account Google

- Effettua il login con il tuo account Google
- Se non hai un account Google, creane uno gratuitamente

## Passo 3: Crea una Nuova API Key

1. Clicca su **"Create API Key"** o **"Get API Key"**
2. Seleziona un progetto Google Cloud esistente o creane uno nuovo
   - Se è la prima volta, clicca su "Create API key in new project"
3. La tua API key verrà generata immediatamente

## Passo 4: Copia l'API Key

- Copia la chiave API generata (formato: `AIzaSy...`)
- **IMPORTANTE**: Conservala in modo sicuro, non condividerla pubblicamente

## Passo 5: Aggiungi l'API Key a GitHub Secrets

1. Vai sul tuo repository GitHub
2. Clicca su **Settings** > **Secrets and variables** > **Actions**
3. Clicca su **New repository secret**
4. Nome: `GEMINI_API_KEY`
5. Valore: Incolla la tua API key
6. Clicca su **Add secret**

## Limiti del Free Tier

Google Gemini offre un generoso free tier:

- ✅ **15 richieste al minuto** (per modello)
- ✅ **1500 richieste al giorno** (per modello)
- ✅ **100% gratis** per uso personale
- ✅ Nessuna carta di credito richiesta

Per il nostro caso d'uso (2-3 chiamate al giorno), è più che sufficiente!

## 🛡️ Sistema di Fallback Intelligente

Il nostro sistema usa **3 modelli diversi** per garantire massima affidabilità:

1. **gemini-1.5-flash** (principale - veloce e accurato)
2. **gemini-1.5-flash-8b** (fallback 1 - più leggero)
3. **gemini-1.0-pro** (fallback 2 - affidabile)

Se un modello ha la quota esaurita, prova automaticamente il successivo. **Non ti devi preoccupare di nulla!**

## Test Locale (Opzionale)

Se vuoi testare localmente prima di deployare:

```bash
export GEMINI_API_KEY="la_tua_chiave_api_qui"
python src/data_collector.py
```

## Link Utili

- 📖 [Google AI Studio](https://makersuite.google.com/app/apikey)
- 📚 [Gemini API Documentation](https://ai.google.dev/docs)
- 💰 [Pricing e Free Tier](https://ai.google.dev/pricing)

---

✨ Una volta configurata, il tuo portfolio recap includerà automaticamente le news AI sui mercati USA, CHINA ed EU!
