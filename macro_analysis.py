from fredapi import Fred
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys

# API Key provided by user
FRED_API_KEY = '10b52d62b316f7f27fd58a6111c80adf'

def fetch_macro_data(api_key):
    print("Fetching Macroeconomic Data from FRED...")
    fred = Fred(api_key=api_key)
    
    # Key Economic Indicators
    indicators = {
        'FEDFUNDS': 'Federal Funds Rate (Interest Rate)',
        'CPIAUCSL': 'CPI (Inflation)',
        'M2SL': 'M2 Money Supply',
        'UNRATE': 'Unemployment Rate',
        'GDPC1': 'Real GDP'
    }
    
    macro_data = {}
    latest_values = {}
    
    for series_id, name in indicators.items():
        try:
            # Fetch last 5 years of data
            series = fred.get_series(series_id, observation_start='2021-01-01')
            macro_data[name] = series
            
            # Get latest value and date
            latest_date = series.index[-1]
            latest_val = series.iloc[-1]
            
            # Calculate YoY change for context
            try:
                year_ago_val = series.asof(latest_date - timedelta(days=365))
                yoy_change = ((latest_val - year_ago_val) / year_ago_val) * 100
            except:
                yoy_change = 0
                
            latest_values[name] = {
                'Current': latest_val,
                'Date': latest_date.strftime('%Y-%m-%d'),
                'YoY Change': f"{yoy_change:+.2f}%"
            }
            print(f"✓ {name}: {latest_val:.2f} (YoY: {yoy_change:+.2f}%)")
            
        except Exception as e:
            print(f"✗ Failed to fetch {name}: {e}")
            
    return latest_values

def analyze_investment_environment(macro_values):
    print("\n" + "="*50)
    print("MACRO-BASED INVESTMENT ANALYSIS (ARK THEMES)")
    print("="*50)
    
    # 1. Interest Rate Analysis (FEDFUNDS)
    rate = macro_values.get('Federal Funds Rate (Interest Rate)', {}).get('Current', 0)
    print(f"\n[1] Interest Rate Environment (Current: {rate:.2f}%)")
    if rate > 4.0:
        print("  → HIGH RATES: Headwind for unprofitable growth stocks (Biotech, early-stage Tech).")
        print("  → STRATEGY: Focus on 'Cash Rich' & 'High Margin' companies (Nvidia, Microsoft, Google).")
        print("  → ARK THEME IMPACT: Multiomics & Small Caps may face funding pressure.")
    elif rate < 2.0:
        print("  → LOW RATES: Tailwind for high-growth innovation.")
        print("  → STRATEGY: Aggressive allocation to disruptive tech (Tesla, CRISPR, Bitcoin).")
    else:
        print("  → NEUTRAL RATES: Balanced environment.")

    # 2. Money Supply Analysis (M2)
    m2_change = float(macro_values.get('M2 Money Supply', {}).get('YoY Change', '0%').strip('%'))
    print(f"\n[2] Liquidity & Money Supply (M2 YoY: {m2_change:+.2f}%)")
    if m2_change > 0:
        print("  → EXPANDING LIQUIDITY: Historically positive for Bitcoin and scarce assets.")
        print("  → ARK THEME IMPACT: Bitcoin & Digital Assets strongly favored.")
    else:
        print("  → CONTRACTING LIQUIDITY: Risk-off environment favored.")

    # 3. Inflation Analysis (CPI)
    cpi_change = float(macro_values.get('CPI (Inflation)', {}).get('YoY Change', '0%').strip('%'))
    print(f"\n[3] Inflation Trend (CPI YoY: {cpi_change:+.2f}%)")
    if cpi_change > 3.0:
        print("  → HIGH INFLATION: Pricing power is key.")
        print("  → ARK THEME IMPACT: Automation/Robotics (deflationary force) becomes essential for cost cutting.")
        print("  → STOCK PICK: Amazon (Robotics), Tesla (Manufacturing efficiency).")
    
    # 4. Economic Growth (GDP)
    gdp_change = float(macro_values.get('Real GDP', {}).get('YoY Change', '0%').strip('%'))
    print(f"\n[4] Economic Growth (Real GDP YoY: {gdp_change:+.2f}%)")
    if gdp_change > 0:
        print("  → GROWING ECONOMY: Supportive for cyclical tech (Semiconductors, Consumer AI).")
    else:
        print("  → RECESSION RISK: Defensive tech and essential infrastructure preferred.")

if __name__ == "__main__":
    try:
        data = fetch_macro_data(FRED_API_KEY)
        analyze_investment_environment(data)
    except Exception as e:
        print(f"Error: {e}")
