# 📱 Guida Setup Social Media — Portfolio Recap

> Ogni piattaforma è **opzionale** — se i secrets GitHub non sono configurati, il runner la salta senza errori.

---

## 📌 Secrets GitHub da aggiungere

`GitHub → repo → Settings → Secrets and variables → Actions → New repository secret`

| Secret | Piattaforma |
|---|---|
| `THREADS_ACCESS_TOKEN` | Threads |
| `THREADS_USER_ID` | Threads |
| `TWITTER_API_KEY` | Twitter/X |
| `TWITTER_API_SECRET` | Twitter/X |
| `TWITTER_ACCESS_TOKEN` | Twitter/X |
| `TWITTER_ACCESS_TOKEN_SECRET` | Twitter/X |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | Facebook |
| `FACEBOOK_PAGE_ID` | Facebook |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram |
| `INSTAGRAM_USER_ID` | Instagram |
| `IMGBB_API_KEY` | Instagram (image hosting) |

---

## 🟣 THREADS (10 minuti)

### Step 1: Crea una Meta App
1. [developers.facebook.com](https://developers.facebook.com) → **My Apps → Create App**
2. Tipo: **"Other"** → **"Business"**

### Step 2: Aggiungi il prodotto Threads
- App dashboard → **Add Product → Threads API → Set Up**

### Step 3: Ottieni il token
1. **Graph API Explorer** (`developers.facebook.com/tools/explorer/`)
2. User Token con permissions: `threads_basic`, `threads_content_publish`
3. Converti in long-lived token (60 giorni):
   ```
   GET https://graph.threads.net/access_token
     ?grant_type=th_exchange_token
     &client_id={APP_ID}&client_secret={APP_SECRET}
     &access_token={SHORT_TOKEN}
   ```
4. Trova il tuo User ID:
   ```
   GET https://graph.threads.net/v1.0/me?access_token={TOKEN}
   ```

```
THREADS_ACCESS_TOKEN = eyJ...
THREADS_USER_ID      = 1234567890
```

> ⚠️ Token scade dopo 60 giorni — da rinnovare manualmente.

---

## 🐦 TWITTER/X (15 minuti)

> Piano Free: **1 post/mese** in scrittura. Il codice lo gestisce automaticamente.

### Step 1: Crea app su Developer Portal
- [developer.twitter.com](https://developer.twitter.com) → **Projects & Apps → New App**

### Step 2: Chiavi API
1. App → **Keys and Tokens**
2. Copia **API Key** e **API Key Secret**
3. Sezione **Access Token and Secret** → **Generate**

### Step 3: Abilita write permissions
- App Settings → **User authentication settings → Edit**  
- App permissions: **Read and write** → Salva → **Rigenera** i token

```
TWITTER_API_KEY             = abc123...
TWITTER_API_SECRET          = xyz789...
TWITTER_ACCESS_TOKEN        = 1234567890-abc...
TWITTER_ACCESS_TOKEN_SECRET = def456...
```

---

## 📘 FACEBOOK (20 minuti)

> Prerequisito: devi avere una **Facebook Page** (non profilo personale).  
> Crea una page: [facebook.com/pages/create](https://www.facebook.com/pages/create)

### Step 1: Graph API Explorer
1. `developers.facebook.com/tools/explorer/`
2. User Token con: `pages_manage_posts`, `pages_read_engagement`

### Step 2: Ottieni il Page Token
```
GET https://graph.facebook.com/me/accounts?access_token={USER_TOKEN}
```
→ Restituisce la lista pages con `access_token` e `id` per ognuna.

```
FACEBOOK_PAGE_ACCESS_TOKEN = EAAx...  (token della Page)
FACEBOOK_PAGE_ID           = 1234567890
```

---

## 📸 INSTAGRAM (25 minuti)

### Prerequisiti
- Account Instagram **Business** o **Creator**  
  (Impostazioni → Account → Passa ad account professionale)
- Account collegato a una Facebook Page

### Step 1: Meta App + permessi
1. Graph API Explorer → User Token con:  
   `instagram_basic`, `instagram_content_publish`, `pages_show_list`

### Step 2: Trova Instagram User ID
```
GET https://graph.facebook.com/me/accounts?access_token={TOKEN}
GET https://graph.facebook.com/{PAGE_ID}?fields=instagram_business_account&access_token={TOKEN}
→ {"instagram_business_account": {"id": "9876543210"}}
```

### Step 3: imgbb API Key (upload immagini)
1. Registrati su [api.imgbb.com](https://api.imgbb.com/) (gratuito)
2. Copia la API Key dalla dashboard

```
INSTAGRAM_ACCESS_TOKEN = EAAx...
INSTAGRAM_USER_ID      = 9876543210
IMGBB_API_KEY          = abc123...
```

---

## 🔄 Come funziona in automatico

Una volta configurati i secrets, il runner pubblica su tutti i canali abilitati:

| Piattaforma | Contenuto |
|---|---|
| **Telegram** | Messaggio HTML completo + grafico |
| **Threads** | Testo plain (max 500 chars) |
| **Twitter/X** | Teaser 280 chars (1×/mese) |
| **Facebook** | Testo completo + grafico allegato |
| **Instagram** | Grafico + caption |

Il log del runner mostra:
```
✅ Telegram
✅ Threads
✅ Twitter/X
❌ Facebook  (errore API)
⏭️ Instagram  (non configurato)
```

> ⚠️ I token Meta (Threads/Instagram/Facebook) scadono ogni **60 giorni** — segna un promemoria per rinnovarli.
