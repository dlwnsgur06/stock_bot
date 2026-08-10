from pykrx import stock
from datetime import datetime, timedelta

print()
print("==============================")
print(" KOSPI + KOSDAQ 종목 목록 테스트")
print("==============================")

today = datetime.now()

stocks = {}

for market in ["KOSPI", "KOSDAQ"]:

    tickers = []

    for i in range(10):

        date = (
            today - timedelta(days=i)
        ).strftime("%Y%m%d")

        try:

            tickers = stock.get_market_ticker_list(
                date=date,
                market=market
            )

            if tickers:
                break

        except Exception as e:

            print(
                f"{market} 조회 실패 : {e}"
            )

    print()
    print(
        f"{market} 종목 수 : "
        f"{len(tickers)}개"
    )

    for ticker in tickers:

        try:

            name = stock.get_market_ticker_name(
                ticker
            )

            stocks[name] = ticker

        except Exception:

            continue

print()
print("==============================")
print(
    f"전체 종목 수 : {len(stocks)}개"
)
print("==============================")

if not stocks:

    print()
    print("종목 목록 가져오기 실패")
    raise SystemExit(1)

print()
print("종목 목록 가져오기 성공")

print()
print("===== 샘플 20개 =====")

for i, (name, ticker) in enumerate(
    stocks.items()
):

    if i >= 20:
        break

    print(
        f"{name} : {ticker}"
    )

print()
print("==============================")
print(" 테스트 완료")
print("==============================")
