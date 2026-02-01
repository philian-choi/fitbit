import yfinance as yf
import pandas as pd
import sys

# Define the list of tickers based on ARK Big Ideas 2026 report
tickers = [
    # AI Infrastructure & Big Tech
    'NVDA', 'TSLA', 'AMD', 'MSFT', 'GOOGL', 'META', 'AMZN', 'AVGO', 'TSM',
    # Consumer AI & Robotics
    'SHOP', 'UBER', 'TDY', 
    # Bitcoin & Fintech
    'COIN', 'HOOD', 'MSTR', 'SQ', 'PYPL',
    # Multiomics
    'CRSP', 'NTLA', 'BEAM', 'RXRX',
    # Energy & Space
    'OKLO', 'FLNC', 'TMUS', 'VSAT'
]

print(f"Fetching data for {len(tickers)} companies from Yahoo Finance...")
print("-" * 50)

data = []

for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract relevant data points
        name = info.get('shortName', ticker)
        price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        market_cap = info.get('marketCap', 0)
        pe_ratio = info.get('trailingPE', None)
        fwd_pe = info.get('forwardPE', None)
        rev_growth = info.get('revenueGrowth', None)
        fifty_two_high = info.get('fiftyTwoWeekHigh', 0)
        
        # Calculate drawdown from 52w high
        drawdown = 0
        if fifty_two_high and price:
            drawdown = ((price - fifty_two_high) / fifty_two_high) * 100

        # Format large numbers
        market_cap_fmt = f"${market_cap / 1e9:.2f}B" if market_cap else "N/A"
        if market_cap > 1e12:
            market_cap_fmt = f"${market_cap / 1e12:.2f}T"
            
        data.append({
            'Ticker': ticker,
            'Name': name,
            'Price': f"${price:.2f}",
            'Market Cap': market_cap_fmt,
            'P/E (TTM)': f"{pe_ratio:.2f}" if pe_ratio else "N/A",
            'Fwd P/E': f"{fwd_pe:.2f}" if fwd_pe else "N/A",
            'Rev Growth': f"{rev_growth * 100:.1f}%" if rev_growth else "N/A",
            'From 52W High': f"{drawdown:.1f}%"
        })
        print(f"✓ {ticker}")
        
    except Exception as e:
        print(f"✗ {ticker}: {str(e)}")

print("-" * 50)
print("Data fetch complete. Generating table...")

# Create DataFrame and sort by Market Cap (descending) for better readability
# We need to parse the Market Cap string back to numbers for sorting, or just sort by ticker
# Let's keep it simple and just print
df = pd.DataFrame(data)

# Use tabulate for pretty printing if available, otherwise standard string
try:
    from tabulate import tabulate
    print(tabulate(df, headers='keys', tablefmt='github', showindex=False))
except ImportError:
    print(df.to_string(index=False))
