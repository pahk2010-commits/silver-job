from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import os
import asyncio
from datetime import datetime
from html import escape

app = FastAPI()

# =========================================================
# 한국노인인력개발원 노인 구인정보 API 설정
# =========================================================

API_URL = os.getenv(
    "SENIOR_JOB_API_URL",
    "https://apis.data.go.kr/B552474/SenuriService/getJobList"
).strip()

SENIOR_JOB_API_KEY = os.getenv("SENIOR_JOB_API_KEY", "").strip()

DEFAULT_ROWS = 100
REFRESH_SECONDS = 1800

LIVE_JOB_CACHE = []
LAST_UPDATE_TIME = ""


# =========================================================
# API가 연결되지 않을 때 표시할 예비자료
# =========================================================

FALLBACK_JOBS = [
    {
        "type": "👵👴 노인일자리",
        "job_id": "",
        "company": "한국노인인력개발원",
        "title": "노인일자리 정보를 불러오는 중입니다.",
        "location": "전국",
        "start_date": "",
        "end_date": "",
        "deadline": "실시간 자료 확인 중",
        "employment": "",
        "accept_method": "",
        "url": "https://www.seniorro.or.kr/"
    }
]


# =========================================================
# 날짜 형식 변환
# =========================================================

def format_date(value):
    value = (value or "").strip()

    if len(value) == 8 and value.isdigit():
        return (
            value[:4]
            + "-"
            + value[4:6]
            + "-"
            + value[6:8]
        )

    return value


# =========================================================
# 노인일자리 API 호출
# =========================================================

def fetch_senior_jobs(
    page_no=1,
    num_of_rows=100,
    search="",
    region=""
):
    if not SENIOR_JOB_API_KEY:
        print("[노인일자리] SENIOR_JOB_API_KEY가 없습니다.")
        return []

    params = {
        "serviceKey": SENIOR_JOB_API_KEY,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
        "_type": "xml"
    }

    if search:
        params["search"] = search

    if region:
        params["workPlcNm"] = region

    print("=" * 60)
    print("[노인일자리] API 호출 시작")
    print("[노인일자리] 페이지:", page_no)
    print("[노인일자리] 검색어:", search if search else "전국")
    print("[노인일자리] 지역:", region if region else "전국")

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=20
        )

        print("[노인일자리] HTTP 상태:", response.status_code)

        if response.status_code != 200:
            print(
                "[노인일자리] HTTP 오류:",
                response.text[:1000]
            )
            return []

        print(
            "[노인일자리] 응답 길이:",
            len(response.content)
        )

        print(
            "[노인일자리] 응답 앞부분:",
            response.text[:1000]
        )

        # XML 파싱
        try:
            root = ET.fromstring(response.content)

        except ET.ParseError as e:
            print(
                "[노인일자리] XML 파싱 오류:",
                repr(e)
            )
            return []

        # API 결과 확인
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

        # 채용공고 추출
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

            company = (
                item.findtext("oranNm")
                or "기관명 미상"
            ).strip()

            title = (
                item.findtext("recrtTitle")
                or "채용공고"
            ).strip()

            location = (
                item.findtext("workPlcNm")
                or "지역정보 없음"
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

            employment = (
                item.findtext("emplymShpNm")
                or ""
            ).strip()

            accept_method = (
                item.findtext("acptMthd")
                or ""
            ).strip()

            # 현재는 개별 공고 주소가 확인되지 않았으므로
            # 시니어로 메인 페이지를 연결
            job_url = (
                "https://www.seniorro.or.kr/"
            )

            jobs.append(
                {
                    "type": "👵👴 노인일자리",
                    "job_id": job_id,
                    "company": company,
                    "title": title,
                    "location": location,
                    "start_date": format_date(start_date),
                    "end_date": format_date(end_date),
                    "deadline": deadline,
                    "employment": employment,
                    "accept_method": accept_method,
                    "url": job_url
                }
            )

        print(
            "[노인일자리] 최종 변환:",
            len(jobs),
            "건"
        )

        print("=" * 60)

        return jobs

    except requests.exceptions.Timeout:
        print("[노인일자리] API 요청 시간 초과")
        return []

    except requests.exceptions.RequestException as e:
        print(
            "[노인일자리] 네트워크 오류:",
            repr(e)
        )
        return []

    except Exception as e:
        print(
            "[노인일자리] 예상하지 못한 오류:",
            repr(e)
        )
        return []


# =========================================================
# 실시간 자료 갱신
# =========================================================

def refresh_live_jobs():

    global LIVE_JOB_CACHE
    global LAST_UPDATE_TIME

    print()
    print("=" * 70)

    print(
        "[실시간 갱신 시작]",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    jobs = fetch_senior_jobs(
        page_no=1,
        num_of_rows=DEFAULT_ROWS
    )

    if jobs:

        LIVE_JOB_CACHE = jobs

        LAST_UPDATE_TIME = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        print(
            "[전체] 새로운 자료:",
            len(jobs),
            "건"
        )

    else:

        if not LIVE_JOB_CACHE:

            LIVE_JOB_CACHE = (
                FALLBACK_JOBS.copy()
            )

            print(
                "[전체] API 자료가 없어 "
                "예비자료를 표시합니다."
            )

        else:

            print(
                "[전체] 새로운 자료가 없어 "
                "기존 자료를 유지합니다."
            )

    print(
        "[실시간 갱신 완료]",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 70)


# =========================================================
# 자동 갱신 스케줄러
# =========================================================

async def job_scheduler():

    while True:

        try:
            await asyncio.to_thread(
                refresh_live_jobs
            )

        except Exception as e:

            print(
                "[스케줄러 오류]",
                repr(e)
            )

        await asyncio.sleep(
            REFRESH_SECONDS
        )


# =========================================================
# 서버 시작
# =========================================================

@app.on_event("startup")
async def startup_event():

    print("[서버] 애플리케이션 시작")

    await asyncio.to_thread(
        refresh_live_jobs
    )

    asyncio.create_task(
        job_scheduler()
    )


# =========================================================
# 메인 화면
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse
)
def home(
    search: str = "",
    region: str = ""
):

    global LIVE_JOB_CACHE

    search = search.strip()
    region = region.strip()

    # -----------------------------------------------------
    # 검색이 없는 경우
    # -----------------------------------------------------

    if not search and not region:

        filtered_jobs = LIVE_JOB_CACHE

    else:

        filtered_jobs = []

        search_lower = search.lower()
        region_lower = region.lower()

        for job in LIVE_JOB_CACHE:

            title = (
                job.get("title", "")
                .lower()
            )

            company = (
                job.get("company", "")
                .lower()
            )

            location = (
                job.get("location", "")
                .lower()
            )

            employment = (
                job.get("employment", "")
                .lower()
            )

            region_match = (
                not region_lower
                or region_lower in location
            )

            search_match = (
                not search_lower
                or search_lower in title
                or search_lower in company
                or search_lower in location
                or search_lower in employment
            )

            if region_match and search_match:

                filtered_jobs.append(job)

    # =====================================================
    # 채용공고 카드 만들기
    # =====================================================

    cards = ""

    for job in filtered_jobs:

        job_type = job.get(
            "type",
            "👵👴 노인일자리"
        )

        company = job.get(
            "company",
            "기관명 미상"
        )

        title = job.get(
            "title",
            "채용공고"
        )

        location = job.get(
            "location",
            "지역정보 없음"
        )

        start_date = job.get(
            "start_date",
            ""
        )

        end_date = job.get(
            "end_date",
            ""
        )

        deadline = job.get(
            "deadline",
            ""
        )

        employment = job.get(
            "employment",
            ""
        )

        accept_method = job.get(
            "accept_method",
            ""
        )

        job_id = job.get(
            "job_id",
            ""
        )

        job_url = job.get(
            "url",
            "https://www.seniorro.or.kr/"
        )

        # HTML 특수문자 보호
        company_html = escape(
            str(company)
        )

        title_html = escape(
            str(title)
        )

        location_html = escape(
            str(location)
        )

        start_date_html = escape(
            str(start_date)
        )

        end_date_html = escape(
            str(end_date)
        )

        deadline_html = escape(
            str(deadline)
        )

        employment_html = escape(
            str(employment)
        )

        accept_method_html = escape(
            str(accept_method)
        )

        job_id_html = escape(
            str(job_id)
        )

        job_url_html = escape(
            str(job_url),
            quote=True
        )

        cards += f"""
        <a
            href="{job_url_html}"
            target="_blank"
            rel="noopener noreferrer"
            style="
                text-decoration:none;
                color:inherit;
                display:block;
            "
        >

            <div
                style="
                    background:white;
                    padding:22px;
                    margin-bottom:16px;
                    border-radius:14px;
                    box-shadow:
                        0 4px 10px
                        rgba(0,0,0,0.06);
                    border:2px solid #e2e8f0;
                "
            >

                <div
                    style="
                        display:flex;
                        justify-content:space-between;
                        align-items:center;
                        margin-bottom:10px;
                        flex-wrap:wrap;
                        gap:8px;
                    "
                >

                    <span
                        style="
                            font-size:1.15rem;
                            color:#475569;
                            font-weight:bold;
                        "
                    >
                        🏢 {company_html}
                    </span>

                    <span
                        style="
                            background:#059669;
                            color:white;
                            padding:5px 11px;
                            border-radius:7px;
                            font-size:0.9rem;
                            font-weight:bold;
                        "
                    >
                        {job_type}
                    </span>

                </div>

                <h2
                    style="
                        font-size:1.4rem;
                        color:#1e293b;
                        margin:
                            0 0 14px 0;
                        font-weight:800;
                        line-height:1.45;
                    "
                >
                    {title_html}
                </h2>

                <div
                    style="
                        color:#475569;
                        font-size:1.05rem;
                        line-height:1.8;
                    "
                >

                    <div>
                        📍
                        <strong>근무지역:</strong>
                        {location_html}
                    </div>

                    <div>
                        💼
                        <strong>고용형태:</strong>
                        {employment_html or "정보 없음"}
                    </div>

                    <div>
                        📝
                        <strong>접수방법:</strong>
                        {accept_method_html or "정보 없음"}
                    </div>

                    <div>
                        📅
                        <strong>접수기간:</strong>
                        {start_date_html}
                        ~
                        {end_date_html}
                    </div>

                    <div
                        style="
                            color:#dc2626;
                            font-weight:bold;
                        "
                    >
                        📌
                        <strong>접수상태:</strong>
                        {deadline_html or "정보 없음"}
                    </div>

                    <div
                        style="
                            color:#94a3b8;
                            font-size:0.85rem;
                            margin-top:6px;
                        "
                    >
                        공고번호:
                        {job_id_html}
                    </div>

                </div>

                <div
                    style="
                        margin-top:15px;
                        text-align:right;
                        color:#059669;
                        font-weight:bold;
                    "
                >
                    👉 공고 확인하기
                </div>

            </div>

        </a>
        """

    # =====================================================
    # 검색 결과가 없는 경우
    # =====================================================

    if not cards:

        cards = """
        <div
            style="
                text-align:center;
                padding:50px 20px;
                font-size:1.2rem;
                color:#64748b;
                font-weight:bold;
                background:white;
                border-radius:14px;
                border:2px dashed #cbd5e1;
            "
        >
            검색 결과가 없습니다.
            <br><br>
            다른 지역이나 검색어를 입력해 보세요.
        </div>
        """

    update_time = (
        LAST_UPDATE_TIME
        or "자료 확인 중"
    )

    # =====================================================
    # HTML 전체
    # =====================================================

    html = f"""
    <!DOCTYPE html>

    <html lang="ko">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="
                width=device-width,
                initial-scale=1.0
            "
        >

        <title>
            시니어 행복 일자리 찾기
        </title>

        <style>

            body {{
                font-family:
                    'Malgun Gothic',
                    Arial,
                    sans-serif;

                background-color:#f8fafc;

                margin:0;
                padding:0;
            }}

            .container {{
                max-width:850px;

                margin:0 auto;

                padding:20px;
            }}

            .header {{
                text-align:center;

                padding:35px 20px;

                background:
                    linear-gradient(
                        135deg,
                        #059669,
                        #10b981
                    );

                color:white;

                border-radius:16px;

                margin-bottom:22px;

                box-shadow:
                    0 4px 10px
                    rgba(0,0,0,0.1);
            }}

            .header h1 {{
                margin:
                    0 0 10px 0;

                font-size:2.25rem;

                font-weight:900;
            }}

            .header p {{
                margin:0;

                font-size:1.15rem;
            }}

            .update-time {{
                margin-top:12px;

                font-size:0.9rem;

                opacity:0.9;
            }}

            .search-panel {{
                background:white;

                padding:20px;

                border-radius:14px;

                margin-bottom:22px;

                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,0.05);
            }}

            .search-row {{
                display:flex;

                gap:10px;

                margin-bottom:12px;
            }}

            .search-input,
            .region-input {{
                flex:1;

                padding:15px;

                font-size:1.1rem;

                border:
                    2px solid #cbd5e1;

                border-radius:10px;

                font-weight:bold;

                box-sizing:border-box;
            }}

            .search-input:focus,
            .region-input:focus {{
                border-color:#10b981;

                outline:none;
            }}

            .search-btn {{
                padding:0 25px;

                font-size:1.1rem;

                background-color:#10b981;

                color:white;

                border:none;

                border-radius:10px;

                font-weight:bold;

                cursor:pointer;
            }}

            .search-btn:hover {{
                background-color:#059669;
            }}

            .region-buttons {{
                display:flex;

                gap:8px;

                flex-wrap:wrap;

                margin-top:8px;
            }}

            .region-buttons a {{
                text-decoration:none;

                background:#f1f5f9;

                color:#334155;

                padding:8px 13px;

                border-radius:8px;

                font-size:0.95rem;

                font-weight:bold;
            }}

            .region-buttons a:hover {{
                background:#d1fae5;

                color:#047857;
            }}

            .result-info {{
                font-size:1rem;

                color:#475569;

                margin:
                    0 0 14px 4px;

                font-weight:bold;
            }}

            @media(max-width:600px) {{

                .container {{
                    padding:12px;
                }}

                .header h1 {{
                    font-size:1.8rem;
                }}

                .search-row {{
                    flex-direction:column;
                }}

                .search-btn {{
                    padding:15px;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <div class="header">

                <h1>
                    👵👴 어르신 맞춤 일자리 찾기
                </h1>

                <p>
                    전국의 노인일자리 정보를
                    검색해 보세요.
                </p>

                <div class="update-time">
                    🔄 마지막 자료 확인:
                    {escape(update_time)}
                </div>

            </div>


            <div class="search-panel">

                <form method="get">

                    <div class="search-row">

                        <input
                            type="text"
                            name="region"
                            class="region-input"
                            placeholder="
                                지역:
                                예) 강원, 동해, 삼척
                            "
                            value="
                                {escape(
                                    region,
                                    quote=True
                                )}
                            "
                        >

                        <input
                            type="text"
                            name="search"
                            class="search-input"
                            placeholder="
                                일자리:
                                예) 경비, 미화, 청소
                            "
                            value="
                                {escape(
                                    search,
                                    quote=True
                                )}
                            "
                        >

                        <button
                            type="submit"
                            class="search-btn"
                        >
                            검색
                        </button>

                    </div>

                </form>


                <div
                    style="
                        margin-top:10px;
                        color:#64748b;
                        font-size:0.9rem;
                    "
                >
                    지역을 입력하지 않으면
                    전국 자료를 검색합니다.
                </div>


                <div class="region-buttons">

                    <a href="/">
                        전국
                    </a>

                    <a href="/?region=서울">
                        서울
                    </a>

                    <a href="/?region=경기">
                        경기
                    </a>

                    <a href="/?region=인천">
                        인천
                    </a>

                    <a href="/?region=강원">
                        강원
                    </a>

                    <a href="/?region=충북">
                        충북
                    </a>

                    <a href="/?region=충남">
                        충남
                    </a>

                    <a href="/?region=전북">
                        전북
                    </a>

                    <a href="/?region=전남">
                        전남
                    </a>

                    <a href="/?region=경북">
                        경북
                    </a>

                    <a href="/?region=경남">
                        경남
                    </a>

                    <a href="/?region=제주">
                        제주
                    </a>

                </div>

            </div>


            <div class="result-info">

                검색 결과:
                {len(filtered_jobs)}
                건

                {
                    (
                        " / 지역: "
                        + escape(region)
                        if region
                        else " / 전국"
                    )
                }

                {
                    (
                        " / 검색어: "
                        + escape(search)
                        if search
                        else ""
                    )
                }

            </div>


            <div class="job-list">

                {cards}

            </div>

        </div>

    </body>

    </html>
    """

    return HTMLResponse(
        content=html,
        status_code=200
    )