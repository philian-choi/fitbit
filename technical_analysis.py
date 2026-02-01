from alpha_vantage.techindicators import TechIndicators
from alpha_vantage.timeseries import TimeSeries
import pandas as pd
import time
import sys

# API Key provided by user
ALPHA_VANTAGE_KEY = 'KSMIL9TPZGEV07TP'

# Top picks to analyze for timing (High volatility or key holdings)
tickers = ['NVDA', 'TSLA', 'COIN', 'MSTR', 'HOOD', 'AMZN', 'NTLA']

def fetch_technical_analysis(api_key, tickers):
    print(f"Fetching Technical Indicators (RSI) for {len(tickers)} companies...")
    print("Note: Alpha Vantage free tier has rate limits (5 calls/min). Adding delays.")
    print("-" * 50)
    
    ti = TechIndicators(key=api_key, output_format='pandas')
    ts = TimeSeries(key=api_key, output_format='pandas')
    
    results = []
    
    for i, ticker in enumerate(tickers):
        try:
            # Rate limiting: sleep 12 seconds between calls to be safe (5 calls/60s = 1 call/12s)
            if i > 0:
                print("Waiting for API rate limit...")
                time.sleep(15)
                
            print(f"Analyzing {ticker}...")
            
            # 1. Get RSI (Relative Strength Index) - Daily, Period 14
            data_rsi, meta_rsi = ti.get_rsi(symbol=ticker, interval='daily', time_period=14, series_type='close')
            current_rsi = data_rsi['RSI'].iloc[-1]
            
            # 2. Get SMA (Simple Moving Average) - 50 Day to check trend
            # Note: We might hit rate limits if we do too many calls per ticker. 
            # Let's stick to RSI for now as it's the best "Timing" indicator for overbought/oversold.
            # If we want more, we need to wait more. Let's try to get price relative to 50-day SMA if possible
            # or just use RSI which is sufficient for "Overbought/Oversold" check.
            
            # Interpret RSI
            signal = "NEUTRAL"
            if current_rsi > 70:
                signal = "OVERBOUGHT (Wait)"
            elif current_rsi < 30:
                signal = "OVERSOLD (Buy)"
            elif current_rsi > 60:
                signal = "MOMENTUM STRONG (Cautious Buy)"
            elif current_rsi < 40:
                signal = "WEAKNESS (Accumulate)"
                
            results.append({
                'Ticker': ticker,
                'RSI (14D)': f"{current_rsi:.2f}",
                'Signal': signal
            })
            print(f"✓ {ticker}: RSI {current_rsi:.2f} -> {signal}")
            
        except Exception as e:
            print(f"✗ {ticker}: {e}")
            # If rate limit hit, wait longer and try next
            if "Thank you" in str(e) or "call frequency" in str(e):
                 print("Rate limit hit. Waiting 60 seconds...")
                 time.sleep(60)
    
    return results

if __name__ == "__main__":
    data = fetch_technical_analysis(ALPHA_VANTAGE_KEY, tickers)
    
    print("\n" + "="*50)
    print("TECHNICAL TIMING ANALYSIS (RSI)")
    print("="*50)
    
    df = pd.DataFrame(data)
    try:
        from tabulate import tabulate
        print(tabulate(df, headers='keys', tablefmt='github', showindex=False))
    except ImportError:
        print(df.to_string(index=False))
