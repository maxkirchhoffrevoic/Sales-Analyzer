import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
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
st.markdown("""
**So bereitet ihr euren Business Report für den Upload vor:**

1. Navigiert zu **Berichte > Statistiken & Berichte** in eurem Amazon Seller Central
2. Wählt auf der linken Seite den Bericht **Verkäufe und Traffic** unter **"Nach Datum"** aus
3. Setzt in den Filtern folgende Einstellungen:
   - **Anzeigen:** Nach Tag
   - **Zeitraum:** Euren benutzerdefinierten Zeitraum
   - **Dashboard Aufrufe:** Alle Spalten
4. Ladet den Bericht herunter und fügt ihn hier ein
""")

# Hilfsfunktionen
def format_number_de(value, decimals=0):
    """Formatiert Zahlen im deutschen Format (Punkt als Tausender, Komma als Dezimal)
    
    Args:
        value: Zahl (int oder float)
        decimals: Anzahl der Dezimalstellen (Standard: 0)
    
    Returns:
        Formatierter String (z.B. "16.104,81" für 16104.81 mit decimals=2)
    """
    if pd.isna(value) or value is None:
        return "0" if decimals == 0 else "0," + "0" * decimals
    
    # Konvertiere zu float
    num = float(value)
    
    # Formatiere mit Komma als Dezimaltrennzeichen
    if decimals == 0:
        # Ganze Zahl: Tausenderpunkte
        return f"{int(num):,}".replace(",", ".")
    else:
        # Dezimalzahl: Tausenderpunkte und Komma als Dezimaltrennzeichen
        formatted = f"{num:,.{decimals}f}"
        # Ersetze Komma durch temporären Platzhalter, dann Punkt durch Komma, dann Platzhalter durch Punkt
        parts = formatted.split(".")
        if len(parts) == 2:
            integer_part = parts[0].replace(",", ".")
            decimal_part = parts[1]
            return f"{integer_part},{decimal_part}"
        else:
            # Fallback falls Formatierung nicht wie erwartet
            return formatted.replace(".", ",")

def parse_euro_value(value):
    """Konvertiert Euro-Strings (z.B. '1.999,55 €' oder '368,14 €') zu Float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    # Entferne Leerzeichen und €
    value_str = str(value).replace(' ', '').replace('€', '').strip()
    
    # Format: "1.999,55" (Punkt = Tausender, Komma = Dezimal)
    # Prüfe ob Punkt als Tausendertrennzeichen verwendet wird (mehr als ein Punkt)
    if '.' in value_str and ',' in value_str:
        # Format: "1.999,55" - Punkt ist Tausender, Komma ist Dezimal
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Format: "368,14" - Komma ist Dezimal
        value_str = value_str.replace(',', '.')
    # Falls nur Punkt vorhanden, könnte es Tausender oder Dezimal sein
    # Wenn mehr als ein Punkt, dann Tausender
    elif value_str.count('.') > 1:
        value_str = value_str.replace('.', '')
    
    try:
        return float(value_str)
    except:
        return 0.0

def parse_percentage(value):
    """Konvertiert Prozent-Strings (z.B. '16,40%' oder '16.40%') zu Float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    value_str = str(value).replace('%', '').replace(' ', '').strip()
    
    # Komma als Dezimaltrennzeichen (deutsches Format)
    if ',' in value_str:
        value_str = value_str.replace(',', '.')
    
    try:
        return float(value_str)
    except:
        return 0.0

def parse_numeric_value(value):
    """Konvertiert numerische Strings mit deutschem Format (z.B. '9,778' oder '6,333') zu Float"""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    value_str = str(value).replace(' ', '').strip()
    
    # Format: "9,778" (Komma als Tausendertrennzeichen) oder "1.234,56" (Punkt = Tausender, Komma = Dezimal)
    if '.' in value_str and ',' in value_str:
        # Format: "1.234,56" - Punkt ist Tausender, Komma ist Dezimal
        value_str = value_str.replace('.', '').replace(',', '.')
    elif ',' in value_str:
        # Prüfe ob Komma Tausender oder Dezimal ist
        parts = value_str.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Komma ist Dezimaltrennzeichen (z.B. "123,45")
            value_str = value_str.replace(',', '.')
        else:
            # Komma ist Tausendertrennzeichen (z.B. "9,778" oder "6,333")
            value_str = value_str.replace(',', '')
    # Falls nur Punkt vorhanden und mehr als einer, dann Tausender
    elif value_str.count('.') > 1:
        value_str = value_str.replace('.', '')
    
    try:
        return float(value_str)
    except:
        return 0.0

def parse_date_column(date_str):
    """Parst Datum im Format DD.MM.YY zu YYYY-MM-DD"""
    if pd.isna(date_str) or date_str == '':
        return None
    date_str = str(date_str).strip()
    # Versuche verschiedene Formate
    date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{2})', date_str)
    if date_match:
        day, month, year = date_match.groups()
        year_full = f"20{year}" if int(year) < 50 else f"19{year}"
        return f"{year_full}-{month}-{day}"
    return date_str

def load_and_process_csv(uploaded_file, file_name):
    """Lädt und verarbeitet eine CSV-Datei (ASIN-Level oder Account-Level)"""
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        
        # Entferne doppelte Spaltennamen (behalte die erste)
        if df.columns.duplicated().any():
            df = df.loc[:, ~df.columns.duplicated()]
        
        # Prüfe ob es ein Account-Level Report ist (hat "Datum"-Spalte)
        is_account_level = 'Datum' in df.columns
        
        if is_account_level:
            # Account-Level Report: Verwende Datumsspalte
            df['Zeitraum'] = df['Datum'].apply(parse_date_column)
            df = df.dropna(subset=['Zeitraum'])  # Entferne Zeilen ohne gültiges Datum
            df['Dateiname'] = file_name
            df['Report_Typ'] = 'Account-Level'
        else:
            # ASIN-Level Report: Extrahiere Datum aus Dateinamen
            date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{2})', file_name)
            if date_match:
                day, month, year = date_match.groups()
                year_full = f"20{year}" if int(year) < 50 else f"19{year}"
                date_str = f"{year_full}-{month}-{day}"
            else:
                date_str = file_name
            
            df['Zeitraum'] = date_str
            df['Dateiname'] = file_name
            df['Report_Typ'] = 'ASIN-Level'
        
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
            'Sitzungen – Browser – B2B',
            # Zusätzliche Spalten
            'Durchschnittlicher Umsatz/Bestellposten',
            'Durchschnittlicher Umsatz pro Bestellposten – B2B',
            'Durchschnitt Anzahl von Einheiten/Bestellposten',
            'Durchschnitt Anzahl von Einheiten/Bestellposten – B2B',
            'Durchschnittlicher Verkaufspreis',
            'Durchschnittlicher Verkaufspreis – B2B',
            'Prozentsatz Bestellposten pro Sitzung',
            'Bestellposten pro Sitzung Prozentwert – B2B',
            'Durchschnittliche Angebotszahl'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                # Euro-Werte
                if 'Umsatz' in col or 'Bestellsumme' in col or 'Verkaufspreis' in col:
                    df[col] = df[col].apply(parse_euro_value)
                # Prozentwerte
                elif 'Prozentsatz' in col or 'Prozentwert' in col or col.endswith('%'):
                    df[col] = df[col].apply(parse_percentage)
                # Normale numerische Werte (können auch mit Komma als Tausendertrennzeichen sein)
                else:
                    # Konvertiere zu String, dann parse mit deutschem Format
                    df[col] = df[col].apply(parse_numeric_value)
        
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
    
    # Prüfe ob es eine B2B-Suche ist (wenn "B2B" in einem der möglichen Namen enthalten ist)
    is_b2b_search = any('b2b' in name.lower() for name in possible_names)
    
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
            # Bei B2B-Suche: Stelle sicher, dass "b2b" auch im Spaltennamen enthalten ist
            if is_b2b_search and 'b2b' not in col_lower:
                continue
            # Bei B2B-Suche: Stelle sicher, dass normale Spalten (ohne B2B) nicht gefunden werden
            if is_b2b_search and 'bestellte' in col_lower and 'einheiten' in col_lower and 'b2b' not in col_lower:
                continue
            # Prüfe ob alle wichtigen Keywords in Spaltenname enthalten sind
            if all(keyword in col_lower for keyword in name_keywords if len(keyword) > 2):
                return col
    
    return None

def find_b2b_units_column(df):
    """Findet die B2B-Einheiten-Spalte, berücksichtigt auch Non-Breaking Spaces (\xa0)"""
    for col in df.columns:
        if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
            # Prüfe ob es wirklich die B2B-Spalte ist (nicht die normale)
            if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                return col
    return None

def find_cr_column(df, traffic_type='normal'):
    """Findet die Conversion Rate Spalte, berücksichtigt auch Non-Breaking Spaces (\xa0)"""
    if traffic_type == 'B2B':
        # Suche nach B2B Conversion Rate Spalte (mit Non-Breaking Space)
        for col in df.columns:
            col_lower = col.lower()
            if 'bestellposten' in col_lower and 'sitzung' in col_lower and 'prozentwert' in col_lower and 'b2b' in col_lower:
                return col
    else:
        # Suche nach Normal Conversion Rate Spalte
        for col in df.columns:
            col_lower = col.lower()
            if 'bestellposten' in col_lower and 'sitzung' in col_lower and 'prozentsatz' in col_lower and 'b2b' not in col_lower:
                return col
    return None

def aggregate_data(df, traffic_type='normal', is_account_level=False):
    """Aggregiert Daten über alle ASINs (oder Account-Level) und berechnet zusätzliche KPIs"""
    if traffic_type == 'B2B':
        # Für B2B: AUSSCHLIESSLICH die Spalte "Bestellte Einheiten – B2B" verwenden
        # KEINE Fallbacks, KEINE Suche nach ähnlichen Spalten, KEINE normale Spalte
        # DIREKT im ersten Schritt setzen, damit nichts anderes es überschreiben kann
        # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
        units_col = find_b2b_units_column(df)
        if units_col is None:
            # Spalte existiert nicht - erstelle sie mit 0-Werten
            units_col = 'Bestellte Einheiten – B2B'
            df[units_col] = 0
        
        b2b_revenue_candidates = ['Bestellsumme – B2B', 'Bestellsumme - B2B']
        revenue_col = None
        for candidate in b2b_revenue_candidates:
            if candidate in df.columns:
                revenue_col = candidate
                break
        if revenue_col is None:
            revenue_col = find_column(df, b2b_revenue_candidates)
        # Für B2B: Prüfe explizit ob B2B-Spalten existieren
        b2b_views_candidates = ['Seitenaufrufe – Summe – B2B', 'Seitenaufrufe - Summe - B2B', 'Sitzungen – Summe – B2B', 'Sitzungen - Summe - B2B']
        views_col = None
        for candidate in b2b_views_candidates:
            if candidate in df.columns:
                views_col = candidate
                break
        if views_col is None:
            views_col = find_column(df, b2b_views_candidates)
        
        # Für B2B: AUSSCHLIESSLICH die exakte B2B-Sitzungen-Spalte verwenden
        sessions_col = None
        # Prüfe exakt diese beiden Varianten (mit unterschiedlichen Bindestrichen)
        if 'Sitzungen – Summe – B2B' in df.columns:
            sessions_col = 'Sitzungen – Summe – B2B'
        elif 'Sitzungen - Summe - B2B' in df.columns:
            sessions_col = 'Sitzungen - Summe - B2B'
        # KEINE Fallback-Suche, KEINE ähnlichen Spalten
        
        b2b_orders_candidates = ['Zahl der Bestellposten – B2B', 'Zahl der Bestellposten - B2B']
        orders_col = None
        for candidate in b2b_orders_candidates:
            if candidate in df.columns:
                orders_col = candidate
                break
        if orders_col is None:
            orders_col = find_column(df, b2b_orders_candidates)
        
        b2b_mobile_candidates = ['Sitzungen – mobile App – B2B', 'Sitzungen - mobile App - B2B']
        mobile_sessions_col = None
        for candidate in b2b_mobile_candidates:
            if candidate in df.columns:
                mobile_sessions_col = candidate
                break
        if mobile_sessions_col is None:
            mobile_sessions_col = find_column(df, b2b_mobile_candidates)
        
        b2b_browser_candidates = ['Sitzungen – Browser – B2B', 'Sitzungen - Browser - B2B']
        browser_sessions_col = None
        for candidate in b2b_browser_candidates:
            if candidate in df.columns:
                browser_sessions_col = candidate
                break
        if browser_sessions_col is None:
            browser_sessions_col = find_column(df, b2b_browser_candidates)
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
    
    # Für units_col - prüfe ob Spalte existiert
    # BEI B2B: KEINE Fallbacks zur normalen Spalte! NUR B2B-Spalte verwenden!
    if units_col is None:
        if traffic_type == 'B2B':
            # Für B2B: AUSSCHLIESSLICH die exakte B2B-Spalte verwenden (mit Non-Breaking Space)
            # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
            units_col = find_b2b_units_column(df)
            if units_col is None:
                # Spalte fehlt wirklich - erstelle sie mit 0-Werten
                missing_cols.append('Bestellte Einheiten – B2B')
                units_col = 'Bestellte Einheiten – B2B'
                df[units_col] = 0
        else:
            expected_name = 'Bestellte Einheiten'
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
        if traffic_type == 'B2B':
            # Bei B2B: AUSSCHLIESSLICH die exakte B2B-Sitzungen-Spalte verwenden
            if 'Sitzungen – Summe – B2B' in df.columns:
                sessions_col = 'Sitzungen – Summe – B2B'
            elif 'Sitzungen - Summe - B2B' in df.columns:
                sessions_col = 'Sitzungen - Summe - B2B'
            else:
                # KEIN Fallback - Fehler anzeigen
                # Erstelle Spalte mit 0-Werten als letzten Ausweg
                sessions_col = 'Sitzungen – Summe – B2B'
                df[sessions_col] = 0
        else:
            expected_name = 'Sitzungen – Summe'
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
    
    # WICHTIG: Bei B2B muss sichergestellt werden, dass wirklich die B2B-Spalte verwendet wird
    # Prüfe dies SOFORT nach dem Finden der Spalten, VOR der Debug-Ausgabe
    if traffic_type == 'B2B':
        # Prüfe ob units_col wirklich die exakte B2B-Spalte ist (mit Non-Breaking Space)
        # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
        b2b_col_found = find_b2b_units_column(df)
        if b2b_col_found:
            units_col = b2b_col_found
        elif units_col is None:
            units_col = None
    
    # Bei B2B: FORCIERE die exakte B2B-Spalte nochmal (mit Non-Breaking Space)
    if traffic_type == 'B2B':
        # ÜBERSCHREIBE units_col IMMER mit der exakten B2B-Spalte
        b2b_col_found = find_b2b_units_column(df)
        if b2b_col_found:
            if units_col != b2b_col_found:
                units_col = b2b_col_found
    
    # Prüfe ob Spalten wirklich im DataFrame existieren
    final_missing = []
    if units_col and units_col not in df.columns:
        final_missing.append(units_col)
    if revenue_col and revenue_col not in df.columns:
        final_missing.append(revenue_col)
    if views_col and views_col not in df.columns:
        final_missing.append(views_col)
    
    # Prüfe ob Conversion Rate Spalte vorhanden ist (mit Non-Breaking Space) - VOR der Aggregation
    cr_col = find_cr_column(df, traffic_type)
    
    # Bei Account-Level Reports sind die Daten bereits aggregiert, bei ASIN-Level müssen wir gruppieren
    if is_account_level:
        # Daten sind bereits pro Zeitraum aggregiert
        aggregated = df.copy()
        # Stelle sicher, dass keine doppelten Spaltennamen existieren
        if aggregated.columns.duplicated().any():
            aggregated = aggregated.loc[:, ~aggregated.columns.duplicated()]
        # Stelle sicher, dass alle benötigten Spalten vorhanden sind
        for col in [units_col, revenue_col, views_col, sessions_col, orders_col, mobile_sessions_col, browser_sessions_col]:
            if col not in aggregated.columns:
                aggregated[col] = 0
    else:
        # ASIN-Level: Gruppiere nach Zeitraum
        # KRITISCH: Bei B2B - FORCIERE die exakte B2B-Spalte
        if traffic_type == 'B2B':
            # ÜBERSCHREIBE units_col mit der exakten B2B-Spalte, egal was vorher gesetzt war (mit Non-Breaking Space)
            b2b_col_found = find_b2b_units_column(df)
            if b2b_col_found:
                units_col = b2b_col_found
            else:
                # Erstelle Spalte mit 0-Werten als letzten Ausweg
                units_col = 'Bestellte Einheiten – B2B'
                df[units_col] = 0
        
        # Stelle sicher, dass units_col gesetzt ist, bevor aggregiert wird
        # BEI B2B: FORCIERE IMMER die exakte B2B-Spalte, auch wenn units_col bereits gesetzt ist
        if traffic_type == 'B2B':
            # ÜBERSCHREIBE units_col IMMER mit der exakten B2B-Spalte (mit Non-Breaking Space)
            b2b_col_found = find_b2b_units_column(df)
            if b2b_col_found:
                if units_col != b2b_col_found:
                    units_col = b2b_col_found
            else:
                # Erstelle Spalte mit 0-Werten als letzten Ausweg
                units_col = 'Bestellte Einheiten – B2B'
                df[units_col] = 0
        elif units_col is None:
            # Nur für normalen Traffic, nicht für B2B
            if traffic_type != 'B2B':
                units_col = 'Bestellte Einheiten'
                if units_col not in df.columns:
                    df[units_col] = 0
        
        # KRITISCH: Bei B2B - FINALE Prüfung direkt vor Aggregation
        # AUSSCHLIESSLICH die exakte Spalte "Bestellte Einheiten – B2B" verwenden
        if traffic_type == 'B2B':
            # Prüfe ob units_col wirklich die exakte B2B-Spalte ist (mit Non-Breaking Space)
            b2b_col_found = find_b2b_units_column(df)
            if b2b_col_found and units_col != b2b_col_found:
                # Korrigiere auf die exakte Spalte
                units_col = b2b_col_found
        
        # ABSOLUT KRITISCH: Bei B2B - Letzte Prüfung direkt VOR der Aggregation
        # AUSSCHLIESSLICH die exakte Spalte "Bestellte Einheiten – B2B" verwenden
        if traffic_type == 'B2B':
            # Prüfe ob units_col wirklich die exakte B2B-Spalte ist
            if units_col not in ['Bestellte Einheiten – B2B', 'Bestellte Einheiten - B2B']:
                # Korrigiere auf die exakte Spalte
                if 'Bestellte Einheiten – B2B' in df.columns:
                    units_col = 'Bestellte Einheiten – B2B'
                elif 'Bestellte Einheiten - B2B' in df.columns:
                    units_col = 'Bestellte Einheiten - B2B'
        
        # ABSOLUT LETZTE PRÜFUNG: Bei B2B FORCIERE die exakte B2B-Spalte direkt vor der Aggregation (mit Non-Breaking Space)
        if traffic_type == 'B2B':
            b2b_col_found = find_b2b_units_column(df)
            if b2b_col_found and units_col != b2b_col_found:
                units_col = b2b_col_found
        
        # ABSOLUT FINALE PRÜFUNG: Bei B2B FORCIERE die B2B-Spalte DIREKT vor groupby.agg() (mit Non-Breaking Space)
        if traffic_type == 'B2B':
            # ÜBERSCHREIBE units_col IMMER mit der exakten B2B-Spalte, egal was vorher war
            b2b_col_found = find_b2b_units_column(df)
            if b2b_col_found and units_col != b2b_col_found:
                units_col = b2b_col_found
        
        # KRITISCH: Bei B2B - Letzte Prüfung DIREKT vor groupby.agg()
        # Stelle sicher, dass units_col wirklich die B2B-Spalte ist
        if traffic_type == 'B2B':
            # Prüfe ob units_col wirklich die B2B-Spalte ist
            if units_col not in ['Bestellte Einheiten – B2B', 'Bestellte Einheiten - B2B']:
                # Korrigiere auf die exakte B2B-Spalte
                if 'Bestellte Einheiten – B2B' in df.columns:
                    units_col = 'Bestellte Einheiten – B2B'
                elif 'Bestellte Einheiten - B2B' in df.columns:
                    units_col = 'Bestellte Einheiten - B2B'
        
        # Aggregations-Dictionary
        agg_dict = {
            units_col: 'sum',
            revenue_col: 'sum',
            views_col: 'sum',
            sessions_col: 'sum',
            orders_col: 'sum',
            mobile_sessions_col: 'sum',
            browser_sessions_col: 'sum'
        }
        
        # Wenn Conversion Rate Spalte vorhanden ist, füge sie mit 'mean' hinzu
        if cr_col and cr_col in df.columns:
            agg_dict[cr_col] = 'mean'  # Mittelwert für Conversion Rate
        
        aggregated = df.groupby('Zeitraum').agg(agg_dict).reset_index()
    
    if final_missing:
        st.warning(f"⚠️ Folgende Spalten fehlen wirklich in den Daten: {', '.join(final_missing)}")
    
    # Stelle sicher, dass alle Spalten numerisch sind (mit deutschem Format)
    for col in [units_col, revenue_col, views_col, sessions_col, orders_col, mobile_sessions_col, browser_sessions_col]:
        if col in aggregated.columns:
            # Verwende parse_numeric_value für alle numerischen Werte (erkennt Komma als Tausender)
            # Ausnahme: revenue_col verwendet parse_euro_value
            if col == revenue_col:
                aggregated[col] = aggregated[col].apply(parse_euro_value)
            else:
                aggregated[col] = aggregated[col].apply(parse_numeric_value)
    
    # Conversion Rate: Verwende vorhandene Spalte oder berechne aus Bestellposten / Sitzungen (mit Non-Breaking Space)
    # WICHTIG: Suche die CR-Spalte in aggregated (nach Aggregation), aber verwende die ursprünglich gefundene cr_col wenn sie noch vorhanden ist
    cr_col_after_agg = None
    if cr_col and cr_col in aggregated.columns:
        # Die ursprünglich gefundene CR-Spalte ist noch vorhanden (wurde aggregiert)
        cr_col_after_agg = cr_col
    else:
        # Suche erneut in aggregated (falls Spalte umbenannt wurde oder nicht gefunden wurde)
        cr_col_after_agg = find_cr_column(aggregated, traffic_type)
    
    if cr_col_after_agg and cr_col_after_agg in aggregated.columns:
        # Verwende vorhandene Conversion Rate Spalte (bereits als Mittelwert aggregiert)
        aggregated['Conversion Rate (%)'] = aggregated[cr_col_after_agg].fillna(0)
    else:
        # Fallback: Berechne aus Bestellposten / Sitzungen * 100
        aggregated['Conversion Rate (%)'] = (
            (aggregated[orders_col] / aggregated[sessions_col].replace(0, np.nan) * 100)
            .fillna(0)
            .replace([np.inf, -np.inf], 0)
        )
    
    # AOV = Umsatz / Anzahl der Bestellposten
    # Prüfe zuerst, ob bereits eine AOV-Spalte in den Originaldaten vorhanden ist
    aov_col_name = 'Durchschnittlicher Umsatz/Bestellposten' if traffic_type == 'normal' else 'Durchschnittlicher Umsatz pro Bestellposten – B2B'
    aov_col_alt = find_column(df, [aov_col_name, 'Durchschnittlicher Umsatz/Bestellposten', 'Durchschnittlicher Umsatz pro Bestellposten – B2B'])
    
    if aov_col_alt and aov_col_alt in df.columns:
        # Wenn AOV-Spalte in Originaldaten vorhanden ist, verwende diese
        # Aggregiere die AOV-Werte (gewichtet nach Anzahl der Bestellposten)
        if is_account_level:
            # Bei Account-Level: AOV ist bereits pro Zeitraum vorhanden
            if aov_col_alt in aggregated.columns:
                aggregated['AOV (€)'] = aggregated[aov_col_alt]
            else:
                # Fallback: Berechne aus Umsatz / Bestellposten
                aggregated['AOV (€)'] = (
                    (aggregated[revenue_col] / aggregated[orders_col].replace(0, np.nan))
                    .fillna(0)
                    .replace([np.inf, -np.inf], 0)
                )
        else:
            # Bei ASIN-Level: Gewichteter Durchschnitt der AOV-Werte
            # AOV gesamt = Summe(Umsatz) / Summe(Bestellposten)
            aggregated['AOV (€)'] = (
                (aggregated[revenue_col] / aggregated[orders_col].replace(0, np.nan))
                .fillna(0)
                .replace([np.inf, -np.inf], 0)
            )
    else:
        # Berechne AOV aus Umsatz / Anzahl der Bestellposten
        aggregated['AOV (€)'] = (
            (aggregated[revenue_col] / aggregated[orders_col].replace(0, np.nan))
            .fillna(0)
            .replace([np.inf, -np.inf], 0)
        )
    
    # Revenue per Session = Umsatz / Sitzungen
    aggregated['Revenue per Session (€)'] = (
        (aggregated[revenue_col] / aggregated[sessions_col].replace(0, np.nan))
        .fillna(0)
        .replace([np.inf, -np.inf], 0)
    )
    
    # Umbenennen der Spalten - nur die Spalten die tatsächlich vorhanden sind
    # Erstelle Mapping ohne 'Zeitraum' (wird nicht umbenannt)
    # KRITISCH: Bei B2B muss sichergestellt werden, dass units_col wirklich die B2B-Spalte ist
    # Prüfe DIREKT in aggregated.columns, welche Spalte tatsächlich aggregiert wurde
    if traffic_type == 'B2B':
        # Prüfe welche B2B-Spalte tatsächlich in aggregated.columns vorhanden ist
        actual_b2b_col = None
        if 'Bestellte Einheiten – B2B' in aggregated.columns:
            actual_b2b_col = 'Bestellte Einheiten – B2B'
        elif 'Bestellte Einheiten - B2B' in aggregated.columns:
            actual_b2b_col = 'Bestellte Einheiten - B2B'
        
        # Wenn eine B2B-Spalte gefunden wurde, verwende diese
        if actual_b2b_col:
            if units_col != actual_b2b_col:
                old_units_col = units_col
                units_col = actual_b2b_col
    
    # KRITISCH: Bei B2B - FINALE Prüfung VOR dem Erstellen des column_mapping
    # Stelle sicher, dass units_col wirklich die B2B-Spalte ist, die aggregiert wurde
    if traffic_type == 'B2B':
        # Prüfe welche B2B-Spalte tatsächlich in aggregated.columns vorhanden ist
        actual_b2b_col_in_agg = None
        if 'Bestellte Einheiten – B2B' in aggregated.columns:
            actual_b2b_col_in_agg = 'Bestellte Einheiten – B2B'
        elif 'Bestellte Einheiten - B2B' in aggregated.columns:
            actual_b2b_col_in_agg = 'Bestellte Einheiten - B2B'
        
        # Wenn eine B2B-Spalte in aggregated gefunden wurde, verwende diese für das Mapping
        if actual_b2b_col_in_agg:
            if units_col != actual_b2b_col_in_agg:
                units_col = actual_b2b_col_in_agg
    
    # Bei B2B: Behalte den originalen Spaltennamen "Bestellte Einheiten – B2B"
    # Bei normalem Traffic: Benenne zu "Bestellte Einheiten" um
    if traffic_type == 'B2B':
        # Für B2B: Behalte den originalen Namen, benenne NICHT um
        column_mapping = {
            revenue_col: 'Umsatz',
            views_col: 'Seitenaufrufe',
            sessions_col: 'Sitzungen',
            orders_col: 'Bestellungen',
            mobile_sessions_col: 'Mobile Sitzungen',
            browser_sessions_col: 'Browser Sitzungen'
        }
        # units_col wird NICHT umbenannt, bleibt "Bestellte Einheiten – B2B" (oder "Bestellte Einheiten - B2B")
    else:
        # Für normalen Traffic: Benenne alle Spalten um
        column_mapping = {
            units_col: 'Bestellte Einheiten',
            revenue_col: 'Umsatz',
            views_col: 'Seitenaufrufe',
            sessions_col: 'Sitzungen',
            orders_col: 'Bestellungen',
            mobile_sessions_col: 'Mobile Sitzungen',
            browser_sessions_col: 'Browser Sitzungen'
        }
    
    # Prüfe auf doppelte Zielnamen und benenne nur um, wenn nötig
    rename_dict = {}
    for old_name, new_name in column_mapping.items():
        if old_name in aggregated.columns and old_name != new_name:
            # Prüfe ob Zielname bereits existiert (aber nicht als die aktuelle Spalte)
            if new_name not in aggregated.columns or aggregated.columns.get_loc(new_name) != aggregated.columns.get_loc(old_name):
                rename_dict[old_name] = new_name
    
    # Führe Umbenennung in einem Schritt durch
    if rename_dict:
        aggregated = aggregated.rename(columns=rename_dict)
    
    # Stelle sicher, dass keine doppelten Spaltennamen existieren
    if aggregated.columns.duplicated().any():
        # Entferne doppelte Spalten (behalte die erste)
        aggregated = aggregated.loc[:, ~aggregated.columns.duplicated()]
    
    return aggregated

def aggregate_by_period(df, period='week', traffic_type='normal'):
    """Aggregiert Daten nach Zeitraum (Woche, Monat, YTD)"""
    if 'Zeitraum' not in df.columns:
        return df
    
    # Konvertiere Zeitraum zu Datetime
    df = df.copy()
    df['Zeitraum_DT'] = pd.to_datetime(df['Zeitraum'], errors='coerce')
    df = df.dropna(subset=['Zeitraum_DT'])
    
    if len(df) == 0:
        return df
    
    if period == 'week':
        # Aggregiere nach Woche (Jahr-Kalenderwoche)
        df['Zeitraum_Agg'] = df['Zeitraum_DT'].dt.to_period('W').astype(str)
    elif period == 'month':
        # Aggregiere nach Monat (Jahr-Monat)
        df['Zeitraum_Agg'] = df['Zeitraum_DT'].dt.to_period('M').astype(str)
    elif period == 'ytd':
        # Year-to-Date: Gruppiere nach Jahr
        df['Jahr'] = df['Zeitraum_DT'].dt.year
        df['Zeitraum_Agg'] = df['Jahr'].astype(str) + ' (YTD)'
    else:
        # Fallback: Keine Aggregation (sollte nicht vorkommen, da Tag entfernt wurde)
        df['Zeitraum_Agg'] = df['Zeitraum_DT'].dt.strftime('%Y-%m-%d')
    
    # Identifiziere Spalten die NICHT summiert werden sollen (sondern neu berechnet)
    # AOV und Conversion Rate müssen neu berechnet werden, nicht summiert
    exclude_from_sum = ['AOV (€)', 'Conversion Rate (%)', 'Revenue per Session (€)', 'Zeitraum_DT', 'Zeitraum_Nr']
    # Conversion Rate Spalten sollen als Mittelwert aggregiert werden, nicht summiert
    # Finde alle Conversion Rate Spalten (auch mit Non-Breaking Spaces) und füge sie hinzu
    for col in df.columns:
        col_lower = col.lower()
        if ('bestellposten' in col_lower and 'sitzung' in col_lower and 
            ('prozentsatz' in col_lower or 'prozentwert' in col_lower)):
            exclude_from_sum.append(col)
    if 'Jahr' in df.columns:
        exclude_from_sum.append('Jahr')
    
    # Prüfe ob Conversion Rate Spalten vorhanden sind (sollten als Mittelwert aggregiert werden, mit Non-Breaking Space)
    cr_col_normal = find_cr_column(df, 'normal')
    cr_col_b2b = find_cr_column(df, 'B2B')
    
    # Numerische Spalten für Aggregation identifizieren
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    # Entferne Spalten die nicht summiert werden sollen
    numeric_cols = [col for col in numeric_cols if col not in exclude_from_sum]
    
    # Gruppiere und aggregiere (nur Spalten die summiert werden sollen)
    agg_dict = {col: 'sum' for col in numeric_cols if col in df.columns}
    
    # Conversion Rate Spalten als Mittelwert aggregieren (wenn vorhanden)
    if cr_col_normal and cr_col_normal in df.columns:
        agg_dict[cr_col_normal] = 'mean'
    if cr_col_b2b and cr_col_b2b in df.columns:
        agg_dict[cr_col_b2b] = 'mean'
    
    agg_dict['Zeitraum_DT'] = 'first'  # Behalte erstes Datum für Sortierung
    
    aggregated = df.groupby('Zeitraum_Agg', as_index=False).agg(agg_dict)
    
    # Sortiere nach Datum
    aggregated = aggregated.sort_values('Zeitraum_DT')
    aggregated['Zeitraum'] = aggregated['Zeitraum_Agg']
    aggregated = aggregated.drop(columns=['Zeitraum_DT', 'Zeitraum_Agg'])
    
    # Entferne temporäre Spalten
    if 'Zeitraum_DT' in aggregated.columns:
        aggregated = aggregated.drop(columns=['Zeitraum_DT'])
    if 'Zeitraum_Agg' in aggregated.columns:
        aggregated = aggregated.drop(columns=['Zeitraum_Agg'])
    
    # Berechne AOV, Conversion Rate und Revenue per Session NEU für aggregierte Zeiträume
    # Diese müssen aus den aggregierten Basiswerten neu berechnet werden, nicht summiert werden
    
    # Finde die Basis-Spalten für die Berechnung
    # Diese sollten bereits in aggregated vorhanden sein (wurden summiert)
    # Bei B2B: Verwende die originale Spalte "Bestellte Einheiten – B2B" (mit Non-Breaking Space)
    units_col_agg = None
    # Zuerst prüfe ob B2B-Spalte vorhanden ist (berücksichtigt auch Non-Breaking Spaces)
    b2b_col = find_b2b_units_column(aggregated)
    if b2b_col:
        units_col_agg = b2b_col
    elif 'Bestellte Einheiten' in aggregated.columns:
        units_col_agg = 'Bestellte Einheiten'
    
    revenue_col_agg = 'Umsatz' if 'Umsatz' in aggregated.columns else None
    sessions_col_agg = 'Sitzungen' if 'Sitzungen' in aggregated.columns else None
    orders_col_agg = 'Bestellungen' if 'Bestellungen' in aggregated.columns else None
    
    # Conversion Rate: Verwende vorhandene Spalte oder berechne aus Bestellposten / Sitzungen (mit Non-Breaking Space)
    # WICHTIG: Verwende den übergebenen traffic_type Parameter, um die richtige CR-Spalte zu finden
    cr_col = find_cr_column(aggregated, traffic_type)
    
    if cr_col and cr_col in aggregated.columns:
        # Verwende die gefundene CR-Spalte (bereits als Mittelwert aggregiert)
        aggregated['Conversion Rate (%)'] = aggregated[cr_col].fillna(0)
    elif orders_col_agg and sessions_col_agg:
        # Fallback: Berechne aus Bestellposten / Sitzungen * 100
        aggregated['Conversion Rate (%)'] = (
            (aggregated[orders_col_agg] / aggregated[sessions_col_agg].replace(0, np.nan) * 100)
            .fillna(0)
            .replace([np.inf, -np.inf], 0)
        )
    
    # AOV = Umsatz / Anzahl der Bestellposten
    if revenue_col_agg and orders_col_agg:
        aggregated['AOV (€)'] = (
            (aggregated[revenue_col_agg] / aggregated[orders_col_agg].replace(0, np.nan))
            .fillna(0)
            .replace([np.inf, -np.inf], 0)
        )
    
    # Revenue per Session = Umsatz / Sitzungen
    if revenue_col_agg and sessions_col_agg:
        aggregated['Revenue per Session (€)'] = (
            (aggregated[revenue_col_agg] / aggregated[sessions_col_agg].replace(0, np.nan))
            .fillna(0)
            .replace([np.inf, -np.inf], 0)
        )
    
    return aggregated

def get_top_flop_asins(df, traffic_type='normal'):
    """Identifiziert Top- und Flop-ASINs basierend auf Umsatz"""
    if traffic_type == 'B2B':
        # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
        units_col = find_b2b_units_column(df)
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
    # Conversion Rate: Verwende vorhandene Spalte oder berechne aus Bestellposten / Sitzungen (mit Non-Breaking Space)
    cr_col = find_cr_column(df, traffic_type)
    
    if cr_col and cr_col in df.columns:
        # Verwende vorhandene Conversion Rate Spalte (als Mittelwert aggregiert)
        asin_cr = df.groupby(asin_column)[cr_col].mean().reset_index()
        asin_cr.columns = [asin_column, 'Conversion Rate (%)']
        asin_data = asin_data.merge(asin_cr, on=asin_column, how='left')
        asin_data['Conversion Rate (%)'] = asin_data['Conversion Rate (%)'].fillna(0)
    else:
        # Fallback: Berechne aus Bestellposten / Sitzungen * 100
        asin_data['Conversion Rate (%)'] = (
            (asin_data[orders_col] / asin_data[sessions_col].replace(0, np.nan) * 100)
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
    
    # Bestellte Einheiten - bei kombinierter Ansicht: Summe aus Normal und B2B
    # Bei B2B: nur B2B-Spalte, bei Normal: nur Normal-Spalte
    units_col_name = None
    if traffic_type == 'normal' and 'Bestellte Einheiten (Gesamt)' in current.index and 'Bestellte Einheiten (Gesamt)' in previous.index:
        # Kombinierte Ansicht: Verwende die bereits berechnete Gesamt-Spalte
        units_col_name = 'Bestellte Einheiten (Gesamt)'
    elif traffic_type == 'B2B':
        # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
        # Prüfe beide DataFrames (current und previous)
        current_df = pd.DataFrame([current])
        previous_df = pd.DataFrame([previous])
        b2b_col_current = find_b2b_units_column(current_df)
        b2b_col_previous = find_b2b_units_column(previous_df)
        # Verwende die Spalte, wenn sie in beiden vorhanden ist
        if b2b_col_current and b2b_col_previous and b2b_col_current == b2b_col_previous:
            units_col_name = b2b_col_current
        # Fallback: Prüfe direkt im Index
        elif 'Bestellte Einheiten – B2B' in current.index and 'Bestellte Einheiten – B2B' in previous.index:
            units_col_name = 'Bestellte Einheiten – B2B'
        elif 'Bestellte Einheiten - B2B' in current.index and 'Bestellte Einheiten - B2B' in previous.index:
            units_col_name = 'Bestellte Einheiten - B2B'
    else:
        # Normal Traffic oder kombinierte Ansicht ohne Gesamt-Spalte
        if 'Bestellte Einheiten (Gesamt)' in current.index and 'Bestellte Einheiten (Gesamt)' in previous.index:
            units_col_name = 'Bestellte Einheiten (Gesamt)'
        elif 'Bestellte Einheiten' in current.index and 'Bestellte Einheiten' in previous.index:
            units_col_name = 'Bestellte Einheiten'
        else:
            # Fallback: Versuche beide Spalten zu finden und zu summieren
            normal_col = 'Bestellte Einheiten' if 'Bestellte Einheiten' in current.index else None
            current_df = pd.DataFrame([current])
            previous_df = pd.DataFrame([previous])
            b2b_col_current = find_b2b_units_column(current_df)
            b2b_col_previous = find_b2b_units_column(previous_df)
            
            if normal_col and b2b_col_current and b2b_col_previous:
                # Beide Spalten vorhanden: Berechne Summe manuell
                current_sum = current[normal_col] if normal_col in current.index else 0
                current_sum += current[b2b_col_current] if b2b_col_current in current.index else 0
                previous_sum = previous[normal_col] if normal_col in previous.index else 0
                previous_sum += previous[b2b_col_previous] if b2b_col_previous in previous.index else 0
                # Verwende temporäre Werte
                current['Bestellte Einheiten (Gesamt)'] = current_sum
                previous['Bestellte Einheiten (Gesamt)'] = previous_sum
                units_col_name = 'Bestellte Einheiten (Gesamt)'
            elif normal_col:
                units_col_name = normal_col
            elif b2b_col_current and b2b_col_previous:
                units_col_name = b2b_col_current
    
    if units_col_name and units_col_name in current.index and units_col_name in previous.index:
        units_change = current[units_col_name] - previous[units_col_name]
        units_pct = ((current[units_col_name] / previous[units_col_name] - 1) * 100) if previous[units_col_name] > 0 else 0
        if units_change > 0:
            summary_parts.append(f"**✅ Bestellte Einheiten:** {format_number_de(previous[units_col_name], 0)} → **{format_number_de(current[units_col_name], 0)}** | **+{format_number_de(units_change, 0)}** ({units_pct:+.1f}%)")
        elif units_change < 0:
            summary_parts.append(f"**❌ Bestellte Einheiten:** {format_number_de(previous[units_col_name], 0)} → **{format_number_de(current[units_col_name], 0)}** | **{format_number_de(units_change, 0)}** ({units_pct:+.1f}%)")
        else:
            summary_parts.append(f"**➡️ Bestellte Einheiten:** **{format_number_de(current[units_col_name], 0)}** (unverändert)")
    
    # Umsatz
    revenue_change = current['Umsatz'] - previous['Umsatz']
    revenue_pct = ((current['Umsatz'] / previous['Umsatz'] - 1) * 100) if previous['Umsatz'] > 0 else 0
    if revenue_change > 0:
        summary_parts.append(f"**✅ Umsatz:** {format_number_de(previous['Umsatz'], 2)} € → **{format_number_de(current['Umsatz'], 2)} €** | **+{format_number_de(revenue_change, 2)} €** ({revenue_pct:+.1f}%)")
    elif revenue_change < 0:
        summary_parts.append(f"**❌ Umsatz:** {format_number_de(previous['Umsatz'], 2)} € → **{format_number_de(current['Umsatz'], 2)} €** | **{format_number_de(revenue_change, 2)} €** ({revenue_pct:+.1f}%)")
    else:
        summary_parts.append(f"**➡️ Umsatz:** **{format_number_de(current['Umsatz'], 2)} €** (unverändert)")
    
    # Seitenaufrufe (nur wenn verfügbar)
    if 'Seitenaufrufe' in current and 'Seitenaufrufe' in previous:
        views_change = current['Seitenaufrufe'] - previous['Seitenaufrufe']
        views_pct = ((current['Seitenaufrufe'] / previous['Seitenaufrufe'] - 1) * 100) if previous['Seitenaufrufe'] > 0 else 0
        if views_change > 0:
            summary_parts.append(f"**✅ Seitenaufrufe:** {format_number_de(previous['Seitenaufrufe'], 0)} → **{format_number_de(current['Seitenaufrufe'], 0)}** | **+{format_number_de(views_change, 0)}** ({views_pct:+.1f}%)")
        elif views_change < 0:
            summary_parts.append(f"**❌ Seitenaufrufe:** {format_number_de(previous['Seitenaufrufe'], 0)} → **{format_number_de(current['Seitenaufrufe'], 0)}** | **{format_number_de(views_change, 0)}** ({views_pct:+.1f}%)")
        else:
            summary_parts.append(f"**➡️ Seitenaufrufe:** **{format_number_de(current['Seitenaufrufe'], 0)}** (unverändert)")
    elif 'Sitzungen' in current and 'Sitzungen' in previous:
        # Falls keine Seitenaufrufe, verwende Sitzungen
        sessions_change = current['Sitzungen'] - previous['Sitzungen']
        sessions_pct = ((current['Sitzungen'] / previous['Sitzungen'] - 1) * 100) if previous['Sitzungen'] > 0 else 0
        if sessions_change > 0:
            summary_parts.append(f"**✅ Sitzungen:** {format_number_de(previous['Sitzungen'], 0)} → **{format_number_de(current['Sitzungen'], 0)}** | **+{format_number_de(sessions_change, 0)}** ({sessions_pct:+.1f}%)")
        elif sessions_change < 0:
            summary_parts.append(f"**❌ Sitzungen:** {format_number_de(previous['Sitzungen'], 0)} → **{format_number_de(current['Sitzungen'], 0)}** | **{format_number_de(sessions_change, 0)}** ({sessions_pct:+.1f}%)")
        else:
            summary_parts.append(f"**➡️ Sitzungen:** **{format_number_de(current['Sitzungen'], 0)}** (unverändert)")
    
    # Conversion Rate
    if 'Conversion Rate (%)' in current and 'Conversion Rate (%)' in previous:
        cr_change = current['Conversion Rate (%)'] - previous['Conversion Rate (%)']
        if cr_change > 0:
            summary_parts.append(f"**✅ Conversion Rate:** {format_number_de(previous['Conversion Rate (%)'], 2)}% → **{format_number_de(current['Conversion Rate (%)'], 2)}%** | **+{format_number_de(cr_change, 2)} PP**")
        elif cr_change < 0:
            summary_parts.append(f"**❌ Conversion Rate:** {format_number_de(previous['Conversion Rate (%)'], 2)}% → **{format_number_de(current['Conversion Rate (%)'], 2)}%** | **{format_number_de(cr_change, 2)} PP**")
        else:
            summary_parts.append(f"**➡️ Conversion Rate:** **{format_number_de(current['Conversion Rate (%)'], 2)}%** (unverändert)")
    
    # AOV
    if 'AOV (€)' in current and 'AOV (€)' in previous:
        aov_change = current['AOV (€)'] - previous['AOV (€)']
        aov_pct = ((current['AOV (€)'] / previous['AOV (€)'] - 1) * 100) if previous['AOV (€)'] > 0 else 0
        if aov_change > 0:
            summary_parts.append(f"**✅ AOV:** {format_number_de(previous['AOV (€)'], 2)} € → **{format_number_de(current['AOV (€)'], 2)} €** | **+{format_number_de(aov_change, 2)} €** ({aov_pct:+.1f}%)")
        elif aov_change < 0:
            summary_parts.append(f"**❌ AOV:** {format_number_de(previous['AOV (€)'], 2)} € → **{format_number_de(current['AOV (€)'], 2)} €** | **{format_number_de(aov_change, 2)} €** ({aov_pct:+.1f}%)")
        else:
            summary_parts.append(f"**➡️ AOV:** **{format_number_de(current['AOV (€)'], 2)} €** (unverändert)")
    
    # Revenue per Session
    if 'Revenue per Session (€)' in current and 'Revenue per Session (€)' in previous:
        rps_change = current['Revenue per Session (€)'] - previous['Revenue per Session (€)']
        rps_pct = ((current['Revenue per Session (€)'] / previous['Revenue per Session (€)'] - 1) * 100) if previous['Revenue per Session (€)'] > 0 else 0
        if rps_change > 0:
            summary_parts.append(f"**✅ Revenue per Session:** {format_number_de(previous['Revenue per Session (€)'], 2)} € → **{format_number_de(current['Revenue per Session (€)'], 2)} €** | **+{format_number_de(rps_change, 2)} €** ({rps_pct:+.1f}%)")
        elif rps_change < 0:
            summary_parts.append(f"**❌ Revenue per Session:** {format_number_de(previous['Revenue per Session (€)'], 2)} € → **{format_number_de(current['Revenue per Session (€)'], 2)} €** | **{format_number_de(rps_change, 2)} €** ({rps_pct:+.1f}%)")
        else:
            summary_parts.append(f"**➡️ Revenue per Session:** **{format_number_de(current['Revenue per Session (€)'], 2)} €** (unverändert)")
    
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
            ['Normal', 'B2B', 'Kombiniert'],
            index=0
        )
        
        if traffic_type == 'Kombiniert':
            show_combined = True
            traffic_type_key = 'normal'  # Für die Verarbeitung, wird dann beide laden
        else:
            show_combined = False
            traffic_type_key = 'B2B' if traffic_type == 'B2B' else 'normal'
        
        # Prüfe ob es Account-Level oder ASIN-Level Reports sind
        is_account_level = combined_df['Report_Typ'].iloc[0] == 'Account-Level' if 'Report_Typ' in combined_df.columns else False
        
        # ASIN-Filter nur bei ASIN-Level Reports
        if not is_account_level:
            asin_column = '(Untergeordnete) ASIN'
            if asin_column not in combined_df.columns:
                # Fallback auf übergeordnete ASINs falls Spalte nicht existiert
                asin_column = '(Übergeordnete) ASIN'
            
            if asin_column in combined_df.columns:
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
            else:
                filtered_df = combined_df.copy()
        else:
            # Account-Level: Keine ASIN-Filterung möglich
            filtered_df = combined_df.copy()
            st.sidebar.info("ℹ️ Account-Level Report: ASIN-Filterung nicht verfügbar")
        
        # Hauptbereich
        st.header("📈 KPI-Übersicht")
        
        # Aggregiere Daten
        if show_combined:
            # Lade beide Traffic-Typen
            aggregated_data_normal = aggregate_data(filtered_df, 'normal', is_account_level=is_account_level)
            aggregated_data_b2b = aggregate_data(filtered_df, 'B2B', is_account_level=is_account_level)
            
            # Markiere die Daten mit Traffic-Typ
            aggregated_data_normal['Traffic_Typ'] = 'Normal'
            aggregated_data_b2b['Traffic_Typ'] = 'B2B'
            
            # Verwende normal für die weitere Verarbeitung (wird später beide zeigen)
            aggregated_data = aggregated_data_normal.copy()
        else:
            aggregated_data = aggregate_data(filtered_df, traffic_type_key, is_account_level=is_account_level)
        
        # Prüfe ob Daten auf Tagesebene sind
        # Versuche Zeiträume zu parsen und prüfe ob es Tagesdaten sind
        try:
            periods_as_dates = pd.to_datetime(aggregated_data['Zeitraum'], errors='coerce')
            valid_dates = periods_as_dates.dropna()
            if len(valid_dates) > 0:
                # Prüfe ob Zeiträume tägliche Unterschiede haben
                date_diffs = valid_dates.diff().dropna()
                # Wenn die meisten Unterschiede 1 Tag sind, sind es Tagesdaten
                daily_diffs = (date_diffs == pd.Timedelta(days=1)).sum()
                is_daily_data = len(date_diffs) > 0 and (daily_diffs / len(date_diffs)) > 0.5
            else:
                is_daily_data = False
        except:
            is_daily_data = False
        
        # Aggregationsebene-Auswahl
        if is_daily_data:
            st.sidebar.subheader("📅 Aggregationsebene")
            aggregation_level = st.sidebar.radio(
                "Zeitraum-Aggregation",
                ['Woche', 'Monat', 'YTD'],
                index=0,
                help="Wählen Sie, auf welcher Ebene die Daten angezeigt werden sollen"
            )
            
            # Konvertiere Auswahl zu Period-Key
            period_map = {'Woche': 'week', 'Monat': 'month', 'YTD': 'ytd'}
            period_key = period_map[aggregation_level]
        else:
            aggregation_level = None
            period_key = 'week'
        
        # Aggregiere Daten nach gewählter Ebene (vor Jahr-Filterung)
        if is_daily_data:
            if show_combined:
                # Aggregiere beide Traffic-Typen (mit korrektem traffic_type Parameter)
                aggregated_data_normal = aggregate_by_period(aggregated_data_normal, period=period_key, traffic_type='normal')
                aggregated_data_b2b = aggregate_by_period(aggregated_data_b2b, period=period_key, traffic_type='B2B')
                aggregated_data_normal['Traffic_Typ'] = 'Normal'
                aggregated_data_b2b['Traffic_Typ'] = 'B2B'
                aggregated_data = aggregated_data_normal.copy()
            else:
                aggregated_data = aggregate_by_period(aggregated_data, period=period_key, traffic_type=traffic_type_key)
        
        # Jahr-Auswahl (wenn mehrere Jahre vorhanden)
        if 'Zeitraum' in aggregated_data.columns:
            if period_key == 'ytd':
                # Bei YTD sind Jahre bereits im Zeitraum-String (z.B. "2024 (YTD)")
                # Extrahiere Jahre aus Zeitraum-Strings
                available_years = []
                for period_str in aggregated_data['Zeitraum'].unique():
                    year_match = re.search(r'(\d{4})\s*\(YTD\)', str(period_str))
                    if year_match:
                        available_years.append(int(year_match.group(1)))
                available_years = sorted(list(set(available_years)))
            else:
                # Extrahiere Jahre aus Zeiträumen
                # Verwende Regex, um Jahre aus allen Zeitraum-Formaten zu extrahieren
                # (funktioniert für Datumsangaben, Wochen, Monate, etc.)
                available_years = []
                for period_str in aggregated_data['Zeitraum'].unique():
                    # Versuche Jahr aus verschiedenen Formaten zu extrahieren
                    year_match = re.search(r'(\d{4})', str(period_str))
                    if year_match:
                        available_years.append(int(year_match.group(1)))
                available_years = sorted(list(set(available_years)))
                
                # Erstelle Jahr_Extracted Spalte für Filterung
                aggregated_data['Jahr_Extracted'] = aggregated_data['Zeitraum'].str.extract(r'(\d{4})', expand=False).astype(float)
            
            if len(available_years) > 1:
                st.sidebar.subheader("📆 Jahr-Auswahl")
                selected_year = st.sidebar.selectbox(
                    "Jahr filtern",
                    ['Alle Jahre'] + [str(y) for y in available_years],
                    index=0,
                    help="Wählen Sie ein Jahr, um nur Daten dieses Jahres anzuzeigen"
                )
                
                if selected_year != 'Alle Jahre':
                    year_filter = int(selected_year)
                    if period_key == 'ytd':
                        # Filtere nach Jahr im Zeitraum-String
                        aggregated_data = aggregated_data[
                            aggregated_data['Zeitraum'].str.contains(str(year_filter), na=False)
                        ].copy()
                        if show_combined:
                            aggregated_data_normal = aggregated_data_normal[
                                aggregated_data_normal['Zeitraum'].str.contains(str(year_filter), na=False)
                            ].copy()
                            aggregated_data_b2b = aggregated_data_b2b[
                                aggregated_data_b2b['Zeitraum'].str.contains(str(year_filter), na=False)
                            ].copy()
                    else:
                        # Filtere nach extrahiertem Jahr
                        if 'Jahr_Extracted' in aggregated_data.columns:
                            aggregated_data = aggregated_data[aggregated_data['Jahr_Extracted'] == year_filter].copy()
                            if show_combined:
                                if 'Jahr_Extracted' in aggregated_data_normal.columns:
                                    aggregated_data_normal = aggregated_data_normal[aggregated_data_normal['Jahr_Extracted'] == year_filter].copy()
                                if 'Jahr_Extracted' in aggregated_data_b2b.columns:
                                    aggregated_data_b2b = aggregated_data_b2b[aggregated_data_b2b['Jahr_Extracted'] == year_filter].copy()
                        else:
                            # Fallback: Filtere nach String-Match
                            aggregated_data = aggregated_data[
                                aggregated_data['Zeitraum'].str.contains(str(year_filter), na=False)
                            ].copy()
                            if show_combined:
                                aggregated_data_normal = aggregated_data_normal[
                                    aggregated_data_normal['Zeitraum'].str.contains(str(year_filter), na=False)
                                ].copy()
                                aggregated_data_b2b = aggregated_data_b2b[
                                    aggregated_data_b2b['Zeitraum'].str.contains(str(year_filter), na=False)
                                ].copy()
            
            # Entferne temporäre Spalte
            if 'Jahr_Extracted' in aggregated_data.columns:
                aggregated_data = aggregated_data.drop(columns=['Jahr_Extracted'])
            if show_combined:
                if 'Jahr_Extracted' in aggregated_data_normal.columns:
                    aggregated_data_normal = aggregated_data_normal.drop(columns=['Jahr_Extracted'])
                if 'Jahr_Extracted' in aggregated_data_b2b.columns:
                    aggregated_data_b2b = aggregated_data_b2b.drop(columns=['Jahr_Extracted'])
        
        # Erstelle numerische Zeitraum-IDs für die X-Achse
        if show_combined:
            # Kombiniere beide Traffic-Typen
            aggregated_data_normal['Zeitraum_Nr'] = range(1, len(aggregated_data_normal) + 1)
            aggregated_data_b2b['Zeitraum_Nr'] = range(1, len(aggregated_data_b2b) + 1)
            
            # Kombiniere beide DataFrames für Visualisierung
            combined_aggregated = pd.concat([aggregated_data_normal, aggregated_data_b2b], ignore_index=True)
            # Sortiere nach Zeitraum und Traffic-Typ
            combined_aggregated = combined_aggregated.sort_values(['Zeitraum', 'Traffic_Typ'])
            # Erstelle neue Zeitraum_Nr für kombinierte Ansicht
            combined_aggregated['Zeitraum_Nr'] = combined_aggregated.groupby('Zeitraum').ngroup() + 1
            
            aggregated_data = combined_aggregated.copy()
        else:
            aggregated_data = aggregated_data.copy()
            aggregated_data['Zeitraum_Nr'] = range(1, len(aggregated_data) + 1)
        
        # Statistiken (ganz oben)
        st.header("📊 Statistiken")
        
        if show_combined:
            # Zeige Statistiken für beide Traffic-Typen nebeneinander
            st.subheader("Normal Traffic")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            # WICHTIG: Verwende die separaten aggregierten DataFrames, nicht das kombinierte
            # aggregated_data_normal und aggregated_data_b2b haben die korrekten Conversion Rate Werte
            # Prüfe ob die Variablen im globalen Scope verfügbar sind
            try:
                normal_data_combined = aggregated_data_normal.copy()
            except NameError:
                # Fallback: Filtere aus kombiniertem DataFrame
                normal_data_combined = aggregated_data[aggregated_data['Traffic_Typ'] == 'Normal'] if 'Traffic_Typ' in aggregated_data.columns else aggregated_data
            
            # Finde Spalten für Normal Traffic
            units_col_stat = find_column(filtered_df, ['Bestellte Einheiten'])
            revenue_col_stat = find_column(filtered_df, ['Durch bestellte Produkte erzielter Umsatz'])
            views_col_stat = find_column(filtered_df, ['Seitenaufrufe – Summe', 'Sitzungen – Summe'])
            
            with col1:
                # Verwende die aggregierten Normal-Daten direkt, da diese bereits korrekt aus "Bestellte Einheiten" berechnet wurden
                if 'Bestellte Einheiten' in normal_data_combined.columns:
                    total_units = normal_data_combined['Bestellte Einheiten'].sum()
                elif units_col_stat and units_col_stat in filtered_df.columns:
                    units_numeric = filtered_df[units_col_stat].apply(parse_numeric_value)
                    total_units = units_numeric.sum()
                else:
                    total_units = 0
                st.metric("Gesamt bestellte Einheiten", format_number_de(total_units, 0))
            
            with col2:
                if revenue_col_stat and revenue_col_stat in filtered_df.columns:
                    revenue_numeric = filtered_df[revenue_col_stat].apply(parse_euro_value)
                    total_revenue = revenue_numeric.sum()
                else:
                    total_revenue = normal_data_combined['Umsatz'].sum() if 'Umsatz' in normal_data_combined.columns else 0
                st.metric("Gesamtumsatz", f"{format_number_de(total_revenue, 2)} €")
            
            with col3:
                if views_col_stat and views_col_stat in filtered_df.columns:
                    views_numeric = filtered_df[views_col_stat].apply(parse_numeric_value)
                    total_views = views_numeric.sum()
                    st.metric("Gesamt Seitenaufrufe", format_number_de(total_views, 0))
                else:
                    total_views = normal_data_combined['Seitenaufrufe'].sum() if 'Seitenaufrufe' in normal_data_combined.columns else (normal_data_combined['Sitzungen'].sum() if 'Sitzungen' in normal_data_combined.columns else 0)
                    st.metric("Gesamt Seitenaufrufe", format_number_de(total_views, 0))
            
            with col4:
                asin_col_metric = '(Untergeordnete) ASIN' if '(Untergeordnete) ASIN' in filtered_df.columns else '(Übergeordnete) ASIN'
                unique_asins = filtered_df[asin_col_metric].nunique() if asin_col_metric in filtered_df.columns else 0
                st.metric("Anzahl ASINs", f"{unique_asins}")
            
            with col5:
                # Conversion Rate: Verwende vorhandene Spalte aus aggregierten Daten
                cr_col_normal_stat = find_cr_column(normal_data_combined, 'normal')
                if cr_col_normal_stat and cr_col_normal_stat in normal_data_combined.columns:
                    # Verwende die vorhandene CR-Spalte (bereits als Mittelwert aggregiert)
                    avg_cr = normal_data_combined[cr_col_normal_stat].mean()
                elif 'Conversion Rate (%)' in normal_data_combined.columns:
                    avg_cr = normal_data_combined['Conversion Rate (%)'].mean()
                else:
                    avg_cr = 0
                st.metric("Ø Conversion Rate", f"{format_number_de(avg_cr, 2)}%")
            
            with col6:
                avg_aov = normal_data_combined['AOV (€)'].mean() if 'AOV (€)' in normal_data_combined.columns else 0
                st.metric("Ø AOV", f"{format_number_de(avg_aov, 2)} €")
            
            st.subheader("B2B Traffic")
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            # WICHTIG: Verwende die separaten aggregierten DataFrames, nicht das kombinierte
            # aggregated_data_normal und aggregated_data_b2b haben die korrekten Conversion Rate Werte
            # WICHTIG: Verwende die separaten aggregierten DataFrames, nicht das kombinierte
            # aggregated_data_normal und aggregated_data_b2b haben die korrekten Conversion Rate Werte
            # Prüfe ob die Variablen im globalen Scope verfügbar sind
            try:
                b2b_data_combined = aggregated_data_b2b.copy()
            except NameError:
                # Fallback: Filtere aus kombiniertem DataFrame
                b2b_data_combined = aggregated_data[aggregated_data['Traffic_Typ'] == 'B2B'] if 'Traffic_Typ' in aggregated_data.columns else pd.DataFrame()
            
            # Finde Spalten für B2B Traffic
            units_col_stat_b2b = find_column(filtered_df, ['Bestellte Einheiten – B2B'])
            revenue_col_stat_b2b = find_column(filtered_df, ['Bestellsumme – B2B'])
            views_col_stat_b2b = find_column(filtered_df, ['Seitenaufrufe – Summe – B2B', 'Sitzungen – Summe – B2B'])
            
            with col1:
                # Verwende die aggregierten B2B-Daten direkt, die Spalte heißt jetzt "Bestellte Einheiten – B2B" (nicht umbenannt)
                b2b_units_col_name = None
                if 'Bestellte Einheiten – B2B' in b2b_data_combined.columns:
                    b2b_units_col_name = 'Bestellte Einheiten – B2B'
                elif 'Bestellte Einheiten - B2B' in b2b_data_combined.columns:
                    b2b_units_col_name = 'Bestellte Einheiten - B2B'
                
                # Verwende die aggregierten B2B-Daten direkt (wie bei Normal)
                # Die Spalte heißt "Bestellte Einheiten – B2B" statt "Bestellte Einheiten"
                total_units = 0
                b2b_units_col_found = None
                
                # Suche nach der B2B-Spalte (mit verschiedenen Leerzeichen-Varianten, inkl. Non-Breaking Space)
                for col in b2b_data_combined.columns:
                    if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                        # Prüfe ob es wirklich die B2B-Spalte ist (nicht die normale)
                        if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                            b2b_units_col_found = col
                            break
                
                if b2b_units_col_found:
                    total_units = b2b_data_combined[b2b_units_col_found].sum()
                else:
                    # Wenn aggregierte Daten 0 sind oder Spalte nicht gefunden, verwende filtered_df
                    # Suche auch in filtered_df nach der B2B-Spalte
                    b2b_col_in_df = None
                    for col in filtered_df.columns:
                        if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                            if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                                b2b_col_in_df = col
                                break
                    
                    if b2b_col_in_df:
                        units_numeric = filtered_df[b2b_col_in_df].apply(parse_numeric_value)
                        total_units = units_numeric.sum()
                    elif units_col_stat_b2b and units_col_stat_b2b in filtered_df.columns:
                        units_numeric = filtered_df[units_col_stat_b2b].apply(parse_numeric_value)
                        total_units = units_numeric.sum()
                
                st.metric("Gesamt bestellte Einheiten", format_number_de(total_units, 0))
            
            with col2:
                if revenue_col_stat_b2b and revenue_col_stat_b2b in filtered_df.columns:
                    revenue_numeric = filtered_df[revenue_col_stat_b2b].apply(parse_euro_value)
                    total_revenue = revenue_numeric.sum()
                else:
                    total_revenue = b2b_data_combined['Umsatz'].sum() if 'Umsatz' in b2b_data_combined.columns else 0
                st.metric("Gesamtumsatz", f"{format_number_de(total_revenue, 2)} €")
            
            with col3:
                if views_col_stat_b2b and views_col_stat_b2b in filtered_df.columns:
                    views_numeric = filtered_df[views_col_stat_b2b].apply(parse_numeric_value)
                    total_views = views_numeric.sum()
                    st.metric("Gesamt Seitenaufrufe", format_number_de(total_views, 0))
                else:
                    total_views = b2b_data_combined['Seitenaufrufe'].sum() if 'Seitenaufrufe' in b2b_data_combined.columns else (b2b_data_combined['Sitzungen'].sum() if 'Sitzungen' in b2b_data_combined.columns else 0)
                    st.metric("Gesamt Seitenaufrufe", format_number_de(total_views, 0))
            
            with col4:
                asin_col_metric = '(Untergeordnete) ASIN' if '(Untergeordnete) ASIN' in filtered_df.columns else '(Übergeordnete) ASIN'
                unique_asins = filtered_df[asin_col_metric].nunique() if asin_col_metric in filtered_df.columns else 0
                st.metric("Anzahl ASINs", f"{unique_asins}")
            
            with col5:
                # Conversion Rate: Verwende vorhandene Spalte aus aggregierten Daten (mit Non-Breaking Space)
                cr_col_b2b_stat = find_cr_column(b2b_data_combined, 'B2B')
                if cr_col_b2b_stat and cr_col_b2b_stat in b2b_data_combined.columns:
                    # Verwende die vorhandene CR-Spalte (bereits als Mittelwert aggregiert)
                    avg_cr = b2b_data_combined[cr_col_b2b_stat].mean()
                elif 'Conversion Rate (%)' in b2b_data_combined.columns:
                    avg_cr = b2b_data_combined['Conversion Rate (%)'].mean()
                else:
                    avg_cr = 0
                st.metric("Ø Conversion Rate", f"{format_number_de(avg_cr, 2)}%")
            
            with col6:
                avg_aov = b2b_data_combined['AOV (€)'].mean() if 'AOV (€)' in b2b_data_combined.columns else 0
                st.metric("Ø AOV", f"{format_number_de(avg_aov, 2)} €")
        else:
            # Normale Ansicht (ein Traffic-Typ)
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
                # Verwende die aggregierten Daten direkt (wie bei Normal)
                # Bei B2B: Die Spalte heißt "Bestellte Einheiten – B2B" statt "Bestellte Einheiten"
                total_units = 0
                if traffic_type_key == 'B2B':
                    # Suche die B2B-Spalte - berücksichtige auch Non-Breaking Spaces (\xa0)
                    b2b_units_col_found = None
                    
                    # Suche nach der B2B-Spalte (mit verschiedenen Leerzeichen-Varianten)
                    for col in aggregated_data.columns:
                        col_normalized = col.replace('\xa0', ' ').replace('–', '-').replace('—', '-')
                        if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                            # Prüfe ob es wirklich die B2B-Spalte ist (nicht die normale)
                            if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                                b2b_units_col_found = col
                                break
                    
                    if b2b_units_col_found:
                        total_units = aggregated_data[b2b_units_col_found].sum()
                    else:
                        # Wenn aggregierte Daten 0 sind oder Spalte nicht gefunden, verwende filtered_df
                        # Suche auch in filtered_df nach der B2B-Spalte
                        b2b_col_in_df = None
                        for col in filtered_df.columns:
                            if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                                if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                                    b2b_col_in_df = col
                                    break
                        
                        if b2b_col_in_df:
                            units_numeric = filtered_df[b2b_col_in_df].apply(parse_numeric_value)
                            total_units = units_numeric.sum()
                        elif units_col_stat and units_col_stat in filtered_df.columns:
                            units_numeric = filtered_df[units_col_stat].apply(parse_numeric_value)
                            total_units = units_numeric.sum()
                else:
                    # Normaler Traffic: Verwende aggregierte Daten oder filtered_df
                    if 'Bestellte Einheiten' in aggregated_data.columns:
                        total_units = aggregated_data['Bestellte Einheiten'].sum()
                    elif units_col_stat and units_col_stat in filtered_df.columns:
                        units_numeric = filtered_df[units_col_stat].apply(parse_numeric_value)
                        total_units = units_numeric.sum()
                
                st.metric("Gesamt bestellte Einheiten", format_number_de(total_units, 0))
            
            with col2:
                if revenue_col_stat and revenue_col_stat in filtered_df.columns:
                    revenue_numeric = filtered_df[revenue_col_stat].apply(parse_euro_value)
                    total_revenue = revenue_numeric.sum()
                else:
                    total_revenue = 0
                st.metric("Gesamtumsatz", f"{format_number_de(total_revenue, 2)} €")
            
            with col3:
                # Seitenaufrufe oder Sitzungen
                if views_col_stat and views_col_stat in filtered_df.columns:
                    # Konvertiere zu numerisch und berechne Summe
                    views_numeric = filtered_df[views_col_stat].apply(parse_numeric_value)
                    total_views = views_numeric.sum()
                    if total_views > 0:
                        st.metric("Gesamt Seitenaufrufe", format_number_de(total_views, 0))
                    elif 'Sitzungen – Summe' in filtered_df.columns:
                        sessions_numeric = filtered_df['Sitzungen – Summe'].apply(parse_numeric_value)
                        total_sessions = sessions_numeric.sum()
                        st.metric("Gesamt Sitzungen", format_number_de(total_sessions, 0))
                    else:
                        st.metric("Gesamt Seitenaufrufe", "N/A")
                elif 'Sitzungen – Summe' in filtered_df.columns:
                    sessions_numeric = filtered_df['Sitzungen – Summe'].apply(parse_numeric_value)
                    total_sessions = sessions_numeric.sum()
                    st.metric("Gesamt Sitzungen", format_number_de(total_sessions, 0))
                else:
                    st.metric("Gesamt Seitenaufrufe", "N/A")
            
            with col4:
                asin_col_metric = '(Untergeordnete) ASIN' if '(Untergeordnete) ASIN' in filtered_df.columns else '(Übergeordnete) ASIN'
                unique_asins = filtered_df[asin_col_metric].nunique() if asin_col_metric in filtered_df.columns else 0
                st.metric("Anzahl ASINs", f"{unique_asins}")
            
            with col5:
                # Durchschnittliche Conversion Rate
                avg_cr = aggregated_data['Conversion Rate (%)'].mean() if 'Conversion Rate (%)' in aggregated_data.columns else 0
                st.metric("Ø Conversion Rate", f"{format_number_de(avg_cr, 2)}%")
            
            with col6:
                # Durchschnittlicher AOV
                avg_aov = aggregated_data['AOV (€)'].mean() if 'AOV (€)' in aggregated_data.columns else 0
                st.metric("Ø AOV", f"{format_number_de(avg_aov, 2)} €")
        
        st.divider()
        
        # KPI-Übersicht (Kombinierte Visualisierung)
        st.subheader("📊 KPI-Übersicht")
        
        # Bestimme den dritten Titel basierend auf verfügbaren Daten
        if 'Seitenaufrufe' in aggregated_data.columns and aggregated_data['Seitenaufrufe'].sum() > 0:
            third_title = 'Seitenaufrufe'
        elif 'Sitzungen' in aggregated_data.columns:
            third_title = 'Sitzungen'
        else:
            third_title = 'Nicht verfügbar'
        
        if show_combined and 'Traffic_Typ' in aggregated_data.columns:
            # Kombinierte Ansicht: Zeige beide Traffic-Typen nebeneinander
            fig_combined = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Bestellte Einheiten', 'Umsatz (€)', third_title),
                specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Normal Traffic
            normal_data = aggregated_data[aggregated_data['Traffic_Typ'] == 'Normal']
            b2b_data = aggregated_data[aggregated_data['Traffic_Typ'] == 'B2B']
            
            # Bestellte Einheiten
            fig_combined.add_trace(
                go.Bar(x=normal_data['Zeitraum'], y=normal_data['Bestellte Einheiten'], 
                       name='Normal', marker_color='#1f77b4', showlegend=True),
                row=1, col=1
            )
            # Für B2B: Verwende die originale Spalte "Bestellte Einheiten – B2B" (mit Non-Breaking Space)
            b2b_units_col_chart = None
            # Suche nach der B2B-Spalte (berücksichtigt auch Non-Breaking Spaces)
            for col in b2b_data.columns:
                if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                    # Prüfe ob es wirklich die B2B-Spalte ist (nicht die normale)
                    if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                        b2b_units_col_chart = col
                        break
            
            if b2b_units_col_chart:
                fig_combined.add_trace(
                    go.Bar(x=b2b_data['Zeitraum'], y=b2b_data[b2b_units_col_chart], 
                           name='B2B', marker_color='#ff7f0e', showlegend=True),
                    row=1, col=1
                )
            else:
                # Fallback falls Spalte nicht gefunden
                fig_combined.add_trace(
                    go.Bar(x=b2b_data['Zeitraum'], y=[0] * len(b2b_data), 
                           name='B2B', marker_color='#ff7f0e', showlegend=True),
                    row=1, col=1
                )
            
            # Umsatz
            fig_combined.add_trace(
                go.Bar(x=normal_data['Zeitraum'], y=normal_data['Umsatz'], 
                       name='Normal', marker_color='#1f77b4', showlegend=False),
                row=1, col=2
            )
            fig_combined.add_trace(
                go.Bar(x=b2b_data['Zeitraum'], y=b2b_data['Umsatz'], 
                       name='B2B', marker_color='#ff7f0e', showlegend=False),
                row=1, col=2
            )
            
            # Seitenaufrufe oder Sitzungen
            if 'Seitenaufrufe' in aggregated_data.columns and aggregated_data['Seitenaufrufe'].sum() > 0:
                fig_combined.add_trace(
                    go.Bar(x=normal_data['Zeitraum'], y=normal_data['Seitenaufrufe'], 
                           name='Normal', marker_color='#1f77b4', showlegend=False),
                    row=1, col=3
                )
                fig_combined.add_trace(
                    go.Bar(x=b2b_data['Zeitraum'], y=b2b_data['Seitenaufrufe'], 
                           name='B2B', marker_color='#ff7f0e', showlegend=False),
                    row=1, col=3
                )
            elif 'Sitzungen' in aggregated_data.columns:
                fig_combined.add_trace(
                    go.Bar(x=normal_data['Zeitraum'], y=normal_data['Sitzungen'], 
                           name='Normal', marker_color='#1f77b4', showlegend=False),
                    row=1, col=3
                )
                fig_combined.add_trace(
                    go.Bar(x=b2b_data['Zeitraum'], y=b2b_data['Sitzungen'], 
                           name='B2B', marker_color='#ff7f0e', showlegend=False),
                    row=1, col=3
                )
            
            fig_combined.update_layout(height=400, showlegend=True, barmode='group')
            fig_combined.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_combined, use_container_width=True)
        else:
            # Normale Ansicht (ein Traffic-Typ)
            fig_combined = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Bestellte Einheiten', 'Umsatz (€)', third_title),
                specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Bei B2B: Verwende die originale Spalte "Bestellte Einheiten – B2B" (mit Non-Breaking Space)
            if traffic_type == 'B2B':
                # Suche nach der B2B-Spalte (berücksichtigt auch Non-Breaking Spaces)
                b2b_units_col_chart = None
                for col in aggregated_data.columns:
                    if 'bestellte' in col.lower() and 'einheiten' in col.lower() and 'b2b' in col.lower():
                        # Prüfe ob es wirklich die B2B-Spalte ist (nicht die normale)
                        if 'bestellte einheiten' in col.lower() and 'b2b' in col.lower():
                            b2b_units_col_chart = col
                            break
                
                if b2b_units_col_chart:
                    fig_combined.add_trace(
                        go.Bar(x=aggregated_data['Zeitraum'], y=aggregated_data[b2b_units_col_chart], name='Einheiten'),
                        row=1, col=1
                    )
                else:
                    # Fallback falls Spalte nicht gefunden
                    fig_combined.add_trace(
                        go.Bar(x=aggregated_data['Zeitraum'], y=[0] * len(aggregated_data), name='Einheiten'),
                        row=1, col=1
                    )
            else:
                # Normaler Traffic: Verwende "Bestellte Einheiten"
                fig_combined.add_trace(
                    go.Bar(x=aggregated_data['Zeitraum'], y=aggregated_data['Bestellte Einheiten'], name='Einheiten'),
                    row=1, col=1
                )
            
            fig_combined.add_trace(
                go.Bar(x=aggregated_data['Zeitraum'], y=aggregated_data['Umsatz'], name='Umsatz', marker_color='green'),
                row=1, col=2
            )
            
            # Seitenaufrufe oder Sitzungen für dritte Spalte
            if 'Seitenaufrufe' in aggregated_data.columns and aggregated_data['Seitenaufrufe'].sum() > 0:
                fig_combined.add_trace(
                    go.Bar(x=aggregated_data['Zeitraum'], y=aggregated_data['Seitenaufrufe'], name='Seitenaufrufe', marker_color='blue'),
                    row=1, col=3
                )
            elif 'Sitzungen' in aggregated_data.columns:
                fig_combined.add_trace(
                    go.Bar(x=aggregated_data['Zeitraum'], y=aggregated_data['Sitzungen'], name='Sitzungen', marker_color='blue'),
                    row=1, col=3
                )
            else:
                fig_combined.add_trace(
                    go.Bar(x=aggregated_data['Zeitraum'], y=[0]*len(aggregated_data), name='Nicht verfügbar', marker_color='gray'),
                    row=1, col=3
                )
            
            fig_combined.update_layout(height=400, showlegend=False)
            fig_combined.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_combined, use_container_width=True)
        
        # Neue KPIs
        st.subheader("📊 Zusätzliche KPIs")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if show_combined and 'Traffic_Typ' in aggregated_data.columns:
                fig_cr = px.line(
                    aggregated_data,
                    x='Zeitraum',
                    y='Conversion Rate (%)',
                    color='Traffic_Typ',
                    title='Conversion Rate (Kombiniert)',
                    labels={'Conversion Rate (%)': 'Conversion Rate (%)', 'Zeitraum': 'Zeitraum', 'Traffic_Typ': 'Traffic-Typ'},
                    markers=True,
                    color_discrete_map={'Normal': '#1f77b4', 'B2B': '#ff7f0e'}
                )
            else:
                fig_cr = px.line(
                    aggregated_data,
                    x='Zeitraum',
                    y='Conversion Rate (%)',
                    title=f'Conversion Rate ({traffic_type})',
                    labels={'Conversion Rate (%)': 'Conversion Rate (%)', 'Zeitraum': 'Zeitraum'},
                    markers=True
                )
                fig_cr.update_traces(line_color='purple', marker_color='purple')
            fig_cr.update_layout(height=300)
            fig_cr.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_cr, use_container_width=True)
        
        with col2:
            if show_combined and 'Traffic_Typ' in aggregated_data.columns:
                fig_aov = px.bar(
                    aggregated_data,
                    x='Zeitraum',
                    y='AOV (€)',
                    color='Traffic_Typ',
                    title='Average Order Value (Kombiniert)',
                    labels={'AOV (€)': 'AOV (€)', 'Zeitraum': 'Zeitraum', 'Traffic_Typ': 'Traffic-Typ'},
                    barmode='group',
                    color_discrete_map={'Normal': '#1f77b4', 'B2B': '#ff7f0e'}
                )
            else:
                fig_aov = px.bar(
                    aggregated_data,
                    x='Zeitraum',
                    y='AOV (€)',
                    title=f'Average Order Value ({traffic_type})',
                    labels={'AOV (€)': 'AOV (€)', 'Zeitraum': 'Zeitraum'}
                )
                fig_aov.update_traces(marker_color='orange')
            fig_aov.update_layout(height=300)
            fig_aov.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_aov, use_container_width=True)
        
        with col3:
            if show_combined and 'Traffic_Typ' in aggregated_data.columns:
                fig_rps = px.bar(
                    aggregated_data,
                    x='Zeitraum',
                    y='Revenue per Session (€)',
                    color='Traffic_Typ',
                    title='Revenue per Session (Kombiniert)',
                    labels={'Revenue per Session (€)': 'Revenue/Session (€)', 'Zeitraum': 'Zeitraum', 'Traffic_Typ': 'Traffic-Typ'},
                    barmode='group',
                    color_discrete_map={'Normal': '#1f77b4', 'B2B': '#ff7f0e'}
                )
            else:
                fig_rps = px.bar(
                    aggregated_data,
                    x='Zeitraum',
                    y='Revenue per Session (€)',
                    title=f'Revenue per Session ({traffic_type})',
                    labels={'Revenue per Session (€)': 'Revenue/Session (€)', 'Zeitraum': 'Zeitraum'}
                )
                fig_rps.update_traces(marker_color='teal')
            fig_rps.update_layout(height=300)
            fig_rps.update_xaxes(title_text='Zeitraum')
            st.plotly_chart(fig_rps, use_container_width=True)
        
        # Mobile vs Browser Performance (nur wenn Daten verfügbar)
        # Prüfe ob sowohl Mobile als auch Browser Daten vorhanden sind UND ob sie nicht alle 0 sind
        has_mobile_data = 'Mobile Sitzungen' in aggregated_data.columns
        has_browser_data = 'Browser Sitzungen' in aggregated_data.columns
        
        if has_mobile_data and has_browser_data:
            # Prüfe ob Daten vorhanden sind (nicht alle 0)
            mobile_sum = aggregated_data['Mobile Sitzungen'].sum() if has_mobile_data else 0
            browser_sum = aggregated_data['Browser Sitzungen'].sum() if has_browser_data else 0
            
            if mobile_sum > 0 or browser_sum > 0:
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
                    mobile_browser_pct['Mobile %'] = (mobile_browser_pct['Mobile Sitzungen'] / total_sessions.replace(0, np.nan) * 100).fillna(0)
                    mobile_browser_pct['Browser %'] = (mobile_browser_pct['Browser Sitzungen'] / total_sessions.replace(0, np.nan) * 100).fillna(0)
                    
                    mobile_browser_pct_data = mobile_browser_pct[['Zeitraum', 'Mobile %', 'Browser %']].melt(
                        id_vars='Zeitraum',
                        value_vars=['Mobile %', 'Browser %'],
                        var_name='Gerät',
                        value_name='Anteil (%)'
                    )
                    
                    fig_mobile_browser_pct = px.bar(
                        mobile_browser_pct_data,
                        x='Zeitraum',
                        y='Anteil (%)',
                        color='Gerät',
                        title=f'Mobile vs Browser Anteil ({traffic_type})',
                        labels={'Anteil (%)': 'Anteil (%)', 'Zeitraum': 'Zeitraum'},
                        color_discrete_map={'Mobile %': '#1f77b4', 'Browser %': '#ff7f0e'}
                    )
                    fig_mobile_browser_pct.update_layout(height=350, barmode='stack')
                    fig_mobile_browser_pct.update_xaxes(title_text='Zeitraum')
                    st.plotly_chart(fig_mobile_browser_pct, use_container_width=True)
            # Wenn keine Daten vorhanden, wird die Sektion einfach nicht angezeigt
        
        # Zusammenfassung
        st.header("📝 Zusammenfassung")
        
        # Bei kombinierter Ansicht: Kombiniere Normal und B2B Daten für Zusammenfassung
        if show_combined and 'Traffic_Typ' in aggregated_data.columns:
            # Kombiniere Normal und B2B Daten pro Zeitraum
            # Prüfe welche Einheiten-Spalten vorhanden sind
            agg_dict_combined = {
                'Umsatz': 'sum',
                'Seitenaufrufe': 'sum' if 'Seitenaufrufe' in aggregated_data.columns else 'first',
                'Sitzungen': 'sum' if 'Sitzungen' in aggregated_data.columns else 'first',
                'Bestellungen': 'sum' if 'Bestellungen' in aggregated_data.columns else 'first',
            }
            
            # Conversion Rate Spalten als Mittelwert aggregieren (wenn vorhanden, mit Non-Breaking Space)
            cr_col_normal_combined = find_cr_column(aggregated_data, 'normal')
            cr_col_b2b_combined = find_cr_column(aggregated_data, 'B2B')
            if cr_col_normal_combined and cr_col_normal_combined in aggregated_data.columns:
                agg_dict_combined[cr_col_normal_combined] = 'mean'
            if cr_col_b2b_combined and cr_col_b2b_combined in aggregated_data.columns:
                agg_dict_combined[cr_col_b2b_combined] = 'mean'
            
            # Bei kombinierten Daten: Summiere Normal und B2B Einheiten separat
            # WICHTIG: Wir müssen die Werte aus den separaten Normal- und B2B-Zeilen nehmen!
            normal_units_col_agg = 'Bestellte Einheiten' if 'Bestellte Einheiten' in aggregated_data.columns else None
            b2b_col_agg = find_b2b_units_column(aggregated_data)
            
            # Erstelle summary_data durch Gruppierung (ohne Einheiten-Spalten, die werden separat berechnet)
            summary_data = aggregated_data.groupby('Zeitraum').agg(agg_dict_combined).reset_index()
            
            # Berechne Gesamt-Einheiten separat: Normal (aus Normal-Zeilen) + B2B (aus B2B-Zeilen)
            if normal_units_col_agg and b2b_col_agg:
                summary_data['Bestellte Einheiten (Gesamt)'] = 0
                for period in summary_data['Zeitraum']:
                    # Hole Normal-Wert für diesen Zeitraum (nur aus Normal-Zeilen)
                    normal_rows = aggregated_data[(aggregated_data['Zeitraum'] == period) & (aggregated_data['Traffic_Typ'] == 'Normal')]
                    normal_value = normal_rows[normal_units_col_agg].sum() if len(normal_rows) > 0 and normal_units_col_agg in normal_rows.columns else 0
                    
                    # Hole B2B-Wert für diesen Zeitraum (nur aus B2B-Zeilen)
                    b2b_rows = aggregated_data[(aggregated_data['Zeitraum'] == period) & (aggregated_data['Traffic_Typ'] == 'B2B')]
                    b2b_value = b2b_rows[b2b_col_agg].sum() if len(b2b_rows) > 0 and b2b_col_agg in b2b_rows.columns else 0
                    
                    # Setze Gesamt-Wert
                    summary_data.loc[summary_data['Zeitraum'] == period, 'Bestellte Einheiten (Gesamt)'] = normal_value + b2b_value
            elif normal_units_col_agg:
                # Nur Normal vorhanden
                normal_rows = aggregated_data[aggregated_data['Traffic_Typ'] == 'Normal']
                if len(normal_rows) > 0:
                    summary_data = summary_data.merge(
                        normal_rows.groupby('Zeitraum')[normal_units_col_agg].sum().reset_index().rename(columns={normal_units_col_agg: 'Bestellte Einheiten (Gesamt)'}),
                        on='Zeitraum',
                        how='left'
                    )
            elif b2b_col_agg:
                # Nur B2B vorhanden
                b2b_rows = aggregated_data[aggregated_data['Traffic_Typ'] == 'B2B']
                if len(b2b_rows) > 0:
                    summary_data = summary_data.merge(
                        b2b_rows.groupby('Zeitraum')[b2b_col_agg].sum().reset_index().rename(columns={b2b_col_agg: 'Bestellte Einheiten (Gesamt)'}),
                        on='Zeitraum',
                        how='left'
                    )
            
            # Berechne KPIs neu aus kombinierten Daten
            # Die Gesamt-Einheiten-Spalte wurde bereits oben berechnet
            # Verwende sie für die KPI-Berechnung
            if 'Bestellte Einheiten (Gesamt)' in summary_data.columns:
                units_col_summary = 'Bestellte Einheiten (Gesamt)'
            else:
                # Fallback: Versuche einzelne Spalten zu finden
                normal_units_col = 'Bestellte Einheiten' if 'Bestellte Einheiten' in summary_data.columns else None
                b2b_col_summary = find_b2b_units_column(summary_data)
                if normal_units_col and b2b_col_summary:
                    # Beide vorhanden: Summiere sie
                    summary_data['Bestellte Einheiten (Gesamt)'] = (
                        summary_data[normal_units_col].fillna(0) + summary_data[b2b_col_summary].fillna(0)
                    )
                    units_col_summary = 'Bestellte Einheiten (Gesamt)'
                elif b2b_col_summary:
                    units_col_summary = b2b_col_summary
                elif normal_units_col:
                    units_col_summary = normal_units_col
                else:
                    units_col_summary = None
            
            # Conversion Rate: Verwende vorhandene Spalten oder berechne aus Bestellposten / Sitzungen (mit Non-Breaking Space)
            cr_col_normal_summary = find_cr_column(summary_data, 'normal')
            cr_col_b2b_summary = find_cr_column(summary_data, 'B2B')
            
            if cr_col_normal_summary and cr_col_normal_summary in summary_data.columns:
                # Verwende Normal Conversion Rate Spalte
                summary_data['Conversion Rate (%)'] = summary_data[cr_col_normal_summary].fillna(0)
            elif cr_col_b2b_summary and cr_col_b2b_summary in summary_data.columns:
                # Verwende B2B Conversion Rate Spalte
                summary_data['Conversion Rate (%)'] = summary_data[cr_col_b2b_summary].fillna(0)
            elif 'Sitzungen' in summary_data.columns and 'Bestellungen' in summary_data.columns:
                # Fallback: Berechne aus Bestellposten / Sitzungen * 100
                summary_data['Conversion Rate (%)'] = (
                    (summary_data['Bestellungen'] / summary_data['Sitzungen'].replace(0, np.nan) * 100)
                    .fillna(0)
                    .replace([np.inf, -np.inf], 0)
                )
            if 'Bestellungen' in summary_data.columns and 'Umsatz' in summary_data.columns:
                summary_data['AOV (€)'] = (
                    (summary_data['Umsatz'] / summary_data['Bestellungen'].replace(0, np.nan))
                    .fillna(0)
                    .replace([np.inf, -np.inf], 0)
                )
            if 'Sitzungen' in summary_data.columns and 'Umsatz' in summary_data.columns:
                summary_data['Revenue per Session (€)'] = (
                    (summary_data['Umsatz'] / summary_data['Sitzungen'].replace(0, np.nan))
                    .fillna(0)
                    .replace([np.inf, -np.inf], 0)
                )
            
            # Verwende kombinierte Daten für Zusammenfassung
            summary_aggregated_data = summary_data.copy()
        else:
            # Bei Einzelansicht: Verwende Daten wie bisher
            summary_aggregated_data = aggregated_data.copy()
        
        if len(summary_aggregated_data) > 1:
            # Zeitraum-Auswahl für Vergleich
            available_periods = summary_aggregated_data['Zeitraum'].unique().tolist()
            available_periods.sort()
            
            col1, col2 = st.columns(2)
            
            with col1:
                previous_period = st.selectbox(
                    "Vergleichszeitraum (von)",
                    available_periods,
                    index=len(available_periods) - 2 if len(available_periods) > 1 else 0,
                    help="Wählen Sie den ersten Zeitraum für den Vergleich"
                )
            
            with col2:
                current_period = st.selectbox(
                    "Aktueller Zeitraum (zu)",
                    available_periods,
                    index=len(available_periods) - 1,
                    help="Wählen Sie den zweiten Zeitraum für den Vergleich"
                )
            
            # Filtere Daten für die ausgewählten Zeiträume
            previous_data = summary_aggregated_data[summary_aggregated_data['Zeitraum'] == previous_period].copy()
            current_data = summary_aggregated_data[summary_aggregated_data['Zeitraum'] == current_period].copy()
            
            if len(previous_data) > 0 and len(current_data) > 0:
                # Bei kombinierter Ansicht: Verwende 'normal' als traffic_type (ist nur für Formatierung)
                summary_traffic_type = 'normal' if show_combined else traffic_type_key
                summary = generate_summary(current_data, previous_data, summary_traffic_type)
            else:
                summary = "Fehler beim Laden der Zeiträume. Bitte wählen Sie andere Zeiträume aus."
        else:
            summary = "Nur ein Zeitraum verfügbar. Lade weitere Dateien hoch, um Vergleiche zu sehen."
        
        st.markdown(summary)
        
        # Top- und Flop-ASINs (nur bei ASIN-Level Reports)
        if not is_account_level:
            st.subheader("🏆 Top- und Flop-ASINs")
            
            # Verwende den aktuellsten Zeitraum für Top/Flop Analyse
            latest_period = aggregated_data['Zeitraum'].iloc[-1] if len(aggregated_data) > 0 else None
            if latest_period:
                latest_df = filtered_df[filtered_df['Zeitraum'] == latest_period].copy()
            else:
                latest_df = filtered_df.copy()
            
            # Bei kombinierter Ansicht: Zeige Top/Flop für beide Traffic-Typen
            if show_combined:
                top_asins_normal, flop_asins_normal = get_top_flop_asins(latest_df, 'normal')
                top_asins_b2b, flop_asins_b2b = get_top_flop_asins(latest_df, 'B2B')
                
                # Zeige beide Traffic-Typen
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🟢 Top ASIN Normal Traffic (nach Umsatz)")
                    if top_asins_normal is not None and len(top_asins_normal) > 0:
                        row = top_asins_normal.iloc[0]
                        with st.container():
                            st.markdown(f"**{row['ASIN']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                                st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                            with col_b:
                                st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                                st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                    else:
                        st.info("Keine Daten verfügbar")
                
                with col2:
                    st.markdown("### 🟢 Top ASIN B2B Traffic (nach Umsatz)")
                    if top_asins_b2b is not None and len(top_asins_b2b) > 0:
                        row = top_asins_b2b.iloc[0]
                        with st.container():
                            st.markdown(f"**{row['ASIN']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                                st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                            with col_b:
                                st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                                st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                    else:
                        st.info("Keine Daten verfügbar")
                
                st.divider()
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 🔴 Flop ASIN Normal Traffic (nach Umsatz)")
                    if flop_asins_normal is not None and len(flop_asins_normal) > 0:
                        row = flop_asins_normal.iloc[0]
                        with st.container():
                            st.markdown(f"**{row['ASIN']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                                st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                            with col_b:
                                st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                                st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                    else:
                        st.info("Keine Daten verfügbar")
                
                with col2:
                    st.markdown("### 🔴 Flop ASIN B2B Traffic (nach Umsatz)")
                    if flop_asins_b2b is not None and len(flop_asins_b2b) > 0:
                        row = flop_asins_b2b.iloc[0]
                        with st.container():
                            st.markdown(f"**{row['ASIN']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                                st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                            with col_b:
                                st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                                st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                    else:
                        st.info("Keine Daten verfügbar")
                
                # Setze top_asins und flop_asins für die weitere Verarbeitung (falls benötigt)
                top_asins = top_asins_normal
                flop_asins = flop_asins_normal
            else:
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
                            st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                            st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                        with col_b:
                            st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                            st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                        st.caption(f"Revenue/Session: {format_number_de(row['Revenue per Session (€)'], 2)} € | Sitzungen: {format_number_de(row['Sitzungen'], 0)} | Seitenaufrufe: {format_number_de(row['Seitenaufrufe'], 0)}")
                
                with col2:
                    if flop_asins is not None and len(flop_asins) > 0:
                        st.markdown("### 🔴 Flop ASIN (nach Umsatz)")
                        row = flop_asins.iloc[0]
                        with st.container():
                            st.markdown(f"**{row['ASIN']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Umsatz", f"{format_number_de(row['Umsatz'], 2)} €")
                                st.metric("Einheiten", format_number_de(row['Einheiten'], 0))
                            with col_b:
                                st.metric("Conversion Rate", f"{format_number_de(row['Conversion Rate (%)'], 2)}%")
                                st.metric("AOV", f"{format_number_de(row['AOV (€)'], 2)} €")
                            st.caption(f"Revenue/Session: {format_number_de(row['Revenue per Session (€)'], 2)} € | Sitzungen: {format_number_de(row['Sitzungen'], 0)} | Seitenaufrufe: {format_number_de(row['Seitenaufrufe'], 0)}")
                    else:
                        st.markdown("### 🔴 Flop ASIN")
                        st.info("Keine Flop-ASIN verfügbar (nur ein ASIN mit Umsatz vorhanden oder alle ASINs haben keinen Umsatz).")
            else:
                st.info("Top- und Flop-ASINs konnten nicht berechnet werden. Bitte überprüfe die Daten.")
        else:
            st.info("ℹ️ Account-Level Report: Top- und Flop-ASINs sind nicht verfügbar (Daten sind bereits auf Account-Ebene aggregiert).")
        
        # Detaillierte Tabelle
        st.header("📋 Detaillierte Daten")
        
        if show_combined:
            # Bei kombinierter Ansicht: Zeige beide Traffic-Typen in separaten Tabs
            tab1, tab2 = st.tabs(["Normal Traffic", "B2B Traffic"])
            
            with tab1:
                # Normal Traffic Spalten
                units_col_display_normal = find_column(filtered_df, ['Bestellte Einheiten'])
                revenue_col_display_normal = find_column(filtered_df, ['Durch bestellte Produkte erzielter Umsatz'])
                views_col_display_normal = find_column(filtered_df, ['Seitenaufrufe – Summe', 'Sitzungen – Summe'])
                
                display_columns_normal = ['Zeitraum']
                if '(Übergeordnete) ASIN' in filtered_df.columns:
                    display_columns_normal.append('(Übergeordnete) ASIN')
                if '(Untergeordnete) ASIN' in filtered_df.columns:
                    display_columns_normal.append('(Untergeordnete) ASIN')
                if 'Titel' in filtered_df.columns:
                    display_columns_normal.append('Titel')
                if units_col_display_normal:
                    display_columns_normal.append(units_col_display_normal)
                if revenue_col_display_normal:
                    display_columns_normal.append(revenue_col_display_normal)
                if views_col_display_normal:
                    display_columns_normal.append(views_col_display_normal)
                
                available_columns_normal = [col for col in display_columns_normal if col in filtered_df.columns]
                st.dataframe(
                    filtered_df[available_columns_normal],
                    use_container_width=True,
                    height=400
                )
            
            with tab2:
                # B2B Traffic Spalten - verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
                units_col_display_b2b = find_b2b_units_column(filtered_df)
                revenue_col_display_b2b = find_column(filtered_df, ['Bestellsumme – B2B', 'Bestellsumme - B2B'])
                views_col_display_b2b = find_column(filtered_df, ['Seitenaufrufe – Summe – B2B', 'Sitzungen – Summe – B2B'])
                
                display_columns_b2b = ['Zeitraum']
                if '(Übergeordnete) ASIN' in filtered_df.columns:
                    display_columns_b2b.append('(Übergeordnete) ASIN')
                if '(Untergeordnete) ASIN' in filtered_df.columns:
                    display_columns_b2b.append('(Untergeordnete) ASIN')
                if 'Titel' in filtered_df.columns:
                    display_columns_b2b.append('Titel')
                if units_col_display_b2b:
                    display_columns_b2b.append(units_col_display_b2b)
                if revenue_col_display_b2b:
                    display_columns_b2b.append(revenue_col_display_b2b)
                if views_col_display_b2b:
                    display_columns_b2b.append(views_col_display_b2b)
                
                available_columns_b2b = [col for col in display_columns_b2b if col in filtered_df.columns]
                st.dataframe(
                    filtered_df[available_columns_b2b],
                    use_container_width=True,
                    height=400
                )
        else:
            # Einzelansicht: Zeige nur einen Traffic-Typ
            # Finde die tatsächlichen Spaltennamen für die Anzeige
            if traffic_type_key == 'B2B':
                # Verwende Hilfsfunktion die auch Non-Breaking Spaces berücksichtigt
                units_col_display = find_b2b_units_column(filtered_df)
            else:
                units_col_display = find_column(filtered_df, ['Bestellte Einheiten'])
            revenue_col_display = find_column(filtered_df, ['Durch bestellte Produkte erzielter Umsatz' if traffic_type_key == 'normal' else 'Bestellsumme – B2B', 'Bestellsumme - B2B'])
            views_col_display = find_column(filtered_df, [
                'Seitenaufrufe – Summe' if traffic_type_key == 'normal' else 'Seitenaufrufe – Summe – B2B',
                'Seitenaufrufe - Summe - B2B',
                'Sitzungen – Summe',
                'Sitzungen - Summe'
            ])
            
            display_columns = ['Zeitraum']
            
            # Füge ASIN-Spalten nur hinzu, wenn vorhanden (nicht bei Account-Level)
            if '(Übergeordnete) ASIN' in filtered_df.columns:
                display_columns.append('(Übergeordnete) ASIN')
            if '(Untergeordnete) ASIN' in filtered_df.columns:
                display_columns.append('(Untergeordnete) ASIN')
            if 'Titel' in filtered_df.columns:
                display_columns.append('Titel')
            
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

