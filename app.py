import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import os
import feedparser

# --- Page Config (NO SIDEBAR) ---
st.set_page_config(
    page_title="투자 도우미", 
    layout="centered",  # Better for mobile
    initial_sidebar_state="collapsed",
    page_icon="$"
)

# --- Hide sidebar completely ---
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
</style>
""", unsafe_allow_html=True)

# --- SVG Icons ---
ICONS = {
    "check": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>',
    "x": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
    "minus": '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
}

# --- CSS (Mobile-first, Dark Mode) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    
    * { font-family: 'Noto Sans KR', sans-serif; }
    
    .main .block-container {
        padding: 1rem 1rem 2rem 1rem;
        max-width: 800px;
    }
    
    /* Stats row */
    .stats-row {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }
    .stat-box {
        flex: 1;
        text-align: center;
        padding: 0.8rem 0.5rem;
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
    }
    .stat-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: #f1f5f9 !important;
    }
    .stat-label {
        font-size: 0.7rem;
        color: #94a3b8 !important;
        margin-top: 0.2rem;
    }
    .stat-green { color: #34d399 !important; }
    .stat-red { color: #f87171 !important; }
    
    /* Stock item */
    .stock-item {
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border: 1px solid rgba(255,255,255,0.08);
    }
    .stock-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .stock-name {
        font-weight: 600;
        color: #e2e8f0 !important;
        font-size: 1rem;
    }
    .stock-ticker {
        font-size: 0.75rem;
        color: #64748b !important;
        background: rgba(255,255,255,0.1);
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        margin-left: 0.5rem;
    }
    .stock-price {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f1f5f9 !important;
    }
    .stock-desc {
        font-size: 0.8rem;
        color: #94a3b8 !important;
        margin: 0.4rem 0;
    }
    .stock-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid rgba(255,255,255,0.05);
    }
    
    /* RSI mini bar */
    .rsi-mini {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .rsi-bar-mini {
        width: 60px;
        height: 6px;
        border-radius: 3px;
        background: linear-gradient(to right, #10b981 0%, #10b981 30%, #fbbf24 30%, #fbbf24 70%, #ef4444 70%, #ef4444 100%);
        position: relative;
    }
    .rsi-dot {
        position: absolute;
        top: -3px;
        width: 12px;
        height: 12px;
        background: white;
        border-radius: 50%;
        border: 2px solid #1d4ed8;
        transform: translateX(-50%);
    }
    .rsi-text {
        font-size: 0.8rem;
        color: #94a3b8 !important;
    }
    
    /* Action badge */
    .action {
        display: inline-flex;
        align-items: center;
        gap: 3px;
        padding: 0.25rem 0.5rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .action-buy { background: rgba(16, 185, 129, 0.2); color: #34d399 !important; }
    .action-sell { background: rgba(239, 68, 68, 0.2); color: #f87171 !important; }
    .action-hold { background: rgba(148, 163, 184, 0.15); color: #94a3b8 !important; }
    
    /* Buy amount */
    .buy-amount {
        font-size: 1rem;
        font-weight: 700;
        color: #60a5fa !important;
    }
    
    /* Section */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #e2e8f0 !important;
        margin: 1.2rem 0 0.8rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Info box */
    .info-box {
        background: rgba(59, 130, 246, 0.1);
        border-left: 3px solid #3b82f6;
        padding: 0.8rem;
        border-radius: 0 8px 8px 0;
        font-size: 0.85rem;
        color: #cbd5e1 !important;
    }
    
    /* Hide Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    
    /* Better multiselect */
    .stMultiSelect > div {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- Company Data ---
# 각 종목에 대한 상세 설명 (초보자를 위한 투자 포인트)
company_info = {
    "TSLA": {
        "name": "Tesla",
        "kr": "전기차 1위 + 로보택시 + 로봇",
        "en": "#1 EV + Robotaxi + Robots",
        "detail_kr": "🚗 전기차만 만드는 게 아니에요! 2030년까지 로보택시 시장이 34조 달러(4.7경원)로 성장하는데, Tesla의 자율주행(FSD) 기술이 1등이에요. 휴머노이드 로봇(Optimus)도 개발 중이고, 에너지 저장장치(Megapack) 매출도 급성장해요.",
        "detail_en": "🚗 Not just EVs! Robotaxi market to reach $34T by 2030. Tesla leads in self-driving (FSD) and is building humanoid robots (Optimus). Energy storage (Megapack) revenue growing fast too."
    },
    "NVDA": {
        "name": "NVIDIA",
        "kr": "AI 반도체 독보적 1위",
        "en": "#1 AI chips dominant",
        "detail_kr": "🧠 AI의 두뇌를 만드는 회사예요. AI 칩 시장 점유율 85%, 마진 75%로 '독점'에 가까워요. 2030년까지 AI 인프라 투자가 1.4조 달러(1,900조원)로 성장하는데, 그 핵심 수혜자예요.",
        "detail_en": "🧠 Makes the 'brain' of AI. 85% market share, 75% margins - near monopoly. AI infrastructure to reach $1.4T by 2030, and NVIDIA is the core beneficiary."
    },
    "COIN": {
        "name": "Coinbase",
        "kr": "암호화폐 거래소 + Base 체인",
        "en": "Crypto exchange + Base chain",
        "detail_kr": "💰 미국 최대 암호화폐 거래소예요. 비트코인 ETF 수탁도 맡고, 자체 블록체인(Base)으로 DeFi 생태계도 구축 중이에요. 비트코인이 2030년 760만원→10억원 간다면 가장 큰 수혜주 중 하나예요.",
        "detail_en": "💰 Largest US crypto exchange. Custody for Bitcoin ETFs + building Base chain for DeFi. If Bitcoin reaches $760K by 2030, COIN is a major beneficiary."
    },
    "PLTR": {
        "name": "Palantir",
        "kr": "기업용 AI 플랫폼",
        "en": "Enterprise AI platform",
        "detail_kr": "📊 정부와 대기업을 위한 AI 데이터 분석 플랫폼(AIP)을 만들어요. '지능의 비용'이 99% 하락하면서 소프트웨어 시장이 2030년 3.4조~13조 달러로 성장하는데, Palantir가 핵심 기업이에요.",
        "detail_en": "📊 AI data platform for governments & enterprises. As 'cost of intelligence' drops 99%, software market grows to $3.4-13T by 2030. Palantir is a key player."
    },
    "ISRG": {
        "name": "Intuitive",
        "kr": "수술 로봇 세계 1위",
        "en": "World #1 surgical robots",
        "detail_kr": "🏥 다빈치 수술 로봇의 제조사예요. 로봇 시장이 26조 달러(3.6경원) 규모인데, 의료 분야는 가장 빠르게 자동화되는 영역 중 하나예요. AI로 수술 정밀도가 계속 높아지고 있어요.",
        "detail_en": "🏥 Makes da Vinci surgical robots. Robotics TAM is $26T, and healthcare is one of the fastest automating sectors. AI is continuously improving surgical precision."
    },
    "AMD": {
        "name": "AMD",
        "kr": "AI 칩 가성비 도전자",
        "en": "AI chip value challenger",
        "detail_kr": "💻 NVIDIA의 유일한 경쟁자예요! 새 칩(MI355X)이 메모리 288GB로 NVIDIA보다 크고, 가격 대비 성능도 더 좋아요. 특히 'AI 추론' 시장에서 점유율이 빠르게 올라가고 있어요.",
        "detail_en": "💻 NVIDIA's only real competitor! New MI355X has 288GB memory (more than NVIDIA) with better price-performance. Growing share in AI inference market."
    },
    "AMZN": {
        "name": "Amazon",
        "kr": "AI 쇼핑 + 클라우드 + 로봇",
        "en": "AI shopping + Cloud + Robots",
        "detail_kr": "📦 세계 최대 온라인 쇼핑몰이자 클라우드(AWS) 1위예요. AI 쇼핑 에이전트(Rufus), 창고 로봇(직원 1만명당 1,279대!), 드론 배송(Prime Air)까지 미래 기술을 모두 갖고 있어요.",
        "detail_en": "📦 World's largest e-commerce + #1 cloud (AWS). Has AI shopping agent (Rufus), warehouse robots (1,279 per 10K employees!), and drone delivery (Prime Air)."
    },
    "GOOGL": {
        "name": "Google",
        "kr": "AI 검색 + 자율주행 + 클라우드",
        "en": "AI search + Self-driving + Cloud",
        "detail_kr": "🔍 검색의 왕이지만, AI 검색(ChatGPT 등)에 위협받고 있어요. 하지만! 자율주행(Waymo)에서 기술 1등이고, 자체 AI 칩(TPU)도 있어요. 성공적으로 전환하면 더 커질 수 있어요.",
        "detail_en": "🔍 Search king but threatened by AI search. However! Leads in self-driving (Waymo) and has own AI chips (TPU). Could grow bigger with successful transition."
    },
    "MSFT": {
        "name": "Microsoft",
        "kr": "Copilot AI + Azure 클라우드",
        "en": "Copilot AI + Azure Cloud",
        "detail_kr": "🖥️ OpenAI와 독점 파트너십으로 AI 시대를 선도해요. 모든 오피스 제품에 AI(Copilot)를 넣고, 기업용 AI 시장을 장악 중이에요. 안정적이면서도 AI 성장의 수혜를 받는 종목이에요.",
        "detail_en": "🖥️ Exclusive OpenAI partnership leads AI era. Adding Copilot AI to all Office products, dominating enterprise AI. Stable yet benefits from AI growth."
    },
    "META": {
        "name": "Meta",
        "kr": "SNS AI + 스마트 안경",
        "en": "Social AI + Smart glasses",
        "detail_kr": "👓 페이스북, 인스타그램의 30억 사용자 데이터로 AI를 학습시켜요. Meta AI가 개인 맞춤 추천을 하고, Ray-Ban 스마트 안경도 인기예요. AI 소비자 시장(2030년 9000억 달러)의 핵심 주자예요.",
        "detail_en": "👓 Trains AI on 3B users' data from FB/IG. Meta AI does personalized recommendations, Ray-Ban smart glasses popular. Key player in AI consumer market ($900B by 2030)."
    },
    "SHOP": {
        "name": "Shopify",
        "kr": "AI 커머스 플랫폼의 허브",
        "en": "AI commerce platform hub",
        "detail_kr": "🛒 수백만 온라인 상점을 운영하게 해주는 플랫폼이에요. Google과 함께 'AI 커머스 프로토콜(UCP)'을 만들고 있어요. AI가 대신 쇼핑하는 시대(2030년 8조 달러 거래)의 핵심 인프라예요.",
        "detail_en": "🛒 Platform powering millions of online stores. Building 'Universal Commerce Protocol' with Google. Core infrastructure for AI shopping era ($8T transactions by 2030)."
    },
    "UBER": {
        "name": "Uber",
        "kr": "라이드쉐어 + 로보택시 연결",
        "en": "Ride-share + Robotaxi network",
        "detail_kr": "🚕 차량 호출/배달 앱 1위예요. 자율주행은 직접 못 만들지만, Waymo 같은 로보택시 회사와 협력해요. 로보택시 시대에도 '앱'으로 살아남을 수 있는지가 관건이에요.",
        "detail_en": "🚕 #1 ride-hail/delivery app. Can't build self-driving but partners with Waymo. Key question: can they survive as 'the app' in robotaxi era?"
    },
    "SQ": {
        "name": "Block",
        "kr": "비트코인 + 결제 서비스",
        "en": "Bitcoin + Payment services",
        "detail_kr": "💳 Cash App으로 비트코인 매매도 가능하고, 비트코인 지갑(Bitkey)도 만들어요. 비트코인 결제 인프라의 핵심 회사예요. 비트코인이 오르면 같이 오르는 구조예요.",
        "detail_en": "💳 Cash App enables Bitcoin trading, also makes Bitkey wallet. Core Bitcoin payment infrastructure. Benefits directly from Bitcoin price increases."
    },
    "PYPL": {
        "name": "PayPal",
        "kr": "스테이블코인 + 온라인 결제",
        "en": "Stablecoin + Online payments",
        "detail_kr": "💵 온라인 결제의 원조예요. 자체 스테이블코인(PYUSD)이 1년만에 6배 성장했어요. 토큰화 자산 시장(2030년 11조 달러)에서 결제 인프라로 자리잡을 수 있어요.",
        "detail_en": "💵 Pioneer of online payments. Own stablecoin (PYUSD) grew 6x in one year. Could become payment infrastructure for tokenized assets ($11T by 2030)."
    },
    "RKLB": {
        "name": "Rocket Lab",
        "kr": "소형 로켓 + 우주 시스템",
        "en": "Small rockets + Space systems",
        "detail_kr": "🚀 SpaceX 다음가는 민간 로켓 회사예요. 소형 위성 발사에 특화되어 있어요. 위성 통신 시장이 2030년 1600억 달러(210조원)로 성장하는데, 발사 비용은 계속 떨어지고 있어요.",
        "detail_en": "🚀 Second largest private rocket company after SpaceX. Specializes in small satellite launches. Satellite market to reach $160B by 2030, launch costs keep dropping."
    },
    "NET": {
        "name": "Cloudflare",
        "kr": "인터넷 인프라 + AI 엣지",
        "en": "Internet infra + AI edge",
        "detail_kr": "🌐 전 세계 인터넷 트래픽의 상당 부분을 처리하는 보안/가속 서비스예요. AI가 더 많이 쓰일수록 인터넷 인프라도 더 중요해져요. AI 시대의 숨은 수혜주예요.",
        "detail_en": "🌐 Security/acceleration for major portion of internet traffic. As AI usage grows, internet infrastructure becomes more critical. Hidden beneficiary of AI era."
    },
}

default_tickers = ["TSLA", "NVDA", "COIN"]  # 기본 3종목
all_tickers = list(company_info.keys())

# --- API ---
FRED_API_KEY = os.environ.get('FRED_API_KEY', '10b52d62b316f7f27fd58a6111c80adf')

# --- Data Functions ---
@st.cache_data(ttl=3600)
def get_macro_data():
    try:
        fred = Fred(api_key=FRED_API_KEY)
        fed_funds = fred.get_series('FEDFUNDS', observation_start='2024-01-01').iloc[-1]
        return fed_funds
    except:
        return 4.33

@st.cache_data(ttl=1800)
def get_stock_data(tickers, lang="한국어"):
    is_kr = lang == "한국어"
    data = []
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            try:
                price = stock.fast_info.last_price
            except:
                hist = stock.history(period="5d")
                price = hist['Close'].iloc[-1] if len(hist) > 0 else 0
                if price == 0:
                    continue
            
            hist = stock.history(period="2mo")
            if len(hist) > 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
            else:
                rsi = 50
            
            company = company_info.get(ticker, {"name": ticker, "kr": "", "en": "", "detail_kr": "", "detail_en": ""})
            data.append({
                "ticker": ticker,
                "name": company["name"],
                "desc": company["kr"] if is_kr else company["en"],
                "detail": company.get("detail_kr", "") if is_kr else company.get("detail_en", ""),
                "price": price,
                "rsi": round(rsi, 1),
            })
        except:
            continue
    return data

@st.cache_data(ttl=3600)
def get_news(ticker):
    """Fetch news for a ticker from Yahoo Finance RSS"""
    try:
        url = f"https://finance.yahoo.com/rss/headline?s={ticker}"
        feed = feedparser.parse(url)
        news_items = []
        for entry in feed.entries[:3]:  # 최대 3개
            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.get('published', '')[:16] if entry.get('published') else ''
            })
        return news_items
    except:
        return []

# --- Session State ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "한국어"
if "selected" not in st.session_state:
    st.session_state["selected"] = default_tickers
if "budget" not in st.session_state:
    st.session_state["budget"] = 1000
if "weights" not in st.session_state:
    # 기본 비중: 균등 배분
    st.session_state["weights"] = {t: 100 // len(default_tickers) for t in default_tickers}

# === MAIN UI (No Sidebar!) ===

# Language toggle (simple)
col_lang1, col_lang2 = st.columns([1, 1])
with col_lang1:
    if st.button("한국어", use_container_width=True, type="primary" if st.session_state["lang"] == "한국어" else "secondary"):
        st.session_state["lang"] = "한국어"
        st.rerun()
with col_lang2:
    if st.button("English", use_container_width=True, type="primary" if st.session_state["lang"] == "English" else "secondary"):
        st.session_state["lang"] = "English"
        st.rerun()

lang = st.session_state["lang"]
is_kr = lang == "한국어"

# Settings in main area (collapsible)
with st.expander("설정" if is_kr else "Settings", expanded=False):
    # 종목 선택
    selected = st.multiselect(
        "종목 선택" if is_kr else "Select Stocks",
        options=all_tickers,
        default=st.session_state["selected"],
        format_func=lambda x: f"{x} - {company_info.get(x, {}).get('name', x)}"
    )
    if selected != st.session_state["selected"]:
        st.session_state["selected"] = selected
        # 새 종목 추가 시 비중 초기화
        new_weights = {}
        for t in selected:
            new_weights[t] = st.session_state["weights"].get(t, 0)
        # 비중 합이 100이 아니면 균등 배분
        if sum(new_weights.values()) != 100:
            equal_weight = 100 // len(selected) if selected else 0
            new_weights = {t: equal_weight for t in selected}
        st.session_state["weights"] = new_weights
        st.rerun()
    
    # 월 투자금
    budget = st.number_input(
        "월 투자금 ($)" if is_kr else "Monthly Budget ($)",
        min_value=10,
        max_value=1000000,
        value=st.session_state["budget"],
        step=50
    )
    if budget != st.session_state["budget"]:
        st.session_state["budget"] = budget
    
    # 비중 설정
    if selected:
        st.markdown("---")
        st.markdown(f"**{'비중 설정 (%)' if is_kr else 'Allocation (%)'}**")
        
        weights_changed = False
        new_weights = {}
        total_weight = 0
        
        cols = st.columns(len(selected)) if len(selected) <= 4 else st.columns(4)
        
        for i, ticker in enumerate(selected):
            col_idx = i % len(cols)
            with cols[col_idx]:
                current_weight = st.session_state["weights"].get(ticker, 0)
                new_weight = st.number_input(
                    ticker,
                    min_value=0,
                    max_value=100,
                    value=current_weight,
                    step=5,
                    key=f"weight_{ticker}"
                )
                new_weights[ticker] = new_weight
                total_weight += new_weight
                if new_weight != current_weight:
                    weights_changed = True
        
        # 비중 합계 표시
        if total_weight == 100:
            st.success(f"{'합계' if is_kr else 'Total'}: {total_weight}%")
        else:
            st.warning(f"{'합계' if is_kr else 'Total'}: {total_weight}% ({'100%가 되어야 해요' if is_kr else 'Should be 100%'})")
        
        if weights_changed:
            st.session_state["weights"] = new_weights

# Get data
fed_rate = get_macro_data()
selected_tickers = st.session_state["selected"]
monthly_budget = st.session_state["budget"]

stock_data = get_stock_data(tuple(selected_tickers), lang) if selected_tickers else []

# Market status
if fed_rate > 4.5:
    weather = "caution"
    weather_text = "조심" if is_kr else "Caution"
elif fed_rate > 3.5:
    weather = "normal"
    weather_text = "보통" if is_kr else "Normal"
else:
    weather = "good"
    weather_text = "좋음" if is_kr else "Good"

# Calculate recommendations
total_suggested = 0
recommendations = []
weights = st.session_state["weights"]

for stock in stock_data:
    ticker_weight = weights.get(stock["ticker"], 0)
    base = monthly_budget * (ticker_weight / 100)
    
    if stock["rsi"] < 35:
        mult, action = 1.3, "buy"
    elif stock["rsi"] > 70:
        mult, action = 0.7, "sell"
    else:
        mult, action = 1.0, "hold"
    
    suggested = base * mult
    total_suggested += suggested
    recommendations.append({
        **stock, 
        "suggested": suggested, 
        "action": action, 
        "weight": ticker_weight,
        "detail": stock.get("detail", "")
    })

oversold = len([s for s in stock_data if s["rsi"] < 35])
overbought = len([s for s in stock_data if s["rsi"] > 70])

# === STATS (compact) ===
st.markdown(f"""
<div class="stats-row">
    <div class="stat-box">
        <div class="stat-value">{len(stock_data)}</div>
        <div class="stat-label">{"종목" if is_kr else "Stocks"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value stat-green">{oversold}</div>
        <div class="stat-label">{"세일" if is_kr else "Sale"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value stat-red">{overbought}</div>
        <div class="stat-label">{"비쌈" if is_kr else "High"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value">{fed_rate:.1f}%</div>
        <div class="stat-label">{"금리" if is_kr else "Rate"}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === STOCK LIST ===
if recommendations:
    st.markdown(f'<div class="section-title">{"매수 계획" if is_kr else "Buy Plan"}</div>', unsafe_allow_html=True)
    
    # Sort: buy first, then hold, then sell
    sorted_recs = sorted(recommendations, key=lambda x: (x["action"] != "buy", x["action"] != "hold"))
    
    for rec in sorted_recs:
        action_class = f"action-{rec['action']}"
        action_icon = ICONS["check"] if rec["action"] == "buy" else (ICONS["x"] if rec["action"] == "sell" else ICONS["minus"])
        action_text = {"buy": "더 사기" if is_kr else "BUY+", "sell": "덜 사기" if is_kr else "BUY-", "hold": "유지" if is_kr else "HOLD"}[rec["action"]]
        weight_text = f"{rec['weight']}%"
        
        # 상세 설명 가져오기
        detail_text = rec.get('detail', '')
        
        st.markdown(f"""
        <div class="stock-item">
            <div class="stock-row">
                <div>
                    <span class="stock-name">{rec['name']}</span>
                    <span class="stock-ticker">{rec['ticker']}</span>
                    <span class="stock-ticker">{weight_text}</span>
                </div>
                <span class="buy-amount">${rec['suggested']:.0f}</span>
            </div>
            <div class="stock-desc">{rec['desc']}</div>
            <div class="stock-meta">
                <div class="rsi-mini">
                    <div class="rsi-bar-mini">
                        <div class="rsi-dot" style="left: {rec['rsi']}%;"></div>
                    </div>
                    <span class="rsi-text">RSI {rec['rsi']:.0f}</span>
                </div>
                <span class="action {action_class}">{action_icon} {action_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 투자 포인트 상세 설명 (펼치기)
        if detail_text:
            with st.expander(f"{'왜 투자해야 할까요?' if is_kr else 'Why invest?'} 💡", expanded=False):
                st.markdown(f"""
                <div style="font-size: 0.9rem; line-height: 1.6; color: #e2e8f0; padding: 0.5rem 0;">
                    {detail_text}
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("설정에서 종목을 선택하세요." if is_kr else "Select stocks in Settings.")

# === NEWS ===
if recommendations:
    st.markdown(f'<div class="section-title">{"뉴스" if is_kr else "News"}</div>', unsafe_allow_html=True)
    
    # 탭으로 종목별 뉴스 표시
    if len(recommendations) > 0:
        tabs = st.tabs([rec["ticker"] for rec in recommendations])
        
        for i, rec in enumerate(recommendations):
            with tabs[i]:
                news_items = get_news(rec["ticker"])
                if news_items:
                    for news in news_items:
                        st.markdown(f"""
                        <div style="padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <a href="{news['link']}" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.9rem;">
                                {news['title']}
                            </a>
                            <div style="font-size: 0.75rem; color: #64748b; margin-top: 0.2rem;">{news['published']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("뉴스 없음" if is_kr else "No news")

# === HELP ===
with st.expander("RSI란?" if is_kr else "What is RSI?"):
    st.markdown(f"""
    <div class="info-box">
    <strong>RSI</strong>{"는 주식이 세일 중인지 비싼지 알려주는 지표예요." if is_kr else " tells you if a stock is on sale or expensive."}
    <br><br>
    <span style="color: #34d399;">30 이하</span>: {"세일! 더 사세요" if is_kr else "Sale! Buy more"}
    <br>
    <span>30-70</span>: {"적정가" if is_kr else "Fair price"}
    <br>
    <span style="color: #f87171;">70 이상</span>: {"비쌈! 덜 사세요" if is_kr else "Expensive! Buy less"}
    </div>
    """, unsafe_allow_html=True)

# Footer
st.caption("Yahoo Finance, FRED | " + ("투자 조언 아님" if is_kr else "Not financial advice"))
