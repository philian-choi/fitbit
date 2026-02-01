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
    page_icon="$"
)

# --- SVG Icons (Lucide-style) ---
ICONS = {
    "dollar": '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>',
    "trending_up": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>',
    "trending_down": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"></polyline><polyline points="17 18 23 18 23 12"></polyline></svg>',
    "sun": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
    "cloud": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"></path></svg>',
    "cloud_rain": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="16" y1="13" x2="16" y2="21"></line><line x1="8" y1="13" x2="8" y2="21"></line><line x1="12" y1="15" x2="12" y2="23"></line><path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"></path></svg>',
    "settings": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
    "bar_chart": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"></line><line x1="18" y1="20" x2="18" y2="4"></line><line x1="6" y1="20" x2="6" y2="16"></line></svg>',
    "briefcase": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg>',
    "search": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
    "help": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "x": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
    "minus": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
}

# --- Modern CSS (Dark Mode Compatible) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    
    * { font-family: 'Noto Sans KR', sans-serif; }
    
    .main .block-container {
        padding: 1rem 2rem 2rem 2rem;
        max-width: 1200px;
    }
    
    /* Hero section - works on both light/dark */
    .hero-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 50%, #1e40af 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white !important;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    .hero-card h1 {
        font-size: 1.5rem;
        margin: 0;
        font-weight: 500;
        color: rgba(255,255,255,0.9) !important;
    }
    .hero-amount {
        font-size: 4rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0.5rem 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    .hero-subtitle {
        font-size: 1rem;
        color: rgba(255,255,255,0.85) !important;
        margin-top: 0.5rem;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 0.5rem 1.2rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.5rem;
    }
    .status-good { background: #10b981; color: white !important; }
    .status-normal { background: #f59e0b; color: white !important; }
    .status-caution { background: #8b5cf6; color: white !important; }
    
    /* Stock cards - dark mode compatible */
    .stock-card {
        background: rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 1rem;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stock-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        background: rgba(255,255,255,0.08);
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
        color: #e2e8f0 !important;
    }
    .stock-ticker {
        font-size: 0.85rem;
        color: #94a3b8 !important;
        background: rgba(255,255,255,0.1);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
    }
    .stock-price {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f1f5f9 !important;
    }
    .stock-change {
        font-size: 0.9rem;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
    }
    .change-up { background: rgba(16, 185, 129, 0.2); color: #34d399 !important; }
    .change-down { background: rgba(239, 68, 68, 0.2); color: #f87171 !important; }
    .stock-desc {
        color: #94a3b8 !important;
        font-size: 0.85rem;
        margin-bottom: 0.8rem;
    }
    
    /* RSI bar */
    .rsi-container { margin-top: 0.8rem; }
    .rsi-bar {
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(to right, #10b981 0%, #10b981 30%, #fbbf24 30%, #fbbf24 70%, #ef4444 70%, #ef4444 100%);
        position: relative;
        margin: 0.5rem 0;
    }
    .rsi-marker {
        position: absolute;
        top: -4px;
        width: 16px;
        height: 16px;
        background: #ffffff;
        border-radius: 50%;
        border: 3px solid #1e40af;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        transform: translateX(-50%);
    }
    .rsi-labels {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        color: #94a3b8 !important;
    }
    .rsi-info {
        font-size: 0.85rem;
        color: #94a3b8 !important;
    }
    .rsi-status {
        font-size: 0.85rem;
        font-weight: 600;
    }
    .rsi-status-sale { color: #34d399 !important; }
    .rsi-status-fair { color: #94a3b8 !important; }
    .rsi-status-high { color: #f87171 !important; }
    
    /* Action badge */
    .action-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .action-buy { background: rgba(16, 185, 129, 0.2); color: #34d399 !important; }
    .action-sell { background: rgba(239, 68, 68, 0.2); color: #f87171 !important; }
    .action-hold { background: rgba(148, 163, 184, 0.2); color: #94a3b8 !important; }
    
    /* Section headers */
    .section-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #e2e8f0 !important;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid rgba(255,255,255,0.1);
    }
    
    /* Info box */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border-left: 4px solid #3b82f6;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.9rem;
        color: #cbd5e1 !important;
        margin: 0.5rem 0;
    }
    
    /* Quick stats */
    .quick-stat {
        text-align: center;
        padding: 1rem;
        background: rgba(255,255,255,0.03);
        border-radius: 12px;
    }
    .quick-stat-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #f1f5f9 !important;
    }
    .quick-stat-label {
        font-size: 0.85rem;
        color: #94a3b8 !important;
        margin-top: 0.3rem;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    .stButton > button {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        padding: 0.5rem 1.5rem;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Language ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "한국어"

with st.sidebar:
    st.markdown(f'<span style="display:flex;align-items:center;gap:8px;">{ICONS["settings"]} 설정</span>', unsafe_allow_html=True)
    lang = st.radio("언어", ["한국어", "English"], index=0, label_visibility="collapsed")
    st.session_state["lang"] = lang
    
lang = st.session_state["lang"]
is_kr = lang == "한국어"

# --- Company Data (no emojis) ---
company_info = {
    "TSLA": {"name": "Tesla", "kr": "전기차 1위. 전기차, 에너지 저장, 태양광", "en": "#1 EV maker. Electric vehicles, energy storage, solar", "sector": "전기차" if is_kr else "EV"},
    "NVDA": {"name": "NVIDIA", "kr": "AI 반도체 1위. AI 학습용 GPU 칩", "en": "#1 AI chips. GPUs for AI training", "sector": "반도체" if is_kr else "Chips"},
    "COIN": {"name": "Coinbase", "kr": "미국 최대 암호화폐 거래소", "en": "Largest US crypto exchange", "sector": "암호화폐" if is_kr else "Crypto"},
    "PLTR": {"name": "Palantir", "kr": "빅데이터 분석 소프트웨어", "en": "Big data analytics software", "sector": "소프트웨어" if is_kr else "Software"},
    "ISRG": {"name": "Intuitive Surgical", "kr": "수술 로봇 1위 (다빈치)", "en": "#1 surgical robotics (da Vinci)", "sector": "의료" if is_kr else "Medical"},
    "AMD": {"name": "AMD", "kr": "CPU/GPU 제조 (인텔 경쟁사)", "en": "CPU/GPU maker (Intel competitor)", "sector": "반도체" if is_kr else "Chips"},
    "AMZN": {"name": "Amazon", "kr": "이커머스 + 클라우드(AWS) 1위", "en": "#1 e-commerce + cloud (AWS)", "sector": "이커머스" if is_kr else "E-commerce"},
    "GOOGL": {"name": "Google", "kr": "검색 1위. 광고, 유튜브, 클라우드", "en": "#1 search. Ads, YouTube, cloud", "sector": "광고" if is_kr else "Ads"},
    "MSFT": {"name": "Microsoft", "kr": "윈도우, 오피스, Azure 클라우드", "en": "Windows, Office, Azure cloud", "sector": "소프트웨어" if is_kr else "Software"},
    "META": {"name": "Meta", "kr": "페이스북, 인스타그램, 왓츠앱", "en": "Facebook, Instagram, WhatsApp", "sector": "SNS" if is_kr else "Social"},
    "SHOP": {"name": "Shopify", "kr": "온라인 쇼핑몰 구축 플랫폼", "en": "E-commerce platform builder", "sector": "이커머스" if is_kr else "E-commerce"},
    "UBER": {"name": "Uber", "kr": "차량 공유 + 음식 배달", "en": "Ride-sharing + food delivery", "sector": "모빌리티" if is_kr else "Mobility"},
    "SQ": {"name": "Block", "kr": "결제 서비스 + 캐시앱", "en": "Payment services + Cash App", "sector": "핀테크" if is_kr else "Fintech"},
    "PYPL": {"name": "PayPal", "kr": "온라인 결제 (벤모 포함)", "en": "Online payments (incl. Venmo)", "sector": "핀테크" if is_kr else "Fintech"},
    "HOOD": {"name": "Robinhood", "kr": "무료 주식거래 앱", "en": "Commission-free trading app", "sector": "핀테크" if is_kr else "Fintech"},
    "CRSP": {"name": "CRISPR", "kr": "유전자 가위 치료제 개발", "en": "Gene editing therapeutics", "sector": "바이오" if is_kr else "Biotech"},
    "RKLB": {"name": "Rocket Lab", "kr": "소형 로켓 발사 서비스", "en": "Small rocket launch service", "sector": "우주" if is_kr else "Space"},
    "OKLO": {"name": "Oklo", "kr": "소형 원자로 개발", "en": "Small nuclear reactors", "sector": "에너지" if is_kr else "Energy"},
    "NET": {"name": "Cloudflare", "kr": "인터넷 보안/성능 서비스", "en": "Internet security/performance", "sector": "클라우드" if is_kr else "Cloud"},
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
def get_stock_data(tickers, language="한국어"):
    """Fetch stock data for given tickers"""
    is_korean = language == "한국어"
    data = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            
            # Get price
            try:
                price = stock.fast_info.last_price
            except:
                hist = stock.history(period="5d")
                if len(hist) > 0:
                    price = hist['Close'].iloc[-1]
                else:
                    continue
            
            # Get history for RSI
            hist = stock.history(period="2mo")
            
            if len(hist) > 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                rsi = 50
            
            # Get 52w high
            try:
                info = stock.info
                high_52 = info.get('fiftyTwoWeekHigh', price)
            except:
                high_52 = price
            
            drawdown = ((price - high_52) / high_52) * 100
            
            company = company_info.get(ticker, {"name": ticker, "kr": "", "en": "", "sector": ""})
            
            data.append({
                "ticker": ticker,
                "name": company["name"],
                "desc": company["kr"] if is_korean else company["en"],
                "sector": company.get("sector", ""),
                "price": price,
                "rsi": round(rsi, 1),
                "drawdown": round(drawdown, 1),
                "high_52": high_52
            })
        except Exception as e:
            # Skip failed tickers silently
            continue
    
    return data

# --- Sidebar Settings ---
with st.sidebar:
    st.markdown("---")
    st.markdown(f'<span style="display:flex;align-items:center;gap:8px;">{ICONS["bar_chart"]} {"포트폴리오" if is_kr else "Portfolio"}</span>', unsafe_allow_html=True)
    
    selected_tickers = st.multiselect(
        "종목 선택" if is_kr else "Select Stocks",
        options=sorted(all_tickers),
        default=core_tickers,
        format_func=lambda x: f"{x} - {company_info.get(x, {}).get('name', x)}"
    )
    
    st.markdown("---")
    monthly_budget = st.number_input(
        "월 투자금 ($)" if is_kr else "Monthly Budget ($)",
        min_value=100,
        max_value=100000,
        value=1000,
        step=100
    )
    
    if selected_tickers:
        weight_per_stock = 100 // len(selected_tickers)
        portfolio_weights = {t: weight_per_stock for t in selected_tickers}
    else:
        portfolio_weights = {}

# --- Main Content ---
fed_rate, m2_growth = get_macro_data()
stock_data = get_stock_data(tuple(selected_tickers), lang) if selected_tickers else []

# Determine market status
if fed_rate > 4.5 or m2_growth < 0:
    weather = "caution"
    weather_icon = ICONS["cloud_rain"]
    weather_text = "조심" if is_kr else "Caution"
    weather_desc = "금리가 높아요. 신중하게 투자하세요." if is_kr else "High rates. Invest carefully."
elif fed_rate > 3.5:
    weather = "normal"
    weather_icon = ICONS["cloud"]
    weather_text = "보통" if is_kr else "Normal"
    weather_desc = "평소대로 투자하세요." if is_kr else "Continue regular investing."
else:
    weather = "good"
    weather_icon = ICONS["sun"]
    weather_text = "좋음" if is_kr else "Good"
    weather_desc = "투자하기 좋은 환경이에요!" if is_kr else "Good environment for investing!"

# Calculate recommendations
total_suggested = 0
buy_recommendations = []

for stock in stock_data:
    weight = portfolio_weights.get(stock["ticker"], 0)
    base_amount = monthly_budget * (weight / 100)
    
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
    <h1>{"이번 주 투자 금액" if is_kr else "This Week's Investment"}</h1>
    <div class="hero-amount">${total_suggested:,.0f}</div>
    <div>
        <span class="status-badge status-{weather}">{weather_icon} {weather_text}</span>
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
        <div class="quick-stat-value" style="color: #16a34a;">{oversold_count}</div>
        <div class="quick-stat-label">{"세일 중" if is_kr else "On Sale"}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="quick-stat">
        <div class="quick-stat-value" style="color: #dc2626;">{overbought_count}</div>
        <div class="quick-stat-label">{"비쌈" if is_kr else "Expensive"}</div>
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
    ("매수 계획" if is_kr else "Buy Plan"),
    ("종목 상세" if is_kr else "Stock Details"),
    ("세일 찾기" if is_kr else "Find Sales")
])

# --- TAB 1: Buy Plan ---
with tab1:
    st.markdown(f'<div class="section-header">{"이번 주 매수 계획" if is_kr else "This Week\'s Buy Plan"}</div>', unsafe_allow_html=True)
    
    if buy_recommendations:
        sorted_recs = sorted(buy_recommendations, key=lambda x: (x["action"] != "buy", x["action"] != "hold"))
        
        for rec in sorted_recs:
            action_class = f"action-{rec['action']}"
            action_icon = ICONS["check"] if rec["action"] == "buy" else (ICONS["x"] if rec["action"] == "sell" else ICONS["minus"])
            action_text = {
                "buy": "더 사세요" if is_kr else "BUY MORE",
                "sell": "덜 사세요" if is_kr else "BUY LESS",
                "hold": "평소대로" if is_kr else "NORMAL"
            }[rec["action"]]
            
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            with col1:
                st.markdown(f"**{rec['name']}** `{rec['ticker']}`")
                st.caption(rec['desc'])
            
            with col2:
                delta_text = "세일!" if rec['rsi'] < 35 else ("비쌈" if rec['rsi'] > 70 else None)
                st.metric("RSI", f"{rec['rsi']:.0f}", 
                         delta=delta_text,
                         delta_color="normal" if rec['rsi'] < 35 else "inverse")
            
            with col3:
                st.markdown(f"<span class='action-badge {action_class}'>{action_icon} {action_text}</span>", unsafe_allow_html=True)
            
            with col4:
                st.metric("매수액" if is_kr else "Buy", f"${rec['suggested']:.0f}")
            
            st.markdown("---")
    else:
        st.info("사이드바에서 종목을 선택하세요." if is_kr else "Select stocks in the sidebar.")

# --- TAB 2: Stock Details ---
with tab2:
    st.markdown(f'<div class="section-header">{"종목 상세 정보" if is_kr else "Stock Details"}</div>', unsafe_allow_html=True)
    
    if stock_data:
        cols = st.columns(2)
        
        for idx, stock in enumerate(stock_data):
            with cols[idx % 2]:
                if stock["rsi"] < 30:
                    rsi_status = "세일!" if is_kr else "On Sale!"
                    rsi_status_class = "rsi-status-sale"
                elif stock["rsi"] > 70:
                    rsi_status = "비쌈" if is_kr else "Expensive"
                    rsi_status_class = "rsi-status-high"
                else:
                    rsi_status = "적정가" if is_kr else "Fair"
                    rsi_status_class = "rsi-status-fair"
                
                dd_class = "change-up" if stock["drawdown"] > -10 else "change-down"
                dd_label = "고점대비" if is_kr else "From High"
                
                st.markdown(f"""
                <div class="stock-card">
                    <div class="stock-header">
                        <span class="stock-name">{stock['name']}</span>
                        <span class="stock-ticker">{stock['ticker']}</span>
                    </div>
                    <div class="stock-desc">{stock['desc']}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="stock-price">${stock['price']:.2f}</span>
                        <span class="stock-change {dd_class}">{dd_label} {stock['drawdown']:.1f}%</span>
                    </div>
                    <div class="rsi-container">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span class="rsi-info">RSI: {stock['rsi']:.0f}</span>
                            <span class="rsi-status {rsi_status_class}">{rsi_status}</span>
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
    st.markdown(f'<div class="section-header">{"관심 종목 중 세일 찾기" if is_kr else "Find Sales in Watchlist"}</div>', unsafe_allow_html=True)
    
    watchlist_to_scan = [t for t in all_tickers if t not in selected_tickers]
    
    if watchlist_to_scan:
        with st.spinner("스캔 중..." if is_kr else "Scanning..."):
            watchlist_data = get_stock_data(tuple(watchlist_to_scan), lang)
            sales = [s for s in watchlist_data if s["rsi"] < 35]
        
        if sales:
            st.success(f"{len(sales)}{'개 종목이 세일 중!' if is_kr else ' stocks on sale!'}")
            
            for stock in sorted(sales, key=lambda x: x["rsi"]):
                col1, col2, col3 = st.columns([4, 2, 2])
                
                with col1:
                    st.markdown(f"**{stock['name']}** `{stock['ticker']}`")
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

with st.expander(("도움말: RSI가 뭐예요?" if is_kr else "Help: What is RSI?")):
    st.markdown(f"""
    <div class="info-box">
    <strong>RSI (상대강도지수)</strong>{"는 주식이 '세일 중'인지 '비싼지' 알려주는 지표예요." if is_kr else " tells you if a stock is 'on sale' or 'expensive'."}
    <br><br>
    <span style="color: #16a34a; font-weight: 600;">RSI 30 이하</span>: {"세일 중! 더 사기 좋은 타이밍" if is_kr else "On sale! Good time to buy more"}
    <br>
    <span style="font-weight: 600;">RSI 30-70</span>: {"적정 가격. 평소대로 투자" if is_kr else "Fair price. Normal investing"}
    <br>
    <span style="color: #dc2626; font-weight: 600;">RSI 70 이상</span>: {"비쌈! 덜 사는 게 좋아요" if is_kr else "Expensive! Consider buying less"}
    </div>
    """, unsafe_allow_html=True)

st.caption("데이터: Yahoo Finance, FRED | 투자 조언이 아닙니다" if is_kr else "Data: Yahoo Finance, FRED | Not financial advice")
