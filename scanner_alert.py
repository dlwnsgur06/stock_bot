import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import json
import os


# =========================
# 중복 알림 방지
# =========================

ALERT_FILE = "alert_history.json"


def load_alert_history():

    if not os.path.exists(ALERT_FILE):
        return {}

    try:

        with open(
            ALERT_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_alert_history(history):

    with open(
        ALERT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            ensure_ascii=False,
            indent=4
        )


# =========================
# Telegram 설정
# =========================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_CHAT_ID = CHAT_ID

TELEGRAM_URL = (
    f"https://api.telegram.org/bot"
    f"{BOT_TOKEN}/sendMessage"
)


# =========================
# 보유종목 저장
# =========================

HOLDINGS_FILE = "holdings.json"


def load_holdings():

    if not os.path.exists(HOLDINGS_FILE):
        return {}

    try:

        with open(
            HOLDINGS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_holdings(holdings):

    with open(
        HOLDINGS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            holdings,
            f,
            ensure_ascii=False,
            indent=4
        )

# =========================
# Telegram 매수 메시지 확인
# =========================

def check_buy_message():

    print("매수 메시지 확인 함수 실행")
    
    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/getUpdates"
    )

    try:

        response = requests.get(
            url,
            timeout=10
        )

        data = response.json()

        print("Telegram 업데이트 확인:", data)

        if not data.get("ok"):
            return

        holdings = load_holdings()
        

        for update in data.get("result", []):

            message_data = update.get("message")

            if not message_data:
                continue

            chat_id = str(
                message_data["chat"]["id"]
            )

            if chat_id != str(TELEGRAM_CHAT_ID):
                continue

            text = message_data.get(
                "text",
                ""
            ).strip()

            if not text.startswith("매수 "):
                continue

            parts = text.split()

            if len(parts) != 4:
                continue

            stock_name = parts[1]

            # 종목명 검증
            if stock_name not in STOCKS:
                print(
                    f"잘못된 종목명 : {stock_name}"
                )
                continue

            try:

                buy_price = int(parts[2])
                quantity = int(parts[3])

            except ValueError:

                continue

            holdings[stock_name] = {

                "종목": stock_name,
                "매수가": buy_price,
                "수량": quantity
            }

            save_holdings(holdings)

            send_telegram(
                f"✅ 매수 등록 완료\n\n"
                f"종목 : {stock_name}\n"
                f"매수가 : {buy_price:,}원\n"
                f"수량 : {quantity}주"
            )

    except Exception as e:

        print(
            f"매수 메시지 확인 오류 : {e}"
        )


# =========================
# 종목 목록
# =========================

STOCKS = {
    "LG에너지솔루션": "373220.KS",
    "신한지주": "055550.KS",
    "삼성SDI": "006400.KS",
    "POSCO홀딩스": "005490.KS",
    "고려아연": "010130.KS",
    "KT&G": "033780.KS",
    "삼성에스디에스": "018260.KS",
    "에이피알": "278470.KQ",
    "포스코퓨처엠": "003670.KS",
    "LS": "006260.KS",
}


# =========================
# 설정
# =========================

MIN_SCORE = 70


# =========================
# RSI 계산
# =========================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (
        100 / (1 + rs)
    )

    return rsi


# =========================
# Telegram 전송
# =========================

def send_telegram(message):

    try:

        response = requests.post(
            TELEGRAM_URL,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            },
            timeout=10
        )

        if response.ok:

            print()
            print("Telegram 알림 전송 완료")

        else:

            print()
            print(
                f"Telegram 알림 실패 : "
                f"{response.text}"
            )

    except Exception as e:

        print()
        print(
            f"Telegram 오류 : {e}"
        )


# =========================
# 종목 분석
# =========================

def analyze_stock(name, ticker):

    try:

        df = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:

            return None


        # =========================
        # MultiIndex 처리
        # =========================

        if isinstance(df.columns, pd.MultiIndex):

            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < 30:

            return None


        # =========================
        # 현재 데이터
        # =========================

        close = float(
            df["Close"].iloc[-1]
        )

        volume = float(
            df["Volume"].iloc[-1]
        )


        # =========================
        # 이동평균
        # =========================

        ma5_series = (
            df["Close"]
            .rolling(5)
            .mean()
        )

        ma20_series = (
            df["Close"]
            .rolling(20)
            .mean()
        )

        ma5 = float(
            ma5_series.iloc[-1]
        )

        ma20 = float(
            ma20_series.iloc[-1]
        )


        # =========================
        # 어제 이동평균
        # =========================

        ma5_yesterday = float(
            ma5_series.iloc[-2]
        )

        ma20_yesterday = float(
            ma20_series.iloc[-2]
        )

        # =========================
        # MACD
        # =========================

        ema12 = (
            df["Close"]
            .ewm(span=12, adjust=False)
            .mean()
        )

        ema26 = (
            df["Close"]
            .ewm(span=26, adjust=False)
            .mean()
        )

        macd_series = ema12 - ema26

        signal_series = (
            macd_series
            .ewm(span=9, adjust=False)
            .mean()
        )

        macd = float(
            macd_series.iloc[-1]
        )

        macd_signal = float(
            signal_series.iloc[-1]
        )

        macd_bullish = (
            macd > macd_signal
        )

        macd_bearish = (
            macd < macd_signal
        )

        # =========================
        # 볼린저밴드
        # =========================

        bb_middle = (
            df["Close"]
            .rolling(20)
            .mean()
        )

        bb_std = (
            df["Close"]
            .rolling(20)
            .std()
        )

        bb_upper = (
            bb_middle + (bb_std * 2)
        )

        bb_lower = (
            bb_middle - (bb_std * 2)
        )

        bollinger_middle = float(
            bb_middle.iloc[-1]
        )

        bollinger_upper = float(
            bb_upper.iloc[-1]
        )

        bollinger_lower = float(
            bb_lower.iloc[-1]
        )


        # =========================
        # 볼린저밴드 위치
        # =========================

        if close >= bollinger_upper:

            bollinger_position = "상단 돌파"

        elif close <= bollinger_lower:

            bollinger_position = "하단 근접"

        elif close > bollinger_middle:

            bollinger_position = "중간선 위"

        else:

            bollinger_position = "중간선 아래"
            

        # =========================
        # 지지선 / 저항선
        # =========================

        support_level = float(
            df["Low"]
            .iloc[-20:]
            .min()
        )

        resistance_level = float(
            df["High"]
            .iloc[-20:]
            .max()
        )

        # =========================
        # 지지선 / 저항선 거리
        # =========================

        support_distance = (
            (close - support_level)
            / close
        ) * 100

        resistance_distance = (
            (resistance_level - close)
            / close
        ) * 100

        # =========================
        # 고점 돌파 (Breakout)
        # =========================

        previous_high = float(
            df["High"]
            .iloc[-21:-1]
            .max()
        )

        breakout = (
            close > previous_high
        )
        

        # =========================
        # 캔들 패턴
        # =========================

        open_price = float(
            df["Open"].iloc[-1]
        )

        high_price = float(
            df["High"].iloc[-1]
        )

        low_price = float(
            df["Low"].iloc[-1]
        )

        body_size = abs(
            close - open_price
        )

        candle_range = (
            high_price - low_price
        )

        if candle_range > 0:

            body_ratio = (
                body_size / candle_range
            )

        else:

            body_ratio = 0


        if (
            close > open_price
            and body_ratio >= 0.7
        ):

            candle_signal = "강한 양봉"

        elif (
            close < open_price
            and body_ratio >= 0.7
        ):

            candle_signal = "강한 음봉"

        else:

            candle_signal = "중립"


        # =========================
        # 골든크로스 / 데드크로스
        # =========================

        golden_cross = (
            ma5_yesterday <= ma20_yesterday
            and ma5 > ma20
        )

        dead_cross = (
            ma5_yesterday >= ma20_yesterday
            and ma5 < ma20
        )

        # =========================
        # 스토캐스틱
        # =========================

        lowest_low = (
            df["Low"]
            .rolling(14)
            .min()
        )

        highest_high = (
            df["High"]
            .rolling(14)
            .max()
        )

        stochastic_k = (
            (df["Close"] - lowest_low)
            / (highest_high - lowest_low)
        ) * 100

        stochastic_d = (
            stochastic_k
            .rolling(3)
            .mean()
        )

        stoch_k = float(
            stochastic_k.iloc[-1]
        )

        stoch_d = float(
            stochastic_d.iloc[-1]
        )


        # =========================
        # RSI
        # =========================

        rsi_series = calculate_rsi(
            df["Close"]
        )

        rsi = float(
            rsi_series.iloc[-1]
        )

        # =========================
        # ADX
        # =========================

        high = df["High"]
        low = df["Low"]
        close_series = df["Close"]

        high_diff = high.diff()
        low_diff = -low.diff()

        plus_dm = high_diff.where(
            (high_diff > low_diff) & (high_diff > 0),
            0
        )

        minus_dm = low_diff.where(
            (low_diff > high_diff) & (low_diff > 0),
            0
        )

        previous_close = close_series.shift(1)

        tr1 = high - low
        tr2 = abs(high - previous_close)
        tr3 = abs(low - previous_close)

        true_range = pd.concat(
            [tr1, tr2, tr3],
            axis=1
        ).max(axis=1)

        atr = true_range.rolling(14).mean()

        plus_di = (
            100
            * plus_dm.rolling(14).mean()
            / atr
        )

        minus_di = (
            100
            * minus_dm.rolling(14).mean()
            / atr
        )

        dx = (
            100
            * abs(plus_di - minus_di)
            / (plus_di + minus_di)
        )

        adx_series = dx.rolling(14).mean()

        adx = float(
            adx_series.iloc[-1]
        )

        plus_di_current = float(
            plus_di.iloc[-1]
        )

        minus_di_current = float(
            minus_di.iloc[-1]
        )


        # =========================
        # 거래량
        # =========================

        volume_ma20 = float(
            df["Volume"]
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        if volume_ma20 <= 0:

            volume_ratio = 0

        else:

            volume_ratio = (
                volume / volume_ma20
            )


        # =========================
        # 5일 수익률
        # =========================

        close_5 = float(
            df["Close"].iloc[-6]
        )

        return_5 = (
            close / close_5 - 1
        ) * 100


        # =========================
        # 20일 수익률
        # =========================

        close_20 = float(
            df["Close"].iloc[-21]
        )

        return_20 = (
            close / close_20 - 1
        ) * 100


        # =========================
        # 점수
        # =========================

        score = 0


        # =========================
        # 추세
        # =========================

        if ma5 > ma20:

            score += 20


        # =========================
        # 가격 위치
        # =========================

        if close > ma5:

            score += 15

        if close > ma20:

            score += 15


        # =========================
        # RSI
        # =========================

        if 50 <= rsi <= 70:

            score += 20

        elif 40 <= rsi < 50:

            score += 10

        # =========================
        # 스토캐스틱 점수
        # =========================

        if stoch_k > stoch_d and stoch_k < 80:

            score += 5

        elif stoch_k < stoch_d and stoch_k > 20:

            score -= 5

        # =========================
        # ADX 점수
        # =========================

        if adx >= 25 and plus_di_current > minus_di_current:

            score += 5

        elif adx >= 25 and plus_di_current < minus_di_current:

            score -= 5


        # =========================
        # 거래량
        # =========================

        if volume_ratio > 1.0:

            score += 15


        # =========================
        # 최근 5일 수익률
        # =========================

        if return_5 > 5:

            score += 10

        elif return_5 > 2:

            score += 7

        elif return_5 > 0:

            score += 4


        # =========================
        # 골든크로스 / 데드크로스
        # =========================

        if golden_cross:

            score += 10

        elif dead_cross:

            score -= 10
            

        # =========================
        # MACD 점수
        # =========================

        if macd_bullish:

            score += 10

        elif macd_bearish:

            score -= 10

        # =========================
        # 볼린저밴드 점수
        # =========================

        if close >= bollinger_upper:

            score -= 5

        elif close <= bollinger_lower:

            score += 10

        elif close > bollinger_middle:

            score += 5

        # =========================
        # 지지선 / 저항선 점수
        # =========================

        if support_distance <= 5:

            score += 5

        if resistance_distance <= 3:

            score -= 5

        # =========================
        # 고점 돌파 점수
        # =========================

        if breakout:

            score += 10

        # =========================
        # 캔들 패턴 점수
        # =========================

        if candle_signal == "강한 양봉":

            score += 5

        elif candle_signal == "강한 음봉":

            score -= 5


        # =========================
        # 변동성
        # =========================

        recent_high = float(
            df["High"]
            .iloc[-20:]
            .max()
        )

        recent_low = float(
            df["Low"]
            .iloc[-20:]
            .min()
        )

        volatility = (
            (recent_high - recent_low)
            / close
        ) * 100


        # =========================
        # 고변동성 필터
        # =========================

        if volatility >= 20:

            print(
                f"{name} 제외 : "
                f"변동성 {volatility:.2f}%"
            )

            return None


        # =========================
        # 손절 / 익절
        # =========================

        if volatility < 8:

            stop_rate = 4
            target_rate = 8

        elif volatility < 15:

            stop_rate = 5
            target_rate = 10

        else:

            stop_rate = 7
            target_rate = 14


        stop_price = round(
            close * (
                1 - stop_rate / 100
            )
        )

        target_price = round(
            close * (
                1 + target_rate / 100
            )
        )


        # =========================
        # 신호
        # =========================

        if score >= 90:

            signal = "강한 매수 후보"

        elif score >= 80:

            signal = "매수 후보"

        elif score >= 70:

            signal = "관심"

        else:

            signal = "관망"


        # =========================
        # 결과
        # =========================

        return {

            "종목": name,

            "현재가": round(close),

            "5일선": round(
                ma5,
                2
            ),

            "20일선": round(
                ma20,
                2
            ),

            "골든크로스": golden_cross,

            "데드크로스": dead_cross,

            "MACD": round(macd, 4),

            "MACD신호": round(
                macd_signal,
                4
            ),

            "MACD상승": macd_bullish,

            "볼린저상단": round(
                bollinger_upper,
                2
            ),

            "볼린저중간": round(
                bollinger_middle,
                2
            ),

            "볼린저하단": round(
                bollinger_lower,
                2
            ),

            "볼린저위치": bollinger_position,

            "지지선": round(
                support_level,
                2
             ),

            "저항선": round(
                resistance_level,
                2
            ),

            "지지선거리": round(
                support_distance,
                2
            ),

            "저항선거리": round(
                resistance_distance,
                2
            ),

            "이전고점": round(
                previous_high,
                2
            ),

            "고점돌파": breakout,

            "캔들신호": candle_signal,

            "RSI": round(
                rsi,
                2
            ),

            "스토캐스틱K": round(
                stoch_k,
                2
            ),

            "스토캐스틱D": round(
                stoch_d,
                2
            ),

            "스토캐스틱상태": (
                "상승"
                if stoch_k > stoch_d
                else "하락"
            ),

            "ADX": round(
                adx,
                2
            ),

            "ADX상태": (
                "상승추세"
                if plus_di_current > minus_di_current
                else "하락추세"
            ),

            "거래량배수": round(
                volume_ratio,
                2
            ),

            "5일수익률": round(
                return_5,
                2
            ),

            "20일수익률": round(
                return_20,
                2
            ),

            "변동성": round(
                volatility,
                2
            ),

            "점수": score,

            "손절가": stop_price,

            "익절가": target_price,

            "손절률": stop_rate,

            "익절률": target_rate,

            "신호": signal
        }


    except Exception as e:

        print()
        print(
            f"❌ {name} 분석 오류"
        )

        print(
            f"오류 내용 : {e}"
        )

        return None
        
# =========================
# 시장환경 분석
# =========================

def analyze_market():

    try:

        df = yf.download(
            "^KS11",
            period="3mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < 30:
            return None

        close = df["Close"]

        ma20 = (
            close
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        current_price = float(
            close.iloc[-1]
        )

        previous_price = float(
            close.iloc[-6]
        )

        return_5 = (
            current_price / previous_price - 1
        ) * 100

        score = 0

        if current_price > ma20:
            score += 5

        if return_5 > 2:
            score += 5

        elif return_5 < -2:
            score -= 5

        if score >= 10:
            market_status = "강한 상승장"

        elif score >= 5:
            market_status = "상승장"

        elif score <= -5:
            market_status = "약세장"

        else:
            market_status = "중립"

        return {
            "시장": "KOSPI",
            "현재가": round(current_price, 2),
            "20일선": round(float(ma20), 2),
            "5일수익률": round(return_5, 2),
            "점수": score,
            "상태": market_status
        }

    except Exception as e:

        print(
            f"시장 분석 오류 : {e}"
        )

        return None

# =========================
# KOSDAQ 시장환경 분석
# =========================

def analyze_kosdaq():

    try:

        df = yf.download(
            "^KQ11",
            period="3mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.dropna()

        if len(df) < 30:
            return None

        close = df["Close"]

        ma20 = (
            close
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        current_price = float(
            close.iloc[-1]
        )

        previous_price = float(
            close.iloc[-6]
        )

        return_5 = (
            current_price / previous_price - 1
        ) * 100

        score = 0

        if current_price > ma20:
            score += 5

        if return_5 > 2:
            score += 5

        elif return_5 < -2:
            score -= 5

        if score >= 10:
            market_status = "강한 상승장"

        elif score >= 5:
            market_status = "상승장"

        elif score <= -5:
            market_status = "약세장"

        else:
            market_status = "중립"

        return {
            "시장": "KOSDAQ",
            "현재가": round(current_price, 2),
            "20일선": round(float(ma20), 2),
            "5일수익률": round(return_5, 2),
            "점수": score,
            "상태": market_status
        }

    except Exception as e:

        print(
            f"KOSDAQ 시장 분석 오류 : {e}"
        )

        return None


# =========================
# 메인
# =========================

print()
print("==============================")
print(" 실시간 매수 후보 알림 시스템")
print("==============================")

print()
print(
    f"스캔 종목 수 : "
    f"{len(STOCKS)}개"
)

print()
print("데이터 다운로드 중...")


market = analyze_market()
kosdaq = analyze_kosdaq()

if market is not None:

    print(
        f"시장 상태 : "
        f"{market['상태']} "
        f"({market['점수']:+d}점)"
    )

    print(
        f"KOSPI 현재가 : "
        f"{market['현재가']}"
    )

    print(
        f"KOSPI 20일선 : "
        f"{market['20일선']}"
    )

    print(
        f"KOSPI 5일 수익률 : "
        f"{market['5일수익률']:+.2f}%"
    )

else:

    print("시장 상태 : 분석 실패")

if kosdaq is not None:

    print(
        f"KOSDAQ 상태 : "
        f"{kosdaq['상태']} "
        f"({kosdaq['점수']:+d}점)"
    )

    print(
        f"KOSDAQ 현재가 : "
        f"{kosdaq['현재가']}"
    )

    print(
        f"KOSDAQ 20일선 : "
        f"{kosdaq['20일선']}"
    )

    print(
        f"KOSDAQ 5일 수익률 : "
        f"{kosdaq['5일수익률']:+.2f}%"
    )

else:

    print("KOSDAQ 상태 : 분석 실패")
    

results = []

for name, ticker in STOCKS.items():

    print(
        f"{name} 확인 중..."
    )

    result = analyze_stock(
        name,
        ticker
    )

    if result is None:

        print(
            f"❌ {name} → 분석 결과 없음"
        )

    else:

        print(
            f"✅ {name} → 분석 성공 / "
            f"점수 {result['점수']}"
        )

        if market is not None:

            result["점수"] += market["점수"]

            result["시장상태"] = market["상태"]

        results.append(result)

print()
print("데이터 다운로드 완료")


# =========================
# 점수순 정렬
# =========================

results.sort(
    key=lambda x: x["점수"],
    reverse=True
)

print()
print("===== 전체 종목 점수 =====")

for item in results:

    print(
        item["종목"],
        item["점수"]
    )


# =========================
# 매수 후보
# =========================

candidates = [

    item

    for item in results

    if item["점수"] >= MIN_SCORE
]


print()
print("==============================")
print(" 오늘의 매수 후보")
print("==============================")


if not candidates:

    print()
    print("오늘의 매수 후보가 없습니다.")

else:

    for rank, item in enumerate(
        candidates[:10],
        1
    ):

        print()

        print(
            f"{rank}위 | "
            f"{item['종목']} | "
            f"점수 {item['점수']} | "
            f"RSI {item['RSI']:.2f}"
        )

        print(
            f"    현재가 : "
            f"{item['현재가']:,}원"
        )

        print(
            f"    5일선 : "
            f"{item['5일선']:,.2f}"
        )

        print(
            f"    20일선 : "
            f"{item['20일선']:,.2f}"
        )

        print(
            f"    골든크로스 : "
            f"{'발생' if item['골든크로스'] else '없음'}"
        )

        print(
            f"    데드크로스 : "
            f"{'발생' if item['데드크로스'] else '없음'}"
        )

        print(
            f"    5일 수익률 : "
            f"{item['5일수익률']:+.2f}%"
        )

        print(
            f"    20일 수익률 : "
            f"{item['20일수익률']:+.2f}%"
        )

        print(
            f"    거래량 : "
            f"{item['거래량배수']:.2f}배"
        )

        print(
            f"    변동성 : "
            f"{item['변동성']:.2f}%"
        )

        print(
            f"    손절가 : "
            f"{item['손절가']:,}원 "
            f"(-{item['손절률']}%)"
        )

        print(
            f"    익절가 : "
            f"{item['익절가']:,}원 "
            f"(+{item['익절률']}%)"
        )

        print(
            f"    신호 : "
            f"{item['신호']}"
        )


# =========================
# Telegram 메시지
# =========================

top_candidates = candidates[:5]

total_candidates = len(top_candidates)

print()
print("==============================")
print(" 알림 메시지")
print("==============================")

# =========================
# 중복 알림 확인 + Telegram 전송
# =========================

history = load_alert_history()

today = datetime.now().strftime("%Y-%m-%d")

for rank, item in enumerate(top_candidates, 1):

    stock_name = item["종목"]

    today_key = f"{today}_{stock_name}"

    current_score = item["점수"]

    message = (
        f"[매수 후보 {rank}/{len(top_candidates)}]\n"
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        f"종목 : {stock_name}\n"
        f"점수 : {current_score}\n"
        f"시장 상태 : {item['시장상태']}\n"
        f"시장 점수 : {market['점수']:+d}\n\n"

        f"현재가 : {item['현재가']:,}원\n"
        f"5일선 : {item['5일선']:,.2f}\n"
        f"20일선 : {item['20일선']:,.2f}\n"
        f"골든크로스 : {'발생' if item['골든크로스'] else '없음'}\n"
        f"데드크로스 : {'발생' if item['데드크로스'] else '없음'}\n\n"

        f"MACD : {item['MACD']:.4f}\n"
        f"MACD 신호선 : {item['MACD신호']:.4f}\n"
        f"MACD 상태 : {'상승' if item['MACD상승'] else '하락'}\n\n"

        f"볼린저 상단 : {item['볼린저상단']:,.2f}\n"
        f"볼린저 중간 : {item['볼린저중간']:,.2f}\n"
        f"볼린저 하단 : {item['볼린저하단']:,.2f}\n"
        f"볼린저 위치 : {item['볼린저위치']}\n\n"

        f"지지선 : {item['지지선']:,.0f}원 "
        f"(현재가 대비 -{item['지지선거리']:.2f}%)\n"

        f"저항선 : {item['저항선']:,.0f}원 "
        f"(현재가 대비 +{item['저항선거리']:.2f}%)\n\n"

        f"이전 20일 고점 : {item['이전고점']:,.0f}원\n"
        f"고점 돌파 : {'발생' if item['고점돌파'] else '없음'}\n"
        f"캔들 신호 : {item['캔들신호']}\n\n"

        f"RSI : {item['RSI']:.2f}\n"
        f"스토캐스틱 K : {item['스토캐스틱K']:.2f}\n"
        f"스토캐스틱 D : {item['스토캐스틱D']:.2f}\n"
        f"스토캐스틱 상태 : {item['스토캐스틱상태']}\n\n"

        f"ADX : {item['ADX']:.2f}\n"
        f"ADX 상태 : {item['ADX상태']}\n\n"

        f"5일 수익률 : {item['5일수익률']:+.2f}%\n"
        f"20일 수익률 : {item['20일수익률']:+.2f}%\n"
        f"거래량 : {item['거래량배수']:.2f}배\n"
        f"변동성 : {item['변동성']:.2f}%\n\n"

        f"손절가 : {item['손절가']:,}원 "
        f"(-{item['손절률']}%)\n"

        f"익절가 : {item['익절가']:,}원 "
        f"(+{item['익절률']}%)\n\n"

        f"신호 : {item['신호']}"
    )

    print()
    print(message)

    # =========================
    # 중복 확인
    # =========================

    if today_key in history:

        previous_score = history[today_key]["점수"]

        if current_score > previous_score:

            send_telegram(message)

            history[today_key]["점수"] = current_score
            history[today_key]["시간"] = datetime.now().strftime("%H:%M:%S")

            save_alert_history(history)

            print(
                f"점수 상승 재알림 : "
                f"{stock_name} "
                f"{previous_score} → {current_score}"
            )

        else:

            print(
                f"이미 알림 완료 : "
                f"{stock_name} "
                f"(기존 {previous_score}점 / "
                f"현재 {current_score}점)"
            )

    else:

        send_telegram(message)

        history[today_key] = {
            "종목": stock_name,
            "점수": current_score,
            "시간": datetime.now().strftime("%H:%M:%S")
        }

        save_alert_history(history)

        print(
            f"새 알림 기록 완료 : {stock_name}"
        )


print()
print("==============================")
print(" 스캔 완료")
print("==============================")

check_buy_message()
