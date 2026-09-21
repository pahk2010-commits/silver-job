from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import os
import asyncio
from datetime import datetime

app = FastAPI()

# =========================================================
# 실시간 일자리 저장소
# =========================================================
LIVE_JOB_CACHE = []


# =========================================================
# 예비 데이터
# API가 일시적으로 실패했을 때 화면이 완전히 비어버리지 않도록 사용
# =========================================================
FALLBACK_JOBS = [
    {
        "type": "👵👴 정부 지원형",
        "title": "지역사회 환경정화 및 생활지원 일자리",
        "company": "지역 시니어 일자리 기관",
        "location": "강원도 동해시",
        "end_date": "채용기관 문의",
        "url": "https://www.work24.go.kr/"
    },
    {
        "type": "👵👴 정부 지원형",
        "title": "노인일자리 및 사회활동 지원사업",
        "company": "지역 노인일자리 수행기관",
        "location": "강원도 삼척시",
        "end_date": "채용기관 문의",
        "url": "https://www.work24.go.kr/"
    }
]


# =========================================================
# 고용24 실시간 채용정보 API
# =========================================================
def fetch_employment24_jobs():

    EMPLOYMENT24_KEY = os.getenv(
        "EMPLOYMENT24_KEY", ""
    ).strip()

    if not EMPLOYMENT24_KEY:
        print("[고용24] EMPLOYMENT24_KEY가 없습니다.")
        return []

    # 고용24 공식 채용정보 목록 API
    url = (
        "https://www.work24.go.kr/"
        "cm/openApi/call/wk/"
        "callOpenApiSvcInfo210L01.do"
    )

    params = {
        "authKey": EMPLOYMENT24_KEY,
        "callTp": "L",
        "returnType": "XML",
        "startPage": "1",
        "display": "100",

        # (준)고령자(50세 이상)
        "pfPreferential": "B"
    }

    print("[고용24] API 호출 시작")

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        print(
            "[고용24] HTTP 상태:",
            response.status_code
        )

        # HTTP 오류
        if response.status_code != 200:

            print(
                "[고용24] HTTP 오류:",
                response.text[:500]
            )

            return []

        # XML 변환
        try:
            root = ET.fromstring(
                response.content
            )

        except ET.ParseError as e:

            print(
                "[고용24] XML 파싱 오류:",
                repr(e)
            )

            print(
                "[고용24] 응답 일부:",
                response.text[:1000]
            )

            return []

        # API에서 제공하는 채용공고
        wanted_list = root.findall(
            ".//wanted"
        )

        print(
            "[고용24] 채용공고 수:",
            len(wanted_list)
        )

        jobs = []

        for item in wanted_list:

            # 공식 API 필드
            company = (
                item.findtext("company")
                or item.findtext("corpNm")
                or "기업명 미상"
            ).strip()

            title = (
                item.findtext("title")
                or "채용공고"
            ).strip()

            location = (
                item.findtext("region")
                or "지역정보 없음"
            ).strip()

            close_date = (
                item.findtext("closeDt")
                or "채용시까지"
            ).strip()

            # 고용24 실제 채용공고 URL
            wanted_url = (
                item.findtext(
                    "wantedInfoUrl"
                )
                or ""
            ).strip()

            # URL이 없는 경우 고용24 검색 페이지로 연결
            if not wanted_url:

                wanted_url = (
                    "https://www.work24.go.kr/"
                )

            jobs.append(
                {
                    "type": "🚀 고용24 민간취업형",
                    "company": company,
                    "title": title,
                    "location": location,
                    "end_date": close_date,
                    "url": wanted_url
                }
            )

        return jobs

    except requests.exceptions.Timeout:

        print(
            "[고용24] API 요청 시간 초과"
        )

        return []

    except requests.exceptions.RequestException as e:

        print(
            "[고용24] 네트워크 오류:",
            repr(e)
        )

        return []

    except Exception as e:

        print(
            "[고용24] 예상하지 못한 오류:",
            repr(e)
        )

        return []


# =========================================================
# 전체 실시간 자료 갱신
# =========================================================
def fetch_all_live_jobs():

    global LIVE_JOB_CACHE

    print("=" * 60)
    print(
        "[실시간 갱신 시작]",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    new_jobs = []

    # -----------------------------------------------------
    # 고용24
    # -----------------------------------------------------
    employment_jobs = fetch_employment24_jobs()

    if employment_jobs:

        new_jobs.extend(
            employment_jobs
        )

        print(
            "[고용24] 정상적으로",
            len(employment_jobs),
            "건을 가져왔습니다."
        )

    else:

        print(
            "[고용24] 가져온 자료가 없습니다."
        )

    # -----------------------------------------------------
    # 자료가 하나라도 있으면 기존 캐시 교체
    # -----------------------------------------------------
    if new_jobs:

        LIVE_JOB_CACHE = new_jobs

        print(
            "[전체] 현재 화면에 표시할 자료:",
            len(LIVE_JOB_CACHE),
            "건"
        )

    # -----------------------------------------------------
    # API가 실패했지만 기존 자료가 있는 경우
    # 기존 자료 유지
    # -----------------------------------------------------
    elif LIVE_JOB_CACHE:

        print(
            "[전체] 새로운 자료가 없어 기존 자료를 유지합니다."
        )

    # -----------------------------------------------------
    # 처음 실행했는데 API도 실패한 경우
    # 예비 데이터 사용
    # -----------------------------------------------------
    else:

        LIVE_JOB_CACHE = FALLBACK_JOBS.copy()

        print(
            "[전체] API 자료가 없어 예비 데이터를 표시합니다."
        )

    print(
        "[실시간 갱신 완료]",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    print("=" * 60)


# =========================================================
# 1시간마다 자동 갱신
# =========================================================
async def job_scheduler():

    while True:

        try:

            await asyncio.to_thread(
                fetch_all_live_jobs
            )

        except Exception as e:

            print(
                "[스케줄러 오류]",
                repr(e)
            )

        # 1시간
        await asyncio.sleep(3600)


# =========================================================
# 서버 시작
# =========================================================
@app.on_event("startup")
async def startup_event():

    print("[서버] 애플리케이션 시작")

    # 최초 1회 즉시 실행
    await asyncio.to_thread(
        fetch_all_live_jobs
    )

    # 백그라운드 자동 갱신
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
def home(search: str = ""):

    global LIVE_JOB_CACHE

    keyword = search.strip().lower()

    if keyword:

        filtered_jobs = [

            job
            for job in LIVE_JOB_CACHE

            if (
                keyword
                in job.get(
                    "title",
                    ""
                ).lower()

                or keyword
                in job.get(
                    "company",
                    ""
                ).lower()

                or keyword
                in job.get(
                    "location",
                    ""
                ).lower()

                or keyword
                in job.get(
                    "type",
                    ""
                ).lower()
            )
        ]

    else:

        filtered_jobs = LIVE_JOB_CACHE

    # =====================================================
    # 채용 카드 생성
    # =====================================================
    cards = ""

    for job in filtered_jobs:

        job_type = job.get(
            "type",
            "일반 취업형"
        )

        company = job.get(
            "company",
            "기업명 미상"
        )

        title = job.get(
            "title",
            "채용공고"
        )

        location = job.get(
            "location",
            "지역정보 없음"
        )

        end_date = job.get(
            "end_date",
            "채용시까지"
        )

        job_url = job.get(
            "url",
            "https://www.work24.go.kr/"
        )

        # 카드 색상
        if "정부" in job_type:

            color = "#0284c7"

        elif "고용24" in job_type:

            color = "#ea580c"

        elif "잡알리오" in job_type:

            color = "#0ea5e9"

        else:

            color = "#059669"

        cards += f"""
        <a
            href="{job_url}"
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
                    border-radius:12px;
                    box-shadow:
                        0 4px 6px
                        rgba(0,0,0,0.05);
                    border:
                        2px solid #e2e8f0;
                "
            >

                <div
                    style="
                        display:flex;
                        justify-content:
                            space-between;
                        align-items:center;
                        margin-bottom:10px;
                        flex-wrap:wrap;
                        gap:8px;
                    "
                >

                    <span
                        style="
                            font-size:1.2rem;
                            color:#475569;
                            font-weight:bold;
                        "
                    >
                        🏢 {company}
                    </span>

                    <span
                        style="
                            background:{color};
                            color:white;
                            padding:4px 10px;
                            border-radius:6px;
                            font-size:0.95rem;
                            font-weight:bold;
                        "
                    >
                        {job_type}
                    </span>

                </div>

                <h2
                    style="
                        font-size:1.45rem;
                        color:#1e293b;
                        margin:
                            0 0 12px 0;
                        font-weight:800;
                        line-height:1.4;
                    "
                >
                    {title}
                </h2>

                <div
                    style="
                        display:flex;
                        justify-content:
                            space-between;
                        font-size:1.05rem;
                        color:#64748b;
                        flex-wrap:wrap;
                        gap:10px;
                    "
                >

                    <span>
                        📍 {location}
                    </span>

                    <span
                        style="
                            color:#ef4444;
                            font-weight:bold;
                        "
                    >
                        📅 마감일:
                        {end_date}
                    </span>

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
            class="no-result"
        >
            검색 결과에 맞는 일자리가 없습니다.
            다른 검색어를 입력해 보세요.
        </div>
        """

    # =====================================================
    # 마지막 갱신 시간
    # =====================================================
    update_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # =====================================================
    # HTML
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
                    dotum,
                    sans-serif;

                background-color:
                    #f8fafc;

                margin:0;
                padding:0;
            }}

            .container {{
                max-width:800px;
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

                margin-bottom:24px;

                box-shadow:
                    0 4px 10px
                    rgba(0,0,0,0.1);
            }}

            .header h1 {{
                margin:
                    0 0 10px 0;

                font-size:2.3rem;
                font-weight:900;
            }}

            .header p {{
                margin:0;
                font-size:1.25rem;
                opacity:0.95;
            }}

            .update-time {{
                margin-top:12px;
                font-size:0.95rem;
                opacity:0.9;
            }}

            .search-box {{
                display:flex;
                gap:10px;
                margin-bottom:24px;
            }}

            .search-input {{
                flex:1;
                padding:18px;
                font-size:1.25rem;

                border:
                    3px solid #cbd5e1;

                border-radius:12px;

                font-weight:bold;
            }}

            .search-input:focus {{
                border-color:#10b981;
                outline:none;
            }}

            .search-btn {{
                padding:
                    0 30px;

                font-size:1.25rem;

                background-color:
                    #10b981;

                color:white;

                border:none;

                border-radius:12px;

                font-weight:bold;

                cursor:pointer;
            }}

            .search-btn:hover {{
                background-color:
                    #059669;
            }}

            .no-result {{
                text-align:center;

                padding:40px;

                font-size:1.2rem;

                color:#64748b;

                font-weight:bold;

                background:white;

                border-radius:12px;

                border:
                    2px dashed #cbd5e1;
            }}

            @media (
                max-width:600px
            ) {{

                .search-box {{
                    flex-direction:column;
                }}

                .search-btn {{
                    padding:16px;
                }}

                .header h1 {{
                    font-size:1.8rem;
                }}

            }}

        </style>

    </head>

    <body>

        <div class="container">

            <div class="header">

                <h1>
                    👵👴
                    어르신 맞춤 일자리 찾기
                </h1>

                <p>
                    원하시는 지역이나
                    일자리 종류를 검색해 보세요.
                </p>

                <div class="update-time">
                    🔄 마지막 자료 확인:
                    {update_time}
                </div>

            </div>

            <form
                method="get"
                class="search-box"
            >

                <input
                    type="text"
                    name="search"
                    class="search-input"
                    placeholder="
                        예: 삼척, 동해,
                        청소, 경비
                    "
                    value="{keyword}"
                >

                <button
                    type="submit"
                    class="search-btn"
                >
                    검색하기
                </button>

            </form>

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