#!/usr/bin/env python3
"""
Niche Stock Focus Generator & Visual Suite
==========================================
Generates 10 high-impact Single Stock Focus posts (text + Hitachi-style infographics)
for the 10 portfolio assets that the default algorithm rarely highlights:
  1. $ENEL.MI - Enel S.p.A. (Clean Electrification & Smart Grids)
  2. $GLEN.L  - Glencore PLC (Transition Metals & Commodity Trading)
  3. $ULVR.L  - Unilever PLC (Defensive Consumer Staples & Brand Moat)
  4. $PRY.MI  - Prysmian S.p.A. (Cabling Systems & Energy Grid Infrastructure)
  5. $1919.HK - COSCO SHIPPING Holdings (Maritime Global Supply Chain & Cash Flow)
  6. $2318.HK - Ping An Insurance Group (Finance, Insurtech & Asian Healthcare)
  7. $TRIG.L  - The Renewables Infrastructure Group (Clean Energy Yield)
  8. $HUM     - Humana Inc (Senior Healthcare & Medicare Advantage)
  9. $AZN.L   - AstraZeneca PLC (Biopharma & Oncology Powerhouse)
  10. $ABT.US - Abbott Laboratories (Diversified Medical Devices & Dividend Aristocrat)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

# Load .env if present
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

import stock_focus_infographic

NICHE_POSTS = {
    "ENEL.MI": {
        "ticker": "ENEL.MI",
        "company": "Enel S.p.A.",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Enel S.p.A. ($ENEL.MI)

Nel mio portafoglio Enel rappresenta attualmente l'1.24% dell'allocazione complessiva. È una holding core per combinare un generoso rendimento da dividendo con la transizione verso l'elettrificazione sostenibile e le reti intelligenti in Europa e America Latina.

🚀 POSSIBILI UPSIDE:
• Monopolio Naturale delle Reti: La divisione Grids genera flussi di cassa regolati, stabili e protetti dall'inflazione.
• Crescita Eolico & Solare: Oltre 60 GW di capacità rinnovabile con investimenti mirati a massimizzare il rendimento del capitale rispetto a competitor come $IBE.MC e $RWE.DE.
• Ritorno di Capitale Solido: Politica di dividendi in costante crescita con un dividend yield superiore al 6.5%.

⚠️ POSSIBILI DOWNSIDE:
• Sensibilità ai Tassi d'Interesse: Il debito netto, pur in riduzione, rende il titolo sensibile alle oscillazioni dei rendimenti obbligazionari.
• Rischio Regolatorio: Interventi governativi o cap sui prezzi energetici nei mercati chiave europei ed extra-UE.

La combinazione tra leadership verde, reti smart e dividendi sostenibili rende $ENEL.MI ($ENLAY) un asset difensivo fondamentale per la crescita a lungo termine.

👇 Cosa ne pensate del posizionamento di Enel rispetto a $EDP.LS?"""
    },

    "GLEN.L": {
        "ticker": "GLEN.L",
        "company": "Glencore PLC",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Glencore PLC ($GLEN.L)

Glencore pesa attualmente l'1.12% nel mio portafoglio. È la nostra esposizione strategica ai metalli critici indispensabili per l'elettrificazione globale, l'intelligenza artificiale e la transizione energetica.

🚀 POSSIBILI UPSIDE:
• Dominio nel Rame e Metalli di Transizione: Risorse minerarie Tier-1 di rame, cobalto e nichel, la cui domanda globale supera strutturalmente l'offerta.
• Divisione Marketing & Trading Unica: A differenza di giganti puramente estrattivi come $RIO.L e $BHP.L, Glencore sfrutta la volatilità globale dei prezzi per generare miliardi di cassa operativa aggiuntiva in ogni scenario di mercato.
• Remunerazione Azionisti Generosa: Elevato free cash flow convertito in dividendi ciclicamente ricchi e buyback.

⚠️ POSSIBILI DOWNSIDE:
• Ciclicità delle Materie Prime: Un rallentamento marcato della produzione industriale cinese può deprimere i prezzi spot dei metalli.
• Rischio Geopolitico e Minerario: Asset estrattivi localizzati in giurisdizioni emergenti con complessità operative superiori rispetto ad $AAL.L.

Punto su $GLEN.L per capitalizzare sul deficit secolare di rame fisico che alimenterà la nuova rete elettrica mondiale.

👇 Credete che il rame supererà i massimi storici nei prossimi trimestri?"""
    },

    "ULVR.L": {
        "ticker": "ULVR.L",
        "company": "Unilever PLC",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Unilever PLC ($ULVR.L)

Unilever ha un peso certificato del 2.38% nel mio portafoglio. Rappresenta la nostra roccia difensiva e macchina da flusso di cassa nel settore dei beni di largo consumo (Consumer Staples).

🚀 POSSIBILI UPSIDE:
• Moat dei Marchi Iconici: Oltre 30 'Power Brands' (Dove, Knorr, Rexona, Hellmann's) utilizzati quotidianamente da oltre 3.4 miliardi di persone in tutto il mondo.
• Leadership nei Mercati Emergenti: Circa il 60% dei ricavi proviene da economie emergenti in forte espansione demografica.
• Pricing Power e Margini in Espansione: Capacità comprovata di ribaltare l'inflazione sui prezzi finali senza perdere volumi rispetto a rivali globali.
• Cedola Sicura: Dividend yield vicino al 4% con decenni di pagamenti ininterrotti.

⚠️ POSSIBILI DOWNSIDE:
• Pressione dei Private Label: Nei periodi di inflazione prolungata i consumatori occidentali possono orientarsi verso marchi commerciali discount.
• Oscillazioni Valutarie: L'ampia presenza in valute emergenti può erodere parte della crescita convertita in sterline ed euro.

$ULVR.L ($UL) è il classico asset a basso beta che protegge il capitale e genera cassa in qualsiasi fase macroeconomica.

👇 Qual è il vostro brand preferito del gruppo Unilever?"""
    },

    "PRY.MI": {
        "ticker": "PRY.MI",
        "company": "Prysmian S.p.A.",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Prysmian S.p.A. ($PRY.MI)

Prysmian rappresenta attualmente il 3.86% del mio portafoglio. È il leader mondiale indiscusso nei sistemi in cavo per l'energia, le interconnessioni sottomarine dei parchi eolici e la fibra ottica per le telecomunicazioni e i data center.

🚀 POSSIBILI UPSIDE:
• Monopolio dei Grandi Collegamenti Elettrici: Fornitore insostituibile per i progetti HVDC (alta tensione sottomarina) con un portafoglio ordini record superiore a 18 miliardi di euro.
• Megatrend Reti & AI Data Center: La modernizzazione delle reti elettriche mondiali e la connettività dei data center richiedono decenni di fornitura continua.
• Espansione USA (Encore Wire): Presenza rafforzata nel mercato nordamericano con forti sinergie commerciali rispetto a rivali come $NEX.PA e $NKT.CO.
• Margini Operativi in Forte Crescita: L'alto valore aggiunto delle soluzioni chiavi in mano continua ad espandere l'EBITDA.

⚠️ POSSIBILI DOWNSIDE:
• Costi e Reperibilità Materie Prime: Fluttuazioni nei prezzi di rame e alluminio, sebbene ampiamente coperte da contratti di hedging.
• Complessità di Esecuzione Navi Posacavi: Ritardi meteorologici o incidenti nell'installazione sottomarina complessa.

Punto su $PRY.MI ($PRY) come pilastro industriale insostituibile: non esiste transizione energetica né intelligenza artificiale senza cavi che trasportano potenza e dati.

👇 Quanto ritenete cruciale l'infrastruttura di rete per sostenere il boom dell'AI?"""
    },

    "1919.HK": {
        "ticker": "1919.HK",
        "company": "COSCO SHIPPING Holdings",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio COSCO SHIPPING Holdings ($1919.HK)

COSCO SHIPPING rappresenta il 2.12% del mio portafoglio. È la spina dorsale logistica del commercio marittimo globale, posizionata come 3° vettore container al mondo per capacità e leader nei terminal portuali.

🚀 POSSIBILI UPSIDE:
• Integrazione Rotte e Porti: La sinergia tra la flotta di oltre 3.1 milioni di TEU e la rete di terminal COSCO Ports garantisce priorità di attracco ed efficienza operativa superiore a rivali come $ZIM e $MATX.
• Fortezza di Cassa e Cedole Straordinarie: Riserve di liquidità nette accumulate negli ultimi anni che supportano dividend yield superiori all'8% e buyback.
• Nuova Flotta a Basse Emissioni: Investimenti massicci in navi alimentate a metanolo e GNL per rispettare le stringenti normative marittime internazionali.

⚠️ POSSIBILI DOWNSIDE:
• Volatilità dei Noli Container: I tassi spot di trasporto marittimo possono subire forti oscillazioni in base alla riapertura delle rotte e all'offerta di naviglio.
• Rischi Geopolitici: Tensioni su canali marittimi strategici (Mar Rosso, Stretto di Malacca) e guerre commerciali con dazi.

$1919.HK ($CICOY) offre un flusso di cassa e dividendi formidabili per catturare la ripresa degli scambi Asia-Europa.

👇 Come vedete l'evoluzione dei noli marittimi nei prossimi mesi?"""
    },

    "2318.HK": {
        "ticker": "2318.HK",
        "company": "Ping An Insurance Group",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Ping An Insurance ($2318.HK)

Ping An pesa l'1.06% nel mio portafoglio. Rappresenta la nostra esposizione ad alto valore nel settore assicurativo, bancario e fintech integrato in Asia.

🚀 POSSIBILI UPSIDE:
• Ecosistema 'Finance + Healthcare': Oltre 235 milioni di clienti retail che utilizzano polizze vita, sanità privata e telemedicina proprietaria su un'unica piattaforma.
• Pioniere nell'Insurtech e AI: Algoritmi avanzati proprietari per l'underwriting e la liquidazione immediata dei sinistri che abbattono le spese di gestione rispetto a compagnie tradizionali come $2628.HK e $939.HK.
• Valutazioni a Sconto Storico: Multipli compressi con un dividend yield superiore al 6.5% e ampio margine di rivalutazione del capitale (re-rating).

⚠️ POSSIBILI DOWNSIDE:
• Esposizione al Settore Immobiliare Cinese: Gli investimenti nel portafoglio generale risentono dei cicli di ristrutturazione del real estate domestico.
• Regolamentazione Finanziaria: Requisiti patrimoniali e controlli governativi stringenti sui prodotti previdenziali e d'investimento.

Punto su $2318.HK ($PNGAY) per beneficiare della crescita inarrestabile della classe media asiatica e della richiesta di welfare privato.

👇 Riuscirà Ping An a recuperare i massimi storici con la spinta dell'insurtech?"""
    },

    "TRIG.L": {
        "ticker": "TRIG.L",
        "company": "The Renewables Infrastructure Group",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio The Renewables Infrastructure Group ($TRIG.L)

TRIG pesa l'1.96% nel mio portafoglio. È un fondo infrastrutturale quotato a Londra con oltre 85 impianti di energia pulita (eolico onshore/offshore, parchi solari e batterie) distribuiti tra UK, Francia, Germania e Spagna.

🚀 POSSIBILI UPSIDE:
• Rendimento da Dividendo Indicizzato: Dividend yield superiore al 7.5% distribuito trimestralmente, supportato da contratti energetici a lungo termine e incentivi statali legati all'inflazione.
• Diversificazione Tecnologica e Geografica: Il mix bilanciato tra eolico e solare mitiga la variabilità meteorologica rispetto a fondi monosettoriali come $UKW.L e $FSFL.L.
• Espansione nello Storage a Batteria: Sistemi di accumulo proprietari per catturare i picchi di prezzo dell'elettricità nelle ore di maggior domanda.

⚠️ POSSIBILI DOWNSIDE:
• Tassi d'Interesse Alti: Multipli di valutazione dei trust infrastrutturali penalizzati dal costo del capitale obbligazionario.
• Prezzi dell'Energia all'Ingrosso: Eventuali cali prolungati dei prezzi dell'elettricità spot sul mercato non coperto da contratti PPA.

$TRIG.L è una fonte eccellente di rendimento cedolare reale 100% decorrelato dai cicli tech tradizionali.

👇 Preferite l'eolico o il solare per generare dividendi puliti?"""
    },

    "HUM": {
        "ticker": "HUM",
        "company": "Humana Inc",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Humana Inc ($HUM)

Nel mio portafoglio Humana rappresenta il 3.09% del capitale. È uno dei leader indiscussi negli Stati Uniti nei piani sanitari Medicare Advantage dedicati alla popolazione senior.

🚀 POSSIBILI UPSIDE:
• Megatrend Demografico Inarrestabile: Oltre 10.000 persone compiono 65 anni ogni giorno negli USA, allargando costantemente la base di iscritti ai programmi Medicare.
• Rete Clinica Integrata CenterWell: Più di 300 centri medici primari proprietari che migliorano la prevenzione e riducono i ricoveri ospedalieri costosi, con margini superiori rispetto a concorrenti come $CVS e $CI.
• Potenziale di Ribilanciamento Margini: Aggiustamento programmato dei premi tariffari e aumento delle valutazioni 'Star Rating' per rilanciare la marginalità operativa.

⚠️ POSSIBILI DOWNSIDE:
• Aumento dei Costi di Utilizzo Medico (MLR): Maggiore frequenza di interventi chirurgici e cure post-operatorie tra gli anziani che comprime temporaneamente gli utili.
• Incertezza Politica e Rimborsi Federali: Cambiamenti nelle tariffe di rimborso stabilite dai Centers for Medicare & Medicaid Services (CMS).

Considero $HUM e $UNH asset secolari indispensabili per cavalcare la spesa sanitaria dell'invecchiamento demografico.

👇 Come valutate il potenziale di recupero del settore managed care USA?"""
    },

    "AZN.L": {
        "ticker": "AZN.L",
        "company": "AstraZeneca PLC",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio AstraZeneca PLC ($AZN.L)

AstraZeneca ha un peso del 2.21% nel mio portafoglio. È la seconda major farmaceutica europea per capitalizzazione, dotata di una delle pipeline di ricerca oncologica e biotecnologica più promettenti al mondo.

🚀 POSSIBILI UPSIDE:
• Leadership Globale in Oncologia: Farmaci blockbuster salva-vita (Tagrisso, Imfinzi, Enhertu) che crescono a doppia cifra e continuano ad ottenere estensioni di indicazione terapeutica.
• Espansione nelle Malattie Rare (Alexion): Terapie innovative ad altissimo margine con brevetti blindati e assenza di concorrenza generica.
• Presenza Strategica in Asia: La più grande casa farmaceutica occidentale per fatturato in Cina e nei mercati emergenti.
• Target $80B al 2030: Piano industriale ambizioso per lanciare 20 nuovi farmaci trasformativi entro la fine del decennio.

⚠️ POSSIBILI DOWNSIDE:
• Rischi di Fallimento nei Trial Clinici: Studi di Fase 3 che possono non raggiungere gli endpoint primari prefissati.
• Pressione sui Prezzi dei Farmaci: Riforme negoziali sui prezzi dei medicinali negli USA (Inflation Reduction Act) ed Europa.

Punto su $AZN.L ($AZN) accanto a $LLY e $NOVO-B.CO per costruire un pilastro farmaceutico guidato dalla pura innovazione scientifica.

👇 Quale area terapeutica considerereste più redditizia nel prossimo decennio?"""
    },

    "ABT.US": {
        "ticker": "ABT.US",
        "company": "Abbott Laboratories",
        "text": """🔍 FOCUS ASSET: Perché ho in portafoglio Abbott Laboratories ($ABT.US)

Abbott Laboratories rappresenta il 2.46% del mio portafoglio. È la quintessenza dell'azienda healthcare 'all-weather', forte del titolo di Dividend Aristocrat con oltre 52 anni consecutivi di aumenti della cedola.

🚀 POSSIBILI UPSIDE:
• Monopolio dei Sensori Diabete (CGM): FreeStyle Libre genera oltre 6 miliardi di dollari di vendite annue ed è il dispositivo medico più adottato a livello globale.
• Modello di Business a Quattro Pilastri: Dispositivi cardiovascolari d'avanguardia (TriClip, MitraClip), diagnostica rapida, nutrizione clinica e farmaci consolidati.
• Innovazione Medica Continua: Crescita a doppia cifra nel segmento cardio e neuromodulazione che supera competitor come $MDT e $BSX.
• Solidità Finanziaria Imbattibile: Rating creditizio solido, flusso di cassa costante e crescita ininterrotta del dividendo.

⚠️ POSSIBILI DOWNSIDE:
• Contenziosi Legali sul Latte Neonatale: Cause legali relative a prodotti nutrizionali specialistici per prematuri che possono comportare accantonamenti.
• Normalizzazione Diagnostica Post-Pandemica: Rientro definitivo dei volumi dei test rapidi rispetto ai picchi straordinari degli scorsi anni.

$ABT.US ($ABT) è un pilastro di stabilità patrimoniale, innovazione nei dispositivi medici e crescita composta nel tempo.

👇 Usate o conoscete il sensore FreeStyle Libre per il monitoraggio del glucosio?"""
    }
}


def run():
    os.makedirs("output", exist_ok=True)
    print("=" * 65)
    print("🚀 GENERATING 10 CLEAN NON-RUSSIAN NICHE STOCK FOCUS SUITES")
    print("=" * 65)

    summary = []
    for ticker, info in NICHE_POSTS.items():
        # 1. Save Text Post
        text_filename = f"output/stock_focus_{ticker}.txt"
        with open(text_filename, "w", encoding="utf-8") as f:
            f.write(info["text"])
        char_len = len(info["text"])

        # 2. Generate Infographic Card
        png_filename = f"output/stock_focus_{ticker}.png"
        stock_focus_infographic.generate_stock_infographic(ticker, output_path=png_filename)

        img_exists = os.path.exists(png_filename) and os.path.getsize(png_filename) > 1000
        summary.append({
            "ticker": ticker,
            "company": info["company"],
            "text_file": text_filename,
            "char_count": char_len,
            "img_file": png_filename,
            "img_ok": img_exists,
        })
        print(f"✅ [{ticker}] Post ({char_len} chars) & Card generated -> {png_filename}")

    print("\n" + "=" * 65)
    print(f"🎉 COMPLETED: {len(summary)} Niche Single Stock Focus suites generated!")
    print("=" * 65)
    return summary


if __name__ == "__main__":
    run()
