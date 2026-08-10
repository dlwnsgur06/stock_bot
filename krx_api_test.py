import os
import requests

API_KEY = os.getenv("DATA_GO_KR_SERVICE_KEY")

print()
print("==============================")
print("공공데이터포털 KRX API 인증 테스트")
print("==============================")

if not API_KEY:
    print("DATA_GO_KR_SERVICE_KEY가 없습니다.")
    raise SystemExit(1)

url = (
    "https://apis.data.go.kr/"
    "1160100/service/GetKrxListedInfoService/"
    "getItemInfo"
)

params = {
    "serviceKey": API_KEY,
    "numOfRows": "1",
    "pageNo": "1",
    "resultType": "json"
}

try:
    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    print()
    print("HTTP 상태 :", response.status_code)

    safe_url = response.url.replace(API_KEY, "***")

    print("최종 요청 URL :")
    print(safe_url)

    print()
    print("응답 :")
    print(response.text[:1000])

except requests.exceptions.Timeout:
    print()
    print("API 서버 응답 시간 초과")
    raise SystemExit(1)

except requests.exceptions.RequestException as e:
    print()
    print("API 요청 오류")
    print(e)
    raise SystemExit(1)

if response.status_code != 200:
    print()
    print("API 호출 실패")
    raise SystemExit(1)

print()
print("==============================")
print("API 호출 성공")
print("==============================")
