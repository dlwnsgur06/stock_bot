import os
import requests

SERVICE_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")

URL = (
    "https://apis.data.go.kr/1160100/service/"
    "GetKrxListedInfoService/getItemInfo"
)

print()
print("==============================")
print(" 공공데이터포털 KRX 종목 목록 테스트")
print("==============================")

if not SERVICE_KEY:
    print()
    print("❌ DATA_GO_KR_SERVICE_KEY가 없습니다.")
    print()
    print("GitHub Secrets에")
    print("DATA_GO_KR_SERVICE_KEY")
    print("이름으로 API 키를 등록해야 합니다.")
    raise SystemExit(1)

params = {
    "serviceKey": SERVICE_KEY,
    "numOfRows": 10,
    "pageNo": 1,
    "resultType": "json"
}

try:

    response = requests.get(
        URL,
        params=params,
        timeout=20
    )

    print()
    print(
        "HTTP 상태 :",
        response.status_code
    )

    if response.status_code != 200:

        print("❌ API 호출 실패")
        print(response.text[:1000])

        raise SystemExit(1)

    data = response.json()

    header = (
        data
        .get("response", {})
        .get("header", {})
    )

    result_code = header.get(
        "resultCode"
    )

    result_msg = header.get(
        "resultMsg"
    )

    print(
        "API 결과 :",
        result_code
    )

    print(
        "API 메시지 :",
        result_msg
    )

    if result_code != "00":

        print()
        print("❌ API 오류")
        print(data)

        raise SystemExit(1)

    items = (
        data
        .get("response", {})
        .get("body", {})
        .get("items", {})
        .get("item", [])
    )

    if isinstance(items, dict):
        items = [items]

    print()
    print(
        "가져온 종목 수 :",
        len(items)
    )

    print()
    print("===== 샘플 종목 =====")

    for item in items[:10]:

        print(
            f"{item.get('itmsNm')} | "
            f"{item.get('srtnCd')} | "
            f"{item.get('mrktCtg')}"
        )

    print()
    print("==============================")
    print(" 테스트 성공")
    print("==============================")

except Exception as e:

    print()
    print("❌ 오류 발생")
    print(e)

    raise SystemExit(1)
