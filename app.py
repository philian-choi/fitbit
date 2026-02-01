import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import os

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
    
    /* Hero card */
    .hero-card {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        padding: 1.5rem;
        border-radius: 16px;
        color: white !important;
        text-align: center;
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 1rem;
        margin: 0;
        color: rgba(255,255,255,0.85) !important;
    }
    .hero-amount {
        font-size: 3rem;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0.3rem 0;
    }
    .hero-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 0.3rem;
    }
    .badge-good { background: #10b981; color: white !important; }
    .badge-normal { background: #f59e0b; color: white !important; }
    .badge-caution { background: #8b5cf6; color: white !important; }
    
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
company_info = {
    "TSLA": {"name": "Tesla", "kr": "전기차 1위", "en": "#1 EV maker"},
    "NVDA": {"name": "NVIDIA", "kr": "AI 반도체 1위", "en": "#1 AI chips"},
    "COIN": {"name": "Coinbase", "kr": "암호화폐 거래소", "en": "Crypto exchange"},
    "PLTR": {"name": "Palantir", "kr": "빅데이터 분석", "en": "Big data analytics"},
    "ISRG": {"name": "Intuitive", "kr": "수술 로봇", "en": "Surgical robotics"},
    "AMD": {"name": "AMD", "kr": "CPU/GPU 제조", "en": "CPU/GPU maker"},
    "AMZN": {"name": "Amazon", "kr": "이커머스+AWS", "en": "E-commerce+AWS"},
    "GOOGL": {"name": "Google", "kr": "검색/광고", "en": "Search/Ads"},
    "MSFT": {"name": "Microsoft", "kr": "윈도우/Azure", "en": "Windows/Azure"},
    "META": {"name": "Meta", "kr": "SNS 플랫폼", "en": "Social media"},
    "SHOP": {"name": "Shopify", "kr": "이커머스 플랫폼", "en": "E-commerce platform"},
    "UBER": {"name": "Uber", "kr": "차량공유/배달", "en": "Ride-share/Delivery"},
    "SQ": {"name": "Block", "kr": "결제 서비스", "en": "Payment services"},
    "PYPL": {"name": "PayPal", "kr": "온라인 결제", "en": "Online payments"},
    "RKLB": {"name": "Rocket Lab", "kr": "로켓 발사", "en": "Rocket launches"},
    "NET": {"name": "Cloudflare", "kr": "인터넷 보안", "en": "Internet security"},
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
            
            company = company_info.get(ticker, {"name": ticker, "kr": "", "en": ""})
            data.append({
                "ticker": ticker,
                "name": company["name"],
                "desc": company["kr"] if is_kr else company["en"],
                "price": price,
                "rsi": round(rsi, 1),
            })
        except:
            continue
    return data

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
    budget = st.slider(
        "월 투자금 ($)" if is_kr else "Monthly Budget ($)",
        min_value=100,
        max_value=5000,
        value=st.session_state["budget"],
        step=100
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
    recommendations.append({**stock, "suggested": suggested, "action": action, "weight": ticker_weight})

oversold = len([s for s in stock_data if s["rsi"] < 35])
overbought = len([s for s in stock_data if s["rsi"] > 70])

# === HERO ===
st.markdown(f"""
<div class="hero-card">
    <div class="hero-title">{"이번 주 투자 금액" if is_kr else "This Week's Investment"}</div>
    <div class="hero-amount">${total_suggested:,.0f}</div>
    <span class="hero-badge badge-{weather}">{weather_text}</span>
</div>
""", unsafe_allow_html=True)

# === STATS ===
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
else:
    st.info("설정에서 종목을 선택하세요." if is_kr else "Select stocks in Settings.")

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
