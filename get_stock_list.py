import os
import requests

API_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")

URL = (
    "https://apis.data.go.kr/"
    "1160100/service/GetKrxListedInfoService/"
    "getItemInfo"
)

print()
print("==============================")
print(" KOSPI + KOSDAQ 전체 종목 목록")
print("==============================")

if not API_KEY:
    print("DATA_GO_KR_SERVICE_KEY가 없습니다.")
    raise SystemExit(1)

stocks = {}

for market in ["KOSPI", "KOSDAQ"]:

    print()
    print(f"{market} 종목 조회 중...")

    page = 1
    market_count = 0

    while True:

        params = {
            "serviceKey": API_KEY,
            "numOfRows": "100",
            "pageNo": str(page),
            "resultType": "json"
        }

        try:
            response = requests.get(
                URL,
                params=params,
                timeout=60
            )

            if response.status_code != 200:
                print(f"{market} API 오류 : {response.status_code}")
                print(response.text[:1000])
                raise SystemExit(1)

            data = response.json()

        except Exception as e:
            print(f"{market} 조회 오류 : {e}")
            raise SystemExit(1)

        items = (
            data
            .get("response", {})
            .get("body", {})
            .get("items", {})
            .get("item", [])
        )

        if not items:
            break

        if isinstance(items, dict):
            items = [items]

        for item in items:

            market_name = str(
                item.get("mrktCtg", "")
            ).upper()

            if market_name != market:
                continue

            ticker = item.get("srtnCd")
            name = item.get("itmsNm")

            if ticker and name:
                stocks[name] = ticker
                market_count += 1

        page += 1

        if page > 100:
            break

    print(
        f"{market} 종목 수 : "
        f"{market_count}개"
    )

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
