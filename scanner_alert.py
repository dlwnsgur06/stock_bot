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
        # RSI
        # =========================

        rsi_series = calculate_rsi(
            df["Close"]
        )

        rsi = float(
            rsi_series.iloc[-1]
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

            "RSI": round(
                rsi,
                2
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

        print(
            f"{name} 분석 오류 : {e}"
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


results = []


for name, ticker in STOCKS.items():

    print(
        f"{name} 확인 중..."
    )

    result = analyze_stock(
        name,
        ticker
    )

    if result is not None:

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

    top = candidates[0]

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    message = (
        f"[매수 후보 발생]\n"
        f"{now}\n\n"

        f"종목 : {top['종목']}\n"
        f"점수 : {top['점수']}\n"
        f"현재가 : {top['현재가']:,}원\n\n"

        f"5일선 : "
        f"{top['5일선']:,.2f}\n"

        f"20일선 : "
        f"{top['20일선']:,.2f}\n"

        f"골든크로스 : "
        f"{'발생' if top['골든크로스'] else '없음'}\n"

        f"데드크로스 : "
        f"{'발생' if top['데드크로스'] else '없음'}\n\n"

        f"RSI : {top['RSI']:.2f}\n"

        f"5일 수익률 : "
        f"{top['5일수익률']:+.2f}%\n"

        f"20일 수익률 : "
        f"{top['20일수익률']:+.2f}%\n"

        f"거래량 : "
        f"{top['거래량배수']:.2f}배\n"

        f"변동성 : "
        f"{top['변동성']:.2f}%\n\n"

        f"손절가 : "
        f"{top['손절가']:,}원 "
        f"(-{top['손절률']}%)\n"

        f"익절가 : "
        f"{top['익절가']:,}원 "
        f"(+{top['익절률']}%)\n\n"

        f"신호 : {top['신호']}"
    )


    print()
    print("==============================")
    print(" 알림 메시지")
    print("==============================")

    print()
    print(message)


    # =========================
    # 중복 알림 확인
    # =========================

    history = load_alert_history()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    stock_name = top["종목"]

    today_key = (
        f"{today}_{stock_name}"
    )

    current_score = top["점수"]


    # =========================
    # 기존 알림 확인
    # =========================

    if today_key in history:

        previous_score = (
            history[today_key]["점수"]
        )


        # =========================
        # 점수 상승 재알림
        # =========================

        if current_score > previous_score:

            message = (
                f"🚨 매수 신호 강화\n\n"

                f"종목 : {stock_name}\n"

                f"점수 : "
                f"{previous_score} → "
                f"{current_score}\n"

                f"현재가 : "
                f"{top['현재가']:,}원\n\n"

                f"골든크로스 : "
                f"{'발생' if top['골든크로스'] else '없음'}\n"

                f"데드크로스 : "
                f"{'발생' if top['데드크로스'] else '없음'}\n\n"

                f"RSI : "
                f"{top['RSI']:.2f}\n"

                f"변동성 : "
                f"{top['변동성']:.2f}%\n\n"

                f"손절가 : "
                f"{top['손절가']:,}원 "
                f"(-{top['손절률']}%)\n"

                f"익절가 : "
                f"{top['익절가']:,}원 "
                f"(+{top['익절률']}%)"
            )


            send_telegram(message)


            history[today_key]["점수"] = (
                current_score
            )

            history[today_key]["시간"] = (
                datetime.now().strftime(
                    "%H:%M:%S"
                )
            )

            save_alert_history(history)


            print()

            print(
                f"점수 상승 재알림 : "
                f"{previous_score} → "
                f"{current_score}"
            )


        else:

            print()

            print(
                f"이미 알림 완료 : "
                f"{stock_name} "
                f"(기존 {previous_score}점 / "
                f"현재 {current_score}점)"
            )


    # =========================
    # 첫 알림
    # =========================

    else:

        send_telegram(message)


        history[today_key] = {

            "종목": stock_name,

            "점수": current_score,

            "시간": datetime.now().strftime(
                "%H:%M:%S"
            )
        }


        save_alert_history(history)


        print()

        print(
            f"새 알림 기록 완료 : "
            f"{stock_name}"
        )


print()
print("==============================")
print(" 스캔 완료")
print("==============================")
