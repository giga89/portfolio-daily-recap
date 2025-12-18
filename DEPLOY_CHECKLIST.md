# ✅ Checklist Pre-Deploy

Prima di fare il commit e push finale, verifica questi punti:

## 🔧 Setup Locale (Opzionale)
- [ ] Installato `google-genai` nel venv locale
  ```bash
  source venv/bin/activate
  pip install google-genai
  ```
- [ ] Testato il modulo AI news generator
  ```bash
  python test_ai_news.py
  ```

## 🔑 GitHub Secrets
- [ ] Vai su GitHub: `Settings` → `Secrets and variables` → `Actions`
- [ ] Verifica che esistano già:
  - [x] `TELEGRAM_BOT_TOKEN`
  - [x] `TELEGRAM_CHAT_ID`
  - [x] `GOOGLE_SHEETS_CREDENTIALS`
  - [x] `SPREADSHEET_ID`
- [ ] **NUOVO**: Aggiungi `GEMINI_API_KEY`
  - Nome: `GEMINI_API_KEY`
  - Valore: [la tua API key da Google AI Studio](https://makersuite.google.com/app/apikey)
  
## 📦 Commit e Push
- [ ] Aggiungi tutti i file modificati:
  ```bash
  git add .
  git commit -m "feat: Add AI market news recap and promotional message
  
  - Added AI-powered market news generator using Google Gemini API
  - Added fixed promotional message explaining portfolio benefits
  - Updated workflow to include GEMINI_API_KEY
  - Added comprehensive documentation (GEMINI_SETUP.md, IMPLEMENTATION_SUMMARY.md)
  - Graceful fallback if API key not configured"
  ```
- [ ] Push su GitHub:
  ```bash
  git push origin main
  ```

## 🧪 Verifica Post-Deploy
- [ ] Vai su GitHub Actions
- [ ] Attendi il prossimo run schedulato OPPURE triggera manualmente:
  - Actions → Daily Portfolio Recap → Run workflow
- [ ] Verifica i logs:
  - ✅ Dovrebbe apparire: "🤖 Generating AI market news recap..."
  - ✅ Dovrebbe apparire: "✅ AI news recap generated successfully!"
  - Se API key non configurata: "⚠️ Warning: GEMINI_API_KEY not set"
- [ ] Controlla il messaggio Telegram:
  - ✅ Contiene le performance normali
  - ✅ Contiene il recap AI delle news (se API key configurata)
  - ✅ Contiene il messaggio fisso promozionale alla fine

## 📊 Monitoring
- [ ] Dopo il primo run con successo, controlla:
  - File `output/recap.txt` nel repository
  - Messaggio ricevuto su Telegram
  - Lunghezza del messaggio (dovrebbe essere ~1.5-2x più lungo di prima)

## 🔍 Troubleshooting

### Problema: API key non accettata
**Soluzione**: 
- Verifica di aver copiato correttamente la chiave (formato: `AIzaSy...`)
- Verifica che il secret si chiami esattamente `GEMINI_API_KEY`
- Prova a rigenerare la chiave su Google AI Studio

### Problema: Errore "quota exceeded"
**Soluzione**: 
- Controlla su [Google AI Studio](https://makersuite.google.com/) le tue quote
- Il free tier include 1500 richieste/giorno (più che sufficiente)
- Se necessario, attendi 24h per il reset

### Problema: Messaggio AI troppo lungo
**Soluzione**: 
- Il prompt è già ottimizzato per ~5-6 frasi
- Se necessario, modifica `src/ai_news_generator.py` linea 35 per ridurre

### Problema: Messaggio fisso non appare
**Soluzione**: 
- Questo non dovrebbe mai succedere (è hardcoded)
- Verifica che `src/formatter.py` includa la chiamata a `get_why_copy_message()`
- Controlla i logs per errori

## 💡 Tips
- **Test locale**: Usa un secret temporaneo per testare localmente prima del deploy
- **Personalizzazione**: Il messaggio fisso è in `src/ai_news_generator.py` (funzione `get_why_copy_message()`)
- **Prompt AI**: Puoi modificare il prompt in `src/ai_news_generator.py` per cambiare lo stile delle news
- **Disabilitare AI news**: Semplicemente non configurare `GEMINI_API_KEY`, il resto funzionerà ugualmente

---

## 🎯 Success Criteria
✅ Il workflow GitHub Actions completa senza errori
✅ Il messaggio Telegram include le 3 sezioni: performance + AI news + promotional
✅ Le news AI sono contestualizzate sui mercati USA/CHINA/EU
✅ Il messaggio fisso appare sempre alla fine

**Una volta completata questa checklist, sei pronto! 🚀**
