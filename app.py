import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import os
import feedparser
from newspaper import Article, Config
import nltk

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# --- Page Config ---
st.set_page_config(
    page_title="투자 도우미", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="💰"
)

# --- Modern CSS ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    
    * {
        font-family: 'Noto Sans KR', sans-serif;
    }
    
    /* Clean layout */
    .main .block-container {
        padding: 1rem 2rem 2rem 2rem;
        max-width: 1200px;
    }
    
    /* Hero section */
    .hero-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    }
    .hero-card h1 {
        font-size: 2.5rem;
        margin: 0;
        font-weight: 700;
    }
    .hero-amount {
        font-size: 4rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        opacity: 0.9;
        margin-top: 0.5rem;
    }
    
    /* Weather badge */
    .weather-badge {
        display: inline-block;
        padding: 0.5rem 1.5rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1rem;
        margin: 0.5rem;
    }
    .weather-sunny {
        background: linear-gradient(135deg, #11998e, #38ef7d);
        color: white;
    }
    .weather-cloudy {
        background: linear-gradient(135deg, #f093fb, #f5576c);
        color: white;
    }
    .weather-rainy {
        background: linear-gradient(135deg, #4facfe, #00f2fe);
        color: white;
    }
    
    /* Stock cards */
    .stock-card {
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border: 1px solid #eee;
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stock-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
    }
    .stock-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
    }
    .stock-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
    }
    .stock-ticker {
        font-size: 0.85rem;
        color: #666;
        background: #f5f5f5;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }
    .stock-price {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1a1a2e;
    }
    .stock-change {
        font-size: 0.9rem;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
    }
    .change-up { background: #e8f5e9; color: #2e7d32; }
    .change-down { background: #ffebee; color: #c62828; }
    
    /* RSI bar */
    .rsi-container {
        margin-top: 0.8rem;
    }
    .rsi-bar {
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(to right, #38ef7d 0%, #38ef7d 30%, #ffd93d 30%, #ffd93d 70%, #ff6b6b 70%, #ff6b6b 100%);
        position: relative;
        margin: 0.5rem 0;
    }
    .rsi-marker {
        position: absolute;
        top: -4px;
        width: 16px;
        height: 16px;
        background: #1a1a2e;
        border-radius: 50%;
        border: 2px solid white;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        transform: translateX(-50%);
    }
    .rsi-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #888;
    }
    
    /* Action badge */
    .action-badge {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .action-buy { background: #e8f5e9; color: #2e7d32; }
    .action-sell { background: #ffebee; color: #c62828; }
    .action-hold { background: #f5f5f5; color: #666; }
    
    /* Section headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #eee;
    }
    
    /* Info tooltip */
    .info-tip {
        background: #f8f9fa;
        border-left: 4px solid #3a7bd5;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        color: #555;
        margin: 0.5rem 0;
    }
    
    /* Quick stats */
    .quick-stat {
        text-align: center;
        padding: 1rem;
    }
    .quick-stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
    }
    .quick-stat-label {
        font-size: 0.85rem;
        color: #888;
        margin-top: 0.3rem;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Better buttons */
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1.5rem;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Language ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "한국어"

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ 설정")
    lang = st.radio("언어", ["한국어", "English"], index=0)
    st.session_state["lang"] = lang
    
lang = st.session_state["lang"]
is_kr = lang == "한국어"

# --- Company Data ---
company_info = {
    "TSLA": {"name": "Tesla", "emoji": "🚗", "kr": "전기차 1위. 전기차, 에너지 저장, 태양광", "en": "#1 EV maker. Electric vehicles, energy storage, solar", "sector": "전기차" if is_kr else "EV"},
    "NVDA": {"name": "NVIDIA", "emoji": "🎮", "kr": "AI 반도체 1위. AI 학습용 GPU 칩", "en": "#1 AI chips. GPUs for AI training", "sector": "반도체" if is_kr else "Chips"},
    "COIN": {"name": "Coinbase", "emoji": "🪙", "kr": "미국 최대 암호화폐 거래소", "en": "Largest US crypto exchange", "sector": "암호화폐" if is_kr else "Crypto"},
    "PLTR": {"name": "Palantir", "emoji": "🔍", "kr": "빅데이터 분석 소프트웨어", "en": "Big data analytics software", "sector": "소프트웨어" if is_kr else "Software"},
    "ISRG": {"name": "Intuitive Surgical", "emoji": "🏥", "kr": "수술 로봇 1위 (다빈치)", "en": "#1 surgical robotics (da Vinci)", "sector": "의료" if is_kr else "Medical"},
    "AMD": {"name": "AMD", "emoji": "💻", "kr": "CPU/GPU 제조 (인텔 경쟁사)", "en": "CPU/GPU maker (Intel competitor)", "sector": "반도체" if is_kr else "Chips"},
    "AMZN": {"name": "Amazon", "emoji": "📦", "kr": "이커머스 + 클라우드(AWS) 1위", "en": "#1 e-commerce + cloud (AWS)", "sector": "이커머스" if is_kr else "E-commerce"},
    "GOOGL": {"name": "Google", "emoji": "🔎", "kr": "검색 1위. 광고, 유튜브, 클라우드", "en": "#1 search. Ads, YouTube, cloud", "sector": "광고" if is_kr else "Ads"},
    "MSFT": {"name": "Microsoft", "emoji": "🪟", "kr": "윈도우, 오피스, Azure 클라우드", "en": "Windows, Office, Azure cloud", "sector": "소프트웨어" if is_kr else "Software"},
    "META": {"name": "Meta", "emoji": "👥", "kr": "페이스북, 인스타그램, 왓츠앱", "en": "Facebook, Instagram, WhatsApp", "sector": "SNS" if is_kr else "Social"},
    "SHOP": {"name": "Shopify", "emoji": "🛒", "kr": "온라인 쇼핑몰 구축 플랫폼", "en": "E-commerce platform builder", "sector": "이커머스" if is_kr else "E-commerce"},
    "UBER": {"name": "Uber", "emoji": "🚕", "kr": "차량 공유 + 음식 배달", "en": "Ride-sharing + food delivery", "sector": "모빌리티" if is_kr else "Mobility"},
    "SQ": {"name": "Block", "emoji": "💳", "kr": "결제 서비스 + 캐시앱", "en": "Payment services + Cash App", "sector": "핀테크" if is_kr else "Fintech"},
    "PYPL": {"name": "PayPal", "emoji": "💰", "kr": "온라인 결제 (벤모 포함)", "en": "Online payments (incl. Venmo)", "sector": "핀테크" if is_kr else "Fintech"},
    "HOOD": {"name": "Robinhood", "emoji": "📱", "kr": "무료 주식거래 앱", "en": "Commission-free trading app", "sector": "핀테크" if is_kr else "Fintech"},
    "CRSP": {"name": "CRISPR", "emoji": "🧬", "kr": "유전자 가위 치료제 개발", "en": "Gene editing therapeutics", "sector": "바이오" if is_kr else "Biotech"},
    "RKLB": {"name": "Rocket Lab", "emoji": "🚀", "kr": "소형 로켓 발사 서비스", "en": "Small rocket launch service", "sector": "우주" if is_kr else "Space"},
    "OKLO": {"name": "Oklo", "emoji": "⚛️", "kr": "소형 원자로 개발", "en": "Small nuclear reactors", "sector": "에너지" if is_kr else "Energy"},
    "NET": {"name": "Cloudflare", "emoji": "☁️", "kr": "인터넷 보안/성능 서비스", "en": "Internet security/performance", "sector": "클라우드" if is_kr else "Cloud"},
}

core_tickers = ["TSLA", "NVDA", "COIN", "PLTR", "ISRG"]
watchlist_tickers = ["AMD", "AMZN", "GOOGL", "MSFT", "META", "SHOP", "UBER", "SQ", "PYPL", "HOOD", "CRSP", "RKLB", "OKLO", "NET"]
all_tickers = list(set(core_tickers + watchlist_tickers))

# --- API Keys ---
FRED_API_KEY = os.environ.get('FRED_API_KEY', '10b52d62b316f7f27fd58a6111c80adf')

# --- Data Functions ---
@st.cache_data(ttl=3600)
def get_macro_data():
    try:
        fred = Fred(api_key=FRED_API_KEY)
        fed_funds = fred.get_series('FEDFUNDS', observation_start='2024-01-01').iloc[-1]
        m2 = fred.get_series('M2SL', observation_start='2024-01-01').iloc[-1]
        last_m2 = fred.get_series('M2SL', observation_start='2023-01-01').iloc[-13]
        m2_growth = ((m2 - last_m2) / last_m2) * 100
        return fed_funds, m2_growth
    except:
        return 4.33, 3.5

@st.cache_data(ttl=1800)
def get_stock_data(tickers):
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            price = stock.fast_info.last_price
            hist = stock.history(period="2mo")
            
            if len(hist) > 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                rsi = 50
            
            info = stock.info
            high_52 = info.get('fiftyTwoWeekHigh', price)
            drawdown = ((price - high_52) / high_52) * 100
            
            company = company_info.get(ticker, {"name": ticker, "emoji": "📈", "kr": "", "en": "", "sector": ""})
            
            data.append({
                "ticker": ticker,
                "name": company["name"],
                "emoji": company["emoji"],
                "desc": company["kr"] if is_kr else company["en"],
                "sector": company["sector"],
                "price": price,
                "rsi": round(rsi, 1),
                "drawdown": round(drawdown, 1),
                "high_52": high_52
            })
        except Exception as e:
            continue
    return data

# --- Sidebar Settings ---
with st.sidebar:
    st.markdown("---")
    st.subheader("📊 포트폴리오" if is_kr else "📊 Portfolio")
    
    selected_tickers = st.multiselect(
        "종목 선택" if is_kr else "Select Stocks",
        options=sorted(all_tickers),
        default=core_tickers,
        format_func=lambda x: f"{company_info.get(x, {}).get('emoji', '')} {x}"
    )
    
    st.markdown("---")
    monthly_budget = st.number_input(
        "💵 월 투자금 ($)" if is_kr else "💵 Monthly Budget ($)",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100
    )
    
    # Simple equal weight allocation
    if selected_tickers:
        weight_per_stock = 100 // len(selected_tickers)
        portfolio_weights = {t: weight_per_stock for t in selected_tickers}
    else:
        portfolio_weights = {}

# --- Main Content ---

# Get data
fed_rate, m2_growth = get_macro_data()
stock_data = get_stock_data(selected_tickers) if selected_tickers else []

# Determine market weather
if fed_rate > 4.5 or m2_growth < 0:
    weather = "rainy"
    weather_text = "🌧️ 조심" if is_kr else "🌧️ Caution"
    weather_desc = "금리가 높아요. 신중하게 투자하세요." if is_kr else "High rates. Invest carefully."
elif fed_rate > 3.5:
    weather = "cloudy"
    weather_text = "⛅ 보통" if is_kr else "⛅ Normal"
    weather_desc = "평소대로 투자하세요." if is_kr else "Continue regular investing."
else:
    weather = "sunny"
    weather_text = "☀️ 좋음" if is_kr else "☀️ Good"
    weather_desc = "투자하기 좋은 환경이에요!" if is_kr else "Good environment for investing!"

# Calculate total suggested investment
total_suggested = 0
buy_recommendations = []

for stock in stock_data:
    weight = portfolio_weights.get(stock["ticker"], 0)
    base_amount = monthly_budget * (weight / 100)
    
    # Adjust based on RSI
    if stock["rsi"] < 35:
        multiplier = 1.3
        action = "buy"
    elif stock["rsi"] > 70:
        multiplier = 0.7
        action = "sell"
    else:
        multiplier = 1.0
        action = "hold"
    
    suggested = base_amount * multiplier
    total_suggested += suggested
    
    buy_recommendations.append({
        **stock,
        "base_amount": base_amount,
        "suggested": suggested,
        "action": action
    })

# === HERO SECTION ===
st.markdown(f"""
<div class="hero-card">
    <h1>{"💰 이번 주 투자 금액" if is_kr else "💰 This Week's Investment"}</h1>
    <div class="hero-amount">${total_suggested:,.0f}</div>
    <div>
        <span class="weather-badge weather-{weather}">{weather_text}</span>
    </div>
    <p class="hero-subtitle">{weather_desc}</p>
</div>
""", unsafe_allow_html=True)

# === QUICK STATS ===
col1, col2, col3, col4 = st.columns(4)

oversold_count = len([s for s in stock_data if s["rsi"] < 35])
overbought_count = len([s for s in stock_data if s["rsi"] > 70])

with col1:
    st.markdown(f"""
    <div class="quick-stat">
        <div class="quick-stat-value">{len(stock_data)}</div>
        <div class="quick-stat-label">{"보유 종목" if is_kr else "Stocks"}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="quick-stat">
        <div class="quick-stat-value" style="color: #2e7d32;">{oversold_count}</div>
        <div class="quick-stat-label">{"🟢 세일 중" if is_kr else "🟢 On Sale"}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="quick-stat">
        <div class="quick-stat-value" style="color: #c62828;">{overbought_count}</div>
        <div class="quick-stat-label">{"🔴 비쌈" if is_kr else "🔴 Expensive"}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="quick-stat">
        <div class="quick-stat-value">{fed_rate:.1f}%</div>
        <div class="quick-stat-label">{"기준금리" if is_kr else "Fed Rate"}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# === MAIN TABS ===
tab1, tab2, tab3 = st.tabs([
    "📊 " + ("매수 계획" if is_kr else "Buy Plan"),
    "💼 " + ("종목 상세" if is_kr else "Stock Details"),
    "🔍 " + ("세일 찾기" if is_kr else "Find Sales")
])

# --- TAB 1: Buy Plan ---
with tab1:
    st.markdown(f'<div class="section-header">{"🧮 이번 주 매수 계획" if is_kr else "🧮 This Week\'s Buy Plan"}</div>', unsafe_allow_html=True)
    
    if buy_recommendations:
        # Sort by action priority (buy first)
        sorted_recs = sorted(buy_recommendations, key=lambda x: (x["action"] != "buy", x["action"] != "hold"))
        
        for rec in sorted_recs:
            action_class = f"action-{rec['action']}"
            action_text = {
                "buy": "🟢 더 사세요" if is_kr else "🟢 BUY MORE",
                "sell": "🔴 덜 사세요" if is_kr else "🔴 BUY LESS",
                "hold": "⚪ 평소대로" if is_kr else "⚪ NORMAL"
            }[rec["action"]]
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.markdown(f"**{rec['emoji']} {rec['name']}** `{rec['ticker']}`")
                st.caption(rec['desc'])
            
            with col2:
                st.metric("RSI", f"{rec['rsi']:.0f}", 
                         delta="세일!" if rec['rsi'] < 35 else ("비쌈" if rec['rsi'] > 70 else None),
                         delta_color="normal" if rec['rsi'] < 35 else "inverse")
            
            with col3:
                st.markdown(f"<span class='action-badge {action_class}'>{action_text}</span>", unsafe_allow_html=True)
            
            with col4:
                st.metric("매수액" if is_kr else "Buy", f"${rec['suggested']:.0f}")
            
            st.markdown("---")
    else:
        st.info("사이드바에서 종목을 선택하세요." if is_kr else "Select stocks in the sidebar.")

# --- TAB 2: Stock Details ---
with tab2:
    st.markdown(f'<div class="section-header">{"💼 종목 상세 정보" if is_kr else "💼 Stock Details"}</div>', unsafe_allow_html=True)
    
    if stock_data:
        cols = st.columns(2)
        
        for idx, stock in enumerate(stock_data):
            with cols[idx % 2]:
                # RSI status
                if stock["rsi"] < 30:
                    rsi_status = "🟢 세일!" if is_kr else "🟢 On Sale!"
                    rsi_color = "#2e7d32"
                elif stock["rsi"] > 70:
                    rsi_status = "🔴 비쌈" if is_kr else "🔴 Expensive"
                    rsi_color = "#c62828"
                else:
                    rsi_status = "⚪ 적정가" if is_kr else "⚪ Fair"
                    rsi_color = "#666"
                
                # Drawdown badge
                dd_class = "change-up" if stock["drawdown"] > -10 else "change-down"
                
                st.markdown(f"""
                <div class="stock-card">
                    <div class="stock-header">
                        <span class="stock-name">{stock['emoji']} {stock['name']}</span>
                        <span class="stock-ticker">{stock['ticker']}</span>
                    </div>
                    <div style="color: #888; font-size: 0.85rem; margin-bottom: 0.8rem;">{stock['desc']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="stock-price">${stock['price']:.2f}</span>
                        <span class="stock-change {dd_class}">고점대비 {stock['drawdown']:.1f}%</span>
                    </div>
                    <div class="rsi-container">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.85rem; color: #888;">RSI: {stock['rsi']:.0f}</span>
                            <span style="font-size: 0.85rem; color: {rsi_color}; font-weight: 600;">{rsi_status}</span>
                        </div>
                        <div class="rsi-bar">
                            <div class="rsi-marker" style="left: {stock['rsi']}%;"></div>
                        </div>
                        <div class="rsi-labels">
                            <span>{"세일" if is_kr else "Sale"}</span>
                            <span>{"적정" if is_kr else "Fair"}</span>
                            <span>{"비쌈" if is_kr else "High"}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("사이드바에서 종목을 선택하세요." if is_kr else "Select stocks in the sidebar.")

# --- TAB 3: Find Sales ---
with tab3:
    st.markdown(f'<div class="section-header">{"🔍 관심 종목 중 세일 찾기" if is_kr else "🔍 Find Sales in Watchlist"}</div>', unsafe_allow_html=True)
    
    # Scan watchlist for opportunities
    watchlist_to_scan = [t for t in all_tickers if t not in selected_tickers]
    
    if watchlist_to_scan:
        with st.spinner("스캔 중..." if is_kr else "Scanning..."):
            watchlist_data = get_stock_data(watchlist_to_scan)
            sales = [s for s in watchlist_data if s["rsi"] < 35]
        
        if sales:
            st.success(f"{'🎉 ' + str(len(sales)) + '개 종목이 세일 중!' if is_kr else '🎉 ' + str(len(sales)) + ' stocks on sale!'}")
            
            for stock in sorted(sales, key=lambda x: x["rsi"]):
                col1, col2, col3 = st.columns([4, 2, 2])
                
                with col1:
                    st.markdown(f"**{stock['emoji']} {stock['name']}** `{stock['ticker']}`")
                    st.caption(stock['desc'])
                
                with col2:
                    st.metric("RSI", f"{stock['rsi']:.0f}", delta="세일!" if is_kr else "Sale!")
                
                with col3:
                    st.metric("가격" if is_kr else "Price", f"${stock['price']:.2f}")
                
                st.markdown("---")
        else:
            st.info("지금은 세일 중인 종목이 없어요. 시장이 적정 가격이에요." if is_kr else "No stocks on sale right now. Market is fairly priced.")
    else:
        st.info("모든 종목이 이미 포트폴리오에 있어요." if is_kr else "All stocks are already in your portfolio.")

# === FOOTER ===
st.markdown("---")

# Help section
with st.expander("❓ " + ("도움말: RSI가 뭐예요?" if is_kr else "Help: What is RSI?")):
    st.markdown(f"""
    <div class="info-tip">
    <strong>RSI (상대강도지수)</strong>{"는 주식이 '세일 중'인지 '비싼지' 알려주는 지표예요." if is_kr else " tells you if a stock is 'on sale' or 'expensive'."}
    <br><br>
    • <strong style="color: #2e7d32;">RSI 30 이하</strong>: {"세일 중! 🟢 더 사기 좋은 타이밍" if is_kr else "On sale! 🟢 Good time to buy more"}
    <br>
    • <strong>RSI 30-70</strong>: {"적정 가격 ⚪ 평소대로 투자" if is_kr else "Fair price ⚪ Normal investing"}
    <br>
    • <strong style="color: #c62828;">RSI 70 이상</strong>: {"비쌈! 🔴 덜 사는 게 좋아요" if is_kr else "Expensive! 🔴 Consider buying less"}
    </div>
    """, unsafe_allow_html=True)

st.caption("📊 " + ("데이터: Yahoo Finance, FRED | 투자 조언이 아닙니다" if is_kr else "Data: Yahoo Finance, FRED | Not financial advice"))
