import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import plotly.graph_objects as go
import os

# --- Configuration ---
st.set_page_config(page_title="Weekly DCA Report", layout="wide", initial_sidebar_state="collapsed")

# Get API Key from Environment Variable (Best Practice for Vercel)
# If not found, try to use the hardcoded one (fallback) or show warning
FRED_API_KEY = os.environ.get('FRED_API_KEY')
if not FRED_API_KEY:
    # Fallback for local testing if env var not set, but warn user
    FRED_API_KEY = '10b52d62b316f7f27fd58a6111c80adf' 
    # In production, it's better not to hardcode keys in code.
    # On Vercel, you will set FRED_API_KEY in the Environment Variables settings.

# --- 1. Data Fetching Functions ---
@st.cache_data(ttl=3600) # Cache data for 1 hour
def get_macro_data():
    if not FRED_API_KEY:
        return 3.72, 4.6 # Mock data if no key
        
    try:
        fred = Fred(api_key=FRED_API_KEY)
        # Fetch latest available data (with a buffer for reporting lag)
        fed_funds = fred.get_series('FEDFUNDS', observation_start='2024-01-01').iloc[-1]
        m2 = fred.get_series('M2SL', observation_start='2024-01-01').iloc[-1]
        last_m2 = fred.get_series('M2SL', observation_start='2023-01-01').iloc[-13] # YoY comparison
        m2_growth = ((m2 - last_m2) / last_m2) * 100
        return fed_funds, m2_growth
    except Exception as e:
        st.error(f"Error fetching macro data: {e}")
        return 3.72, 4.6 # Fallback to last known values

def get_stock_data(tickers):
    data = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            # Use fast_info if available or fallback to info (slower)
            # yfinance recent versions use fast_info for price
            price = stock.fast_info.last_price
            
            # Get history for RSI
            hist = stock.history(period="2mo") # Need enough data for 14d RSI
            
            if len(hist) > 14:
                # Calculate RSI
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                rsi = 50 # Default if not enough data
            
            # Get 52w high from info (might be slower, can optimize later)
            # For speed in Vercel (serverless), we might want to skip heavy 'info' calls if possible
            # But let's try to get it.
            info = stock.info
            high_52 = info.get('fiftyTwoWeekHigh', price)
            
            # Moat Logic (Simplified for demo)
            moat_score = "Strong"
            if info.get('grossMargins', 0) < 0.4 and info.get('revenueGrowth', 0) < 0.1:
                moat_score = "Watch"
                
            data.append({
                "Ticker": t,
                "Price": price,
                "RSI": round(rsi, 2),
                "Moat Status": moat_score,
                "52W High": high_52,
                "Drawdown": round((price - high_52) / high_52 * 100, 2)
            })
        except Exception as e:
            st.warning(f"Could not fetch data for {t}: {e}")
            
    return pd.DataFrame(data)

# --- Password Protection ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "7929":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password / 비밀번호", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error.
        st.text_input(
            "Password / 비밀번호", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect / 비밀번호가 틀렸습니다")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()  # Do not continue if password is not correct.

# --- Language Settings ---
lang = st.sidebar.radio("Language / 언어", ["English", "한국어"])

# Text Dictionary
text = {
    "English": {
        "title": "📅 Weekly DCA Investment Report",
        "date": "Date",
        "strategy": "Strategy: Wide Moat & Long-term Growth",
        "macro_header": "1. Macro Environment (Investment Weather)",
        "fed_rate": "Fed Funds Rate",
        "target_range": "Target Range",
        "m2_growth": "M2 Money Supply (YoY)",
        "liquidity": "Liquidity Trend",
        "stance": "Current Stance",
        "green": "🟢 GREEN (Aggressive)",
        "red": "🔴 RED (Defensive)",
        "yellow": "🟡 YELLOW (Balanced)",
        "portfolio_header": "2. Portfolio Health Check",
        "refresh": "🔄 Refresh Data",
        "fetching": "Fetching latest market data...",
        "insights": "💡 Key Insights",
        "oversold": "Oversold. Strong Buy signal for DCA.",
        "overbought": "Overbought. Consider reducing buy amount this week.",
        "drawdown": "Trading below highs. Good accumulation zone.",
        "calc_header": "3. Smart DCA Calculator",
        "calc_desc": "Based on your monthly budget of **${}** and current market conditions:",
        "buy_more": "BUY MORE (Cheap)",
        "buy_less": "BUY LESS (Expensive)",
        "normal": "NORMAL",
        "footer": "Data Sources: Yahoo Finance, FRED API. This is for informational purposes only."
    },
    "한국어": {
        "title": "📅 주간 DCA 투자 리포트",
        "date": "날짜",
        "strategy": "전략: 확실한 해자(Moat) & 장기 성장",
        "macro_header": "1. 매크로 환경 (투자 날씨)",
        "fed_rate": "연방기금금리",
        "target_range": "목표 범위",
        "m2_growth": "M2 통화량 (전년비)",
        "liquidity": "유동성 추세",
        "stance": "현재 포지션",
        "green": "🟢 초록불 (공격적 투자)",
        "red": "🔴 빨간불 (방어적 투자)",
        "yellow": "🟡 노란불 (균형 투자)",
        "portfolio_header": "2. 포트폴리오 건강 진단",
        "refresh": "🔄 데이터 새로고침",
        "fetching": "최신 시장 데이터를 가져오는 중...",
        "insights": "💡 핵심 인사이트",
        "oversold": "과매도 구간. 강력한 추가 매수 기회입니다.",
        "overbought": "과매수 구간. 이번 주 매수량을 줄이는 것을 고려하세요.",
        "drawdown": "고점 대비 하락 중. 장기 적립하기 좋은 구간입니다.",
        "calc_header": "3. 스마트 DCA 계산기",
        "calc_desc": "월 투자금 **${}**와 현재 시장 상황을 반영한 추천 매수액:",
        "buy_more": "더 사세요 (저평가)",
        "buy_less": "덜 사세요 (고평가)",
        "normal": "정량 매수",
        "footer": "데이터 출처: Yahoo Finance, FRED API. 이 정보는 투자 참고용입니다."
    }
}

t = text[lang]

# --- 2. Sidebar: Portfolio Settings ---
st.sidebar.header("💼 My Portfolio Settings")
portfolio_input = {
    "TSLA": st.sidebar.number_input("Tesla (TSLA) Target %", value=30),
    "NVDA": st.sidebar.number_input("Nvidia (NVDA) Target %", value=25),
    "COIN": st.sidebar.number_input("Coinbase (COIN) Target %", value=25),
    "PLTR": st.sidebar.number_input("Palantir (PLTR) Target %", value=10),
    "ISRG": st.sidebar.number_input("Intuitive Surgical (ISRG) Target %", value=10)
}
monthly_investment = st.sidebar.number_input("Monthly DCA Amount ($)", value=1000)

# --- 3. Main Dashboard ---
st.title(t["title"])
st.markdown(f"**{t['date']}:** {datetime.now().strftime('%Y-%m-%d')} | **{t['strategy']}**")

# Section 1: Macro Environment
st.header(t["macro_header"])
fed_rate, m2_growth = get_macro_data()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(t["fed_rate"], f"{fed_rate:.2f}%", t["target_range"])
with col2:
    st.metric(t["m2_growth"], f"+{m2_growth:.2f}%", t["liquidity"])
with col3:
    status = t["green"]
    if fed_rate > 4.5 or m2_growth < 0: status = t["red"]
    elif fed_rate > 3.0: status = t["yellow"]
    st.info(f"**{t['stance']}:** {status}")

# Section 2: Portfolio Health
st.header(t["portfolio_header"])

if st.button(t["refresh"]):
    st.cache_data.clear()

with st.spinner(t["fetching"]):
    df = get_stock_data(portfolio_input.keys())

if not df.empty:
    # Styling
    def color_rsi(val):
        if val > 70: return 'color: red; font-weight: bold'
        elif val < 35: return 'color: green; font-weight: bold'
        return ''

    st.dataframe(df.style.applymap(color_rsi, subset=['RSI'])
                 .format({"Price": "${:.2f}", "52W High": "${:.2f}", "Drawdown": "{:.2f}%"}), 
                 use_container_width=True)

    # Insights Generation
    st.subheader(t["insights"])
    for index, row in df.iterrows():
        ticker = row['Ticker']
        rsi = row['RSI']
        dd = row['Drawdown']
        
        if rsi < 35:
            st.success(f"**{ticker}**: RSI {rsi} - {t['oversold']}")
        elif rsi > 70:
            st.warning(f"**{ticker}**: RSI {rsi} - {t['overbought']}")
        
        if dd < -20:
            st.info(f"**{ticker}**: {dd}% {t['drawdown']}")

    # Section 3: Rebalancing Calculator
    st.header(t["calc_header"])
    st.write(t["calc_desc"].format(monthly_investment))

    rebalance_plan = []
    for ticker, target_pct in portfolio_input.items():
        # Simple logic: Adjust allocation based on RSI (Buy more when cheap)
        # Find RSI for this ticker
        ticker_data = df[df['Ticker'] == ticker]
        if not ticker_data.empty:
            rsi = ticker_data['RSI'].values[0]
            adjusted_weight = target_pct
            
            action = t["normal"]
            if rsi < 40: 
                adjusted_weight *= 1.2 # Buy 20% more if cheap
                action = t["buy_more"]
            elif rsi > 70: 
                adjusted_weight *= 0.8 # Buy 20% less if expensive
                action = t["buy_less"]
            
            # Normalize weights later or just show suggested amount
            amount = monthly_investment * (adjusted_weight / 100)
            
            rebalance_plan.append({
                "Ticker": ticker,
                "Base Target": f"{target_pct}%",
                "RSI": f"{rsi}",
                "Action": action,
                "Suggested Buy ($)": round(amount, 2)
            })

    st.table(pd.DataFrame(rebalance_plan))

else:
    st.error("Failed to load stock data. Please try again later.")

# Footer
st.markdown("---")
st.caption(t["footer"])
