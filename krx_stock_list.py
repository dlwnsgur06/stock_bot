import os
import requests

API_KEY = os.getenv("KRX_API_KEY")

print()
print("==============================")
print(" KRX 전체 종목 목록 테스트")
print("==============================")

if not API_KEY:
    print("KRX_API_KEY가 없습니다.")
    raise SystemExit(1)

BASE_URL = "https://openapi.krx.co.kr"

apis = {
    "유가증권": "/contents/OPP/REST/sto/stk_bydd_trd.json",
    "코스닥": "/contents/OPP/REST/sto/ksq_bydd_trd.json"
}

stocks = {}

for market, path in apis.items():

    print()
    print(f"{market} 조회 중...")

    url = BASE_URL + path

    params = {
        "basDd": "20260810"
    }

    headers = {
        "AUTH_KEY": API_KEY
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=60
        )

        print("HTTP 상태 :", response.status_code)

        if response.status_code != 200:
            print(response.text[:1000])
            raise SystemExit(1)

        data = response.json()

        rows = data.get("OutBlock_1", [])

        for row in rows:

            ticker = row.get("ISU_SRT_CD")
            name = row.get("ISU_ABBRV")

            if ticker and name:
                stocks[name] = ticker

        print(f"{market} 종목 수 : {len(rows)}개")

    except Exception as e:
        print(f"{market} 조회 오류 : {e}")
        raise SystemExit(1)

print()
print("==============================")
print(f"전체 종목 수 : {len(stocks)}개")
print("==============================")

if not stocks:
    print("종목 목록을 가져오지 못했습니다.")
    raise SystemExit(1)

print()
print("종목 목록 가져오기 성공")

print()
print("===== 샘플 30개 =====")

for i, (name, ticker) in enumerate(stocks.items()):

    if i >= 30:
        break

    print(f"{name} : {ticker}")

print()
print("==============================")
print(" 테스트 완료")
print("==============================")
