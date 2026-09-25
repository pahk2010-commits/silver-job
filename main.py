from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import os
import asyncio
from datetime import datetime
from html import escape

app = FastAPI()

API_URL = os.getenv(
    "SENIOR_JOB_API_URL",
    "https://apis.data.go.kr/B552474/SenuriService/getJobList"
).strip()

SENIOR_JOB_API_KEY = unquote(
    os.getenv(
        "SENIOR_JOB_API_KEY",
        ""
    ).strip()
)

EMPLOYMENT24_KEY = os.getenv(
    "EMPLOYMENT24_KEY",
    ""
).strip()

EMPLOYMENT24_URL = (
    "https://www.work24.go.kr/cm/openApi/call/wk/" "callOpenApiSvcInfo210L01.do"
)

DEFAULT_ROWS = 100
REFRESH_SECONDS = 1800

LIVE_JOB_CACHE = []
LAST_UPDATE_TIME = ""


def format_date(value):
    if not value:
        return ""

    value = str(value).strip()

    if len(value) == 8 and value.isdigit():
        return (
            value[:4]
            + "-"
            + value[4:6]
            + "-"
            + value[6:8]
        )

    return value


def fetch_senior_jobs(
    page_no=1,
    num_of_rows=DEFAULT_ROWS,
    keyword="",
    area="전국"
):
    print("[노인일자리] API 호출 시작")
    print("[노인일자리] 페이지:", page_no)
    print("[노인일자리] 검색어:", keyword or "전국")
    print("[노인일자리] 지역:", area)

    params = {
        "serviceKey": SENIOR_JOB_API_KEY,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
        "_type": "xml"
    }

    if keyword:
        params["search"] = keyword

    if area and area != "전국":
        params["workPlcNm"] = area

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=20
        )

        safe_url = response.url.replace(
            SENIOR_JOB_API_KEY,
            "***KEY***"
        )

        print(
            "[노인일자리] 실제 요청 URL:",
            safe_url
        )

        print(
            "[노인일자리] HTTP 상태:",
            response.status_code
        )

        if response.status_code != 200:
            print("[노인일자리] HTTP 오류:")
            print(response.text[:1000])
            return []

        root = ET.fromstring(response.content)

        result_code = (
            root.findtext(".//resultCode")
            or ""
        ).strip()

        result_msg = (
            root.findtext(".//resultMsg")
            or ""
        ).strip()

        print(
            "[노인일자리] 결과코드:",
            result_code
        )

        print(
            "[노인일자리] 결과메시지:",
            result_msg
        )

        if result_code and result_code != "00":
            print("[노인일자리] API 오류입니다.")
            return []

        items = root.findall(".//item")

        print(
            "[노인일자리] 채용공고 수:",
            len(items)
        )

        jobs = []

        for item in items:
            job_id = (
                item.findtext("jobId")
                or ""
            ).strip()

            job_category = (
                item.findtext("jobclsNm")
                or ""
            ).strip()

            company = (
                item.findtext("oranNm")
                or "기관명 미상"
            ).strip()

            title = (
                item.findtext("recrtTitle")
                or "채용공고"
            ).strip()

            workplace = (
                item.findtext("workPlcNm")
                or ""
            ).strip()

            start_date = (
                item.findtext("frDd")
                or ""
            ).strip()

            end_date = (
                item.findtext("toDd")
                or ""
            ).strip()

            deadline = (
                item.findtext("deadline")
                or ""
            ).strip()

            employment_type = (
                item.findtext("emplymShpNm")
                or ""
            ).strip()

            apply_method = (
                item.findtext("acptMthd")
                or ""
            ).strip()

            jobs.append({
                "jobId": job_id,
                "job_category": job_category,
                "company": company,
                "title": title,
                "workplace": workplace,
                "start_date": format_date(start_date),
                "end_date": format_date(end_date),
                "deadline": format_date(deadline),
                "employment_type": employment_type,
                "apply_method": apply_method
            })

        return jobs

    except requests.RequestException as e:
        print("[노인일자리] 네트워크 오류:", e)
        return []

    except ET.ParseError as e:
        print("[노인일자리] XML 파싱 오류:", e)
        return []

    except Exception as e:
        print("[노인일자리] 예기치 않은 오류:", e)
        return []


def refresh_live_jobs():
    global LIVE_JOB_CACHE
    global LAST_UPDATE_TIME

    senior_jobs = []

    # 노인일자리 전국 자료를 여러 페이지 수집
    for page in range(1, 11):
        page_jobs = fetch_senior_jobs(
            page_no=page,
            num_of_rows=100,
            keyword="",
            area="전국"
        )

        senior_jobs.extend(page_jobs)

        # 마지막 페이지이면 종료
        if len(page_jobs) < 100:
            break

    employment24_jobs = fetch_employment24_jobs()

    jobs = senior_jobs + employment24_jobs

    if jobs:
        LIVE_JOB_CACHE = jobs

        LAST_UPDATE_TIME = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        print(
            "[전체] 실시간 자료 갱신:",
            len(jobs),
            "건"
        )

        print(
            "[전체] 노인일자리:",
            len(senior_jobs),
            "건"
        )

        print(
            "[전체] 고용24:",
            len(employment24_jobs),
            "건"
        )

    else:
        print(
            "[전체] API 자료가 없어 예비자료를 표시합니다."
        )

def fetch_employment24_jobs():
    print("[고용24] API 호출 시작")

    if not EMPLOYMENT24_KEY:
        print("[고용24] API 키가 없습니다.")
        return []

    params = {
        "authKey": EMPLOYMENT24_KEY,
        "callTp": "L",
        "returnType": "XML",
        "startPage": "1",
        "display": "100"
    }

    try:
        response = requests.get(
            EMPLOYMENT24_URL,
            params=params,
            timeout=20
        )

        print("[고용24] HTTP 상태:", response.status_code)

        if response.status_code != 200:
            print("[고용24] HTTP 오류:", response.text[:500])
            return []

        print("[고용24] 응답 앞부분:", response.text[:2000])

        root = ET.fromstring(response.content)

        jobs = []

        for item in root.findall(".//wanted"):
            job_id = (
                item.findtext("wantedAuthNo")
                or ""
            ).strip()

            company = (
                item.findtext("company")
                or "기관명 미상"
            ).strip()

            title = (
                item.findtext("title")
                or "채용공고"
            ).strip()

            workplace = (
                item.findtext("region")
                or ""
            ).strip()

            deadline = (
                item.findtext("receiptCloseDt")
                or ""
            ).strip()

            jobs.append({
                "jobId": "W24-" + job_id,
                "job_category": "고용24",
                "company": company,
                "title": title,
                "workplace": workplace,
                "start_date": "",
                "end_date": "",
                "deadline": deadline,
                "employment_type": "",
                "apply_method": "고용24"
            })

        print("[고용24] 채용공고 수:", len(jobs))

        return jobs

    except requests.RequestException as e:
        print("[고용24] 네트워크 오류:", e)
        return []

    except ET.ParseError as e:
        print("[고용24] XML 파싱 오류:", e)
        return []

    except Exception as e:
        print("[고용24] 예기치 않은 오류:", e)
        return []
        
async def auto_refresh():
    while True:
        try:
            refresh_live_jobs()
        except Exception as e:
            print("[자동갱신 오류]", e)

        await asyncio.sleep(REFRESH_SECONDS)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(auto_refresh())


@app.get("/", response_class=HTMLResponse)
async def home(
    keyword: str = "",
    area: str = "전국"
):
    keyword = keyword.strip()
    area = area.strip()

    # 검색은 캐시 데이터에서만 처리
    jobs = LIVE_JOB_CACHE

    # 검색 결과 필터링
    filtered_jobs = []
    for job in jobs:
        text = " ".join([
            job.get("company", ""),
            job.get("title", ""),
            job.get("workplace", ""),
            job.get("employment_type", "")
        ])

        if keyword and keyword.lower() not in text.lower():
            continue

        if area != "전국" and area not in text:
            continue

        filtered_jobs.append(job)

    # 검색 결과 필터링
    filtered_jobs = []

    for job in jobs:
        text = " ".join([
            job.get("company", ""),
            job.get("title", ""),
            job.get("workplace", ""),
            job.get("employment_type", "")
        ])

        if keyword and keyword.lower() not in text.lower():
            continue

        if area != "전국" and area not in text:
            continue

        filtered_jobs.append(job)

    area_list = [
        "전국", "서울", "경기", "인천", "강원",
        "충북", "충남", "전북", "전남",
        "경북", "경남", "제주"
    ]

    buttons = ""

    for item in area_list:
        active = " active" if item == area else ""

        buttons += f"""
        <a class="area-button{active}"
           href="/?area={item}">
           {item}
        </a>
        """

    cards = ""

    for job in filtered_jobs:
        cards += f"""
        <div class="job-card">
            <div class="job-title">
                {escape(job.get("title", "채용공고"))}
            </div>

            <div class="job-info">📂 {escape(job.get("job_category", ""))}</div>

            <div class="job-company">
                {escape(job.get("company", "기관명 미상"))}
            </div>

            <div class="job-info">
                📍 {escape(job.get("workplace", ""))}
            </div>

            <div class="job-info">
                📅 {escape(job.get("start_date", ""))}
                ~
                {escape(job.get("end_date", ""))}
            </div>

            <div class="job-info">
                ⏰ 마감일:
                {escape(job.get("deadline", ""))}
            </div>

            <div class="job-info">
                💼 {escape(job.get("employment_type", ""))}
            </div>

            <div class="job-info">
                📝 접수방법:
                {escape(job.get("apply_method", ""))}
            </div>

            <a class="detail-button"
               href="https://www.seniorro.or.kr/"
               target="_blank">
               자세히 보기
            </a>
        </div>
        """

    if not cards:
        cards = """
        <div class="empty">
            현재 조건에 맞는 채용공고가 없습니다.
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport"
              content="width=device-width, initial-scale=1.0">
        <title>시니어 일자리 찾기</title>

        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, "Malgun Gothic", sans-serif;
                background: #f5f7fa;
                color: #222;
            }}

            .header {{
                background: #ffffff;
                padding: 28px 20px;
                border-bottom: 1px solid #ddd;
            }}

            .container {{
                max-width: 1100px;
                margin: 0 auto;
            }}

            h1 {{
                margin: 0 0 8px 0;
                font-size: 32px;
            }}

            .subtitle {{
                color: #666;
                font-size: 17px;
            }}

            .search-box {{
                margin-top: 20px;
                display: flex;
                gap: 10px;
            }}

            .search-box input {{
                flex: 1;
                padding: 15px;
                border: 1px solid #ccc;
                border-radius: 8px;
                font-size: 17px;
            }}

            .search-box button {{
                padding: 15px 24px;
                border: 0;
                border-radius: 8px;
                background: #333;
                color: white;
                font-size: 17px;
                cursor: pointer;
            }}

            .area-list {{
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin: 20px 0;
            }}

            .area-button {{
                text-decoration: none;
                padding: 10px 16px;
                border-radius: 20px;
                background: #ffffff;
                color: #333;
                border: 1px solid #ddd;
            }}

            .area-button.active {{
                background: #333;
                color: #fff;
            }}

            .status {{
                margin: 15px 0;
                color: #666;
                font-size: 14px;
            }}

            .job-list {{
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(300px, 1fr));
                gap: 18px;
            }}

            .job-card {{
                background: white;
                border-radius: 12px;
                padding: 22px;
                box-shadow:
                    0 2px 8px rgba(0,0,0,0.08);
            }}

            .job-title {{
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 12px;
                line-height: 1.4;
            }}

            .job-company {{
                font-weight: bold;
                margin-bottom: 12px;
            }}

            .job-info {{
                margin: 8px 0;
                color: #555;
                line-height: 1.5;
            }}

            .detail-button {{
                display: inline-block;
                margin-top: 15px;
                padding: 11px 18px;
                border-radius: 7px;
                background: #333;
                color: white;
                text-decoration: none;
            }}

            .empty {{
                background: white;
                padding: 40px;
                text-align: center;
                border-radius: 12px;
            }}

            @media (max-width: 600px) {{
                h1 {{
                    font-size: 26px;
                }}

                .search-box {{
                    flex-direction: column;
                }}

                .search-box button {{
                    width: 100%;
                }}
            }}
        </style>
    </head>

    <body>
        <div class="header">
            <div class="container">
                <h1>시니어 일자리 찾기</h1>

                <div class="subtitle">
                    전국 노인일자리 채용정보를 쉽게 찾아보세요.
                </div>

                <form
                    class="search-box"
                    method="get"
                    action="/">

                    <input
                        type="text"
                        name="keyword"
                        value="{escape(keyword)}"
                        placeholder="일자리, 기관명, 지역 등을 검색하세요">

                    <input
                        type="hidden"
                        name="area"
                        value="{escape(area)}">

                    <button type="submit">
                        검색
                    </button>
                </form>
            </div>
        </div>

        <main class="container">
            <div class="area-list">
                {buttons}
            </div>

            <div class="status">
                현재 표시: {len(filtered_jobs)}건
                <br>
                마지막 갱신:
                {LAST_UPDATE_TIME or "갱신 정보 없음"}
            </div>

            <div class="job-list">
                {cards}
            </div>
        </main>
    </body>
    </html>
    """

    return HTMLResponse(content=html)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "jobs": len(LIVE_JOB_CACHE),
        "last_update": LAST_UPDATE_TIME
    }











