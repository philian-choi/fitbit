import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Top picks to analyze for timing (High volatility or key holdings)
DEFAULT_TICKERS = ['NVDA', 'TSLA', 'COIN', 'MSTR', 'HOOD', 'AMZN', 'NTLA']


class MarketRegime(Enum):
    """시장 국면 정의"""
    STRONG_BULL = "강세장"
    BULL = "상승장"
    NEUTRAL = "횡보장"
    BEAR = "하락장"
    STRONG_BEAR = "약세장"
    HIGH_VOLATILITY = "고변동성"


class SignalStrength(Enum):
    """신호 강도"""
    STRONG_BUY = ("STRONG BUY", "강력 매수", 5)
    BUY = ("BUY", "매수", 4)
    WEAK_BUY = ("WEAK BUY", "약한 매수", 3)
    NEUTRAL = ("NEUTRAL", "중립", 2)
    WEAK_SELL = ("WEAK SELL", "약한 매도", 1)
    SELL = ("SELL", "매도", 0)
    STRONG_SELL = ("STRONG SELL", "강력 매도", -1)
    
    def __init__(self, eng: str, kor: str, rank: int):
        self.eng = eng
        self.kor = kor
        self.rank = rank


@dataclass
class IndicatorResult:
    """개별 지표 결과"""
    name: str
    value: float
    score: int
    max_score: int
    signal: str
    description: str


@dataclass 
class AnalysisResult:
    """종합 분석 결과"""
    ticker: str
    price: float
    technical_score: int
    fundamental_score: int
    market_regime_score: int
    total_score: int
    max_possible_score: int
    confidence: float  # 신호 신뢰도 (0~1)
    signal: SignalStrength
    indicators: Dict[str, IndicatorResult] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    

class TechnicalAnalyzer:
    """
    종합 기술적 분석 시스템 (Enhanced v2.0)
    
    다중 지표를 활용하여 균형 잡힌 매매 신호 생성:
    
    [기술적 지표 - 60점]
    - RSI (14일): 과매수/과매도 판단 (15점)
    - Stochastic (14,3,3): RSI 보완, 단기 반전 (10점)
    - MACD (12,26,9): 추세 전환 감지 (15점)
    - ADX (14일): 추세 강도 측정 (10점)
    - 이동평균선 (SMA 20/50/200): 추세 방향 (10점)
    - 볼린저 밴드: 변동성 및 가격 위치 (별도 가중치 없음, 신호 보조)
    - ATR: 변동성 측정 (리스크 관리용)
    - 거래량 분석: 신호 신뢰도 조정용
    
    [펀더멘털 - 25점]
    - 밸류에이션 (PER/PBR 역사적 위치): 15점
    - 성장성 (매출/이익 성장률): 10점
    
    [시장 환경 - 15점]
    - VIX 수준: 5점
    - 시장 추세 (SPY 기준): 10점
    """
    
    def __init__(self, ticker: str, period: str = "2y"):
        self.ticker = ticker
        self.period = period
        self.data = None
        self.indicators = {}
        self.scores = {}
        self.indicator_results: Dict[str, IndicatorResult] = {}
        self.warnings: List[str] = []
        
    def fetch_data(self) -> bool:
        """Yahoo Finance에서 주가 데이터 가져오기"""
        try:
            stock = yf.Ticker(self.ticker)
            self.data = stock.history(period=self.period)
            if self.data.empty:
                return False
            return True
        except Exception as e:
            print(f"데이터 가져오기 실패 ({self.ticker}): {e}")
            return False
    
    def calculate_rsi(self, period: int = 14) -> float:
        """RSI (Relative Strength Index) 계산 - 15점 배점"""
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        self.indicators['RSI'] = current_rsi
        
        # RSI 다이버전스 체크 (가격은 신고가인데 RSI는 하락 = 베어리시 다이버전스)
        price_higher = self.data['Close'].iloc[-1] > self.data['Close'].iloc[-5]
        rsi_lower = current_rsi < rsi.iloc[-5]
        bearish_divergence = price_higher and rsi_lower
        
        price_lower = self.data['Close'].iloc[-1] < self.data['Close'].iloc[-5]
        rsi_higher = current_rsi > rsi.iloc[-5]
        bullish_divergence = price_lower and rsi_higher
        
        # RSI 점수: -15 ~ +15
        if current_rsi > 80:
            score = -15
            signal = "극단적 과매수"
        elif current_rsi > 70:
            score = -10
            signal = "과매수"
        elif current_rsi > 60:
            score = -3
            signal = "약간 과매수"
        elif current_rsi < 20:
            score = 15
            signal = "극단적 과매도 (기회)"
        elif current_rsi < 30:
            score = 10
            signal = "과매도"
        elif current_rsi < 40:
            score = 3
            signal = "약간 과매도"
        else:
            score = 0
            signal = "중립"
        
        # 다이버전스 보너스/페널티
        if bullish_divergence:
            score += 5
            signal += " + 상승 다이버전스"
        elif bearish_divergence:
            score -= 5
            signal += " + 하락 다이버전스"
            
        score = max(-15, min(15, score))
        self.scores['RSI'] = score
        
        self.indicator_results['RSI'] = IndicatorResult(
            name="RSI (14)",
            value=current_rsi,
            score=score,
            max_score=15,
            signal=signal,
            description=f"RSI {current_rsi:.1f} (이전: {prev_rsi:.1f})"
        )
        
        return current_rsi
    
    def calculate_stochastic(self, k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> dict:
        """Stochastic Oscillator 계산 - 10점 배점"""
        low_min = self.data['Low'].rolling(window=k_period).min()
        high_max = self.data['High'].rolling(window=k_period).max()
        
        # %K (Fast)
        stoch_k = 100 * (self.data['Close'] - low_min) / (high_max - low_min)
        # %K Smoothed
        stoch_k_smooth = stoch_k.rolling(window=smooth_k).mean()
        # %D (Signal)
        stoch_d = stoch_k_smooth.rolling(window=d_period).mean()
        
        current_k = stoch_k_smooth.iloc[-1]
        current_d = stoch_d.iloc[-1]
        prev_k = stoch_k_smooth.iloc[-2]
        prev_d = stoch_d.iloc[-2]
        
        self.indicators['Stoch_K'] = current_k
        self.indicators['Stoch_D'] = current_d
        
        # Stochastic 점수: -10 ~ +10
        score = 0
        
        # 과매수/과매도
        if current_k > 80 and current_d > 80:
            score = -7
            signal = "과매수 영역"
        elif current_k < 20 and current_d < 20:
            score = 7
            signal = "과매도 영역"
        else:
            score = 0
            signal = "중립"
        
        # 크로스오버 시그널 (더 강력한 신호)
        if prev_k <= prev_d and current_k > current_d:  # 골든 크로스
            if current_k < 30:  # 과매도 영역에서 골든크로스 = 강한 매수
                score = 10
                signal = "과매도 탈출 (강한 매수)"
            else:
                score += 3
                signal += " + 골든크로스"
        elif prev_k >= prev_d and current_k < current_d:  # 데드 크로스
            if current_k > 70:  # 과매수 영역에서 데드크로스 = 강한 매도
                score = -10
                signal = "과매수 탈출 (강한 매도)"
            else:
                score -= 3
                signal += " + 데드크로스"
        
        score = max(-10, min(10, score))
        self.scores['Stochastic'] = score
        
        self.indicator_results['Stochastic'] = IndicatorResult(
            name="Stochastic (14,3,3)",
            value=current_k,
            score=score,
            max_score=10,
            signal=signal,
            description=f"%K={current_k:.1f}, %D={current_d:.1f}"
        )
        
        return {'k': current_k, 'd': current_d}
    
    def calculate_adx(self, period: int = 14) -> float:
        """ADX (Average Directional Index) - 추세 강도 측정, 10점 배점"""
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm_smooth = pd.Series(plus_dm, index=self.data.index).rolling(window=period).mean()
        minus_dm_smooth = pd.Series(minus_dm, index=self.data.index).rolling(window=period).mean()
        
        # Directional Indicators
        plus_di = 100 * plus_dm_smooth / atr
        minus_di = 100 * minus_dm_smooth / atr
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]
        
        self.indicators['ADX'] = current_adx
        self.indicators['Plus_DI'] = current_plus_di
        self.indicators['Minus_DI'] = current_minus_di
        
        # ADX 점수: -10 ~ +10
        # ADX는 추세의 강도만 측정, 방향은 +DI/-DI로 판단
        
        trend_strength = ""
        if current_adx < 20:
            # 추세 약함 - 횡보장에서는 RSI/Stochastic이 더 유용
            trend_strength = "약한 추세 (횡보)"
            if current_plus_di > current_minus_di:
                score = 2
            elif current_minus_di > current_plus_di:
                score = -2
            else:
                score = 0
        elif current_adx < 40:
            trend_strength = "보통 추세"
            if current_plus_di > current_minus_di:
                score = 5
            else:
                score = -5
        else:
            trend_strength = "강한 추세"
            if current_plus_di > current_minus_di:
                score = 10  # 강한 상승 추세
            else:
                score = -10  # 강한 하락 추세
        
        direction = "상승" if current_plus_di > current_minus_di else "하락"
        signal = f"{trend_strength} ({direction})"
        
        self.scores['ADX'] = score
        
        self.indicator_results['ADX'] = IndicatorResult(
            name="ADX (14)",
            value=current_adx,
            score=score,
            max_score=10,
            signal=signal,
            description=f"ADX={current_adx:.1f}, +DI={current_plus_di:.1f}, -DI={current_minus_di:.1f}"
        )
        
        return current_adx
    
    def calculate_atr(self, period: int = 14) -> float:
        """ATR (Average True Range) - 변동성 측정 (리스크 관리용, 점수 없음)"""
        high = self.data['High']
        low = self.data['Low']
        close = self.data['Close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        current_atr = atr.iloc[-1]
        current_price = close.iloc[-1]
        atr_percent = (current_atr / current_price) * 100
        
        self.indicators['ATR'] = current_atr
        self.indicators['ATR_Percent'] = atr_percent
        
        # ATR은 점수에 반영하지 않고 리스크 정보로만 사용
        if atr_percent > 5:
            volatility = "매우 높음 (고위험)"
            self.warnings.append(f"높은 변동성 주의: ATR {atr_percent:.1f}%")
        elif atr_percent > 3:
            volatility = "높음"
        elif atr_percent > 1.5:
            volatility = "보통"
        else:
            volatility = "낮음"
        
        self.indicator_results['ATR'] = IndicatorResult(
            name="ATR (14)",
            value=current_atr,
            score=0,
            max_score=0,
            signal=volatility,
            description=f"ATR=${current_atr:.2f} ({atr_percent:.1f}% of price)"
        )
        
        return current_atr
    
    def calculate_macd(self, fast: int = 12, slow: int = 26, signal_period: int = 9) -> dict:
        """MACD (Moving Average Convergence Divergence) 계산 - 15점 배점"""
        exp1 = self.data['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = self.data['Close'].ewm(span=slow, adjust=False).mean()
        
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2]
        prev_macd = macd_line.iloc[-2]
        prev_signal_val = signal_line.iloc[-2]
        
        self.indicators['MACD'] = current_macd
        self.indicators['MACD_Signal'] = current_signal
        self.indicators['MACD_Histogram'] = current_hist
        
        # MACD 점수: -15 ~ +15
        score = 0
        signals = []
        
        # 1. MACD 크로스오버 (가장 중요한 신호)
        if prev_macd <= prev_signal_val and current_macd > current_signal:
            score += 8  # 골든 크로스
            signals.append("골든크로스")
        elif prev_macd >= prev_signal_val and current_macd < current_signal:
            score -= 8  # 데드 크로스
            signals.append("데드크로스")
        else:
            # 현재 위치
            if current_macd > current_signal:
                score += 3
            else:
                score -= 3
            
        # 2. 히스토그램 방향 (모멘텀 변화)
        if current_hist > 0 and current_hist > prev_hist:
            score += 4  # 상승 모멘텀 강화
            signals.append("모멘텀↑")
        elif current_hist < 0 and current_hist < prev_hist:
            score -= 4  # 하락 모멘텀 강화
            signals.append("모멘텀↓")
        elif current_hist > 0 and current_hist < prev_hist:
            score += 1  # 상승 모멘텀 약화
        elif current_hist < 0 and current_hist > prev_hist:
            score -= 1  # 하락 모멘텀 약화
            
        # 3. 제로라인 기준
        if current_macd > 0:
            score += 3
            signals.append("제로선 상단")
        else:
            score -= 3
            signals.append("제로선 하단")
            
        score = max(-15, min(15, score))
        self.scores['MACD'] = score
        
        signal_str = ", ".join(signals) if signals else "중립"
        
        self.indicator_results['MACD'] = IndicatorResult(
            name="MACD (12,26,9)",
            value=current_macd,
            score=score,
            max_score=15,
            signal=signal_str,
            description=f"MACD={current_macd:.3f}, Signal={current_signal:.3f}, Hist={current_hist:.3f}"
        )
        
        return {
            'macd': current_macd,
            'signal': current_signal,
            'histogram': current_hist
        }
    
    def calculate_moving_averages(self) -> dict:
        """이동평균선 (SMA 20/50/200) 계산 - 10점 배점"""
        sma20 = self.data['Close'].rolling(window=20).mean().iloc[-1]
        sma50 = self.data['Close'].rolling(window=50).mean().iloc[-1]
        sma200 = self.data['Close'].rolling(window=200).mean().iloc[-1] if len(self.data) >= 200 else None
        
        current_price = self.data['Close'].iloc[-1]
        
        self.indicators['SMA_20'] = sma20
        self.indicators['SMA_50'] = sma50
        self.indicators['SMA_200'] = sma200
        self.indicators['Price'] = current_price
        
        # 이동평균 점수: -10 ~ +10
        score = 0
        signals = []
        
        # 가격 vs 이동평균선 위치
        if current_price > sma20:
            score += 2
        else:
            score -= 2
            
        if current_price > sma50:
            score += 3
            signals.append("50일선 위")
        else:
            score -= 3
            signals.append("50일선 아래")
            
        if sma200 is not None:
            if current_price > sma200:
                score += 3
                signals.append("200일선 위")
            else:
                score -= 3
                signals.append("200일선 아래")
                
            # 골든크로스 / 데드크로스 확인
            if sma50 > sma200:
                score += 2
                signals.append("골든크로스 상태")
            else:
                score -= 2
                signals.append("데드크로스 상태")
        
        score = max(-10, min(10, score))
        self.scores['MA'] = score
        
        signal_str = ", ".join(signals) if signals else "중립"
        
        self.indicator_results['MA'] = IndicatorResult(
            name="이동평균선",
            value=current_price,
            score=score,
            max_score=10,
            signal=signal_str,
            description=f"Price=${current_price:.2f}, SMA20=${sma20:.2f}, SMA50=${sma50:.2f}" + 
                       (f", SMA200=${sma200:.2f}" if sma200 else "")
        )
        
        return {
            'sma20': sma20,
            'sma50': sma50,
            'sma200': sma200,
            'price': current_price
        }
    
    def calculate_bollinger_bands(self, period: int = 20, std_dev: int = 2) -> dict:
        """볼린저 밴드 계산 - 보조 지표 (점수 없음, 신호 확인용)"""
        sma = self.data['Close'].rolling(window=period).mean()
        std = self.data['Close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_price = self.data['Close'].iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_middle = sma.iloc[-1]
        
        # %B 계산 (가격의 밴드 내 위치, 0~1)
        percent_b = (current_price - current_lower) / (current_upper - current_lower)
        
        # 밴드 폭 (변동성)
        band_width = (current_upper - current_lower) / current_middle
        
        self.indicators['BB_Upper'] = current_upper
        self.indicators['BB_Lower'] = current_lower
        self.indicators['BB_Middle'] = current_middle
        self.indicators['BB_PercentB'] = percent_b
        self.indicators['BB_Width'] = band_width
        
        # 볼린저 밴드는 보조 지표로만 사용 (RSI/Stochastic과 중복 방지)
        if percent_b > 1.0:
            signal = "상단 밴드 돌파 (과열)"
        elif percent_b > 0.8:
            signal = "상단 밴드 근접"
        elif percent_b < 0.0:
            signal = "하단 밴드 돌파 (침체)"
        elif percent_b < 0.2:
            signal = "하단 밴드 근접"
        elif 0.4 <= percent_b <= 0.6:
            signal = "중앙 근처"
        elif percent_b > 0.6:
            signal = "상단 방향"
        else:
            signal = "하단 방향"
            
        # 밴드 스퀴즈 체크 (변동성 축소 -> 큰 움직임 예고)
        avg_width = (upper_band - lower_band).rolling(window=50).mean() / sma.rolling(window=50).mean()
        if band_width < avg_width.iloc[-1] * 0.7:
            signal += " + 밴드 스퀴즈 (변동성 확대 예상)"
            self.warnings.append("볼린저 밴드 스퀴즈: 큰 가격 변동 가능성")
        
        self.indicator_results['BB'] = IndicatorResult(
            name="볼린저 밴드",
            value=percent_b,
            score=0,
            max_score=0,
            signal=signal,
            description=f"%B={percent_b:.2f}, 밴드폭={band_width:.1%}"
        )
        
        return {
            'upper': current_upper,
            'lower': current_lower,
            'middle': current_middle,
            'percent_b': percent_b,
            'band_width': band_width
        }
    
    def analyze_volume(self) -> dict:
        """거래량 분석 - 신호 신뢰도 조정용 (별도 점수 없음)"""
        avg_volume_20 = self.data['Volume'].rolling(window=20).mean().iloc[-1]
        current_volume = self.data['Volume'].iloc[-1]
        
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        
        # 최근 5일 가격 변화
        price_change_5d = (self.data['Close'].iloc[-1] / self.data['Close'].iloc[-5] - 1) * 100
        
        self.indicators['Volume_Ratio'] = volume_ratio
        self.indicators['Avg_Volume_20'] = avg_volume_20
        self.indicators['Price_Change_5D'] = price_change_5d
        
        # 거래량은 신호 신뢰도 조정에만 사용
        if price_change_5d > 0:
            if volume_ratio > 1.5:
                signal = "강한 상승 확인 (고거래량)"
                self.indicators['Volume_Confirmation'] = 1.0
            elif volume_ratio > 1.0:
                signal = "상승 확인"
                self.indicators['Volume_Confirmation'] = 0.8
            else:
                signal = "약한 상승 (저거래량 주의)"
                self.indicators['Volume_Confirmation'] = 0.5
                self.warnings.append("저거래량 상승: 신뢰도 낮음")
        else:
            if volume_ratio > 1.5:
                signal = "강한 하락 확인 (고거래량)"
                self.indicators['Volume_Confirmation'] = 1.0
            elif volume_ratio > 1.0:
                signal = "하락 확인"
                self.indicators['Volume_Confirmation'] = 0.8
            else:
                signal = "약한 하락 (매집 가능성)"
                self.indicators['Volume_Confirmation'] = 0.6
        
        self.indicator_results['Volume'] = IndicatorResult(
            name="거래량 분석",
            value=volume_ratio,
            score=0,
            max_score=0,
            signal=signal,
            description=f"거래량 배율={volume_ratio:.2f}x, 5일 수익률={price_change_5d:.1f}%"
        )
        
        return {
            'volume_ratio': volume_ratio,
            'avg_volume': avg_volume_20,
            'price_change_5d': price_change_5d
        }
    
    def get_technical_score(self) -> int:
        """기술적 분석 점수 합계 (최대 60점)"""
        # RSI(15) + Stochastic(10) + MACD(15) + ADX(10) + MA(10) = 60
        tech_indicators = ['RSI', 'Stochastic', 'MACD', 'ADX', 'MA']
        return sum(self.scores.get(ind, 0) for ind in tech_indicators)
    
    def analyze(self) -> dict:
        """전체 기술적 분석 수행"""
        if not self.fetch_data():
            return {'error': f'{self.ticker} 데이터를 가져올 수 없습니다'}
        
        # 모든 지표 계산
        self.calculate_rsi()
        self.calculate_stochastic()
        self.calculate_macd()
        self.calculate_adx()
        self.calculate_atr()
        self.calculate_moving_averages()
        self.calculate_bollinger_bands()
        self.analyze_volume()
        
        technical_score = self.get_technical_score()
        
        # 전일 종가 계산
        prev_close = self.data['Close'].iloc[-2] if len(self.data) > 1 else self.indicators.get('Price', 0)
        
        return {
            'ticker': self.ticker,
            'price': self.indicators.get('Price'),
            'prev_close': prev_close,
            'indicators': self.indicators,
            'scores': self.scores,
            'indicator_results': self.indicator_results,
            'technical_score': technical_score,
            'max_technical_score': 60,
            'warnings': self.warnings
        }


class FundamentalAnalyzer:
    """
    펀더멘털 분석 시스템 - 25점 배점
    
    - 밸류에이션 (15점): PER/PBR의 역사적 위치 및 섹터 대비
    - 성장성 (10점): 매출/이익 성장률
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.info = None
        self.scores = {}
        self.indicator_results: Dict[str, IndicatorResult] = {}
        self.warnings: List[str] = []
    
    def fetch_data(self) -> bool:
        """Yahoo Finance에서 펀더멘털 데이터 가져오기"""
        try:
            stock = yf.Ticker(self.ticker)
            self.info = stock.info
            self.history = stock.history(period="5y")
            return bool(self.info)
        except Exception as e:
            print(f"펀더멘털 데이터 가져오기 실패 ({self.ticker}): {e}")
            return False
    
    def analyze_valuation(self) -> int:
        """밸류에이션 분석 - 15점 배점"""
        pe_ratio = self.info.get('trailingPE')
        forward_pe = self.info.get('forwardPE')
        pb_ratio = self.info.get('priceToBook')
        peg_ratio = self.info.get('pegRatio')
        
        score = 0
        signals = []
        
        # PER 분석
        if pe_ratio and pe_ratio > 0:
            if pe_ratio < 15:
                score += 5
                signals.append(f"저PER({pe_ratio:.1f})")
            elif pe_ratio < 25:
                score += 2
                signals.append(f"적정PER({pe_ratio:.1f})")
            elif pe_ratio < 40:
                score -= 2
                signals.append(f"고PER({pe_ratio:.1f})")
            else:
                score -= 5
                signals.append(f"과대평가PER({pe_ratio:.1f})")
                self.warnings.append(f"높은 PER 주의: {pe_ratio:.1f}")
        
        # Forward PE vs Trailing PE (이익 성장 예상)
        if forward_pe and pe_ratio and forward_pe > 0 and pe_ratio > 0:
            if forward_pe < pe_ratio * 0.8:
                score += 3  # 이익 성장 예상
                signals.append("이익성장 예상")
            elif forward_pe > pe_ratio * 1.2:
                score -= 3  # 이익 감소 예상
                signals.append("이익감소 예상")
        
        # PBR 분석
        if pb_ratio and pb_ratio > 0:
            if pb_ratio < 1:
                score += 3
                signals.append(f"저PBR({pb_ratio:.1f})")
            elif pb_ratio < 3:
                score += 1
            elif pb_ratio > 10:
                score -= 3
                signals.append(f"고PBR({pb_ratio:.1f})")
        
        # PEG 분석 (가장 균형 잡힌 밸류에이션 지표)
        if peg_ratio and peg_ratio > 0:
            if peg_ratio < 1:
                score += 4
                signals.append(f"저평가PEG({peg_ratio:.2f})")
            elif peg_ratio < 1.5:
                score += 2
                signals.append(f"적정PEG({peg_ratio:.2f})")
            elif peg_ratio > 2:
                score -= 4
                signals.append(f"고평가PEG({peg_ratio:.2f})")
        
        score = max(-15, min(15, score))
        self.scores['Valuation'] = score
        
        signal_str = ", ".join(signals) if signals else "데이터 부족"
        
        self.indicator_results['Valuation'] = IndicatorResult(
            name="밸류에이션",
            value=pe_ratio or 0,
            score=score,
            max_score=15,
            signal=signal_str,
            description=f"PER={pe_ratio or 'N/A'}, PBR={pb_ratio or 'N/A'}, PEG={peg_ratio or 'N/A'}"
        )
        
        return score
    
    def analyze_growth(self) -> int:
        """성장성 분석 - 10점 배점"""
        revenue_growth = self.info.get('revenueGrowth', 0)
        earnings_growth = self.info.get('earningsGrowth', 0)
        revenue_per_share_growth = self.info.get('revenuePerShare', 0)
        
        score = 0
        signals = []
        
        # 매출 성장률
        if revenue_growth:
            if revenue_growth > 0.3:
                score += 4
                signals.append(f"고성장({revenue_growth:.0%})")
            elif revenue_growth > 0.15:
                score += 2
                signals.append(f"성장({revenue_growth:.0%})")
            elif revenue_growth > 0:
                score += 1
            elif revenue_growth < -0.1:
                score -= 3
                signals.append(f"매출감소({revenue_growth:.0%})")
                self.warnings.append(f"매출 감소 주의: {revenue_growth:.0%}")
        
        # 이익 성장률
        if earnings_growth:
            if earnings_growth > 0.3:
                score += 4
                signals.append(f"이익고성장({earnings_growth:.0%})")
            elif earnings_growth > 0.15:
                score += 2
            elif earnings_growth > 0:
                score += 1
            elif earnings_growth < -0.1:
                score -= 3
                signals.append(f"이익감소({earnings_growth:.0%})")
        
        # 마진 분석
        gross_margin = self.info.get('grossMargins', 0)
        operating_margin = self.info.get('operatingMargins', 0)
        
        if gross_margin and gross_margin > 0.5:
            score += 2
            signals.append(f"고마진({gross_margin:.0%})")
        
        score = max(-10, min(10, score))
        self.scores['Growth'] = score
        
        signal_str = ", ".join(signals) if signals else "데이터 부족"
        
        self.indicator_results['Growth'] = IndicatorResult(
            name="성장성",
            value=revenue_growth or 0,
            score=score,
            max_score=10,
            signal=signal_str,
            description=f"매출성장={revenue_growth or 'N/A'}, 이익성장={earnings_growth or 'N/A'}, 마진={gross_margin or 'N/A'}"
        )
        
        return score
    
    def analyze_financial_health(self) -> None:
        """재무 건전성 분석 - 경고용 (점수 없음)"""
        debt_to_equity = self.info.get('debtToEquity', 0)
        current_ratio = self.info.get('currentRatio', 0)
        free_cash_flow = self.info.get('freeCashflow', 0)
        
        signals = []
        
        if debt_to_equity and debt_to_equity > 200:
            self.warnings.append(f"높은 부채비율 주의: {debt_to_equity:.0f}%")
            signals.append(f"고부채({debt_to_equity:.0f}%)")
        elif debt_to_equity and debt_to_equity < 50:
            signals.append("저부채")
        
        if current_ratio and current_ratio < 1:
            self.warnings.append(f"유동성 위험: 유동비율 {current_ratio:.2f}")
            signals.append("유동성 주의")
        elif current_ratio and current_ratio > 2:
            signals.append("양호한 유동성")
        
        if free_cash_flow and free_cash_flow < 0:
            self.warnings.append("음의 잉여현금흐름")
            signals.append("FCF 음수")
        elif free_cash_flow and free_cash_flow > 0:
            signals.append("양의 FCF")
        
        signal_str = ", ".join(signals) if signals else "데이터 부족"
        
        self.indicator_results['FinancialHealth'] = IndicatorResult(
            name="재무건전성",
            value=debt_to_equity or 0,
            score=0,
            max_score=0,
            signal=signal_str,
            description=f"D/E={debt_to_equity or 'N/A'}, 유동비율={current_ratio or 'N/A'}"
        )
    
    def get_fundamental_score(self) -> int:
        """펀더멘털 점수 합계 (최대 25점)"""
        return sum(self.scores.values())
    
    def analyze(self) -> dict:
        """펀더멘털 분석 수행"""
        if not self.fetch_data():
            return {'error': f'{self.ticker} 펀더멘털 데이터를 가져올 수 없습니다'}
        
        self.analyze_valuation()
        self.analyze_growth()
        self.analyze_financial_health()
        
        fundamental_score = self.get_fundamental_score()
        
        return {
            'ticker': self.ticker,
            'scores': self.scores,
            'indicator_results': self.indicator_results,
            'fundamental_score': fundamental_score,
            'max_fundamental_score': 25,
            'warnings': self.warnings
        }


class MarketRegimeAnalyzer:
    """
    시장 국면 분석 - 15점 배점
    
    - VIX 수준: 5점
    - 시장 추세 (SPY 기준): 10점
    """
    
    def __init__(self):
        self.scores = {}
        self.indicator_results: Dict[str, IndicatorResult] = {}
        self.warnings: List[str] = []
        self.regime: MarketRegime = MarketRegime.NEUTRAL
    
    def analyze_vix(self) -> int:
        """VIX (변동성 지수) 분석 - 5점 배점"""
        try:
            vix = yf.Ticker("^VIX")
            vix_data = vix.history(period="3mo")
            
            if vix_data.empty:
                return 0
            
            current_vix = vix_data['Close'].iloc[-1]
            avg_vix = vix_data['Close'].mean()
            
            # VIX 점수 (역방향: 낮을수록 좋음)
            if current_vix < 15:
                score = 5
                signal = "낮은 변동성 (안정)"
            elif current_vix < 20:
                score = 3
                signal = "정상 변동성"
            elif current_vix < 25:
                score = 0
                signal = "약간 높은 변동성"
            elif current_vix < 30:
                score = -3
                signal = "높은 변동성 (경계)"
                self.warnings.append(f"VIX 상승 주의: {current_vix:.1f}")
            else:
                score = -5
                signal = "극단적 공포 (위험/기회)"
                self.warnings.append(f"극단적 VIX: {current_vix:.1f} - 시장 패닉 상태")
            
            self.scores['VIX'] = score
            
            self.indicator_results['VIX'] = IndicatorResult(
                name="VIX (공포지수)",
                value=current_vix,
                score=score,
                max_score=5,
                signal=signal,
                description=f"현재 VIX={current_vix:.1f}, 평균={avg_vix:.1f}"
            )
            
            return score
            
        except Exception as e:
            print(f"VIX 데이터 가져오기 실패: {e}")
            return 0
    
    def analyze_market_trend(self) -> int:
        """시장 추세 분석 (SPY 기준) - 10점 배점"""
        try:
            spy = yf.Ticker("SPY")
            spy_data = spy.history(period="1y")
            
            if spy_data.empty or len(spy_data) < 200:
                return 0
            
            current_price = spy_data['Close'].iloc[-1]
            sma50 = spy_data['Close'].rolling(window=50).mean().iloc[-1]
            sma200 = spy_data['Close'].rolling(window=200).mean().iloc[-1]
            
            # 52주 고점/저점 대비 위치
            high_52w = spy_data['High'].max()
            low_52w = spy_data['Low'].min()
            position_52w = (current_price - low_52w) / (high_52w - low_52w)
            
            score = 0
            signals = []
            
            # 이평선 기준 추세
            if current_price > sma50 and sma50 > sma200:
                score += 6
                signals.append("강한 상승추세")
                self.regime = MarketRegime.STRONG_BULL
            elif current_price > sma50:
                score += 3
                signals.append("상승추세")
                self.regime = MarketRegime.BULL
            elif current_price < sma50 and sma50 < sma200:
                score -= 6
                signals.append("강한 하락추세")
                self.regime = MarketRegime.STRONG_BEAR
            elif current_price < sma50:
                score -= 3
                signals.append("하락추세")
                self.regime = MarketRegime.BEAR
            else:
                self.regime = MarketRegime.NEUTRAL
            
            # 52주 위치 보너스
            if position_52w > 0.9:
                score += 4
                signals.append("52주 신고가 근접")
            elif position_52w > 0.7:
                score += 2
            elif position_52w < 0.2:
                score -= 4
                signals.append("52주 저점 근접")
                self.warnings.append("시장이 52주 저점 근처")
            elif position_52w < 0.4:
                score -= 2
            
            score = max(-10, min(10, score))
            self.scores['MarketTrend'] = score
            
            signal_str = ", ".join(signals) if signals else "중립"
            
            self.indicator_results['MarketTrend'] = IndicatorResult(
                name="시장 추세 (SPY)",
                value=current_price,
                score=score,
                max_score=10,
                signal=signal_str,
                description=f"SPY=${current_price:.2f}, 52주 위치={position_52w:.0%}"
            )
            
            return score
            
        except Exception as e:
            print(f"시장 추세 분석 실패: {e}")
            return 0
    
    def get_market_score(self) -> int:
        """시장 환경 점수 합계 (최대 15점)"""
        return sum(self.scores.values())
    
    def analyze(self) -> dict:
        """시장 환경 분석 수행"""
        self.analyze_vix()
        self.analyze_market_trend()
        
        market_score = self.get_market_score()
        
        return {
            'scores': self.scores,
            'indicator_results': self.indicator_results,
            'market_score': market_score,
            'max_market_score': 15,
            'regime': self.regime,
            'warnings': self.warnings
        }


class ComprehensiveAnalyzer:
    """
    종합 투자 분석 시스템
    
    기술적 분석(60점) + 펀더멘털(25점) + 시장환경(15점) = 100점
    
    신호 신뢰도: 지표 간 일치도를 기반으로 계산
    """
    
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.technical: Optional[dict] = None
        self.fundamental: Optional[dict] = None
        self.market: Optional[dict] = None
        self.all_warnings: List[str] = []
    
    def calculate_confidence(self) -> float:
        """
        신호 신뢰도 계산 (0.0 ~ 1.0)
        
        - 지표들이 같은 방향을 가리키면 신뢰도 높음
        - 충돌하면 신뢰도 낮음
        - 거래량 확인 반영
        """
        if not self.technical:
            return 0.5
        
        scores = self.technical.get('scores', {})
        indicators = self.technical.get('indicators', {})
        
        # 1. 모멘텀 지표 일치도 (RSI, Stochastic, MACD)
        momentum_scores = [
            scores.get('RSI', 0),
            scores.get('Stochastic', 0),
            scores.get('MACD', 0)
        ]
        
        # 모든 지표가 같은 부호면 일치
        positive_count = sum(1 for s in momentum_scores if s > 0)
        negative_count = sum(1 for s in momentum_scores if s < 0)
        
        if positive_count == 3 or negative_count == 3:
            momentum_agreement = 1.0
        elif positive_count == 2 or negative_count == 2:
            momentum_agreement = 0.7
        else:
            momentum_agreement = 0.4
        
        # 2. 추세 지표 일치도 (ADX, MA)
        trend_scores = [
            scores.get('ADX', 0),
            scores.get('MA', 0)
        ]
        
        if all(s > 0 for s in trend_scores) or all(s < 0 for s in trend_scores):
            trend_agreement = 1.0
        elif any(s == 0 for s in trend_scores):
            trend_agreement = 0.6
        else:
            trend_agreement = 0.3
        
        # 3. 거래량 확인
        volume_confirmation = indicators.get('Volume_Confirmation', 0.5)
        
        # 4. 종합 신뢰도
        confidence = (momentum_agreement * 0.4 + 
                     trend_agreement * 0.3 + 
                     volume_confirmation * 0.3)
        
        return round(confidence, 2)
    
    def get_signal(self, total_score: int, confidence: float) -> SignalStrength:
        """종합 점수와 신뢰도에 따른 매매 신호"""
        # 신뢰도가 낮으면 신호 강도 한 단계 낮춤
        confidence_penalty = 0 if confidence >= 0.6 else 1
        
        if total_score >= 50:
            signal = SignalStrength.STRONG_BUY
        elif total_score >= 30:
            signal = SignalStrength.BUY
        elif total_score >= 15:
            signal = SignalStrength.WEAK_BUY
        elif total_score <= -50:
            signal = SignalStrength.STRONG_SELL
        elif total_score <= -30:
            signal = SignalStrength.SELL
        elif total_score <= -15:
            signal = SignalStrength.WEAK_SELL
        else:
            signal = SignalStrength.NEUTRAL
        
        # 신뢰도 페널티 적용
        if confidence_penalty > 0 and signal not in [SignalStrength.NEUTRAL]:
            signal_order = [
                SignalStrength.STRONG_SELL, SignalStrength.SELL, 
                SignalStrength.WEAK_SELL, SignalStrength.NEUTRAL,
                SignalStrength.WEAK_BUY, SignalStrength.BUY, 
                SignalStrength.STRONG_BUY
            ]
            idx = signal_order.index(signal)
            # 중립 방향으로 한 단계
            if signal.rank > 2:  # 매수 신호
                idx = max(3, idx - 1)
            else:  # 매도 신호
                idx = min(3, idx + 1)
            signal = signal_order[idx]
            self.all_warnings.append(f"낮은 신호 신뢰도({confidence:.0%})로 신호 강도 하향 조정")
        
        return signal
    
    def analyze(self) -> AnalysisResult:
        """종합 분석 수행"""
        print(f"  [1/4] 기술적 분석 중...")
        tech_analyzer = TechnicalAnalyzer(self.ticker)
        self.technical = tech_analyzer.analyze()
        
        if 'error' in self.technical:
            return AnalysisResult(
                ticker=self.ticker,
                price=0,
                technical_score=0,
                fundamental_score=0,
                market_regime_score=0,
                total_score=0,
                max_possible_score=100,
                confidence=0,
                signal=SignalStrength.NEUTRAL,
                warnings=[self.technical['error']]
            )
        
        print(f"  [2/4] 펀더멘털 분석 중...")
        fund_analyzer = FundamentalAnalyzer(self.ticker)
        self.fundamental = fund_analyzer.analyze()
        
        print(f"  [3/4] 시장 환경 분석 중...")
        market_analyzer = MarketRegimeAnalyzer()
        self.market = market_analyzer.analyze()
        
        print(f"  [4/4] 종합 점수 계산 중...")
        
        # 점수 합산
        tech_score = self.technical.get('technical_score', 0)
        fund_score = self.fundamental.get('fundamental_score', 0) if self.fundamental else 0
        market_score = self.market.get('market_score', 0) if self.market else 0
        
        total_score = tech_score + fund_score + market_score
        
        # 신뢰도 계산
        confidence = self.calculate_confidence()
        
        # 신호 결정
        signal = self.get_signal(total_score, confidence)
        
        # 경고 수집
        self.all_warnings.extend(self.technical.get('warnings', []))
        if self.fundamental:
            self.all_warnings.extend(self.fundamental.get('warnings', []))
        if self.market:
            self.all_warnings.extend(self.market.get('warnings', []))
        
        # 지표 결과 통합
        all_indicators = {}
        all_indicators.update(self.technical.get('indicator_results', {}))
        if self.fundamental:
            all_indicators.update(self.fundamental.get('indicator_results', {}))
        if self.market:
            all_indicators.update(self.market.get('indicator_results', {}))
        
        return AnalysisResult(
            ticker=self.ticker,
            price=self.technical.get('price', 0),
            technical_score=tech_score,
            fundamental_score=fund_score,
            market_regime_score=market_score,
            total_score=total_score,
            max_possible_score=100,
            confidence=confidence,
            signal=signal,
            indicators=all_indicators,
            warnings=self.all_warnings
        )


def analyze_multiple_tickers(tickers: list) -> List[AnalysisResult]:
    """여러 종목 종합 분석"""
    results = []
    
    print("=" * 80)
    print("         종합 투자 분석 시스템 v2.0")
    print("  기술적(60점) + 펀더멘털(25점) + 시장환경(15점) = 100점")
    print("=" * 80)
    print(f"\n분석 대상: {len(tickers)} 종목")
    print("-" * 80)
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] {ticker} 분석 중...")
        analyzer = ComprehensiveAnalyzer(ticker)
        result = analyzer.analyze()
        results.append(result)
        
        score_bar = "█" * max(0, (result.total_score + 100) // 5) + "░" * (40 - max(0, (result.total_score + 100) // 5))
        print(f"  → 완료: {result.total_score:+d}점 [{score_bar}] {result.signal.kor}")
    
    return results


def print_analysis_report(results: List[AnalysisResult]):
    """분석 결과 출력"""
    print("\n" + "=" * 100)
    print("                              종합 투자 분석 리포트")
    print("=" * 100)
    
    # 요약 테이블
    summary_data = []
    for r in results:
        summary_data.append({
            'Ticker': r.ticker,
            'Price': f"${r.price:.2f}" if r.price else 'N/A',
            '기술(60)': f"{r.technical_score:+d}",
            '펀더(25)': f"{r.fundamental_score:+d}",
            '시장(15)': f"{r.market_regime_score:+d}",
            '총점(100)': f"{r.total_score:+d}",
            '신뢰도': f"{r.confidence:.0%}",
            '신호': f"{r.signal.eng} ({r.signal.kor})"
        })
    
    df_summary = pd.DataFrame(summary_data)
    
    try:
        from tabulate import tabulate
        print(tabulate(df_summary, headers='keys', tablefmt='github', showindex=False))
    except ImportError:
        print(df_summary.to_string(index=False))
    
    # 상세 분석
    print("\n" + "-" * 100)
    print("상세 지표 분석")
    print("-" * 100)
    
    for r in results:
        print(f"\n{'='*50}")
        print(f"[{r.ticker}] 총점: {r.total_score:+d}/100 | 신뢰도: {r.confidence:.0%} | {r.signal.kor}")
        print(f"{'='*50}")
        
        # 카테고리별 출력
        categories = {
            '기술적 지표': ['RSI', 'Stochastic', 'MACD', 'ADX', 'MA', 'ATR', 'BB', 'Volume'],
            '펀더멘털': ['Valuation', 'Growth', 'FinancialHealth'],
            '시장 환경': ['VIX', 'MarketTrend']
        }
        
        for cat_name, indicator_names in categories.items():
            print(f"\n  [{cat_name}]")
            for ind_name in indicator_names:
                if ind_name in r.indicators:
                    ind = r.indicators[ind_name]
                    score_str = f"{ind.score:+d}/{ind.max_score}" if ind.max_score > 0 else "참고용"
                    print(f"    • {ind.name}: {score_str}")
                    print(f"      {ind.signal}")
                    print(f"      ({ind.description})")
        
        # 경고 출력
        if r.warnings:
            print(f"\n  [⚠️ 주의사항]")
            for warning in r.warnings:
                print(f"    • {warning}")
    
    # 최종 추천
    print("\n" + "=" * 100)
    print("                              최종 투자 추천 순위")
    print("=" * 100)
    
    sorted_results = sorted(results, key=lambda x: (x.total_score, x.confidence), reverse=True)
    
    for i, r in enumerate(sorted_results, 1):
        if r.total_score >= 30:
            emoji = "🟢"
            action = "매수 고려"
        elif r.total_score >= 0:
            emoji = "🟡"
            action = "관망"
        elif r.total_score >= -30:
            emoji = "🟠"
            action = "주의"
        else:
            emoji = "🔴"
            action = "매도 고려"
        
        confidence_bar = "●" * int(r.confidence * 5) + "○" * (5 - int(r.confidence * 5))
        print(f"  {i}. {emoji} {r.ticker}: {r.total_score:+d}점 | 신뢰도 [{confidence_bar}] {r.confidence:.0%}")
        print(f"     → {r.signal.eng} ({r.signal.kor}) - {action}")
        if r.warnings:
            print(f"     ⚠️ {r.warnings[0]}" + (" 외 " + str(len(r.warnings)-1) + "건" if len(r.warnings) > 1 else ""))
        print()


def quick_analysis(ticker: str) -> None:
    """단일 종목 빠른 분석"""
    print(f"\n{'='*60}")
    print(f"  {ticker} 빠른 분석")
    print(f"{'='*60}\n")
    
    analyzer = ComprehensiveAnalyzer(ticker)
    result = analyzer.analyze()
    
    print(f"\n[결과]")
    print(f"  총점: {result.total_score:+d}/100")
    print(f"  신뢰도: {result.confidence:.0%}")
    print(f"  신호: {result.signal.eng} ({result.signal.kor})")
    
    if result.warnings:
        print(f"\n[주의사항]")
        for w in result.warnings:
            print(f"  • {w}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 커맨드라인 인자로 종목 지정
        if sys.argv[1] == '--quick' and len(sys.argv) > 2:
            quick_analysis(sys.argv[2].upper())
        else:
            tickers = [t.upper() for t in sys.argv[1:]]
            results = analyze_multiple_tickers(tickers)
            print_analysis_report(results)
    else:
        # 기본 종목 분석
        results = analyze_multiple_tickers(DEFAULT_TICKERS)
        print_analysis_report(results)
