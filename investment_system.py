import yfinance as yf
from fredapi import Fred
from alpha_vantage.techindicators import TechIndicators
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# --- Configuration ---
FRED_API_KEY = os.environ.get('FRED_API_KEY', '10b52d62b316f7f27fd58a6111c80adf')
ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY', 'KSMIL9TPZGEV07TP')

# --- 1. Date & Context ---
def get_current_context():
    today = datetime.now()
    return {
        'date': today.strftime('%Y-%m-%d'),
        'year': today.year,
        'quarter': (today.month - 1) // 3 + 1
    }

# --- 2. Macro Analysis (FRED) ---
def analyze_macro(api_key):
    try:
        fred = Fred(api_key=api_key)
        # Key indicators: Interest Rate, M2 Money Supply, CPI, GDP
        fed_funds = fred.get_series('FEDFUNDS', observation_start='2025-01-01').iloc[-1]
        m2 = fred.get_series('M2SL', observation_start='2025-01-01').iloc[-1]
        cpi = fred.get_series('CPIAUCSL', observation_start='2025-01-01').iloc[-1]
        
        # Simple logic for investment stance
        stance = "NEUTRAL"
        if fed_funds < 2.5: stance = "AGGRESSIVE GROWTH"
        elif fed_funds > 4.5: stance = "DEFENSIVE / CASH RICH"
        else: stance = "BALANCED GROWTH"
        
        return {
            'fed_funds_rate': fed_funds,
            'm2_supply': m2,
            'cpi': cpi,
            'macro_stance': stance
        }
    except Exception as e:
        return {'error': str(e)}

# --- 3. Market Data (Yahoo Finance) ---
def analyze_stock(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Calculate Moat Metrics (High Margin, High Growth)
        gross_margin = info.get('grossMargins', 0)
        rev_growth = info.get('revenueGrowth', 0)
        
        moat_score = 0
        if gross_margin > 0.5: moat_score += 1 # High margin = Pricing power
        if rev_growth > 0.2: moat_score += 1   # High growth = Market expansion
        
        return {
            'price': info.get('currentPrice'),
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'revenue_growth': rev_growth,
            'gross_margins': gross_margin,
            'moat_score': moat_score
        }
    except Exception as e:
        return {'error': str(e)}

# --- 4. ARK Big Ideas Logic (Hardcoded for now, can be dynamic) ---
def apply_ark_logic(ticker, macro_data):
    # Logic mapping based on Big Ideas 2026 themes
    themes = {
        'TSLA': {'theme': 'Autonomous/Robotics', 'sensitivity': 'High'},
        'NVDA': {'theme': 'AI Infrastructure', 'sensitivity': 'Medium'},
        'COIN': {'theme': 'Digital Assets', 'sensitivity': 'High'},
        'CRSP': {'theme': 'Multiomics', 'sensitivity': 'High'},
        'RKLB': {'theme': 'Space', 'sensitivity': 'High'}
    }
    
    if ticker not in themes:
        return "Theme not found in ARK Big Ideas 2026"
        
    theme_info = themes[ticker]
    macro_stance = macro_data.get('macro_stance', 'NEUTRAL')
    
    recommendation = "HOLD"
    if macro_stance == "AGGRESSIVE GROWTH" and theme_info['sensitivity'] == 'High':
        recommendation = "STRONG BUY (DCA)"
    elif macro_stance == "BALANCED GROWTH":
        recommendation = "BUY (DCA)"
    elif macro_stance == "DEFENSIVE" and theme_info['sensitivity'] == 'High':
        recommendation = "CAUTIOUS HOLD / DIP BUY"
        
    return {
        'ark_theme': theme_info['theme'],
        'recommendation': recommendation
    }

# --- Main Execution ---
def generate_investment_report(tickers):
    context = get_current_context()
    print(f"--- Investment Analysis Report ({context['date']}) ---")
    
    # 1. Macro
    macro = analyze_macro(FRED_API_KEY)
    print(f"\n[Macro Environment]")
    print(f"Fed Rate: {macro.get('fed_funds_rate', 'N/A')}%")
    print(f"Strategy Stance: {macro.get('macro_stance', 'N/A')}")
    
    print(f"\n[Stock Analysis]")
    for ticker in tickers:
        stock_data = analyze_stock(ticker)
        ark_analysis = apply_ark_logic(ticker, macro)
        
        print(f"\n> {ticker}")
        print(f"  Price: ${stock_data.get('price', 'N/A')}")
        print(f"  Moat Score (Margin+Growth): {stock_data.get('moat_score', 0)}/2")
        print(f"  ARK Theme: {ark_analysis.get('ark_theme')}")
        print(f"  Action: {ark_analysis.get('recommendation')}")

if __name__ == "__main__":
    # Example Portfolio
    target_tickers = ['TSLA', 'NVDA', 'COIN', 'CRSP', 'RKLB']
    generate_investment_report(target_tickers)
