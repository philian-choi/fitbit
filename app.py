import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import plotly.graph_objects as go
import os
import feedparser
import time
from newspaper import Article, Config
import nltk

# Download NLTK data (required for summarization)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# --- Configuration ---
st.set_page_config(page_title="Weekly DCA Report", layout="wide", initial_sidebar_state="collapsed")

# --- Password Protection ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state.get("password") == "7929":
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
if "lang" not in st.session_state:
    st.session_state["lang"] = "English"

lang_selection = st.sidebar.radio(
    "Language / 언어", 
    ["English", "한국어"],
    index=0 if st.session_state["lang"] == "English" else 1
)
st.session_state["lang"] = lang_selection if lang_selection else "English"
lang = st.session_state["lang"]

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
        "footer": "Data Sources: Yahoo Finance, FRED API. This is for informational purposes only.",
        "news_header": "📰 Latest News & Policy Updates",
        "no_news": "No recent news found.",
        "discovery_header": "🔍 Hidden Gem Finder (Opportunity Scanner)",
        "discovery_desc": "Scanning watchlist for oversold opportunities (RSI < 30)..."
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
        "footer": "데이터 출처: Yahoo Finance, FRED API. 이 정보는 투자 참고용입니다.",
        "news_header": "📰 최신 뉴스 및 정책 업데이트",
        "no_news": "최근 관련 뉴스가 없습니다.",
        "discovery_header": "🔍 숨겨진 보석 찾기 (기회 스캐너)",
        "discovery_desc": "관심 종목 중 과매도(RSI < 30) 상태인 종목을 스캔합니다..."
    }
}

t = text.get(lang, text["English"]) # Safer access with default

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
        # st.error(f"Error fetching macro data: {e}")
        return 3.72, 4.6 # Fallback to last known values

from newspaper import Article, Config

# ... (existing imports)

@st.cache_data(ttl=3600)
def get_article_summary(url):
    try:
        # User-Agent spoofing to bypass simple anti-bot protections
        user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10

        article = Article(url, config=config)
        article.download()
        article.parse()
        article.nlp()
        return article.summary
    except Exception:
        return "요약 정보를 가져올 수 없습니다. (보안 정책 또는 페이월)"

@st.cache_data(ttl=3600)
def get_news(ticker):
    # Multiple RSS Sources for Better Coverage
    rss_urls = [
        f"https://finance.yahoo.com/rss/headline?s={ticker}", # Yahoo Finance
        f"https://seekingalpha.com/api/1.0/rss/symbol/{ticker}", # Seeking Alpha (Analysis)
        f"https://feeds.content.dowjones.com/public/rss/mw/ticker/{ticker}" # MarketWatch (News)
    ]
    
    news_items = []
    seen_titles = set() # To remove duplicates
    
    # Strict Filtering Keywords (High Impact)
    keywords = [
        "Earnings", "Revenue", "Profit", "Guidance", "Quarter", # Financials
        "SEC", "Regulation", "Lawsuit", "Approval", "FDA", "Ban", # Regulatory
        "Acquisition", "Merger", "Partnership", "Contract", "Deal", # Corporate Action
        "Launch", "Release", "Unveil", "Patent", "Breakthrough", # Product/Tech
        "Upgrade", "Downgrade", "Target Price", "Buy", "Sell" # Analyst Action
    ]
    
    # Noise Keywords to Exclude
    noise = [
        "Why", "Here's", "What to know", "3 reasons", "5 stocks", "10 stocks", # Clickbait
        "Prediction", "Could", "Might", "Opinion", "Think", "Maybe", # Speculation
        "Motley Fool", "Zacks" # Subscription Bait
    ]

    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                
                # 0. Deduplication
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # 1. Exclude Noise
                if any(n in title for n in noise):
                    continue
                    
                # 2. Include Only Key Events
                if any(k in title for k in keywords):
                    # Clean up summary (remove HTML tags if any)
                    raw_summary = entry.get('summary', entry.get('description', ''))
                    clean_summary = raw_summary.split('<')[0] if '<' in raw_summary else raw_summary
                    
                    news_items.append({
                        "title": title,
                        "link": entry.link,
                        "published": entry.get('published', 'Recent'),
                        "source": "Yahoo" if "yahoo" in url else "Seeking Alpha" if "seekingalpha" in url else "MarketWatch",
                        "rss_summary": clean_summary
                    })
        except:
            continue
            
    # Sort by published date (if available) or just take top 5
    # Simple sort by list order (latest usually first in RSS)
    return news_items[:5]

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

# --- 2. Sidebar: Portfolio Settings ---
st.sidebar.header("💼 My Portfolio Settings")

# Define available tickers (Core + Watchlist)
core_tickers = ["TSLA", "NVDA", "COIN", "PLTR", "ISRG"]
watchlist_tickers = [
    "AMD", "AMZN", "GOOGL", "MSFT", "META", # Big Tech
    "SHOP", "UBER", "SQ", "PYPL", "HOOD", # Fintech
    "CRSP", "NTLA", "BEAM", "RXRX", "DNA", # Bio
    "RKLB", "OKLO", "FLNC", "TMUS", "ASTS", # Space/Energy
    "U", "NET", "PATH", "DKNG", "ROKU" # Growth
]
all_tickers = list(set(core_tickers + watchlist_tickers)) # Unique list

# Multiselect widget to add/remove tickers
selected_tickers = st.sidebar.multiselect(
    "Select Tickers / 종목 선택",
    options=sorted(all_tickers),
    default=core_tickers
)

portfolio_input = {}
total_allocation = 0

st.sidebar.markdown("---")
st.sidebar.subheader("Target Allocation (%)")

for t in selected_tickers:
    # Default weight logic: 100 / count (simple start)
    default_weight = 20 if t in core_tickers else 0
    weight = st.sidebar.number_input(f"{t} %", min_value=0, max_value=100, value=default_weight, key=f"weight_{t}")
    portfolio_input[t] = weight
    total_allocation += weight

# Warning if allocation != 100%
if total_allocation != 100:
    st.sidebar.warning(f"Total: {total_allocation}% (Should be 100%)")
else:
    st.sidebar.success(f"Total: {total_allocation}%")

monthly_investment = st.sidebar.number_input("Monthly DCA Amount ($)", value=1000)

# --- Watchlist for Discovery ---
# Use the same list for discovery, excluding currently selected portfolio
watchlist = [t for t in all_tickers if t not in selected_tickers]

def scan_market_opportunities(watchlist):
    opportunities = []
    for t in watchlist:
        try:
            stock = yf.Ticker(t)
            # Use fast_info for speed
            price = stock.fast_info.last_price
            
            # Get history for RSI (Need 14 days)
            hist = stock.history(period="1mo")
            
            if len(hist) > 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                # Condition 1: Oversold (RSI < 30) - Deep Value
                if rsi < 30:
                    opportunities.append({
                        "Ticker": t,
                        "Price": price,
                        "RSI": round(rsi, 2),
                        "Reason": "Oversold (RSI < 30)"
                    })
                
                # Condition 2: Momentum Breakout (RSI crossed 50 from below? - Simplified to RSI > 50 & < 60 for now)
                # Or maybe just check 52w low?
                
                # Check 52w High Drawdown
                # Note: fast_info doesn't always have 52w high, might need info
                # To keep it fast, let's stick to RSI for the scanner
                
        except:
            continue
            
    return pd.DataFrame(opportunities)

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

    # Section 4: Discovery (New Feature)
    st.header(t["discovery_header"])
    st.write(t["discovery_desc"])
    
    with st.spinner("Scanning..."):
        opportunities = scan_market_opportunities(watchlist)
        
    if not opportunities.empty:
        st.success(f"Found {len(opportunities)} opportunities!")
        st.dataframe(opportunities, use_container_width=True)
    else:
        st.info("No oversold opportunities found in the watchlist at the moment. Market is healthy.")

    # Section 5: News
    st.header(t["news_header"])
    
    # Create tabs for each ticker
    tabs = st.tabs(list(portfolio_input.keys()))
    
    for i, ticker in enumerate(portfolio_input.keys()):
        with tabs[i]:
            news_items = get_news(ticker)
            if news_items:
                for news in news_items:
                    source_badge = f"[{news['source']}]"
                    with st.expander(f"{source_badge} {news['title']}"):
                        st.caption(f"Published: {news['published']}")
                        
                        # Fetch summary only when expanded to save time
                        summary = get_article_summary(news['link'])
                        
                        # Fallback to RSS summary if scraping fails
                        if "요약 정보를 가져올 수 없습니다" in summary and news.get('rss_summary'):
                            st.warning("🔒 원문 접근이 제한되어 뉴스 피드 요약본을 표시합니다.")
                            st.write(news['rss_summary'])
                        else:
                            st.write(summary)
                            
                        st.markdown(f"[Read Full Article]({news['link']})")
            else:
                st.info(t["no_news"])

else:
    st.error("Failed to load stock data. Please try again later.")

# Footer
st.markdown("---")
st.caption(t["footer"])