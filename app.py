import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import re

# Seitenkonfiguration
st.set_page_config(
    page_title="Amazon Business Report Analyzer",
    page_icon="📊",
    layout="wide"
)

# Titel
st.title("📊 Amazon Business Report Analyzer")
st.markdown("Analysiere deine Amazon Business Reports für Detailseite Verkäufe und Traffic")

# Hilfsfunktionen
def parse_euro_value(value):
    """Konvertiert Euro-Strings (z.B. '368,14 €') zu Float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    # Entferne Leerzeichen und €, ersetze Komma durch Punkt
    value_str = str(value).replace(' ', '').replace('€', '').replace(',', '.')
    try:
        return float(value_str)
    except:
        return 0.0

def parse_percentage(value):
    """Konvertiert Prozent-Strings (z.B. '16.40%') zu Float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    value_str = str(value).replace('%', '').replace(',', '.')
    try:
        return float(value_str)
    except:
        return 0.0

def load_and_process_csv(uploaded_file, file_name):
    """Lädt und verarbeitet eine CSV-Datei"""
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        
        # Extrahiere Datum aus Dateinamen (z.B. BusinessReport-02.12.25.csv)
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{2})', file_name)
        if date_match:
            day, month, year = date_match.groups()
            year_full = f"20{year}" if int(year) < 50 else f"19{year}"
            date_str = f"{year_full}-{month}-{day}"
        else:
            date_str = file_name
        
        # Verarbeite numerische Spalten
        numeric_columns = [
            'Bestellte Einheiten',
            'Bestellte Einheiten – B2B',
            'Durch bestellte Produkte erzielter Umsatz',
            'Bestellsumme – B2B',
            'Seitenaufrufe – Summe',
            'Seitenaufrufe – Summe – B2B',
            'Sitzungen – Summe',
            'Sitzungen – Summe – B2B',
            'Zahl der Bestellposten',
            'Zahl der Bestellposten – B2B',
            'Sitzungen – mobile App',
            'Sitzungen – mobile App – B2B',
            'Sitzungen – Browser',
            'Sitzungen – Browser – B2B'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                if 'Umsatz' in col or 'Bestellsumme' in col:
                    df[col] = df[col].apply(parse_euro_value)
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df['Zeitraum'] = date_str
        df['Dateiname'] = file_name
        
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei {file_name}: {str(e)}")
        return None

def find_column(df, possible_names):
    """Findet eine Spalte anhand mehrerer möglicher Namen"""
    # Zuerst exakte Übereinstimmung versuchen
    for name in possible_names:
        if name in df.columns:
            return name
    
    # Falls keine exakte Übereinstimmung, suche nach ähnlichen Namen (normalisiert)
    # Normalisiere alle Spaltennamen und Suchbegriffe
    normalized_columns = {col.strip().replace('–', '-').replace('—', '-').replace(' ', '').lower(): col for col in df.columns}
    
    for name in possible_names:
        normalized_name = name.strip().replace('–', '-').replace('—', '-').replace(' ', '').lower()
        if normalized_name in normalized_columns:
            return normalized_columns[normalized_name]
    
    # Zusätzliche Suche: Teilstring-Matching
    for name in possible_names:
        name_keywords = name.lower().split()
        for col in df.columns:
            col_lower = col.lower()
            # Prüfe ob alle wichtigen Keywords in Spaltenname enthalten sind
            if all(keyword in col_lower for keyword in name_keywords if len(keyword) > 2):
                return col
    
    return None

def aggregate_data(df, traffic_type='normal'):
    """Aggregiert Daten über alle ASINs und berechnet zusätzliche KPIs"""
    if traffic_type == 'B2B':
        units_col = find_column(df, ['Bestellte Einheiten – B2B', 'Bestellte Einheiten - B2B'])
        revenue_col = find_column(df, ['Bestellsumme – B2B', 'Bestellsumme - B2B'])
        views_col = find_column(df, [
            'Seitenaufrufe – Summe – B2B',
            'Seitenaufrufe - Summe - B2B',
            'Sitzungen – Summe – B2B',
            'Sitzungen - Summe - B2B'
        ])
        sessions_col = find_column(df, ['Sitzungen – Summe – B2B', 'Sitzungen - Summe - B2B'])
        orders_col = find_column(df, ['Zahl der Bestellposten – B2B', 'Zahl der Bestellposten - B2B'])
        mobile_sessions_col = find_column(df, ['Sitzungen – mobile App – B2B', 'Sitzungen - mobile App - B2B'])
        browser_sessions_col = find_column(df, ['Sitzungen – Browser – B2B', 'Sitzungen - Browser - B2B'])
    else:
        units_col = find_column(df, ['Bestellte Einheiten'])
        revenue_col = find_column(df, ['Durch bestellte Produkte erzielter Umsatz'])
        # Die korrekte Spalte heißt "Seitenaufrufe – Summe"
        views_col = find_column(df, [
            'Seitenaufrufe – Summe',
            'Seitenaufrufe - Summe',
            'Sitzungen – Summe',
            'Sitzungen - Summe'
        ])
        sessions_col = find_column(df, ['Sitzungen – Summe', 'Sitzungen - Summe'])
        orders_col = find_column(df, ['Zahl der Bestellposten'])
        mobile_sessions_col = find_column(df, ['Sitzungen – mobile App', 'Sitzungen - mobile App'])
        browser_sessions_col = find_column(df, ['Sitzungen – Browser', 'Sitzungen - Browser'])
    
    # Prüfe ob alle benötigten Spalten vorhanden sind
    # WICHTIG: Prüfe ob Spalte wirklich im DataFrame existiert, nicht ob Werte 0 sind
    missing_cols = []
    
    # Für units_col - prüfe ob Spalte existiert, auch wenn find_column None zurückgab
    if units_col is None:
        expected_name = 'Bestellte Einheiten' + (' – B2B' if traffic_type == 'B2B' else '')
        # Prüfe ob Spalte trotzdem existiert (mit exaktem Namen)
        if expected_name in df.columns:
            units_col = expected_name
        else:
            # Spalte fehlt wirklich
            missing_cols.append(expected_name)
            df[expected_name] = 0
            units_col = expected_name
    
    # Für revenue_col
    if revenue_col is None:
        expected_name = 'Bestellsumme – B2B' if traffic_type == 'B2B' else 'Durch bestellte Produkte erzielter Umsatz'
        if expected_name in df.columns:
            revenue_col = expected_name
        else:
            missing_cols.append(expected_name)
            df[expected_name] = 0
            revenue_col = expected_name
    
    # Für views_col - erweiterte Suche
    if views_col is None:
        expected_name = 'Seitenaufrufe – Summe' + (' – B2B' if traffic_type == 'B2B' else '')
        # Prüfe ob Spalte trotzdem existiert (mit exaktem Namen)
        if expected_name in df.columns:
            views_col = expected_name
        else:
            # Suche nach Spalten die "Seitenaufrufe" oder "Sitzungen" und "Summe" enthalten
            search_keywords = ['seitenaufrufe', 'summe'] if traffic_type != 'B2B' else ['seitenaufrufe', 'summe', 'b2b']
            matching_cols = []
            for col in df.columns:
                col_lower = col.lower()
                if all(keyword in col_lower for keyword in search_keywords):
                    matching_cols.append(col)
            
            if matching_cols:
                # Nimm die erste passende Spalte
                views_col = matching_cols[0]
            else:
                missing_cols.append(expected_name)
                df[expected_name] = 0
                views_col = expected_name
    
    # Für sessions_col
    if sessions_col is None:
        expected_name = 'Sitzungen – Summe' + (' – B2B' if traffic_type == 'B2B' else '')
        if expected_name in df.columns:
            sessions_col = expected_name
        else:
            df[expected_name] = 0
            sessions_col = expected_name
    
    # Für orders_col
    if orders_col is None:
        expected_name = 'Zahl der Bestellposten' + (' – B2B' if traffic_type == 'B2B' else '')
        if expected_name in df.columns:
            orders_col = expected_name
        else:
            df[expected_name] = 0
            orders_col = expected_name
    
    # Für mobile_sessions_col
    if mobile_sessions_col is None:
        expected_name = 'Sitzungen – mobile App' + (' – B2B' if traffic_type == 'B2B' else '')
        if expected_name in df.columns:
            mobile_sessions_col = expected_name
        else:
            df[expected_name] = 0
            mobile_sessions_col = expected_name
    
    # Für browser_sessions_col
    if browser_sessions_col is None:
        expected_name = 'Sitzungen – Browser' + (' – B2B' if traffic_type == 'B2B' else '')
        if expected_name in df.columns:
            browser_sessions_col = expected_name
        else:
            df[expected_name] = 0
            browser_sessions_col = expected_name
    
    # DEBUG: Zeige welche Spalten gefunden wurden
    debug_info = []
    debug_info.append(f"**Gefundene Spalten für {traffic_type} Traffic:**")
    debug_info.append(f"- Bestellte Einheiten: {units_col if units_col else 'NICHT GEFUNDEN'}")
    debug_info.append(f"- Umsatz: {revenue_col if revenue_col else 'NICHT GEFUNDEN'}")
    debug_info.append(f"- Seitenaufrufe: {views_col if views_col else 'NICHT GEFUNDEN'}")
    
    # Prüfe ob Spalten wirklich im DataFrame existieren
    final_missing = []
    if units_col and units_col not in df.columns:
        final_missing.append(units_col)
    if revenue_col and revenue_col not in df.columns:
        final_missing.append(revenue_col)
    if views_col and views_col not in df.columns:
        final_missing.append(views_col)
    
    # Zeige Debug-Info in einem Expander
    with st.expander("🔍 Debug: Spaltensuche", expanded=False):
        st.markdown("\n".join(debug_info))
        if final_missing:
            st.error(f"⚠️ Diese Spalten wurden nicht im DataFrame gefunden: {', '.join(final_missing)}")
        else:
            st.success("✅ Alle benötigten Spalten wurden gefunden!")
    
    if final_missing:
        st.warning(f"⚠️ Folgende Spalten fehlen wirklich in den Daten: {', '.join(final_missing)}")
    
    aggregated = df.groupby('Zeitraum').agg({
        units_col: 'sum',
        revenue_col: 'sum',
        views_col: 'sum',
        sessions_col: 'sum',
        orders_col: 'sum',
        mobile_sessions_col: 'sum',
        browser_sessions_col: 'sum'
    }).reset_index()
    
    # Berechne zusätzliche KPIs (mit Division durch Null Schutz)
    aggregated['Conversion Rate (%)'] = (
        (aggregated[units_col] / aggregated[sessions_col].replace(0, np.nan) * 100)
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    aggregated['AOV (€)'] = (
        (aggregated[revenue_col] / aggregated[orders_col].replace(0, np.nan))
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    aggregated['Revenue per Session (€)'] = (
        (aggregated[revenue_col] / aggregated[sessions_col].replace(0, np.nan))
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    
    # Umbenennen der Spalten
    aggregated.columns = [
        'Zeitraum', 
        'Bestellte Einheiten', 
        'Umsatz', 
        'Seitenaufrufe',
        'Sitzungen',
        'Bestellungen',
        'Mobile Sitzungen',
        'Browser Sitzungen',
        'Conversion Rate (%)',
        'AOV (€)',
        'Revenue per Session (€)'
    ]
    
    return aggregated

def get_top_flop_asins(df, traffic_type='normal'):
    """Identifiziert Top- und Flop-ASINs basierend auf Umsatz"""
    if traffic_type == 'B2B':
        units_col = find_column(df, ['Bestellte Einheiten – B2B', 'Bestellte Einheiten - B2B'])
        revenue_col = find_column(df, ['Bestellsumme – B2B', 'Bestellsumme - B2B'])
        views_col = find_column(df, ['Seitenaufrufe – Summe – B2B', 'Seitenaufrufe - Summe - B2B'])
        sessions_col = find_column(df, ['Sitzungen – Summe – B2B', 'Sitzungen - Summe - B2B'])
        orders_col = find_column(df, ['Zahl der Bestellposten – B2B', 'Zahl der Bestellposten - B2B'])
    else:
        units_col = find_column(df, ['Bestellte Einheiten'])
        revenue_col = find_column(df, ['Durch bestellte Produkte erzielter Umsatz'])
        views_col = find_column(df, ['Seitenaufrufe – Summe', 'Seitenaufrufe - Summe'])
        sessions_col = find_column(df, ['Sitzungen – Summe', 'Sitzungen - Summe'])
        orders_col = find_column(df, ['Zahl der Bestellposten'])
    
    # Fallback falls Spalten nicht gefunden
    if not all([units_col, revenue_col, views_col, sessions_col, orders_col]):
        return None, None
    
    # Verwende untergeordnete ASINs
    asin_column = '(Untergeordnete) ASIN'
    if asin_column not in df.columns:
        asin_column = '(Übergeordnete) ASIN'
    
    if asin_column not in df.columns:
        return None, None
    
    # Aggregiere nach ASIN
    asin_data = df.groupby(asin_column).agg({
        units_col: 'sum',
        revenue_col: 'sum',
        views_col: 'sum',
        sessions_col: 'sum',
        orders_col: 'sum'
    }).reset_index()
    
    # Berechne KPIs
    asin_data['Conversion Rate (%)'] = (
        (asin_data[units_col] / asin_data[sessions_col].replace(0, np.nan) * 100)
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    asin_data['AOV (€)'] = (
        (asin_data[revenue_col] / asin_data[orders_col].replace(0, np.nan))
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    asin_data['Revenue per Session (€)'] = (
        (asin_data[revenue_col] / asin_data[sessions_col].replace(0, np.nan))
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    
    # Sortiere nach Umsatz (absteigend)
    asin_data = asin_data.sort_values(revenue_col, ascending=False)
    
    # Top ASIN (höchster Umsatz)
    top_asins = asin_data.head(1).copy()
    top_asins.columns = ['ASIN', 'Einheiten', 'Umsatz', 'Seitenaufrufe', 'Sitzungen', 'Bestellungen', 'Conversion Rate (%)', 'AOV (€)', 'Revenue per Session (€)']
    
    # Flop ASIN (niedrigster Umsatz, aber > 0)
    # Filtere ASINs mit Umsatz > 0 und sortiere aufsteigend
    asin_data_with_revenue = asin_data[asin_data[revenue_col] > 0].copy()
    if len(asin_data_with_revenue) > 1:
        # Sortiere aufsteigend für Flop
        asin_data_with_revenue = asin_data_with_revenue.sort_values(revenue_col, ascending=True)
        flop_asins = asin_data_with_revenue.head(1).copy()
        flop_asins.columns = ['ASIN', 'Einheiten', 'Umsatz', 'Seitenaufrufe', 'Sitzungen', 'Bestellungen', 'Conversion Rate (%)', 'AOV (€)', 'Revenue per Session (€)']
    elif len(asin_data_with_revenue) == 1:
        # Nur ein ASIN mit Umsatz - das ist dann sowohl Top als auch Flop
        flop_asins = None
    else:
        flop_asins = None
    
    return top_asins, flop_asins

def generate_summary(current_data, previous_data, traffic_type='normal'):
    """Generiert eine Zusammenfassung der Änderungen"""
    if previous_data is None or len(previous_data) == 0:
        return "Dies ist der erste Zeitraum. Keine Vergleichsdaten verfügbar."
    
    current = current_data.iloc[-1] if len(current_data) > 0 else None
    previous = previous_data.iloc[-1] if len(previous_data) > 0 else None
    
    if current is None or previous is None:
        return "Nicht genügend Daten für einen Vergleich verfügbar."
    
    current_period = current['Zeitraum']
    previous_period = previous['Zeitraum']
    
    summary_parts = [f"**Vergleich zwischen {previous_period} und {current_period}:**\n\n"]
    
    # Bestellte Einheiten
    units_change = current['Bestellte Einheiten'] - previous['Bestellte Einheiten']
    units_pct = ((current['Bestellte Einheiten'] / previous['Bestellte Einheiten'] - 1) * 100) if previous['Bestellte Einheiten'] > 0 else 0
    if units_change > 0:
        summary_parts.append(f"✅ Die bestellten Einheiten sind von {previous['Bestellte Einheiten']:.0f} auf {current['Bestellte Einheiten']:.0f} gestiegen (+{units_change:.0f} Einheiten, {units_pct:+.1f}%).")
    elif units_change < 0:
        summary_parts.append(f"❌ Die bestellten Einheiten sind von {previous['Bestellte Einheiten']:.0f} auf {current['Bestellte Einheiten']:.0f} gesunken ({units_change:.0f} Einheiten, {units_pct:+.1f}%).")
    else:
        summary_parts.append(f"➡️ Die bestellten Einheiten sind unverändert bei {current['Bestellte Einheiten']:.0f} Einheiten.")
    
    # Umsatz
    revenue_change = current['Umsatz'] - previous['Umsatz']
    revenue_pct = ((current['Umsatz'] / previous['Umsatz'] - 1) * 100) if previous['Umsatz'] > 0 else 0
    if revenue_change > 0:
        summary_parts.append(f"✅ Der Umsatz ist von {previous['Umsatz']:,.2f} € auf {current['Umsatz']:,.2f} € gestiegen (+{revenue_change:,.2f} €, {revenue_pct:+.1f}%).")
    elif revenue_change < 0:
        summary_parts.append(f"❌ Der Umsatz ist von {previous['Umsatz']:,.2f} € auf {current['Umsatz']:,.2f} € gesunken ({revenue_change:,.2f} €, {revenue_pct:+.1f}%).")
    else:
        summary_parts.append(f"➡️ Der Umsatz ist unverändert bei {current['Umsatz']:,.2f} €.")
    
    # Seitenaufrufe
    views_change = current['Seitenaufrufe'] - previous['Seitenaufrufe']
    views_pct = ((current['Seitenaufrufe'] / previous['Seitenaufrufe'] - 1) * 100) if previous['Seitenaufrufe'] > 0 else 0
    if views_change > 0:
        summary_parts.append(f"✅ Die Seitenaufrufe sind von {previous['Seitenaufrufe']:.0f} auf {current['Seitenaufrufe']:.0f} gestiegen (+{views_change:.0f}, {views_pct:+.1f}%).")
    elif views_change < 0:
        summary_parts.append(f"❌ Die Seitenaufrufe sind von {previous['Seitenaufrufe']:.0f} auf {current['Seitenaufrufe']:.0f} gesunken ({views_change:.0f}, {views_pct:+.1f}%).")
    else:
        summary_parts.append(f"➡️ Die Seitenaufrufe sind unverändert bei {current['Seitenaufrufe']:.0f}.")
    
    # Conversion Rate
    if 'Conversion Rate (%)' in current and 'Conversion Rate (%)' in previous:
        cr_change = current['Conversion Rate (%)'] - previous['Conversion Rate (%)']
        if cr_change > 0:
            summary_parts.append(f"✅ Die Conversion Rate ist von {previous['Conversion Rate (%)']:.2f}% auf {current['Conversion Rate (%)']:.2f}% gestiegen (+{cr_change:.2f} Prozentpunkte).")
        elif cr_change < 0:
            summary_parts.append(f"❌ Die Conversion Rate ist von {previous['Conversion Rate (%)']:.2f}% auf {current['Conversion Rate (%)']:.2f}% gesunken ({cr_change:.2f} Prozentpunkte).")
        else:
            summary_parts.append(f"➡️ Die Conversion Rate ist unverändert bei {current['Conversion Rate (%)']:.2f}%.")
    
    # AOV
    if 'AOV (€)' in current and 'AOV (€)' in previous:
        aov_change = current['AOV (€)'] - previous['AOV (€)']
        if aov_change > 0:
            summary_parts.append(f"✅ Der Average Order Value ist von {previous['AOV (€)']:.2f} € auf {current['AOV (€)']:.2f} € gestiegen (+{aov_change:.2f} €).")
        elif aov_change < 0:
            summary_parts.append(f"❌ Der Average Order Value ist von {previous['AOV (€)']:.2f} € auf {current['AOV (€)']:.2f} € gesunken ({aov_change:.2f} €).")
        else:
            summary_parts.append(f"➡️ Der Average Order Value ist unverändert bei {current['AOV (€)']:.2f} €.")
    
    # Revenue per Session
    if 'Revenue per Session (€)' in current and 'Revenue per Session (€)' in previous:
        rps_change = current['Revenue per Session (€)'] - previous['Revenue per Session (€)']
        if rps_change > 0:
            summary_parts.append(f"✅ Der Revenue per Session ist von {previous['Revenue per Session (€)']:.2f} € auf {current['Revenue per Session (€)']:.2f} € gestiegen (+{rps_change:.2f} €).")
        elif rps_change < 0:
            summary_parts.append(f"❌ Der Revenue per Session ist von {previous['Revenue per Session (€)']:.2f} € auf {current['Revenue per Session (€)']:.2f} € gesunken ({rps_change:.2f} €).")
        else:
            summary_parts.append(f"➡️ Der Revenue per Session ist unverändert bei {current['Revenue per Session (€)']:.2f} €.")
    
    return "\n\n".join(summary_parts)

# CSV-Upload
st.header("📁 Daten-Upload")
uploaded_files = st.file_uploader(
    "Lade eine oder mehrere CSV-Dateien hoch",
    type=['csv'],
    accept_multiple_files=True
)

if uploaded_files:
    # Lade und verarbeite alle Dateien
    all_dataframes = []
    for uploaded_file in uploaded_files:
        df = load_and_process_csv(uploaded_file, uploaded_file.name)
        if df is not None:
            all_dataframes.append(df)
    
    if all_dataframes:
        # Kombiniere alle DataFrames
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Sortiere nach Zeitraum
        combined_df = combined_df.sort_values('Zeitraum')
        
        st.success(f"✅ {len(all_dataframes)} Datei(en) erfolgreich geladen!")
        
        # Sidebar für Filter
        st.sidebar.header("🔍 Filter")
        
        # Traffic-Typ Auswahl
        traffic_type = st.sidebar.radio(
            "Traffic-Typ",
            ['Normal', 'B2B'],
            index=0
        )
        traffic_type_key = 'B2B' if traffic_type == 'B2B' else 'normal'
        
        # ASIN-Filter - verwende untergeordnete ASINs
        asin_column = '(Untergeordnete) ASIN'
        if asin_column not in combined_df.columns:
            # Fallback auf übergeordnete ASINs falls Spalte nicht existiert
            asin_column = '(Übergeordnete) ASIN'
        
        all_asins = combined_df[asin_column].unique().tolist()
        all_asins = [asin for asin in all_asins if pd.notna(asin) and str(asin).strip() != '']  # Entferne leere Werte
        all_asins.sort()
        
        selected_asins = st.sidebar.multiselect(
            "ASINs filtern (leer = alle)",
            all_asins,
            default=[]
        )
        
        # Filtere Daten nach ASINs
        if selected_asins:
            filtered_df = combined_df[combined_df[asin_column].isin(selected_asins)].copy()
        else:
            filtered_df = combined_df.copy()
        
        # Hauptbereich
        st.header("📈 KPI-Übersicht")
        
        # DEBUG: Zeige alle verfügbaren Spalten
        with st.expander("🔍 Debug: Verfügbare Spalten anzeigen", expanded=False):
            st.write("**Alle Spalten im DataFrame:**")
            st.write(list(filtered_df.columns))
            st.write(f"\n**Anzahl Spalten:** {len(filtered_df.columns)}")
            
            # Zeige relevante Spalten
            st.write("\n**Relevante Spalten für aktuellen Traffic-Typ:**")
            if traffic_type_key == 'B2B':
                st.write("- Gesucht: 'Bestellte Einheiten – B2B'")
                st.write("- Gesucht: 'Bestellsumme – B2B'")
                st.write("- Gesucht: 'Seitenaufrufe – Summe – B2B'")
            else:
                st.write("- Gesucht: 'Bestellte Einheiten'")
                st.write("- Gesucht: 'Durch bestellte Produkte erzielter Umsatz'")
                st.write("- Gesucht: 'Seitenaufrufe – Summe'")
            
            # Finde ähnliche Spalten
            st.write("\n**Ähnliche Spalten gefunden:**")
            all_cols = list(filtered_df.columns)
            search_terms = ['seitenaufrufe', 'sitzungen', 'summe', 'bestellte', 'einheiten', 'umsatz', 'b2b']
            for term in search_terms:
                matching = [col for col in all_cols if term.lower() in col.lower()]
                if matching:
                    st.write(f"- '{term}': {matching}")
        
        # Aggregiere Daten
        aggregated_data = aggregate_data(filtered_df, traffic_type_key)
        
        # Erstelle numerische Zeitraum-IDs für die X-Achse
        aggregated_data = aggregated_data.copy()
        aggregated_data['Zeitraum_Nr'] = range(1, len(aggregated_data) + 1)
        
        # Statistiken (ganz oben)
        st.header("📊 Statistiken")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        # Finde die tatsächlichen Spaltennamen (mit flexibler Suche)
        units_col_stat = find_column(filtered_df, ['Bestellte Einheiten' if traffic_type_key == 'normal' else 'Bestellte Einheiten – B2B', 'Bestellte Einheiten - B2B'])
        revenue_col_stat = find_column(filtered_df, ['Durch bestellte Produkte erzielter Umsatz' if traffic_type_key == 'normal' else 'Bestellsumme – B2B', 'Bestellsumme - B2B'])
        views_col_stat = find_column(filtered_df, [
            'Seitenaufrufe – Summe' if traffic_type_key == 'normal' else 'Seitenaufrufe – Summe – B2B',
            'Seitenaufrufe - Summe',
            'Sitzungen – Summe',
            'Sitzungen - Summe',
            'Seitenaufrufe – Summe – B2B',
            'Seitenaufrufe - Summe - B2B'
        ])
        
        # Fallback falls Spalten nicht gefunden werden
        if units_col_stat is None:
            units_col_stat = 'Bestellte Einheiten' if traffic_type_key == 'normal' else 'Bestellte Einheiten – B2B'
        if revenue_col_stat is None:
            revenue_col_stat = 'Durch bestellte Produkte erzielter Umsatz' if traffic_type_key == 'normal' else 'Bestellsumme – B2B'
        if views_col_stat is None:
            views_col_stat = 'Seitenaufrufe – Summe' if traffic_type_key == 'normal' else 'Seitenaufrufe – Summe – B2B'
        
        with col1:
            total_units = filtered_df[units_col_stat].sum() if units_col_stat in filtered_df.columns else 0
            st.metric("Gesamt bestellte Einheiten", f"{total_units:,.0f}")
        
        with col2:
            total_revenue = filtered_df[revenue_col_stat].sum() if revenue_col_stat in filtered_df.columns else 0
            st.metric("Gesamtumsatz", f"{total_revenue:,.2f} €")
        
        with col3:
            total_views = filtered_df[views_col_stat].sum() if views_col_stat in filtered_df.columns else 0
            st.metric("Gesamt Seitenaufrufe", f"{total_views:,.0f}")
        
        with col4:
            asin_col_metric = '(Untergeordnete) ASIN' if '(Untergeordnete) ASIN' in filtered_df.columns else '(Übergeordnete) ASIN'
            unique_asins = filtered_df[asin_col_metric].nunique() if asin_col_metric in filtered_df.columns else 0
            st.metric("Anzahl ASINs", f"{unique_asins}")
        
        with col5:
            # Durchschnittliche Conversion Rate
            avg_cr = aggregated_data['Conversion Rate (%)'].mean() if 'Conversion Rate (%)' in aggregated_data.columns else 0
            st.metric("Ø Conversion Rate", f"{avg_cr:.2f}%")
        
        with col6:
            # Durchschnittlicher AOV
            avg_aov = aggregated_data['AOV (€)'].mean() if 'AOV (€)' in aggregated_data.columns else 0
            st.metric("Ø AOV", f"{avg_aov:.2f} €")
        
        st.divider()
        
        # Erstelle Visualisierungen
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig_units = px.bar(
                aggregated_data,
                x='Zeitraum_Nr',
                y='Bestellte Einheiten',
                title=f'Bestellte Einheiten ({traffic_type})',
                labels={'Bestellte Einheiten': 'Anzahl', 'Zeitraum_Nr': 'Zeitraum'}
            )
            fig_units.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_units.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_units, use_container_width=True)
        
        with col2:
            fig_revenue = px.bar(
                aggregated_data,
                x='Zeitraum_Nr',
                y='Umsatz',
                title=f'Umsatz ({traffic_type})',
                labels={'Umsatz': 'Umsatz (€)', 'Zeitraum_Nr': 'Zeitraum'}
            )
            fig_revenue.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_revenue.update_xaxes(title_text='Zeitraum')
            fig_revenue.update_traces(marker_color='green')
            st.plotly_chart(fig_revenue, use_container_width=True)
        
        with col3:
            fig_views = px.bar(
                aggregated_data,
                x='Zeitraum_Nr',
                y='Seitenaufrufe',
                title=f'Seitenaufrufe ({traffic_type})',
                labels={'Seitenaufrufe': 'Anzahl', 'Zeitraum_Nr': 'Zeitraum'}
            )
            fig_views.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_views.update_xaxes(title_text='Zeitraum')
            fig_views.update_traces(marker_color='blue')
            st.plotly_chart(fig_views, use_container_width=True)
        
        # Kombinierte Visualisierung
        st.subheader("📊 Kombinierte KPI-Übersicht")
        
        fig_combined = make_subplots(
            rows=1, cols=3,
            subplot_titles=('Bestellte Einheiten', 'Umsatz (€)', 'Seitenaufrufe'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
        )
        
        fig_combined.add_trace(
            go.Bar(x=aggregated_data['Zeitraum_Nr'], y=aggregated_data['Bestellte Einheiten'], name='Einheiten'),
            row=1, col=1
        )
        
        fig_combined.add_trace(
            go.Bar(x=aggregated_data['Zeitraum_Nr'], y=aggregated_data['Umsatz'], name='Umsatz', marker_color='green'),
            row=1, col=2
        )
        
        fig_combined.add_trace(
            go.Bar(x=aggregated_data['Zeitraum_Nr'], y=aggregated_data['Seitenaufrufe'], name='Seitenaufrufe', marker_color='blue'),
            row=1, col=3
        )
        
        fig_combined.update_layout(height=400, showlegend=False)
        fig_combined.update_xaxes(title_text='Zeitraum', tickmode='linear', tick0=1, dtick=1)
        st.plotly_chart(fig_combined, use_container_width=True)
        
        # Neue KPIs
        st.subheader("📊 Zusätzliche KPIs")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig_cr = px.line(
                aggregated_data,
                x='Zeitraum_Nr',
                y='Conversion Rate (%)',
                title=f'Conversion Rate ({traffic_type})',
                labels={'Conversion Rate (%)': 'Conversion Rate (%)', 'Zeitraum_Nr': 'Zeitraum'},
                markers=True
            )
            fig_cr.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_cr.update_xaxes(title_text='Zeitraum')
            fig_cr.update_traces(line_color='purple', marker_color='purple')
            st.plotly_chart(fig_cr, use_container_width=True)
        
        with col2:
            fig_aov = px.bar(
                aggregated_data,
                x='Zeitraum_Nr',
                y='AOV (€)',
                title=f'Average Order Value ({traffic_type})',
                labels={'AOV (€)': 'AOV (€)', 'Zeitraum_Nr': 'Zeitraum'}
            )
            fig_aov.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_aov.update_xaxes(title_text='Zeitraum')
            fig_aov.update_traces(marker_color='orange')
            st.plotly_chart(fig_aov, use_container_width=True)
        
        with col3:
            fig_rps = px.bar(
                aggregated_data,
                x='Zeitraum_Nr',
                y='Revenue per Session (€)',
                title=f'Revenue per Session ({traffic_type})',
                labels={'Revenue per Session (€)': 'Revenue/Session (€)', 'Zeitraum_Nr': 'Zeitraum'}
            )
            fig_rps.update_layout(height=300, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_rps.update_xaxes(title_text='Zeitraum')
            fig_rps.update_traces(marker_color='teal')
            st.plotly_chart(fig_rps, use_container_width=True)
        
        # Mobile vs Browser Performance
        st.subheader("📱 Mobile vs Browser Performance")
        
        # Bereite Daten für Mobile vs Browser vor
        mobile_browser_data = aggregated_data[['Zeitraum_Nr', 'Mobile Sitzungen', 'Browser Sitzungen']].copy()
        mobile_browser_data = mobile_browser_data.melt(
            id_vars='Zeitraum_Nr',
            value_vars=['Mobile Sitzungen', 'Browser Sitzungen'],
            var_name='Gerät',
            value_name='Sitzungen'
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_mobile_browser = px.bar(
                mobile_browser_data,
                x='Zeitraum_Nr',
                y='Sitzungen',
                color='Gerät',
                title=f'Mobile vs Browser Sitzungen ({traffic_type})',
                labels={'Sitzungen': 'Anzahl Sitzungen', 'Zeitraum_Nr': 'Zeitraum'},
                color_discrete_map={'Mobile Sitzungen': '#1f77b4', 'Browser Sitzungen': '#ff7f0e'}
            )
            fig_mobile_browser.update_layout(height=350, xaxis=dict(tickmode='linear', tick0=1, dtick=1))
            fig_mobile_browser.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_mobile_browser, use_container_width=True)
        
        with col2:
            # Berechne Mobile vs Browser Anteil
            mobile_browser_pct = aggregated_data.copy()
            total_sessions = mobile_browser_pct['Mobile Sitzungen'] + mobile_browser_pct['Browser Sitzungen']
            mobile_browser_pct['Mobile %'] = (mobile_browser_pct['Mobile Sitzungen'] / total_sessions * 100).fillna(0)
            mobile_browser_pct['Browser %'] = (mobile_browser_pct['Browser Sitzungen'] / total_sessions * 100).fillna(0)
            
            mobile_browser_pct_data = mobile_browser_pct[['Zeitraum_Nr', 'Mobile %', 'Browser %']].melt(
                id_vars='Zeitraum_Nr',
                value_vars=['Mobile %', 'Browser %'],
                var_name='Gerät',
                value_name='Anteil (%)'
            )
            
            fig_mobile_browser_pct = px.bar(
                mobile_browser_pct_data,
                x='Zeitraum_Nr',
                y='Anteil (%)',
                color='Gerät',
                title=f'Mobile vs Browser Anteil ({traffic_type})',
                labels={'Anteil (%)': 'Anteil (%)', 'Zeitraum_Nr': 'Zeitraum'},
                color_discrete_map={'Mobile %': '#1f77b4', 'Browser %': '#ff7f0e'}
            )
            fig_mobile_browser_pct.update_layout(height=350, xaxis=dict(tickmode='linear', tick0=1, dtick=1), barmode='stack')
            fig_mobile_browser_pct.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_mobile_browser_pct, use_container_width=True)
        
        # Zusammenfassung
        st.header("📝 Zusammenfassung")
        
        if len(aggregated_data) > 1:
            # Vergleiche aktuellsten mit vorherigem Zeitraum
            current_data = aggregated_data.tail(1)
            previous_data = aggregated_data.head(len(aggregated_data) - 1)
            summary = generate_summary(current_data, previous_data, traffic_type_key)
        else:
            summary = "Nur ein Zeitraum verfügbar. Lade weitere Dateien hoch, um Vergleiche zu sehen."
        
        st.markdown(summary)
        
        # Top- und Flop-ASINs
        st.subheader("🏆 Top- und Flop-ASINs")
        
        # Verwende den aktuellsten Zeitraum für Top/Flop Analyse
        latest_period = aggregated_data['Zeitraum'].iloc[-1] if len(aggregated_data) > 0 else None
        if latest_period:
            latest_df = filtered_df[filtered_df['Zeitraum'] == latest_period].copy()
        else:
            latest_df = filtered_df.copy()
        
        top_asins, flop_asins = get_top_flop_asins(latest_df, traffic_type_key)
        
        if top_asins is not None and len(top_asins) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🟢 Top ASIN (nach Umsatz)")
                row = top_asins.iloc[0]
                with st.container():
                    st.markdown(f"**{row['ASIN']}**")
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Umsatz", f"{row['Umsatz']:,.2f} €")
                        st.metric("Einheiten", f"{row['Einheiten']:.0f}")
                    with col_b:
                        st.metric("Conversion Rate", f"{row['Conversion Rate (%)']:.2f}%")
                        st.metric("AOV", f"{row['AOV (€)']:.2f} €")
                    st.caption(f"Revenue/Session: {row['Revenue per Session (€)']:.2f} € | Sitzungen: {row['Sitzungen']:.0f} | Seitenaufrufe: {row['Seitenaufrufe']:.0f}")
            
            with col2:
                if flop_asins is not None and len(flop_asins) > 0:
                    st.markdown("### 🔴 Flop ASIN (nach Umsatz)")
                    row = flop_asins.iloc[0]
                    with st.container():
                        st.markdown(f"**{row['ASIN']}**")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Umsatz", f"{row['Umsatz']:,.2f} €")
                            st.metric("Einheiten", f"{row['Einheiten']:.0f}")
                        with col_b:
                            st.metric("Conversion Rate", f"{row['Conversion Rate (%)']:.2f}%")
                            st.metric("AOV", f"{row['AOV (€)']:.2f} €")
                        st.caption(f"Revenue/Session: {row['Revenue per Session (€)']:.2f} € | Sitzungen: {row['Sitzungen']:.0f} | Seitenaufrufe: {row['Seitenaufrufe']:.0f}")
                else:
                    st.markdown("### 🔴 Flop ASIN")
                    st.info("Keine Flop-ASIN verfügbar (nur ein ASIN mit Umsatz vorhanden oder alle ASINs haben keinen Umsatz).")
        else:
            st.info("Top- und Flop-ASINs konnten nicht berechnet werden. Bitte überprüfe die Daten.")
        
        # Detaillierte Tabelle
        st.header("📋 Detaillierte Daten")
        
        # Finde die tatsächlichen Spaltennamen für die Anzeige
        units_col_display = find_column(filtered_df, ['Bestellte Einheiten' if traffic_type_key == 'normal' else 'Bestellte Einheiten – B2B'])
        revenue_col_display = find_column(filtered_df, ['Durch bestellte Produkte erzielter Umsatz' if traffic_type_key == 'normal' else 'Bestellsumme – B2B'])
        views_col_display = find_column(filtered_df, [
            'Seitenaufrufe – Summe' if traffic_type_key == 'normal' else 'Seitenaufrufe – Summe – B2B',
            'Sitzungen – Summe',
            'Sitzungen - Summe'
        ])
        
        display_columns = [
            'Zeitraum',
            '(Übergeordnete) ASIN',
            '(Untergeordnete) ASIN',
            'Titel'
        ]
        
        # Füge dynamisch gefundene Spalten hinzu
        if units_col_display:
            display_columns.append(units_col_display)
        if revenue_col_display:
            display_columns.append(revenue_col_display)
        if views_col_display:
            display_columns.append(views_col_display)
        
        available_columns = [col for col in display_columns if col in filtered_df.columns]
        st.dataframe(
            filtered_df[available_columns],
            use_container_width=True,
            height=400
        )
    else:
        st.error("Keine Daten konnten geladen werden. Bitte überprüfe die CSV-Dateien.")
else:
    st.info("👆 Bitte lade eine oder mehrere CSV-Dateien hoch, um zu beginnen.")

