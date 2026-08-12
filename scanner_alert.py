import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import os
import time


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
# Telegram 메시지 확인
# =========================

def check_telegram_messages():

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

        if not data.get("ok"):
            return

        holdings = load_holdings()

        update_file = "telegram_update_id.txt"

        if os.path.exists(update_file):

            with open(
                update_file,
                "r",
                encoding="utf-8"
            ) as f:

                last_update_id = int(
                    f.read().strip()
                )

        else:

            last_update_id = 0

        latest_update_id = last_update_id

        for update in data.get("result", []):

            update_id = update.get("update_id")

            if update_id is None:
                continue

            if update_id <= last_update_id:
                continue

            latest_update_id = max(
                latest_update_id,
                update_id
            )

            message_data = update.get("message")

            if not message_data:
                continue

            chat_id = str(
                message_data["chat"]["id"]
            )

            if chat_id != str(
                TELEGRAM_CHAT_ID
            ):
                continue

            text = message_data.get(
                "text",
                ""
            ).strip()

            # =========================
            # 매수 명령
            # =========================

            if text.startswith("매수 "):

                parts = text.split()

                if len(parts) != 4:

                    send_telegram(
                        "매수 등록 실패\n\n"
                        "형식이 잘못되었습니다.\n\n"
                        "예시 :\n"
                        "매수 신한지주 110000 10"
                    )

                    continue

                stock_name = parts[1]

                if stock_name not in STOCKS:

                    send_telegram(
                        f"매수 등록 실패\n\n"
                        f"알 수 없는 종목 : {stock_name}"
                    )

                    continue

                try:

                    buy_price = int(parts[2])
                    quantity = int(parts[3])

                except ValueError:

                    send_telegram(
                        "매수 등록 실패\n\n"
                        "가격과 수량은 숫자로 입력해주세요."
                    )

                    continue

                stock_data = analyze_stock(
                    stock_name,
                    STOCKS[stock_name]
                )

                if stock_data is None:

                    send_telegram(
                        f"매수 등록 실패\n\n"
                        f"{stock_name} 분석 실패"
                    )

                    continue

                stop_price = stock_data["손절가"]
                target_price = stock_data["익절가"]

                holdings[stock_name] = {

                    "종목": stock_name,
                    "매수가": buy_price,
                    "수량": quantity,
                    "손절가": stop_price,
                    "익절가": target_price,
                    "손절률": stock_data["손절률"],
                    "익절률": stock_data["익절률"],
                    "매도신호전송": False
                }

                save_holdings(holdings)

                send_telegram(
                    f"매수 등록 완료\n\n"
                    f"종목 : {stock_name}\n"
                    f"매수가 : {buy_price:,}원\n"
                    f"수량 : {quantity}주\n"
                    f"손절가 : {stop_price:,}원\n"
                    f"익절가 : {target_price:,}원"
                )

                continue

            # =========================
            # 매도 명령
            # =========================

            if text.startswith("매도 "):

                parts = text.split()

                if len(parts) != 2:

                    send_telegram(
                        "매도 실패\n\n"
                        "예시 :\n"
                        "매도 신한지주"
                    )

                    continue

                stock_name = parts[1]

                if stock_name not in holdings:

                    send_telegram(
                        f"매도 실패\n\n"
                        f"{stock_name}은(는) "
                        f"보유종목에 없습니다."
                    )

                    continue

                del holdings[stock_name]

                save_holdings(holdings)

                send_telegram(
                    f"매도 등록 완료\n\n"
                    f"종목 : {stock_name}\n"
                    f"보유종목에서 삭제했습니다."
                )

                continue

        # =========================
        # update_id 저장
        # =========================

        if latest_update_id > last_update_id:

            with open(
                update_file,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    str(latest_update_id)
                )

    except Exception as e:

        print(
            f"Telegram 메시지 확인 오류 : {e}"
        )


# =========================
# Telegram 매도 완료 메시지 확인
# =========================

def check_sell_message():

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

        if not data.get("ok"):
            return

        holdings = load_holdings()

        update_file = "telegram_update_id.txt"

        if os.path.exists(update_file):

            with open(
                update_file,
                "r",
                encoding="utf-8"
            ) as f:

                last_update_id = int(
                    f.read().strip()
                )

        else:

            last_update_id = 0

        latest_update_id = last_update_id

        for update in data.get("result", []):

            update_id = update.get("update_id")

            if update_id is None:
                continue

            if update_id <= last_update_id:
                continue

            latest_update_id = max(
                latest_update_id,
                update_id
            )

            message_data = update.get("message")

            if not message_data:
                continue

            chat_id = str(
                message_data["chat"]["id"]
            )

            if chat_id != str(
                TELEGRAM_CHAT_ID
            ):
                continue

            text = message_data.get(
                "text",
                ""
            ).strip()

            if not text.startswith("매도 "):
                continue

            parts = text.split()

            if len(parts) != 2:
                continue

            stock_name = parts[1]

            if stock_name not in holdings:

                send_telegram(
                    f"매도 처리 실패\n\n"
                    f"{stock_name}은(는) "
                    f"현재 보유종목에 없습니다."
                )

                continue

            holding = holdings[stock_name]

            buy_price = holding["매수가"]
            quantity = holding["수량"]

            del holdings[stock_name]

            save_holdings(holdings)

            send_telegram(
                f"매도 처리 완료\n\n"
                f"종목 : {stock_name}\n"
                f"기존 매수가 : {buy_price:,}원\n"
                f"수량 : {quantity}주\n\n"
                f"보유종목에서 삭제되었습니다."
            )

            print(
                f"매도 처리 완료 : "
                f"{stock_name}"
            )

        if latest_update_id > last_update_id:

            with open(
                update_file,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    str(latest_update_id)
                )

    except Exception as e:

        print(
            f"매도 메시지 확인 오류 : {e}"
        )


# =========================
# KRX 전체 종목 목록
# =========================

KRX_API_KEY = os.getenv("KRX_API_KEY")

KOSPI_URL = (
    "https://data-dbg.krx.co.kr/"
    "svc/apis/sto/stk_isu_base_info"
)

KOSDAQ_URL = (
    "https://data-dbg.krx.co.kr/"
    "svc/apis/sto/ksq_isu_base_info"
)

STOCK_MARKETS = {}


def load_krx_stocks():

    if not KRX_API_KEY:
        print("KRX_API_KEY가 없습니다.")
        return {}

    stocks = {}

    today = datetime.now()

    api_list = [
        ("KOSPI", KOSPI_URL, ".KS"),
        ("KOSDAQ", KOSDAQ_URL, ".KQ")
    ]

    for market, url, suffix in api_list:

        success = False

        for i in range(10):

            date = (
                today - pd.Timedelta(days=i)
            ).strftime("%Y%m%d")

            try:

                response = requests.get(
                    url,
                    headers={
                        "AUTH_KEY": KRX_API_KEY
                    },
                    params={
                        "basDd": date
                    },
                    timeout=30
                )
                
                if response.status_code != 200:

                    print(
                        f"{market} {date} "
                        f"HTTP 상태 : {response.status_code}"
                    )

                    print(
                        f"응답 내용 : "
                        f"{response.text[:500]}"
                    )

                    continue


                data = response.json()

                rows = data.get(
                    "OutBlock_1",
                    []
                )

                if not rows:
                    continue

                for row in rows:

                    ticker = row.get(
                        "ISU_SRT_CD"
                    )

                    name = row.get(
                        "ISU_ABBRV"
                    )

                    if ticker and name:

                        ticker = str(ticker)

                        stocks[name] = (
                            ticker + suffix
                        )

                        STOCK_MARKETS[name] = market

                print(
                    f"{market} 종목 수 : "
                    f"{len(rows)}개"
                )

                success = True
                break

            except Exception as e:

                print(
                    f"{market} 조회 오류 : "
                    f"{e}"
                )

        if not success:

            print(
                f"{market} 종목 목록 "
                "가져오기 실패"
            )

    return stocks


# =========================
# KRX 전체 종목
# =========================

STOCKS = load_krx_stocks()

print()
print("==============================")
print(f"KOSPI + KOSDAQ 전체 종목 : {len(STOCKS)}개")
print("==============================")


# =========================
# STOCKS 티커 확인
# =========================

print()
print("==============================")
print("STOCKS 티커 확인")
print("==============================")

for i, (name, ticker) in enumerate(STOCKS.items()):

    print(
        f"{name} → {ticker}"
    )

    if i >= 19:
        break


# =========================
# 보유종목 손절 / 익절 감시
# =========================

def check_sell_signal():

    holdings = load_holdings()

    if not holdings:
        return

    changed = False

    for stock_name, holding in holdings.items():

        if stock_name not in STOCKS:
            continue

        try:

            ticker = STOCKS[stock_name]

            df = yf.download(
                ticker,
                period="5d",
                interval="1d",
                auto_adjust=False,
                progress=False
            )

            if df.empty:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.dropna()

            if df.empty:
                continue

            current_price = float(
                df["Close"].iloc[-1]
            )

            buy_price = holding["매수가"]
            quantity = holding["수량"]
            stop_price = holding["손절가"]
            target_price = holding["익절가"]

            sell_signal_sent = holding.get(
                "매도신호전송",
                False
            )

            if sell_signal_sent:
                continue

            if current_price <= stop_price:

                send_telegram(
                    f"손절 신호\n\n"
                    f"종목 : {stock_name}\n"
                    f"매수가 : {buy_price:,}원\n"
                    f"현재가 : {current_price:,.0f}원\n"
                    f"손절가 : {stop_price:,}원\n"
                    f"수량 : {quantity}주"
                )

                print(
                    f"{stock_name} 손절 신호"
                )

                holding["매도신호전송"] = True
                changed = True

            elif current_price >= target_price:

                send_telegram(
                    f"익절 신호\n\n"
                    f"종목 : {stock_name}\n"
                    f"매수가 : {buy_price:,}원\n"
                    f"현재가 : {current_price:,.0f}원\n"
                    f"익절가 : {target_price:,}원\n"
                    f"수량 : {quantity}주"
                )

                print(
                    f"{stock_name} 익절 신호"
                )

                holding["매도신호전송"] = True
                changed = True

        except Exception as e:

            print(
                f"{stock_name} 매도 감시 오류 : {e}"
            )

    if changed:

        save_holdings(holdings)
        

# =========================
# 설정
# =========================

MIN_SCORE = 70


# =========================
# RSI 계산 - Wilder 방식
# =========================

def calculate_rsi(series, period=14):

    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

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
# 여러 종목 데이터 일괄 다운로드
# =========================

def download_stock_data(tickers, chunk_size=30):

    stock_data = {}

    ticker_list = list(tickers)

    for i in range(0, len(ticker_list), chunk_size):

        chunk = ticker_list[i:i + chunk_size]

        print(
            f"주가 데이터 다운로드 : "
            f"{i + 1} ~ {min(i + chunk_size, len(ticker_list))} "
            f"/ {len(ticker_list)}"
        )

        try:

            data = yf.download(
                chunk,
                period="6mo",
                interval="1d",
                auto_adjust=False,
                progress=False,
                group_by="ticker",
                threads=False
            )

            if data.empty:
                continue

            # 여러 종목 다운로드 결과
            if isinstance(data.columns, pd.MultiIndex):

                for ticker in chunk:

                    try:

                        if ticker not in data.columns.get_level_values(0):
                            continue

                        df = data[ticker].copy()

                        df = df.dropna()

                        if not df.empty:
                            stock_data[ticker] = df

                    except Exception as e:

                        print(
                            f"{ticker} 데이터 처리 실패 : {e}"
                        )

            else:

                # 종목이 1개인 경우
                if len(chunk) == 1:

                    df = data.copy()

                    df = df.dropna()

                    if not df.empty:
                        stock_data[chunk[0]] = df

        except Exception as e:

            print(
                f"주가 데이터 다운로드 오류 : {e}"
            )

    print(
        f"다운로드 완료 종목 : "
        f"{len(stock_data)}개"
    )

    return stock_data


# =========================
# 종목 분석
# =========================

def analyze_stock(name, ticker, df=None):

    try:

        if df is None:

            df = yf.download(
                ticker,
                period="6mo",
                interval="1d",
                auto_adjust=False,
                progress=False
            )

        if df is None or df.empty:

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
        # ADX - Wilder 방식
        # 기간 14 / 스무딩 14
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
        tr2 = (high - previous_close).abs()
        tr3 = (low - previous_close).abs()

        true_range = pd.concat(
            [tr1, tr2, tr3],
            axis=1
        ).max(axis=1)

        # Wilder 방식
        atr = true_range.ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()

        plus_dm_smoothed = plus_dm.ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()

        minus_dm_smoothed = minus_dm.ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()

        plus_di = (
            100
            * plus_dm_smoothed
            / atr
        )

        minus_di = (
            100
            * minus_dm_smoothed
            / atr
        )

        dx = (
            100
            * (plus_di - minus_di).abs()
            / (plus_di + minus_di)
        )

        # ADX 스무딩 14
        adx_series = dx.ewm(
            alpha=1 / 14,
            adjust=False
        ).mean()

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
# 미국 증시 시장환경 분석
# =========================

def analyze_us_market():

    try:

        sp500 = yf.download(
            "^GSPC",
            period="3mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        nasdaq = yf.download(
            "^IXIC",
            period="3mo",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if sp500.empty or nasdaq.empty:
            return None

        if isinstance(sp500.columns, pd.MultiIndex):
            sp500.columns = sp500.columns.get_level_values(0)

        if isinstance(nasdaq.columns, pd.MultiIndex):
            nasdaq.columns = nasdaq.columns.get_level_values(0)

        sp500 = sp500.dropna()
        nasdaq = nasdaq.dropna()

        if len(sp500) < 30 or len(nasdaq) < 30:
            return None

        # =========================
        # S&P 500
        # =========================

        sp500_close = sp500["Close"]

        sp500_ma20 = (
            sp500_close
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        sp500_current = float(
            sp500_close.iloc[-1]
        )

        sp500_previous = float(
            sp500_close.iloc[-6]
        )

        sp500_return_5 = (
            sp500_current / sp500_previous - 1
        ) * 100

        sp500_score = 0

        if sp500_current > sp500_ma20:

            sp500_score += 5

        if sp500_return_5 > 2:

            sp500_score += 5

        elif sp500_return_5 < -2:

            sp500_score -= 5

        if sp500_score >= 10:

            sp500_status = "강한 상승장"

        elif sp500_score >= 5:

            sp500_status = "상승장"

        elif sp500_score <= -5:

            sp500_status = "약세장"

        else:

            sp500_status = "중립"


        # =========================
        # NASDAQ
        # =========================

        nasdaq_close = nasdaq["Close"]

        nasdaq_ma20 = (
            nasdaq_close
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        nasdaq_current = float(
            nasdaq_close.iloc[-1]
        )

        nasdaq_previous = float(
            nasdaq_close.iloc[-6]
        )

        nasdaq_return_5 = (
            nasdaq_current / nasdaq_previous - 1
        ) * 100

        nasdaq_score = 0

        if nasdaq_current > nasdaq_ma20:

            nasdaq_score += 5

        if nasdaq_return_5 > 2:

            nasdaq_score += 5

        elif nasdaq_return_5 < -2:

            nasdaq_score -= 5

        if nasdaq_score >= 10:

            nasdaq_status = "강한 상승장"

        elif nasdaq_score >= 5:

            nasdaq_status = "상승장"

        elif nasdaq_score <= -5:

            nasdaq_status = "약세장"

        else:

            nasdaq_status = "중립"


        # =========================
        # 미국 시장 종합 점수
        # =========================

        us_total_score = (
            sp500_score
            + nasdaq_score
        )

        if us_total_score >= 15:

            us_status = "강한 상승장"

        elif us_total_score >= 5:

            us_status = "상승장"

        elif us_total_score <= -10:

            us_status = "약세장"

        else:

            us_status = "중립"


        return {

            "SP500현재가": round(
                sp500_current,
                2
            ),

            "SP50020일선": round(
                float(sp500_ma20),
                2
            ),

            "SP5005일수익률": round(
                sp500_return_5,
                2
            ),

            "SP500점수": sp500_score,

            "SP500상태": sp500_status,


            "NASDAQ현재가": round(
                nasdaq_current,
                2
            ),

            "NASDAQ20일선": round(
                float(nasdaq_ma20),
                2
            ),

            "NASDAQ5일수익률": round(
                nasdaq_return_5,
                2
            ),

            "NASDAQ점수": nasdaq_score,

            "NASDAQ상태": nasdaq_status,


            "미국시장점수": us_total_score,

            "미국시장상태": us_status

        }


    except Exception as e:

        print(
            f"미국 증시 분석 오류 : {e}"
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
us_market = analyze_us_market()

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

if us_market is not None:

    print(
        f"S&P 500 상태 : "
        f"{us_market['SP500상태']} "
        f"({us_market['SP500점수']:+d}점)"
    )

    print(
        f"S&P 500 현재가 : "
        f"{us_market['SP500현재가']}"
    )

    print(
        f"S&P 500 20일선 : "
        f"{us_market['SP50020일선']}"
    )

    print(
        f"S&P 500 5일 수익률 : "
        f"{us_market['SP5005일수익률']:+.2f}%"
    )

    print(
        f"NASDAQ 상태 : "
        f"{us_market['NASDAQ상태']} "
        f"({us_market['NASDAQ점수']:+d}점)"
    )

    print(
        f"NASDAQ 현재가 : "
        f"{us_market['NASDAQ현재가']}"
    )

    print(
        f"NASDAQ 20일선 : "
        f"{us_market['NASDAQ20일선']}"
    )

    print(
        f"NASDAQ 5일 수익률 : "
        f"{us_market['NASDAQ5일수익률']:+.2f}%"
    )

else:

    print("미국 시장 상태 : 분석 실패")
    

# =========================
# 전체 종목 일괄 데이터 수집
# =========================

stock_data = download_stock_data(
    STOCKS.values()
)
    

# =========================
# 거래대금 TOP 100 추출
# =========================

def get_top_trading_value_stocks(stock_data, top_n=100):

    trading_value_list = []

    for name, ticker in STOCKS.items():

        df = stock_data.get(ticker)

        if df is None or df.empty:
            continue

        try:

            close = float(df["Close"].iloc[-1])
            volume = float(df["Volume"].iloc[-1])

            if close <= 0 or volume <= 0:
                continue

            # 최근 거래일 거래대금
            trading_value = close * volume

            trading_value_list.append(
                (
                    trading_value,
                    name,
                    ticker
                )
            )

        except Exception:
            continue

    # 거래대금 높은 순으로 정렬
    trading_value_list.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return trading_value_list[:top_n]


# =========================
# 거래대금 TOP 100 가져오기
# =========================

top_trading_value_stocks = get_top_trading_value_stocks(
    stock_data,
    100
)

print()
print("==============================")
print(" 거래대금 TOP 20")
print("==============================")

for rank, (value, name, ticker) in enumerate(
    top_trading_value_stocks[:20],
    start=1
):

    print(
        f"{rank}위 | {name} | "
        f"거래대금 약 {value / 100000000:.1f}억원"
    )

print("==============================")


# =========================
# 거래대금 TOP 100을 정밀 분석 대상으로 사용
# =========================

selected_candidates = []

for rank, (trading_value, name, ticker) in enumerate(
    top_trading_value_stocks,
    start=1
):

    selected_candidates.append(
        (
            trading_value,
            name,
            ticker
        )
    )


print()
print("==============================")
print(
    f"거래대금 TOP 100 정밀 분석"
)
print(
    f"정밀 분석 대상 : "
    f"{len(selected_candidates)}개"
)
print("==============================")


# =========================
# 거래대금 TOP 100 정밀 분석
# =========================

results = []

for trading_value, name, ticker in selected_candidates:

    print(
        f"{name} 확인 중..."
    )

    df = stock_data.get(ticker)

    result = analyze_stock(
        name,
        ticker,
        df
    )

    if result is None:

        print(
            f"❌ {name} → "
            f"분석 결과 없음"
        )

    else:

        print(
            f"✅ {name} → "
            f"분석 성공 / "
            f"점수 {result['점수']}"
        )

        # =========================
        # 시장 점수 반영
        # =========================

        stock_market = STOCK_MARKETS.get(
            name
        )

        if stock_market == "KOSPI":

            market_info = market

        elif stock_market == "KOSDAQ":

            market_info = kosdaq

        else:

            market_info = None


        if market_info is not None:

            result["점수"] += (
                market_info["점수"]
            )

            result["시장"] = stock_market

            result["시장상태"] = (
                market_info["상태"]
            )

            result["시장점수"] = (
                market_info["점수"]
            )

        else:

            result["시장"] = stock_market

            result["시장상태"] = "분석 실패"

            result["시장점수"] = 0


        # =========================
        # 거래대금 정보 저장
        # =========================

        result["거래대금"] = (
            trading_value
        )

        result["거래대금순위"] = (
            len(results) + 1
        )

        results.append(
            result
        )


print()
print("데이터 다운로드 및 분석 완료")


# =========================
# 최종 점수순 정렬
# =========================

results.sort(
    key=lambda x: x["점수"],
    reverse=True
)

print()
print("==============================")
print(" 거래대금 TOP 100 분석 결과")
print("==============================")

for item in results:

    print(
        f"{item['종목']} | "
        f"점수 {item['점수']} | "
        f"거래대금 "
        f"{item['거래대금'] / 100000000:.1f}억원"
    )



# =========================
# 기존 정밀 분석
# =========================

results = []

for quick_score, name, ticker in selected_candidates:

    print(
        f"{name} 확인 중..."
    )

    df = stock_data.get(ticker)

    result = analyze_stock(
        name,
        ticker,
        df
    )

    if result is None:

        print(
            f"❌ {name} → "
            f"분석 결과 없음"
        )

    else:

        print(
            f"✅ {name} → "
            f"분석 성공 / "
            f"점수 {result['점수']}"
        )

        stock_market = STOCK_MARKETS.get(
            name
        )

        if stock_market == "KOSPI":

            market_info = market

        elif stock_market == "KOSDAQ":

            market_info = kosdaq

        else:

            market_info = None


        # =========================
        # 국내 시장 점수 반영
        # =========================

        if market_info is not None:

            result["점수"] += (
                market_info["점수"]
            )

            result["시장"] = stock_market

            result["시장상태"] = (
                market_info["상태"]
            )

            result["시장점수"] = (
                market_info["점수"]
            )

        else:

            result["시장"] = stock_market

            result["시장상태"] = "분석 실패"

            result["시장점수"] = 0


        # =========================
        # 미국 시장 점수 반영
        # =========================

        if us_market is not None:

            us_score = (
                us_market["미국시장점수"]
            )

            if us_score >= 15:

                us_market_score = 5

            elif us_score >= 5:

                us_market_score = 3

            elif us_score <= -15:

                us_market_score = -5

            elif us_score <= -5:

                us_market_score = -3

            else:

                us_market_score = 0


            result["점수"] += (
                us_market_score
            )

            result["미국시장점수"] = (
                us_market_score
            )

            result["미국시장상태"] = (
                us_market["미국시장상태"]
            )

        else:

            result["미국시장점수"] = 0

            result["미국시장상태"] = "분석 실패"


        results.append(
            result
        )


print()
print("데이터 다운로드 및 분석 완료")


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

today = datetime.now(
    ZoneInfo("Asia/Seoul")
).strftime("%Y-%m-%d")

for rank, item in enumerate(top_candidates, 1):

    stock_name = item["종목"]

    today_key = f"{today}_{stock_name}"

    current_score = item["점수"]

    message = (
        f"[매수 후보 {rank}/{len(top_candidates)}]\n"
        f"{datetime.now(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        f"종목 : {stock_name}\n"
        f"점수 : {current_score}\n"
        f"시장 : {item['시장']}\n"
        f"시장 상태 : {item['시장상태']}\n"
        f"시장 점수 : {item['시장점수']:+d}\n\n"

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
            history[today_key]["시간"] = datetime.now(
                ZoneInfo("Asia/Seoul")
            ).strftime("%H:%M:%S")

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
            "시간": datetime.now(
                ZoneInfo("Asia/Seoul")
            ).strftime("%H:%M:%S")
        }

        save_alert_history(history)

        print(
            f"새 알림 기록 완료 : {stock_name}"
        )


print()
print("==============================")
print(" 스캔 완료")
print("==============================")

check_telegram_messages()
check_sell_message()
check_sell_signal()
