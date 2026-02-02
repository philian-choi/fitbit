import streamlit as st
import pandas as pd
import yfinance as yf
from fredapi import Fred
from datetime import datetime
import os
import feedparser
from technical_analysis import ComprehensiveAnalyzer, TechnicalAnalyzer, FundamentalAnalyzer, MarketRegimeAnalyzer, SignalStrength

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
    
    /* Score bar (new comprehensive) */
    .score-container {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .score-bar {
        width: 80px;
        height: 8px;
        border-radius: 4px;
        background: linear-gradient(to right, #ef4444 0%, #fbbf24 50%, #10b981 100%);
        position: relative;
    }
    .score-dot {
        position: absolute;
        top: -4px;
        width: 16px;
        height: 16px;
        background: white;
        border-radius: 50%;
        border: 2px solid #1d4ed8;
        transform: translateX(-50%);
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .score-text {
        font-size: 0.85rem;
        font-weight: 600;
        color: #e2e8f0 !important;
    }
    .confidence-text {
        font-size: 0.7rem;
        color: #64748b !important;
    }
    
    /* Score breakdown */
    .score-breakdown {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.4rem;
        flex-wrap: wrap;
    }
    .score-chip {
        font-size: 0.65rem;
        padding: 0.15rem 0.4rem;
        border-radius: 4px;
        background: rgba(255,255,255,0.08);
        color: #94a3b8 !important;
    }
    .score-chip-positive { color: #34d399 !important; }
    .score-chip-negative { color: #f87171 !important; }
    
    /* Warning badge */
    .warning-badge {
        font-size: 0.7rem;
        color: #fbbf24 !important;
        background: rgba(251, 191, 36, 0.15);
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        margin-top: 0.3rem;
        display: inline-block;
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
# category: ai, crypto, robot, energy, space, health, commerce
company_info = {
    "BTC-USD": {
        "name": "Bitcoin",
        "kr": "디지털 금, 가치 저장 수단",
        "en": "Digital gold, store of value",
        "category": "crypto",
        "tam": "$16T",
        "cagr": "63%",
        "detail_kr": "[BTC] 2030년 시총 16조 달러(2.2경원), 1 BTC = 약 10억원 전망. 금 시장의 40%를 대체하고, 기관/국가들이 보유하기 시작했어요. ETF 승인으로 접근성도 좋아졌어요.",
        "detail_en": "[BTC] 2030 market cap $16T, 1 BTC = ~$760K. Replacing 40% of gold market, institutions & nations now holding. ETF approval made access easier."
    },
    "TSLA": {
        "name": "Tesla",
        "kr": "전기차 1위 + 로보택시 + 로봇",
        "en": "#1 EV + Robotaxi + Robots",
        "category": "robot",
        "tam": "$34T",
        "cagr": "50%+",
        "detail_kr": "[EV/Robot] 전기차만 만드는 게 아니에요. 2030년까지 로보택시 시장이 34조 달러(4.7경원)로 성장하는데, Tesla의 자율주행(FSD) 기술이 1등이에요. 휴머노이드 로봇(Optimus)도 개발 중이고, 에너지 저장장치(Megapack) 매출도 급성장해요.",
        "detail_en": "[EV/Robot] Not just EVs. Robotaxi market to reach $34T by 2030. Tesla leads in self-driving (FSD) and is building humanoid robots (Optimus). Energy storage (Megapack) revenue growing fast too."
    },
    "NVDA": {
        "name": "NVIDIA",
        "kr": "AI 반도체 독보적 1위",
        "en": "#1 AI chips dominant",
        "category": "ai",
        "tam": "$1.4T",
        "cagr": "29%",
        "detail_kr": "[AI Chip] AI의 두뇌를 만드는 회사예요. AI 칩 시장 점유율 85%, 마진 75%로 '독점'에 가까워요. 2030년까지 AI 인프라 투자가 1.4조 달러(1,900조원)로 성장하는데, 그 핵심 수혜자예요.",
        "detail_en": "[AI Chip] Makes the 'brain' of AI. 85% market share, 75% margins - near monopoly. AI infrastructure to reach $1.4T by 2030, and NVIDIA is the core beneficiary."
    },
    "COIN": {
        "name": "Coinbase",
        "kr": "암호화폐 거래소 + Base 체인",
        "en": "Crypto exchange + Base chain",
        "category": "crypto",
        "tam": "$11T",
        "cagr": "100%+",
        "detail_kr": "[Crypto] 미국 최대 암호화폐 거래소예요. 비트코인 ETF 수탁도 맡고, 자체 블록체인(Base)으로 DeFi 생태계도 구축 중이에요. 비트코인이 2030년 760만원에서 10억원 간다면 가장 큰 수혜주 중 하나예요.",
        "detail_en": "[Crypto] Largest US crypto exchange. Custody for Bitcoin ETFs + building Base chain for DeFi. If Bitcoin reaches $760K by 2030, COIN is a major beneficiary."
    },
    "PLTR": {
        "name": "Palantir",
        "kr": "기업용 AI 플랫폼",
        "en": "Enterprise AI platform",
        "category": "ai",
        "tam": "$13T",
        "cagr": "56%",
        "detail_kr": "[AI SW] 정부와 대기업을 위한 AI 데이터 분석 플랫폼(AIP)을 만들어요. '지능의 비용'이 99% 하락하면서 소프트웨어 시장이 2030년 3.4조~13조 달러로 성장하는데, Palantir가 핵심 기업이에요.",
        "detail_en": "[AI SW] AI data platform for governments & enterprises. As 'cost of intelligence' drops 99%, software market grows to $3.4-13T by 2030. Palantir is a key player."
    },
    "ISRG": {
        "name": "Intuitive",
        "kr": "수술 로봇 세계 1위",
        "en": "World #1 surgical robots",
        "category": "health",
        "tam": "$26T",
        "cagr": "25%",
        "detail_kr": "[Med Robot] 다빈치 수술 로봇의 제조사예요. 로봇 시장이 26조 달러(3.6경원) 규모인데, 의료 분야는 가장 빠르게 자동화되는 영역 중 하나예요. AI로 수술 정밀도가 계속 높아지고 있어요.",
        "detail_en": "[Med Robot] Makes da Vinci surgical robots. Robotics TAM is $26T, and healthcare is one of the fastest automating sectors. AI is continuously improving surgical precision."
    },
    "AMD": {
        "name": "AMD",
        "kr": "AI 칩 가성비 도전자",
        "en": "AI chip value challenger",
        "category": "ai",
        "tam": "$1.4T",
        "cagr": "29%",
        "detail_kr": "[AI Chip] NVIDIA의 유일한 경쟁자예요. 새 칩(MI355X)이 메모리 288GB로 NVIDIA보다 크고, 가격 대비 성능도 더 좋아요. 특히 'AI 추론' 시장에서 점유율이 빠르게 올라가고 있어요.",
        "detail_en": "[AI Chip] NVIDIA's only real competitor. New MI355X has 288GB memory (more than NVIDIA) with better price-performance. Growing share in AI inference market."
    },
    "AMZN": {
        "name": "Amazon",
        "kr": "AI 쇼핑 + 클라우드 + 로봇",
        "en": "AI shopping + Cloud + Robots",
        "category": "ai",
        "tam": "$900B",
        "cagr": "105%",
        "detail_kr": "[Cloud/Robot] 세계 최대 온라인 쇼핑몰이자 클라우드(AWS) 1위예요. AI 쇼핑 에이전트(Rufus), 창고 로봇(직원 1만명당 1,279대), 드론 배송(Prime Air)까지 미래 기술을 모두 갖고 있어요.",
        "detail_en": "[Cloud/Robot] World's largest e-commerce + #1 cloud (AWS). Has AI shopping agent (Rufus), warehouse robots (1,279 per 10K employees), and drone delivery (Prime Air)."
    },
    "GOOGL": {
        "name": "Google",
        "kr": "AI 검색 + 자율주행 + 클라우드",
        "en": "AI search + Self-driving + Cloud",
        "category": "ai",
        "tam": "$34T",
        "cagr": "40%",
        "detail_kr": "[Search/AV] 검색의 왕이지만, AI 검색(ChatGPT 등)에 위협받고 있어요. 하지만 자율주행(Waymo)에서 기술 1등이고, 자체 AI 칩(TPU)도 있어요. 성공적으로 전환하면 더 커질 수 있어요.",
        "detail_en": "[Search/AV] Search king but threatened by AI search. However, leads in self-driving (Waymo) and has own AI chips (TPU). Could grow bigger with successful transition."
    },
    "MSFT": {
        "name": "Microsoft",
        "kr": "Copilot AI + Azure 클라우드",
        "en": "Copilot AI + Azure Cloud",
        "category": "ai",
        "tam": "$13T",
        "cagr": "56%",
        "detail_kr": "[AI SW] OpenAI와 독점 파트너십으로 AI 시대를 선도해요. 모든 오피스 제품에 AI(Copilot)를 넣고, 기업용 AI 시장을 장악 중이에요. 안정적이면서도 AI 성장의 수혜를 받는 종목이에요.",
        "detail_en": "[AI SW] Exclusive OpenAI partnership leads AI era. Adding Copilot AI to all Office products, dominating enterprise AI. Stable yet benefits from AI growth."
    },
    "META": {
        "name": "Meta",
        "kr": "SNS AI + 스마트 안경",
        "en": "Social AI + Smart glasses",
        "category": "ai",
        "tam": "$900B",
        "cagr": "105%",
        "detail_kr": "[AI Consumer] 페이스북, 인스타그램의 30억 사용자 데이터로 AI를 학습시켜요. Meta AI가 개인 맞춤 추천을 하고, Ray-Ban 스마트 안경도 인기예요. AI 소비자 시장(2030년 9000억 달러)의 핵심 주자예요.",
        "detail_en": "[AI Consumer] Trains AI on 3B users' data from FB/IG. Meta AI does personalized recommendations, Ray-Ban smart glasses popular. Key player in AI consumer market ($900B by 2030)."
    },
    "SHOP": {
        "name": "Shopify",
        "kr": "AI 커머스 플랫폼의 허브",
        "en": "AI commerce platform hub",
        "category": "commerce",
        "tam": "$8T",
        "cagr": "50%",
        "detail_kr": "[Commerce] 수백만 온라인 상점을 운영하게 해주는 플랫폼이에요. Google과 함께 'AI 커머스 프로토콜(UCP)'을 만들고 있어요. AI가 대신 쇼핑하는 시대(2030년 8조 달러 거래)의 핵심 인프라예요.",
        "detail_en": "[Commerce] Platform powering millions of online stores. Building 'Universal Commerce Protocol' with Google. Core infrastructure for AI shopping era ($8T transactions by 2030)."
    },
    "UBER": {
        "name": "Uber",
        "kr": "라이드쉐어 + 로보택시 연결",
        "en": "Ride-share + Robotaxi network",
        "category": "robot",
        "tam": "$34T",
        "cagr": "40%",
        "detail_kr": "[Mobility] 차량 호출/배달 앱 1위예요. 자율주행은 직접 못 만들지만, Waymo 같은 로보택시 회사와 협력해요. 로보택시 시대에도 '앱'으로 살아남을 수 있는지가 관건이에요.",
        "detail_en": "[Mobility] #1 ride-hail/delivery app. Can't build self-driving but partners with Waymo. Key question: can they survive as 'the app' in robotaxi era?"
    },
    "SQ": {
        "name": "Block",
        "kr": "비트코인 + 결제 서비스",
        "en": "Bitcoin + Payment services",
        "category": "crypto",
        "tam": "$16T",
        "cagr": "63%",
        "detail_kr": "[BTC Payment] Cash App으로 비트코인 매매도 가능하고, 비트코인 지갑(Bitkey)도 만들어요. 비트코인 결제 인프라의 핵심 회사예요. 비트코인이 오르면 같이 오르는 구조예요.",
        "detail_en": "[BTC Payment] Cash App enables Bitcoin trading, also makes Bitkey wallet. Core Bitcoin payment infrastructure. Benefits directly from Bitcoin price increases."
    },
    "PYPL": {
        "name": "PayPal",
        "kr": "스테이블코인 + 온라인 결제",
        "en": "Stablecoin + Online payments",
        "category": "crypto",
        "tam": "$11T",
        "cagr": "100%+",
        "detail_kr": "[Stablecoin] 온라인 결제의 원조예요. 자체 스테이블코인(PYUSD)이 1년만에 6배 성장했어요. 토큰화 자산 시장(2030년 11조 달러)에서 결제 인프라로 자리잡을 수 있어요.",
        "detail_en": "[Stablecoin] Pioneer of online payments. Own stablecoin (PYUSD) grew 6x in one year. Could become payment infrastructure for tokenized assets ($11T by 2030)."
    },
    "RKLB": {
        "name": "Rocket Lab",
        "kr": "소형 로켓 + 우주 시스템",
        "en": "Small rockets + Space systems",
        "category": "space",
        "tam": "$160B",
        "cagr": "30%",
        "detail_kr": "[Space] SpaceX 다음가는 민간 로켓 회사예요. 소형 위성 발사에 특화되어 있어요. 위성 통신 시장이 2030년 1600억 달러(210조원)로 성장하는데, 발사 비용은 계속 떨어지고 있어요.",
        "detail_en": "[Space] Second largest private rocket company after SpaceX. Specializes in small satellite launches. Satellite market to reach $160B by 2030, launch costs keep dropping."
    },
    "NET": {
        "name": "Cloudflare",
        "kr": "인터넷 인프라 + AI 엣지",
        "en": "Internet infra + AI edge",
        "category": "ai",
        "tam": "$1.4T",
        "cagr": "29%",
        "detail_kr": "[Infra] 전 세계 인터넷 트래픽의 상당 부분을 처리하는 보안/가속 서비스예요. AI가 더 많이 쓰일수록 인터넷 인프라도 더 중요해져요. AI 시대의 숨은 수혜주예요.",
        "detail_en": "[Infra] Security/acceleration for major portion of internet traffic. As AI usage grows, internet infrastructure becomes more critical. Hidden beneficiary of AI era."
    },
    "OKLO": {
        "name": "Oklo",
        "kr": "소형 원전 (AI 데이터센터용)",
        "en": "Small nuclear (AI data centers)",
        "category": "energy",
        "tam": "$10T",
        "cagr": "40%",
        "detail_kr": "[Nuclear] Sam Altman(OpenAI CEO)이 이사회 의장인 소형 원전(SMR) 회사예요. AI 데이터센터는 엄청난 전력이 필요한데, Oklo가 그 전력을 공급해요. AI 시대의 필수 인프라.",
        "detail_en": "[Nuclear] SMR company with Sam Altman (OpenAI CEO) as chairman. AI data centers need massive power, Oklo supplies it. Essential infrastructure for AI era."
    },
    "CRSP": {
        "name": "CRISPR Tx",
        "kr": "유전자 가위 치료제 1호",
        "en": "Gene editing therapeutics #1",
        "category": "health",
        "tam": "$2.8T",
        "cagr": "50%+",
        "detail_kr": "[Gene Edit] 세계 최초로 유전자 편집 치료제를 승인받았어요. 겸상적혈구 빈혈증을 '완치'해요. 심혈관 질환까지 확장하면 시장이 2.8조 달러(3,800조원)예요. 한 번 치료로 평생 효과.",
        "detail_en": "[Gene Edit] First approved gene editing therapy. Cures sickle cell disease. Expanding to cardiovascular = $2.8T market. One treatment, lifetime effect."
    },
}

default_tickers = ["BTC-USD", "TSLA", "NVDA", "COIN"]  # 기본 4종목 (비트코인 포함)
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

@st.cache_data(ttl=1800, show_spinner=False)
def get_market_analysis():
    """시장 환경 분석 (한 번만 실행)"""
    try:
        market_analyzer = MarketRegimeAnalyzer()
        return market_analyzer.analyze()
    except Exception as e:
        return {'market_score': 0, 'max_market_score': 15, 'warnings': [], 'indicator_results': {}}

@st.cache_data(ttl=1800, show_spinner=False)
def get_comprehensive_analysis(ticker):
    """종목별 종합 분석"""
    try:
        # 기술적 분석
        tech_analyzer = TechnicalAnalyzer(ticker)
        tech_result = tech_analyzer.analyze()
        
        if 'error' in tech_result:
            return None
        
        # 펀더멘털 분석
        fund_analyzer = FundamentalAnalyzer(ticker)
        fund_result = fund_analyzer.analyze()
        
        return {
            'technical': tech_result,
            'fundamental': fund_result if 'error' not in fund_result else None
        }
    except Exception as e:
        return None

@st.cache_data(ttl=1800)
def get_stock_data(tickers, lang="한국어"):
    is_kr = lang == "한국어"
    data = []
    
    # 시장 환경 분석 (공유)
    market_result = get_market_analysis()
    market_score = market_result.get('market_score', 0)
    
    for ticker in tickers:
        try:
            # 종합 분석 가져오기
            analysis = get_comprehensive_analysis(ticker)
            
            if analysis is None:
                continue
            
            tech = analysis['technical']
            fund = analysis['fundamental']
            
            price = tech.get('price', 0)
            if price == 0:
                continue
            
            # 점수 계산
            tech_score = tech.get('technical_score', 0)
            fund_score = fund.get('fundamental_score', 0) if fund else 0
            total_score = tech_score + fund_score + market_score
            max_score = 100
            
            # 신뢰도 계산 (지표 일치도)
            scores = tech.get('scores', {})
            indicators = tech.get('indicators', {})
            
            momentum_scores = [scores.get('RSI', 0), scores.get('Stochastic', 0), scores.get('MACD', 0)]
            positive_count = sum(1 for s in momentum_scores if s > 0)
            negative_count = sum(1 for s in momentum_scores if s < 0)
            
            if positive_count == 3 or negative_count == 3:
                confidence = 0.9
            elif positive_count == 2 or negative_count == 2:
                confidence = 0.7
            else:
                confidence = 0.5
            
            # 거래량 확인 반영
            volume_conf = indicators.get('Volume_Confirmation', 0.7)
            confidence = confidence * 0.7 + volume_conf * 0.3
            
            # 신호 결정
            if total_score >= 40:
                action = "strong_buy"
                signal_text = "강력 매수" if is_kr else "STRONG BUY"
            elif total_score >= 20:
                action = "buy"
                signal_text = "매수" if is_kr else "BUY"
            elif total_score >= 5:
                action = "weak_buy"
                signal_text = "약한 매수" if is_kr else "WEAK BUY"
            elif total_score <= -40:
                action = "strong_sell"
                signal_text = "강력 매도" if is_kr else "STRONG SELL"
            elif total_score <= -20:
                action = "sell"
                signal_text = "매도" if is_kr else "SELL"
            elif total_score <= -5:
                action = "weak_sell"
                signal_text = "약한 매도" if is_kr else "WEAK SELL"
            else:
                action = "hold"
                signal_text = "중립" if is_kr else "NEUTRAL"
            
            # 경고 수집
            warnings = []
            warnings.extend(tech.get('warnings', []))
            if fund:
                warnings.extend(fund.get('warnings', []))
            
            # RSI (레거시 호환)
            rsi = indicators.get('RSI', 50)
            
            company = company_info.get(ticker, {"name": ticker, "kr": "", "en": "", "detail_kr": "", "detail_en": "", "category": "", "tam": "", "cagr": ""})
            
            # 일등락률 계산
            prev_close = tech.get('prev_close', price)
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
            
            data.append({
                "ticker": ticker,
                "name": company["name"],
                "desc": company["kr"] if is_kr else company["en"],
                "detail": company.get("detail_kr", "") if is_kr else company.get("detail_en", ""),
                "category": company.get("category", ""),
                "tam": company.get("tam", ""),
                "cagr": company.get("cagr", ""),
                "price": price,
                "change_pct": round(change_pct, 2),
                "rsi": round(rsi, 1),
                "total_score": total_score,
                "max_score": max_score,
                "tech_score": tech_score,
                "fund_score": fund_score,
                "market_score": market_score,
                "confidence": confidence,
                "action": action,
                "signal_text": signal_text,
                "warnings": warnings[:2],  # 최대 2개 경고만
                "scores": scores,
            })
        except Exception as e:
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

@st.cache_data(ttl=3600)
def get_sparkline_data(ticker, days=30):
    """최근 30일 종가 데이터 (스파크라인용)"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        if len(hist) > 0:
            prices = hist['Close'].tolist()
            return prices
        return []
    except:
        return []

def generate_sparkline_svg(prices, width=80, height=24):
    """SVG 스파크라인 생성"""
    if not prices or len(prices) < 2:
        return ""
    
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price if max_price != min_price else 1
    
    # 포인트 생성
    points = []
    for i, price in enumerate(prices):
        x = (i / (len(prices) - 1)) * width
        y = height - ((price - min_price) / price_range) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")
    
    # 시작과 끝 가격 비교
    is_up = prices[-1] >= prices[0]
    color = "#34d399" if is_up else "#f87171"
    
    path_d = "M " + " L ".join(points)
    
    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display: inline-block; vertical-align: middle;">
        <path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>'''

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

# 카테고리 정보
CATEGORIES = {
    "all": {"kr": "전체", "en": "All", "icon": "ALL"},
    "ai": {"kr": "AI", "en": "AI", "icon": "AI"},
    "crypto": {"kr": "암호화폐", "en": "Crypto", "icon": "BTC"},
    "robot": {"kr": "로봇/자율주행", "en": "Robotics", "icon": "BOT"},
    "energy": {"kr": "에너지", "en": "Energy", "icon": "PWR"},
    "space": {"kr": "우주", "en": "Space", "icon": "SPC"},
    "health": {"kr": "헬스케어", "en": "Healthcare", "icon": "BIO"},
    "commerce": {"kr": "커머스", "en": "Commerce", "icon": "COM"},
}

# 테마 필터 (Quick buttons)
st.markdown(f"<div style='margin-bottom: 0.5rem; font-size: 0.85rem; color: #94a3b8;'>{'테마별 보기' if is_kr else 'Filter by Theme'}</div>", unsafe_allow_html=True)

if "category_filter" not in st.session_state:
    st.session_state["category_filter"] = "all"

cat_cols = st.columns(len(CATEGORIES))
for i, (cat_key, cat_info) in enumerate(CATEGORIES.items()):
    with cat_cols[i]:
        cat_label = f"{cat_info['icon']}"
        is_selected = st.session_state["category_filter"] == cat_key
        if st.button(cat_label, key=f"cat_{cat_key}", use_container_width=True, 
                     type="primary" if is_selected else "secondary"):
            st.session_state["category_filter"] = cat_key
            # 카테고리에 맞는 종목 자동 선택
            if cat_key == "all":
                filtered_tickers = default_tickers
            else:
                filtered_tickers = [t for t, info in company_info.items() if info.get("category") == cat_key]
            if filtered_tickers:
                st.session_state["selected"] = filtered_tickers[:5]  # 최대 5개
                # 비중 재설정
                equal_weight = 100 // len(st.session_state["selected"])
                st.session_state["weights"] = {t: equal_weight for t in st.session_state["selected"]}
            st.rerun()

# 현재 필터 표시
current_cat = st.session_state.get("category_filter", "all")
cat_display = CATEGORIES.get(current_cat, {})
st.caption(f"{cat_display.get('icon', '')} {cat_display.get('kr' if is_kr else 'en', '')}")

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
    
    # 종합 점수 기반 매수 금액 조정
    total_score = stock.get("total_score", 0)
    
    if total_score >= 30:
        mult = 1.4  # 강한 매수 신호 -> 40% 더 매수
    elif total_score >= 15:
        mult = 1.2  # 매수 신호 -> 20% 더 매수
    elif total_score <= -30:
        mult = 0.5  # 강한 매도 신호 -> 50% 덜 매수
    elif total_score <= -15:
        mult = 0.7  # 매도 신호 -> 30% 덜 매수
    else:
        mult = 1.0  # 중립 -> 기본 금액
    
    suggested = base * mult
    total_suggested += suggested
    recommendations.append({
        **stock, 
        "suggested": suggested, 
        "weight": ticker_weight,
        "detail": stock.get("detail", "")
    })

# 통계 계산 (새로운 기준)
buy_signals = len([s for s in stock_data if s.get("total_score", 0) >= 15])
sell_signals = len([s for s in stock_data if s.get("total_score", 0) <= -15])

# === STATS (compact) ===
st.markdown(f"""
<div class="stats-row">
    <div class="stat-box">
        <div class="stat-value" style="color: #60a5fa;">${total_suggested:,.0f}</div>
        <div class="stat-label">{"이번 달 투자" if is_kr else "This Month"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value stat-green">{buy_signals}</div>
        <div class="stat-label">{"매수 신호" if is_kr else "Buy"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value stat-red">{sell_signals}</div>
        <div class="stat-label">{"매도 신호" if is_kr else "Sell"}</div>
    </div>
    <div class="stat-box">
        <div class="stat-value">{fed_rate:.1f}%</div>
        <div class="stat-label">{"금리" if is_kr else "Rate"}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === STOCK LIST ===
if recommendations:
    st.markdown(f'<div class="section-title">{"투자 계획" if is_kr else "Investment Plan"}</div>', unsafe_allow_html=True)
    
    # Sort by total score (best first)
    sorted_recs = sorted(recommendations, key=lambda x: x.get("total_score", 0), reverse=True)
    
    for rec in sorted_recs:
        action = rec.get("action", "hold")
        total_score = rec.get("total_score", 0)
        confidence = rec.get("confidence", 0.5)
        signal_text = rec.get("signal_text", "중립" if is_kr else "NEUTRAL")
        
        # Action styling
        if action in ["strong_buy", "buy", "weak_buy"]:
            action_class = "action-buy"
            action_icon = ICONS["check"]
            action_display = "더 사기" if is_kr else "BUY+"
        elif action in ["strong_sell", "sell", "weak_sell"]:
            action_class = "action-sell"
            action_icon = ICONS["x"]
            action_display = "덜 사기" if is_kr else "BUY-"
        else:
            action_class = "action-hold"
            action_icon = ICONS["minus"]
            action_display = "유지" if is_kr else "HOLD"
        
        weight_text = f"{rec['weight']}%"
        
        # Score bar position (0-100 scale, where -100 to +100 maps to 0% to 100%)
        score_position = max(0, min(100, (total_score + 100) / 2))
        
        # Score color
        if total_score >= 20:
            score_color = "#34d399"  # green
        elif total_score <= -20:
            score_color = "#f87171"  # red
        else:
            score_color = "#fbbf24"  # yellow
        
        # Score breakdown chips
        tech_score = rec.get("tech_score", 0)
        fund_score = rec.get("fund_score", 0)
        market_score = rec.get("market_score", 0)
        
        tech_class = "score-chip-positive" if tech_score > 0 else ("score-chip-negative" if tech_score < 0 else "")
        fund_class = "score-chip-positive" if fund_score > 0 else ("score-chip-negative" if fund_score < 0 else "")
        market_class = "score-chip-positive" if market_score > 0 else ("score-chip-negative" if market_score < 0 else "")
        
        # 상세 설명 가져오기
        detail_text = rec.get('detail', '')
        warnings = rec.get('warnings', [])
        
        # 주가와 등락률
        price = rec.get('price', 0)
        change_pct = rec.get('change_pct', 0)
        change_color = "#34d399" if change_pct >= 0 else "#f87171"
        change_sign = "+" if change_pct >= 0 else ""
        
        # TAM/CAGR
        tam = rec.get('tam', '')
        cagr = rec.get('cagr', '')
        category = rec.get('category', '')
        
        # 카테고리 태그
        category_tags = {
            'ai': 'AI', 'crypto': 'BTC', 'robot': 'BOT', 
            'energy': 'PWR', 'space': 'SPC', 'health': 'BIO', 'commerce': 'COM'
        }
        cat_icon = category_tags.get(category, '')
        
        st.markdown(f"""
        <div class="stock-item">
            <div class="stock-row">
                <div>
                    <span class="stock-name">{rec['name']}</span>
                    <span class="stock-ticker">{rec['ticker']}</span>
                    <span class="stock-ticker">{weight_text}</span>
                    {f'<span class="stock-ticker">{cat_icon}</span>' if cat_icon else ''}
                </div>
                <div style="text-align: right;">
                    <div class="buy-amount">${rec['suggested']:.0f}</div>
                    <div style="font-size: 0.75rem; color: #94a3b8;">{"이번달" if is_kr else "this mo."}</div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 0.3rem 0;">
                <div class="stock-desc">{rec['desc']}</div>
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    {generate_sparkline_svg(get_sparkline_data(rec['ticker']))}
                    <div style="text-align: right;">
                        <span style="font-size: 1rem; font-weight: 600; color: #e2e8f0;">${price:,.2f}</span>
                        <span style="font-size: 0.8rem; color: {change_color}; margin-left: 0.3rem;">{change_sign}{change_pct:.1f}%</span>
                    </div>
                </div>
            </div>
            {f'<div style="display: flex; gap: 0.5rem; margin-bottom: 0.4rem;"><span class="stock-ticker" style="background: rgba(96, 165, 250, 0.2); color: #60a5fa;">2030 TAM {tam}</span><span class="stock-ticker" style="background: rgba(52, 211, 153, 0.2); color: #34d399;">CAGR {cagr}</span></div>' if tam and cagr else ''}
            <div class="stock-meta">
                <div class="score-container">
                    <div class="score-bar">
                        <div class="score-dot" style="left: {score_position}%;"></div>
                    </div>
                    <span class="score-text" style="color: {score_color};">{total_score:+d}{"점" if is_kr else "pt"}</span>
                    <span class="confidence-text">({confidence:.0%})</span>
                </div>
                <span class="action {action_class}">{action_icon} {action_display}</span>
            </div>
            <div class="score-breakdown">
                <span class="score-chip {tech_class}">{"기술" if is_kr else "Tech"} {tech_score:+d}</span>
                <span class="score-chip {fund_class}">{"펀더" if is_kr else "Fund"} {fund_score:+d}</span>
                <span class="score-chip {market_class}">{"시장" if is_kr else "Mkt"} {market_score:+d}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 경고 표시
        if warnings:
            warning_html = " | ".join(warnings[:2])
            st.markdown(f'<div class="warning-badge">[!] {warning_html}</div>', unsafe_allow_html=True)
        
        # 투자 포인트 상세 설명 (펼치기)
        if detail_text:
            with st.expander(f"{'왜 투자해야 할까요?' if is_kr else 'Why invest?'}", expanded=False):
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
with st.expander("점수 시스템 설명" if is_kr else "Score System Explained"):
    st.markdown(f"""
    <div class="info-box">
    <strong>{"종합 점수 (-100 ~ +100)" if is_kr else "Total Score (-100 to +100)"}</strong>
    <br><br>
    {"이 시스템은 3가지 요소를 종합해서 매수/매도 신호를 판단해요:" if is_kr else "This system combines 3 factors to determine buy/sell signals:"}
    <br><br>
    <strong>{"🔧 기술적 분석 (60점)" if is_kr else "🔧 Technical Analysis (60 pts)"}</strong><br>
    {"RSI, MACD, 이동평균선, Stochastic, ADX 등 5가지 지표" if is_kr else "RSI, MACD, Moving Averages, Stochastic, ADX - 5 indicators"}
    <br><br>
    <strong>{"📊 펀더멘털 (25점)" if is_kr else "📊 Fundamentals (25 pts)"}</strong><br>
    {"PER/PBR 밸류에이션, 매출/이익 성장률" if is_kr else "PER/PBR valuation, Revenue/Earnings growth"}
    <br><br>
    <strong>{"🌍 시장 환경 (15점)" if is_kr else "🌍 Market Environment (15 pts)"}</strong><br>
    {"VIX 공포지수, S&P 500 추세" if is_kr else "VIX fear index, S&P 500 trend"}
    <br><br>
    <hr style="border-color: rgba(255,255,255,0.1);">
    <span style="color: #34d399;">+20 이상</span>: {"매수 신호" if is_kr else "Buy signal"}<br>
    <span>-20 ~ +20</span>: {"중립" if is_kr else "Neutral"}<br>
    <span style="color: #f87171;">-20 이하</span>: {"매도 신호" if is_kr else "Sell signal"}
    <br><br>
    <strong>{"신뢰도" if is_kr else "Confidence"}</strong>: {"지표들이 같은 방향을 가리킬수록 신뢰도가 높아요." if is_kr else "Higher when indicators agree on direction."}
    </div>
    """, unsafe_allow_html=True)

# Footer
st.caption("Yahoo Finance, FRED | " + ("투자 조언 아님" if is_kr else "Not financial advice"))
