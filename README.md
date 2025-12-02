# Amazon Business Report Analyzer

Ein Tool zur Analyse von Amazon Business Reports für Detailseite Verkäufe und Traffic.

## Features

- 📊 Upload mehrerer CSV-Dateien für Zeitraumvergleiche
- 📈 Visualisierung der wichtigsten KPIs:
  - Bestellte Einheiten
  - Durch bestellte Produkte erzielter Umsatz
  - Seitenaufrufe
- 🔄 Toggle zwischen normalem Traffic und B2B Traffic
- 🔍 Filterung nach ASINs mit Mehrfachauswahl
- 📝 Automatische Zusammenfassung der Änderungen zwischen Zeiträumen

## Installation

```bash
pip install -r requirements.txt
```

## Verwendung

```bash
streamlit run app.py
```

## Datenformat

Das Tool erwartet CSV-Dateien im Amazon Business Report Format mit folgenden Spalten:
- (Übergeordnete) ASIN
- (Untergeordnete) ASIN
- Bestellte Einheiten / Bestellte Einheiten – B2B
- Durch bestellte Produkte erzielter Umsatz / Bestellsumme – B2B
- Seitenaufrufe – Summe / Seitenaufrufe – Summe – B2B

