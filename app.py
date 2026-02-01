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
st.set_page_config(
    page_title="Weekly DCA Report", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="📈"
)

# --- Custom CSS for Better UX ---
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card styling */
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 12px;
        color: white;
    }
    
    /* Signal cards */
    .signal-card {
        padding: 1.5rem;
        border-radius: 16px;
        margin: 0.5rem 0;
        text-align: center;
    }
    .signal-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
    }
    .signal-yellow {
        background: linear-gradient(135deg, #F2994A 0%, #F2C94C 100%);
        color: white;
    }
    .signal-red {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
    }
    
    /* Action card */
    .action-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 1rem 0;
    }
    .action-card h2 {
        margin: 0;
        font-size: 1.5rem;
    }
    .action-card .amount {
        font-size: 3rem;
        font-weight: bold;
        margin: 1rem 0;
    }
    
    /* Tooltip styling */
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted #666;
        cursor: help;
    }
    
    /* Progress bar for RSI */
    .rsi-gauge {
        height: 20px;
        border-radius: 10px;
        background: linear-gradient(to right, #38ef7d 0%, #F2C94C 50%, #eb3349 100%);
        position: relative;
    }
    
    /* Info boxes */
    .info-box {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Better table styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

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
    st.session_state["lang"] = "한국어"

lang_selection = st.sidebar.radio(
    "Language / 언어", 
    ["English", "한국어"],
    index=1 if st.session_state["lang"] == "한국어" else 0
)
st.session_state["lang"] = lang_selection if lang_selection else "한국어"
lang = st.session_state["lang"]

# Text Dictionary - Enhanced with beginner-friendly explanations
text = {
    "English": {
        "title": "📈 Weekly Investment Helper",
        "subtitle": "Your friendly guide to smarter investing",
        "date": "Date",
        "strategy": "Strategy: Buy quality stocks regularly",
        
        # Beginner Guide
        "guide_title": "🎓 Quick Start Guide",
        "guide_dca": "**DCA (Dollar Cost Averaging)**: Instead of timing the market, invest a fixed amount regularly. This reduces risk!",
        "guide_rsi": "**RSI (Relative Strength Index)**: Think of it as a 'sale detector'. Below 30 = On Sale! Above 70 = Overpriced!",
        "guide_drawdown": "**Drawdown**: How far the price has fallen from its peak. Bigger drops = bigger discounts!",
        
        # Macro Section
        "macro_header": "🌤️ Market Weather Report",
        "macro_desc": "Just like checking the weather before going out, check the market conditions before investing!",
        "fed_rate": "Interest Rate",
        "fed_rate_help": "Higher rates = harder for companies to borrow = stocks may fall",
        "m2_growth": "Money Supply Growth",
        "m2_help": "More money in the economy = good for stocks",
        "target_range": "Fed Target",
        "liquidity": "YoY Change",
        "stance": "Investment Weather",
        "green": "☀️ SUNNY - Great time to invest more!",
        "red": "🌧️ RAINY - Be careful, invest less",
        "yellow": "⛅ CLOUDY - Normal investing is fine",
        
        # Portfolio Section
        "portfolio_header": "💼 Your Portfolio Checkup",
        "portfolio_desc": "Let's see how your stocks are doing today!",
        "refresh": "🔄 Refresh Data",
        "fetching": "Getting the latest prices...",
        "insights": "💡 What Should I Do?",
        "oversold": "🟢 ON SALE! Great time to buy more.",
        "overbought": "🔴 EXPENSIVE! Maybe buy less this week.",
        "drawdown": "📉 Price dropped from peak. Could be a good entry point!",
        
        # Calculator Section
        "calc_header": "🧮 This Week's Buy Plan",
        "calc_desc": "Based on your **${}** monthly budget, here's what I suggest:",
        "buy_more": "🟢 BUY MORE",
        "buy_less": "🔴 BUY LESS", 
        "normal": "⚪ NORMAL",
        "total_action": "💰 Total to Invest This Week",
        
        # Discovery Section
        "discovery_header": "🔍 Bargain Hunter",
        "discovery_desc": "Looking for stocks on sale in your watchlist...",
        "discovery_found": "Found {} stocks on sale!",
        "discovery_none": "No big sales right now. The market is fairly priced.",
        
        # News Section
        "news_header": "📰 Important News",
        "no_news": "No major news for this stock.",
        
        # Footer
        "footer": "Data from Yahoo Finance & FRED. This is not financial advice - always do your own research!",
        
        # RSI Gauge Labels
        "rsi_oversold": "On Sale!",
        "rsi_normal": "Fair Price",
        "rsi_overbought": "Expensive!",
        
        # Action Summary
        "action_summary": "📋 Today's Action Plan",
        "action_total": "Total Investment",
        "action_stocks": "stocks to buy"
    },
    "한국어": {
        "title": "📈 주간 투자 도우미",
        "subtitle": "똑똑한 투자를 위한 친절한 가이드",
        "date": "날짜",
        "strategy": "전략: 좋은 주식을 꾸준히 사기",
        
        # Beginner Guide
        "guide_title": "🎓 초보자 가이드",
        "guide_dca": "**적립식 투자 (DCA)**: 타이밍 맞추려 하지 말고, 매주/매월 일정 금액을 투자하세요. 리스크가 줄어듭니다!",
        "guide_rsi": "**RSI (상대강도지수)**: '세일 감지기'라고 생각하세요. 30 이하 = 세일 중! 70 이상 = 비쌈!",
        "guide_drawdown": "**낙폭**: 최고점에서 얼마나 떨어졌는지. 많이 떨어졌다 = 할인 중!",
        
        # Macro Section
        "macro_header": "🌤️ 시장 날씨 리포트",
        "macro_desc": "외출 전 날씨 확인하듯, 투자 전 시장 상황을 확인하세요!",
        "fed_rate": "기준금리",
        "fed_rate_help": "금리가 높으면 → 기업이 돈 빌리기 어려움 → 주가 하락 가능",
        "m2_growth": "통화량 증가율",
        "m2_help": "시중에 돈이 많아지면 → 주식에 좋음",
        "target_range": "연준 목표",
        "liquidity": "전년 대비",
        "stance": "투자 날씨",
        "green": "☀️ 맑음 - 적극 투자 OK!",
        "red": "🌧️ 비 - 조심! 투자 줄이기",
        "yellow": "⛅ 흐림 - 평소대로 투자",
        
        # Portfolio Section
        "portfolio_header": "💼 내 포트폴리오 건강검진",
        "portfolio_desc": "오늘 내 주식들은 어떤 상태일까요?",
        "refresh": "🔄 새로고침",
        "fetching": "최신 가격 가져오는 중...",
        "insights": "💡 지금 뭘 해야 할까요?",
        "oversold": "🟢 세일 중! 더 사기 좋은 타이밍이에요.",
        "overbought": "🔴 비싸요! 이번 주는 덜 사는 게 좋겠어요.",
        "drawdown": "📉 고점 대비 하락 중. 좋은 매수 기회일 수 있어요!",
        
        # Calculator Section
        "calc_header": "🧮 이번 주 매수 계획",
        "calc_desc": "월 투자금 **${}** 기준, 이번 주 추천 매수액입니다:",
        "buy_more": "🟢 더 사세요",
        "buy_less": "🔴 덜 사세요",
        "normal": "⚪ 평소대로",
        "total_action": "💰 이번 주 총 투자액",
        
        # Discovery Section
        "discovery_header": "🔍 세일 종목 찾기",
        "discovery_desc": "관심 종목 중 할인 중인 주식을 찾고 있어요...",
        "discovery_found": "{}개 종목이 세일 중이에요!",
        "discovery_none": "지금은 큰 세일이 없어요. 시장이 적정 가격이에요.",
        
        # News Section
        "news_header": "📰 중요 뉴스",
        "no_news": "이 종목의 주요 뉴스가 없습니다.",
        
        # Footer
        "footer": "데이터 출처: Yahoo Finance, FRED. 투자 조언이 아닙니다 - 항상 본인의 판단으로 투자하세요!",
        
        # RSI Gauge Labels
        "rsi_oversold": "세일!",
        "rsi_normal": "적정가",
        "rsi_overbought": "비쌈!",
        
        # Action Summary
        "action_summary": "📋 오늘의 액션 플랜",
        "action_total": "총 투자금액",
        "action_stocks": "개 종목 매수"
    }
}

t = text.get(lang, text["한국어"])

# Get API Key from Environment Variable
FRED_API_KEY = os.environ.get('FRED_API_KEY')
if not FRED_API_KEY:
    FRED_API_KEY = '10b52d62b316f7f27fd58a6111c80adf' 

# --- Helper Functions for Visual Elements ---
def create_rsi_gauge(rsi_value, ticker):
    """Create a visual RSI gauge using Plotly"""
    # Determine color based on RSI
    if rsi_value < 30:
        color = "#38ef7d"
        status = t["rsi_oversold"]
    elif rsi_value > 70:
        color = "#eb3349"
        status = t["rsi_overbought"]
    else:
        color = "#F2C94C"
        status = t["rsi_normal"]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rsi_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"{ticker}<br><span style='font-size:0.8em;color:{color}'>{status}</span>"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': 'rgba(56, 239, 125, 0.3)'},
                {'range': [30, 70], 'color': 'rgba(242, 201, 76, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(235, 51, 73, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': rsi_value
            }
        }
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=20),
        font={'size': 14}
    )
    return fig

def get_signal_html(status_type, message):
    """Generate HTML for signal cards"""
    class_name = f"signal-{status_type}"
    return f'<div class="signal-card {class_name}"><h3>{message}</h3></div>'

def get_action_card_html(amount, num_stocks, label):
    """Generate HTML for action summary card"""
    return f'''
    <div class="action-card">
        <h2>{label}</h2>
        <div class="amount">${amount:,.0f}</div>
        <p>{num_stocks} {t["action_stocks"]}</p>
    </div>
    '''

# --- 1. Data Fetching Functions ---
@st.cache_data(ttl=3600)
def get_macro_data():
    if not FRED_API_KEY:
        return 3.72, 4.6
        
    try:
        fred = Fred(api_key=FRED_API_KEY)
        fed_funds = fred.get_series('FEDFUNDS', observation_start='2024-01-01').iloc[-1]
        m2 = fred.get_series('M2SL', observation_start='2024-01-01').iloc[-1]
        last_m2 = fred.get_series('M2SL', observation_start='2023-01-01').iloc[-13]
        m2_growth = ((m2 - last_m2) / last_m2) * 100
        return fed_funds, m2_growth
    except Exception as e:
        return 3.72, 4.6

@st.cache_data(ttl=3600)
def get_article_summary(url):
    try:
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
    rss_urls = [
        f"https://finance.yahoo.com/rss/headline?s={ticker}",
        f"https://seekingalpha.com/api/1.0/rss/symbol/{ticker}",
        f"https://feeds.content.dowjones.com/public/rss/mw/ticker/{ticker}"
    ]
    
    news_items = []
    seen_titles = set()
    
    keywords = [
        "Earnings", "Revenue", "Profit", "Guidance", "Quarter",
        "SEC", "Regulation", "Lawsuit", "Approval", "FDA", "Ban",
        "Acquisition", "Merger", "Partnership", "Contract", "Deal",
        "Launch", "Release", "Unveil", "Patent", "Breakthrough",
        "Upgrade", "Downgrade", "Target Price", "Buy", "Sell"
    ]
    
    noise = [
        "Why", "Here's", "What to know", "3 reasons", "5 stocks", "10 stocks",
        "Prediction", "Could", "Might", "Opinion", "Think", "Maybe",
        "Motley Fool", "Zacks"
    ]

    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                
                if title in seen_titles:
                    continue
                seen_titles.add(title)

                if any(n in title for n in noise):
                    continue
                    
                if any(k in title for k in keywords):
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
            
    return news_items[:5]

def get_stock_data(tickers, include_description=False):
    data = []
    for ticker_symbol in tickers:
        try:
            stock = yf.Ticker(ticker_symbol)
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
            
            moat_score = "Strong"
            if info.get('grossMargins', 0) < 0.4 and info.get('revenueGrowth', 0) < 0.1:
                moat_score = "Watch"
            
            # Get company info
            company = company_info.get(ticker_symbol, {})
            company_name = f"{company.get('emoji', '')} {company.get('name', ticker_symbol)}"
            sector = company.get('sector', '')
            
            row_data = {
                "종목" if lang == "한국어" else "Ticker": company_name,
                "티커" if lang == "한국어" else "Symbol": ticker_symbol,
                "섹터" if lang == "한국어" else "Sector": sector,
                "가격" if lang == "한국어" else "Price": price,
                "RSI": round(rsi, 2),
                "52주 최고" if lang == "한국어" else "52W High": high_52,
                "낙폭" if lang == "한국어" else "Drawdown": round((price - high_52) / high_52 * 100, 2)
            }
            
            data.append(row_data)
        except Exception as e:
            st.warning(f"Could not fetch data for {ticker_symbol}: {e}")
            
    return pd.DataFrame(data)

def scan_market_opportunities(watchlist_tickers):
    opportunities = []
    for ticker_symbol in watchlist_tickers:
        try:
            stock = yf.Ticker(ticker_symbol)
            price = stock.fast_info.last_price
            
            hist = stock.history(period="1mo")
            
            if len(hist) > 14:
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                if rsi < 30:
                    # Get company info
                    company = company_info.get(ticker_symbol, {})
                    company_name = f"{company.get('emoji', '')} {company.get('name', ticker_symbol)}"
                    desc = company.get("kr" if lang == "한국어" else "en", "")
                    sector = company.get("sector", "")
                    
                    opportunities.append({
                        "종목" if lang == "한국어" else "Stock": company_name,
                        "티커" if lang == "한국어" else "Ticker": ticker_symbol,
                        "섹터" if lang == "한국어" else "Sector": sector,
                        "가격" if lang == "한국어" else "Price": f"${price:.2f}",
                        "RSI": round(rsi, 2),
                        "설명" if lang == "한국어" else "Description": desc[:50] + "..." if len(desc) > 50 else desc
                    })
                
        except:
            continue
            
    return pd.DataFrame(opportunities)

# --- 2. Sidebar: Portfolio Settings ---
st.sidebar.header("⚙️ 설정" if lang == "한국어" else "⚙️ Settings")

# Define available tickers
# --- Company Information Dictionary ---
# 각 종목에 대한 설명 (초보자용)
company_info = {
    # Core Holdings
    "TSLA": {
        "name": "Tesla",
        "emoji": "🚗",
        "kr": "전기차 1위 기업. 전기차, 에너지 저장장치, 태양광 패널 판매로 수익 창출",
        "en": "World's #1 EV maker. Revenue from electric vehicles, energy storage, and solar panels",
        "sector": "전기차/에너지" if lang == "한국어" else "EV/Energy"
    },
    "NVDA": {
        "name": "NVIDIA",
        "emoji": "🎮",
        "kr": "AI 반도체 1위. GPU(그래픽카드) 판매, 특히 AI 학습용 칩으로 대박",
        "en": "#1 AI chip maker. Revenue from GPUs, especially AI training chips",
        "sector": "반도체" if lang == "한국어" else "Semiconductors"
    },
    "COIN": {
        "name": "Coinbase",
        "emoji": "🪙",
        "kr": "미국 최대 암호화폐 거래소. 비트코인/이더리움 거래 수수료로 수익",
        "en": "Largest US crypto exchange. Revenue from trading fees on Bitcoin/Ethereum",
        "sector": "암호화폐" if lang == "한국어" else "Crypto"
    },
    "PLTR": {
        "name": "Palantir",
        "emoji": "🔍",
        "kr": "빅데이터 분석 전문. 정부/기업에 데이터 분석 소프트웨어 판매",
        "en": "Big data analytics. Sells data analysis software to governments & enterprises",
        "sector": "소프트웨어" if lang == "한국어" else "Software"
    },
    "ISRG": {
        "name": "Intuitive Surgical",
        "emoji": "🏥",
        "kr": "수술 로봇 1위. 다빈치 로봇 판매 및 수술 도구 소모품으로 수익",
        "en": "#1 surgical robotics. Revenue from da Vinci robots & surgical consumables",
        "sector": "의료기기" if lang == "한국어" else "Medical Devices"
    },
    
    # Big Tech
    "AMD": {
        "name": "AMD",
        "emoji": "💻",
        "kr": "CPU/GPU 제조사. 인텔의 경쟁자, 컴퓨터/서버용 칩 판매",
        "en": "CPU/GPU maker. Intel competitor, sells chips for PCs and servers",
        "sector": "반도체" if lang == "한국어" else "Semiconductors"
    },
    "AMZN": {
        "name": "Amazon",
        "emoji": "📦",
        "kr": "세계 최대 이커머스 + 클라우드(AWS) 1위. 쇼핑몰과 서버 임대로 수익",
        "en": "World's largest e-commerce + #1 cloud (AWS). Revenue from shopping & server rental",
        "sector": "이커머스/클라우드" if lang == "한국어" else "E-commerce/Cloud"
    },
    "GOOGL": {
        "name": "Google (Alphabet)",
        "emoji": "🔎",
        "kr": "검색엔진 1위. 구글 검색 광고, 유튜브 광고, 클라우드로 수익",
        "en": "#1 search engine. Revenue from Google/YouTube ads and cloud services",
        "sector": "광고/클라우드" if lang == "한국어" else "Ads/Cloud"
    },
    "MSFT": {
        "name": "Microsoft",
        "emoji": "🪟",
        "kr": "윈도우, 오피스, 클라우드(Azure). 소프트웨어 구독료와 클라우드로 수익",
        "en": "Windows, Office, Azure cloud. Revenue from software subscriptions & cloud",
        "sector": "소프트웨어/클라우드" if lang == "한국어" else "Software/Cloud"
    },
    "META": {
        "name": "Meta (Facebook)",
        "emoji": "👥",
        "kr": "페이스북, 인스타그램, 왓츠앱 운영. SNS 광고로 대부분 수익",
        "en": "Facebook, Instagram, WhatsApp. Most revenue from social media ads",
        "sector": "소셜미디어" if lang == "한국어" else "Social Media"
    },
    
    # Fintech
    "SHOP": {
        "name": "Shopify",
        "emoji": "🛒",
        "kr": "온라인 쇼핑몰 구축 플랫폼. 소상공인이 쉽게 쇼핑몰 만들게 해줌",
        "en": "E-commerce platform. Helps small businesses create online stores easily",
        "sector": "이커머스" if lang == "한국어" else "E-commerce"
    },
    "UBER": {
        "name": "Uber",
        "emoji": "🚕",
        "kr": "차량 공유 + 음식 배달. 우버 택시와 우버이츠 수수료로 수익",
        "en": "Ride-sharing + food delivery. Revenue from Uber rides & Uber Eats fees",
        "sector": "모빌리티" if lang == "한국어" else "Mobility"
    },
    "SQ": {
        "name": "Block (Square)",
        "emoji": "💳",
        "kr": "결제 서비스 + 캐시앱. 소상공인 카드결제 수수료와 송금 서비스",
        "en": "Payment services + Cash App. Revenue from merchant fees & money transfers",
        "sector": "핀테크" if lang == "한국어" else "Fintech"
    },
    "PYPL": {
        "name": "PayPal",
        "emoji": "💰",
        "kr": "온라인 결제 서비스. 인터넷 결제 수수료로 수익 (벤모 포함)",
        "en": "Online payment service. Revenue from internet payment fees (incl. Venmo)",
        "sector": "핀테크" if lang == "한국어" else "Fintech"
    },
    "HOOD": {
        "name": "Robinhood",
        "emoji": "📱",
        "kr": "무료 주식거래 앱. 주문 흐름 판매와 프리미엄 구독으로 수익",
        "en": "Commission-free trading app. Revenue from order flow & premium subscriptions",
        "sector": "핀테크" if lang == "한국어" else "Fintech"
    },
    
    # Biotech
    "CRSP": {
        "name": "CRISPR Therapeutics",
        "emoji": "🧬",
        "kr": "유전자 가위 기술 회사. 유전병 치료제 개발 중 (아직 초기 단계)",
        "en": "Gene editing company. Developing treatments for genetic diseases (early stage)",
        "sector": "바이오" if lang == "한국어" else "Biotech"
    },
    "NTLA": {
        "name": "Intellia Therapeutics",
        "emoji": "🧬",
        "kr": "유전자 편집 치료제 개발. 체내에서 직접 유전자 수정하는 기술",
        "en": "Gene editing therapeutics. Technology to edit genes directly inside the body",
        "sector": "바이오" if lang == "한국어" else "Biotech"
    },
    "BEAM": {
        "name": "Beam Therapeutics",
        "emoji": "🧬",
        "kr": "정밀 유전자 편집. DNA 한 글자만 정확히 수정하는 기술 개발",
        "en": "Precision gene editing. Developing tech to edit single DNA letters precisely",
        "sector": "바이오" if lang == "한국어" else "Biotech"
    },
    "RXRX": {
        "name": "Recursion Pharma",
        "emoji": "🤖",
        "kr": "AI 신약 개발. 인공지능으로 신약 후보물질 발굴",
        "en": "AI drug discovery. Using AI to find new drug candidates",
        "sector": "바이오/AI" if lang == "한국어" else "Biotech/AI"
    },
    "DNA": {
        "name": "Ginkgo Bioworks",
        "emoji": "🦠",
        "kr": "합성생물학 플랫폼. 미생물을 프로그래밍해서 유용한 물질 생산",
        "en": "Synthetic biology platform. Programs microbes to produce useful materials",
        "sector": "바이오" if lang == "한국어" else "Biotech"
    },
    
    # Space/Energy
    "RKLB": {
        "name": "Rocket Lab",
        "emoji": "🚀",
        "kr": "소형 로켓 발사 회사. 인공위성을 우주로 쏘아 올려주는 서비스",
        "en": "Small rocket launch company. Service to send satellites into space",
        "sector": "우주항공" if lang == "한국어" else "Space"
    },
    "OKLO": {
        "name": "Oklo",
        "emoji": "⚛️",
        "kr": "소형 원자로 개발. 깨끗하고 안전한 차세대 원자력 발전",
        "en": "Small nuclear reactors. Clean and safe next-gen nuclear power",
        "sector": "에너지" if lang == "한국어" else "Energy"
    },
    "FLNC": {
        "name": "Fluence Energy",
        "emoji": "🔋",
        "kr": "대용량 에너지 저장. 태양광/풍력 전기를 저장하는 배터리 시스템",
        "en": "Grid-scale energy storage. Battery systems to store solar/wind power",
        "sector": "에너지" if lang == "한국어" else "Energy"
    },
    "TMUS": {
        "name": "T-Mobile",
        "emoji": "📶",
        "kr": "미국 2위 통신사. 휴대폰 요금제와 인터넷 서비스로 수익",
        "en": "#2 US telecom. Revenue from mobile plans and internet services",
        "sector": "통신" if lang == "한국어" else "Telecom"
    },
    "ASTS": {
        "name": "AST SpaceMobile",
        "emoji": "📡",
        "kr": "위성 직접 통신. 일반 스마트폰이 위성과 직접 통신하는 기술",
        "en": "Direct-to-phone satellite. Tech for regular smartphones to connect to satellites",
        "sector": "우주통신" if lang == "한국어" else "Space/Telecom"
    },
    
    # Growth Tech
    "U": {
        "name": "Unity",
        "emoji": "🎮",
        "kr": "게임 엔진 회사. 모바일 게임 개발 도구와 광고 플랫폼",
        "en": "Game engine company. Mobile game development tools and ad platform",
        "sector": "게임/소프트웨어" if lang == "한국어" else "Gaming/Software"
    },
    "NET": {
        "name": "Cloudflare",
        "emoji": "☁️",
        "kr": "인터넷 보안/성능. 웹사이트를 빠르고 안전하게 만들어주는 서비스",
        "en": "Internet security/performance. Makes websites faster and more secure",
        "sector": "클라우드/보안" if lang == "한국어" else "Cloud/Security"
    },
    "PATH": {
        "name": "UiPath",
        "emoji": "🤖",
        "kr": "업무 자동화(RPA). 반복적인 사무 업무를 로봇이 대신 처리",
        "en": "Robotic Process Automation. Robots handle repetitive office tasks",
        "sector": "소프트웨어" if lang == "한국어" else "Software"
    },
    "DKNG": {
        "name": "DraftKings",
        "emoji": "🏈",
        "kr": "스포츠 베팅 플랫폼. 미국 스포츠 도박 합법화 수혜주",
        "en": "Sports betting platform. Benefits from US sports gambling legalization",
        "sector": "도박/엔터" if lang == "한국어" else "Gaming/Entertainment"
    },
    "ROKU": {
        "name": "Roku",
        "emoji": "📺",
        "kr": "스트리밍 TV 플랫폼. TV에서 넷플릭스 등 볼 수 있게 해주는 기기/서비스",
        "en": "Streaming TV platform. Devices/services to watch Netflix etc. on TV",
        "sector": "미디어" if lang == "한국어" else "Media"
    }
}

# Define available tickers
core_tickers = ["TSLA", "NVDA", "COIN", "PLTR", "ISRG"]
watchlist_tickers = [
    "AMD", "AMZN", "GOOGL", "MSFT", "META",
    "SHOP", "UBER", "SQ", "PYPL", "HOOD",
    "CRSP", "NTLA", "BEAM", "RXRX", "DNA",
    "RKLB", "OKLO", "FLNC", "TMUS", "ASTS",
    "U", "NET", "PATH", "DKNG", "ROKU"
]
all_tickers = list(set(core_tickers + watchlist_tickers))

def get_company_description(ticker):
    """Get company description for a ticker"""
    info = company_info.get(ticker, {})
    if not info:
        return ticker, "", ""
    
    emoji = info.get("emoji", "")
    name = info.get("name", ticker)
    desc = info.get("kr" if lang == "한국어" else "en", "")
    sector = info.get("sector", "")
    return f"{emoji} {name}", desc, sector

# Format ticker options with company names for better UX
def format_ticker_option(ticker):
    info = company_info.get(ticker, {})
    emoji = info.get("emoji", "")
    name = info.get("name", ticker)
    return f"{emoji} {ticker} ({name})"

selected_tickers = st.sidebar.multiselect(
    "종목 선택" if lang == "한국어" else "Select Tickers",
    options=sorted(all_tickers),
    default=core_tickers,
    format_func=format_ticker_option
)

portfolio_input = {}
total_allocation = 0

st.sidebar.markdown("---")
st.sidebar.subheader("비중 설정 (%)" if lang == "한국어" else "Allocation (%)")

for ticker in selected_tickers:
    default_weight = 20 if ticker in core_tickers else 0
    weight = st.sidebar.number_input(f"{ticker} %", min_value=0, max_value=100, value=default_weight, key=f"weight_{ticker}")
    portfolio_input[ticker] = weight
    total_allocation += weight

if total_allocation != 100:
    st.sidebar.warning(f"합계: {total_allocation}% (100%가 되어야 해요)" if lang == "한국어" else f"Total: {total_allocation}% (Should be 100%)")
else:
    st.sidebar.success(f"합계: {total_allocation}% ✓" if lang == "한국어" else f"Total: {total_allocation}% ✓")

monthly_investment = st.sidebar.number_input(
    "월 투자금 ($)" if lang == "한국어" else "Monthly Budget ($)", 
    value=1000
)

watchlist = [ticker for ticker in all_tickers if ticker not in selected_tickers]

# --- 3. Main Dashboard ---
# Header
st.title(t["title"])
st.markdown(f"*{t['subtitle']}*")
st.markdown(f"**{t['date']}:** {datetime.now().strftime('%Y-%m-%d')} | {t['strategy']}")

# Beginner Guide (Collapsible)
with st.expander(t["guide_title"], expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(t["guide_dca"])
    with col2:
        st.info(t["guide_rsi"])
    with col3:
        st.info(t["guide_drawdown"])

st.markdown("---")

# Section 1: Market Weather
st.header(t["macro_header"])
st.caption(t["macro_desc"])

fed_rate, m2_growth = get_macro_data()

# Determine market status
if fed_rate > 4.5 or m2_growth < 0:
    market_status = "red"
    status_text = t["red"]
elif fed_rate > 3.0:
    market_status = "yellow"
    status_text = t["yellow"]
else:
    market_status = "green"
    status_text = t["green"]

col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    st.metric(
        label=t["fed_rate"],
        value=f"{fed_rate:.2f}%",
        delta=t["target_range"],
        help=t["fed_rate_help"]
    )

with col2:
    st.metric(
        label=t["m2_growth"],
        value=f"+{m2_growth:.2f}%",
        delta=t["liquidity"],
        help=t["m2_help"]
    )

with col3:
    st.markdown(get_signal_html(market_status, f"{t['stance']}: {status_text}"), unsafe_allow_html=True)

st.markdown("---")

# Section 2: Portfolio Health
st.header(t["portfolio_header"])
st.caption(t["portfolio_desc"])

col_refresh, col_space = st.columns([1, 5])
with col_refresh:
    if st.button(t["refresh"], use_container_width=True):
        st.cache_data.clear()

with st.spinner(t["fetching"]):
    df = get_stock_data(portfolio_input.keys())

if not df.empty:
    # Company Cards with RSI Gauges
    st.subheader("📊 " + ("내 종목 현황" if lang == "한국어" else "My Stocks Status"))
    
    # Create cards for each stock
    num_stocks = len(df)
    cols_per_row = min(3, num_stocks)  # 3 cards per row for better readability
    
    ticker_col = "티커" if lang == "한국어" else "Symbol"
    name_col = "종목" if lang == "한국어" else "Ticker"
    sector_col = "섹터" if lang == "한국어" else "Sector"
    price_col = "가격" if lang == "한국어" else "Price"
    high_col = "52주 최고" if lang == "한국어" else "52W High"
    dd_col = "낙폭" if lang == "한국어" else "Drawdown"
    
    for i in range(0, num_stocks, cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < num_stocks:
                row = df.iloc[i + j]
                ticker_symbol = row[ticker_col]
                company = company_info.get(ticker_symbol, {})
                
                with col:
                    # Company info card
                    with st.container():
                        st.markdown(f"### {row[name_col]}")
                        st.caption(f"**{row[sector_col]}** | {ticker_symbol}")
                        
                        # Company description
                        desc = company.get("kr" if lang == "한국어" else "en", "")
                        if desc:
                            st.info(f"💡 {desc}")
                        
                        # Price info
                        price = row[price_col]
                        high_52 = row[high_col]
                        drawdown = row[dd_col]
                        
                        price_col1, price_col2 = st.columns(2)
                        with price_col1:
                            st.metric("현재가" if lang == "한국어" else "Price", f"${price:.2f}")
                        with price_col2:
                            dd_color = "🟢" if drawdown < -15 else "🔴" if drawdown > -5 else "⚪"
                            st.metric("고점대비" if lang == "한국어" else "From High", f"{drawdown:.1f}%", delta=dd_color)
                        
                        # RSI Gauge
                        fig = create_rsi_gauge(row['RSI'], ticker_symbol)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")

    # Summary Data Table
    with st.expander("📋 " + ("전체 데이터 보기" if lang == "한국어" else "View All Data")):
        # Style the dataframe
        def style_rsi(val):
            if val < 30:
                return 'background-color: #d4edda; color: #155724; font-weight: bold'
            elif val > 70:
                return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
            return ''
        
        def style_drawdown(val):
            if val < -20:
                return 'background-color: #d4edda; color: #155724'
            return ''
        
        format_dict = {
            price_col: "${:.2f}", 
            high_col: "${:.2f}", 
            dd_col: "{:.1f}%", 
            "RSI": "{:.0f}"
        }
        
        styled_df = df.style.applymap(style_rsi, subset=['RSI'])\
                           .applymap(style_drawdown, subset=[dd_col])\
                           .format(format_dict)
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Insights - Clear action items
    st.subheader(t["insights"])
    
    # Use correct column names based on language
    ticker_col = "티커" if lang == "한국어" else "Symbol"
    name_col = "종목" if lang == "한국어" else "Ticker"
    dd_col = "낙폭" if lang == "한국어" else "Drawdown"
    
    insights_found = False
    for index, row in df.iterrows():
        ticker = row[ticker_col]
        ticker_name = row[name_col]
        rsi = row['RSI']
        dd = row[dd_col]
        
        if rsi < 35:
            st.success(f"**{ticker_name}** (RSI: {rsi:.0f}) - {t['oversold']}")
            insights_found = True
        elif rsi > 70:
            st.warning(f"**{ticker_name}** (RSI: {rsi:.0f}) - {t['overbought']}")
            insights_found = True
        
        if dd < -20:
            st.info(f"**{ticker_name}** ({dd:.1f}%) - {t['drawdown']}")
            insights_found = True
    
    if not insights_found:
        st.info("✅ " + ("모든 종목이 적정 가격대에 있어요. 평소대로 투자하세요!" if lang == "한국어" else "All stocks are fairly priced. Continue your regular investment!"))

    st.markdown("---")

    # Section 3: Smart DCA Calculator
    st.header(t["calc_header"])
    st.write(t["calc_desc"].format(monthly_investment))

    rebalance_plan = []
    total_suggested = 0
    
    ticker_col = "티커" if lang == "한국어" else "Symbol"
    
    for ticker, target_pct in portfolio_input.items():
        ticker_data = df[df[ticker_col] == ticker]
        if not ticker_data.empty:
            rsi = ticker_data['RSI'].values[0]
            adjusted_weight = target_pct
            
            action = t["normal"]
            if rsi < 40: 
                adjusted_weight *= 1.2
                action = t["buy_more"]
            elif rsi > 70: 
                adjusted_weight *= 0.8
                action = t["buy_less"]
            
            amount = monthly_investment * (adjusted_weight / 100)
            total_suggested += amount
            
            # Get company info
            company = company_info.get(ticker, {})
            company_name = f"{company.get('emoji', '')} {company.get('name', ticker)}"
            
            rebalance_plan.append({
                "종목" if lang == "한국어" else "Stock": company_name,
                "티커" if lang == "한국어" else "Ticker": ticker,
                "목표 비중" if lang == "한국어" else "Target": f"{target_pct}%",
                "RSI": f"{rsi:.0f}",
                "추천" if lang == "한국어" else "Action": action,
                "매수액" if lang == "한국어" else "Buy ($)": f"${amount:.0f}"
            })

    # Action Summary Card
    st.markdown(get_action_card_html(total_suggested, len(rebalance_plan), t["total_action"]), unsafe_allow_html=True)
    
    # Detailed plan table
    plan_df = pd.DataFrame(rebalance_plan)
    st.dataframe(plan_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Section 4: Bargain Hunter
    st.header(t["discovery_header"])
    st.caption(t["discovery_desc"])
    
    with st.spinner("🔍 " + ("스캔 중..." if lang == "한국어" else "Scanning...")):
        opportunities = scan_market_opportunities(watchlist)
        
    if not opportunities.empty:
        st.success(t["discovery_found"].format(len(opportunities)))
        st.dataframe(opportunities, use_container_width=True, hide_index=True)
    else:
        st.info(t["discovery_none"])

    st.markdown("---")

    # Section 5: News
    st.header(t["news_header"])
    
    tabs = st.tabs(list(portfolio_input.keys()))
    
    for i, ticker in enumerate(portfolio_input.keys()):
        with tabs[i]:
            news_items = get_news(ticker)
            if news_items:
                for news in news_items:
                    source_badge = f"[{news['source']}]"
                    with st.expander(f"{source_badge} {news['title']}"):
                        st.caption(f"Published: {news['published']}")
                        
                        summary = get_article_summary(news['link'])
                        
                        if "요약 정보를 가져올 수 없습니다" in summary and news.get('rss_summary'):
                            st.warning("🔒 " + ("원문 접근이 제한되어 뉴스 피드 요약본을 표시합니다." if lang == "한국어" else "Original article restricted. Showing RSS summary."))
                            st.write(news['rss_summary'])
                        else:
                            st.write(summary)
                            
                        st.markdown(f"[{'원문 보기' if lang == '한국어' else 'Read Full Article'}]({news['link']})")
            else:
                st.info(t["no_news"])

else:
    st.error("❌ " + ("주식 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요." if lang == "한국어" else "Failed to load stock data. Please try again later."))

# Footer
st.markdown("---")
st.caption(t["footer"])
