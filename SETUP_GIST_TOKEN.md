# Come creare un GitHub Personal Access Token (PAT) per i Gist

Hai bisogno di un token con i permessi di scrittura ("scope") per i Gist per salvare la cronologia. Ecco come crearlo in 2 minuti:

## 1. Vai su GitHub
1. Accedi al tuo account GitHub.
2. Clicca sulla tua immagine del profilo in alto a destra > **Settings**.
3. Scorri in fondo alla colonna di sinistra e clicca su **Developer settings**.
4. Clicca su **Personal access tokens** > **Tokens (classic)**.
   > **Nota**: Puoi usare anche i "Fine-grained tokens", ma i "Classic" sono più semplici da configurare per questo scopo specifico.
5. Clicca su **Generate new token** > **Generate new token (classic)**.

## 2. Configura i permessi (Scope)
1. **Note**: Dai un nome al token, es: `Portfolio Recap Gist`.
2. **Expiration**: Imposta una scadenza (es. "No expiration" se lo usi solo in locale e al sicuro, oppure 90 giorni).
3. **Select scopes** (Molto importante!):
   - Scorri e cerca la casella **`gist`** (Create gists).
   - **Spunta la casella `gist`**. ✅
   - Non servono altri permessi (come `repo`) se devi solo salvare i Gist.

## 3. Genera e Copia
1. Scorri in fondo e clicca **Generate token**.
2. **Copia subito il token** (inizia con `ghp_...`). Non potrai più vederlo dopo aver chiuso la pagina!

## 4. Come usarlo nel progetto

### Opzione A: Temporaneo (solo per questa sessione terminale)
Esegui questo comando nel tuo terminale prima di lanciare lo script:
```bash
export GIST_ACCESS_TOKEN="incolla_qui_il_tuo_token_ghp_..."
```

### Opzione B: Permanente (consigliato per sviluppo locale)
Aggiungilo al tuo file `.bashrc` o `.zshrc`:
1. Apri il file: `nano ~/.bashrc`
2. Aggiungi alla fine: `export GIST_ACCESS_TOKEN="ghp_..."`
3. Salva (Ctrl+O, Enter) ed esci (Ctrl+X).
4. Ricarica: `source ~/.bashrc`

### Opzione C: Se usi GitHub Actions
Vai nelle impostazioni del repository del progetto (`Settings` > `Secrets and variables` > `Actions`) e crea un nuovo **Repository Secret** chiamato `GIST_ACCESS_TOKEN` (**Nota**: GitHub non accetta secret che iniziano con `GITHUB_`) con il valore del token.
