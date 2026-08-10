import os
import requests
from datetime import datetime, timedelta

API_KEY = os.getenv("KRX_API_KEY")

print()
print("==============================")
print(" KRX KOSPI + KOSDAQ 종목 테스트")
print("==============================")

if not API_KEY:
    print("KRX_API_KEY가 없습니다.")
    raise SystemExit(1)

APIS = {
    "KOSPI": "https://data-dbg.krx.co.kr/svc/apis/sto/stk_isu_base_info",
    "KOSDAQ": "https://data-dbg.krx.co.kr/svc/apis/sto/ksq_isu_base_info"
}

stocks = {}

today = datetime.now()

for market, url in APIS.items():

    print()
    print(f"{market} 종목 조회 중...")

    success = False

    for i in range(10):

        date = (
            today - timedelta(days=i)
        ).strftime("%Y%m%d")

        try:

            response = requests.get(
                url,
                headers={
                    "AUTH_KEY": API_KEY
                },
                params={
                    "basDd": date
                },
                timeout=60
            )

            print(
                f"{market} {date} "
                f"HTTP 상태 : {response.status_code}"
            )

            if response.status_code != 200:
                continue

            data = response.json()

            rows = data.get("OutBlock_1", [])

            if not rows:
                continue

            for row in rows:

                ticker = row.get("ISU_SRT_CD")
                name = row.get("ISU_ABBRV")

                if ticker and name:
                    stocks[name] = ticker

            print(
                f"{market} 종목 수 : "
                f"{len(rows)}개"
            )

            success = True
            break

        except Exception as e:

            print(
                f"{market} 조회 오류 : {e}"
            )

    if not success:

        print(
            f"{market} 종목 목록을 "
            "가져오지 못했습니다."
        )

print()
print("==============================")
print(
    f"전체 종목 수 : {len(stocks)}개"
)
print("==============================")

if not stocks:
    print("종목 목록 가져오기 실패")
    raise SystemExit(1)

print()
print("종목 목록 가져오기 성공")

print()
print("===== 샘플 30개 =====")

for i, (name, ticker) in enumerate(
    stocks.items()
):

    if i >= 30:
        break

    print(
        f"{name} : {ticker}"
    )

print()
print("==============================")
print(" 테스트 완료")
print("==============================")
