from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import urllib.parse

app = FastAPI()

# =================================================================
# 🔴 [가장 중요] 발급받으신 진짜 정식 인증키들을 아래에 각각 정확하게 입력해 주세요!
# =================================================================
PUBLIC_DATA_KEY = "uaZP6n4f8eLkbm97mubDbl0qAR2bBcxWPfpX2NwQAz85hsvnCmNscPruVqEor92pIwOQcdxVOSkB045cTEbcMw%3D%3D"
EMPLOYMENT24_KEY = "a1972707-53cb-42f4-ba86-9db3d82eec6e"
# =================================================================


# --- 1. 노인인력개발원 일반 구인정보 수집 ---
def get_kordi_private_jobs(search_keyword=""):
    if not PUBLIC_DATA_KEY: return []
    try:
        url = "http://data.go.kr" 
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                company = item.findtext("oranNm", "민간 기업").strip()
                title = item.findtext("jobNm", "모집 공고").strip()
                link = item.findtext("detlWebAdres", "").strip()
                if not link or "http" not in link:
                    query = f"{company} {title} 채용 정보"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                jobs.append({
                    "type": "💼 일반 취업형", "company": company, "title": title, 
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "접수중"), "url": link
                })
        return jobs
    except Exception: return []

# --- 2. 노인인력개발원 정부 지원 공공일자리 수집 ---
def get_kordi_public_jobs(search_keyword=""):
    if not PUBLIC_DATA_KEY: return []
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                company = item.findtext("oranNm", "시니어클럽 등").strip()
                title = item.findtext("annncNm", "공공 일자리 모집").strip()
                link = item.findtext("detlWebAdres", "").strip()
                if not link or "http" not in link:
                    query = f"{company} {title} 신청 모집"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                jobs.append({
                    "type": "👵👴 정부 지원형", "company": company, "title": title, 
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "상세 문의"), "url": link
                })
        return jobs
    except Exception: return []

# --- 3. 잡알리오(JOB ALIO) 공공기관/공기업 구인정보 수집 ---
def get_job_alio_public_jobs(search_keyword=""):
    if not PUBLIC_DATA_KEY: return []
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//item"):
                company = item.findtext("instNm", "공공기관").strip()
                title = item.findtext("pblntcNm", "공공 채용 정보").strip()
                location = item.findtext("workRgnNm", "전국").strip()
                end_date = item.findtext("pbancEndDt", "상세 확인").strip()
                link = item.findtext("srcUrl", "").strip()
                if not link or "http" not in link:
                    query = f"{company} {title} 잡알리오 채용공고"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                if search_keyword and (search_keyword not in title and search_keyword not in location and search_keyword not in company):
                    continue
                jobs.append({
                    "type": "🏛️ 잡알리오 공공기관형", "company": company, "title": title,
                    "location": location, "end_date": end_date, "url": link
                })
        return jobs
    except Exception: return []

# --- 4. 고용24 (구 워크넷) 실버/장년 우대 채용정보 수집 ---
def get_employment24_jobs(search_keyword=""):
    if not EMPLOYMENT24_KEY: return []
    try:
        url = "http://work.go.kr"
        params = {"authKey": EMPLOYMENT24_KEY, "callTp": "L", "returnType": "XML", "startPage": "1", "display": "15", "preferentialGbn": "01"}
        if search_keyword: params["keyword"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            for item in root.findall(".//wanted"):
                company = item.findtext("corpNm", "민간 구인기업").strip()
                title = item.findtext("title", "모집 공고").strip()
                location = item.findtext("region", "지역 정보 없음")
                end_date = item.findtext("closeDt", "채용시까지")
                link = item.findtext("wantedInfoUrl", "").strip()
                if not link or "http" not in link:
                    query = f"{company} {title} 고용24 구인공고"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                jobs.append({
                    "type": "🚀 고용24 민간취업형", "company": company, "title": title,
                    "location": location, "end_date": end_date, "url": link
                })
        return jobs
    except Exception: return []


@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    kordi_p = get_kordi_private_jobs(search)
    kordi_g = get_kordi_public_jobs(search)
    alio_g = get_job_alio_public_jobs(search)
    emp24 = get_employment24_jobs(search)
    
    total_job_list = kordi_p + kordi_g + alio_g + emp24
    
    # 시스템 테스트용 고품질 시니어 샘플 데이터
    if not total_job_list:
        sample_data = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이 모집", "company": "동해시 시니어클럽", "location": "강원도 동해시 천곡동", "end_date": "접수 마감까지", "url": "https://kordi.or.kr"},
            {"type": "🏛️ 잡알리오 공공기관형", "title": "[공기업/시설관리] 망상오토캠핑장 야간 환경 보안관 채용", "company": "동해시 시설관리공단 (잡알리오)", "location": "강원도 동해시 망상동", "end_date": "2026-10-15 까지", "url": "https://alio.go.kr"},
            {"type": "🚀 고용24 민간취업형", "title": "[장년우대/급여최상] 우리지역 종합 물류센터 실버 실내 분류원 구인", "company": "동해항 물류 연동 기업", "location": "강원도 동해시 평릉동 일대", "end_date": "채용시 마감", "url": "https://work.go.kr"},
            {"type": "💼 일반 취업형", "title": "[시니어 우대] 아파트 단지 실버 택배 배송원 모집", "company": "행복종합관리", "location": "강원도 동해시 송정동", "end_date": "수시 채용", "url": "https://google.com" + urllib.parse.quote("동해시 아파트 실버 택배 채용")},
        ]
        if search:
            total_job_list = [j for j in sample_data if search in j['title'] or search in j['company'] or search in j['location'] or search in j['type']]
        else:
            total_job_list = sample_data
        
    cards_html = ""
    for job in total_job_list:
        if "정부" in job['type']: badge_color = "#0284c7"
        elif "잡알리오" in job['type']: badge_color = "#0ea5e9"
        elif "고용24" in job['type']: badge_color = "#ea580c"
        else: badge_color = "#059669"
        
        # 가독성을 높이기 위해 한 줄씩 문자열을 더하는 방식으로 안전하게 조립합니다.
        cards_html += '<a href="' + job['url'] + '" target="_blank" style="text-decoration: none; color: inherit; display: block;">'
        cards_html += '  <div style="background: white; padding: 22px; margin-bottom: 16px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 2px solid #e2e8f0;">'
        cards_html += '    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">'
        cards_html += '      <span style="font-size: 1.3rem; color: #475569; font-weight: bold;">🏢 ' + job['company'] + '</span>'
        cards_html += '      <span style="background: ' + badge_color + '; color: white; padding: 4px 10px; border-radius: 6px; font-size: 1rem; font-weight: bold; white-space: nowrap;">' + job['type'] + '</span>'
        cards_html += '    </div>'
        cards_html += '    <h2 style="font-size: 1.6rem; color: #1e293b; margin: 0 0 12px 0; font-weight: 800; line-height: 1.4;">' + job['title'] + '</h2>'
        cards_html += '    <div style="display: flex; justify-content: space-between; font-size: 1.1rem; color: #64748b; flex-wrap: wrap; gap: 10px;">'
        cards_html += '      <span>📍 ' + job['location'] + '</span>'
        cards_html += '      <span style="color: #ef4444; font-weight: bold;">📅 마감일: ' + job['end_date'] + '</span>'
        cards_html += '    </div>'
        cards_html += '  </div>'
        cards_html += '</a>'

    if not cards_html:
        cards_html = '<div class="no-result">검색 결과에 맞는 일자리가 없습니다. 다른 검색어를 입력해 보세요.</div>'

    # 삼중 따옴표 오류를 우회하기 위해 전체 HTML을 파이썬 리스트(배열) 형태로 안전하게 결합합니다.
    html_lines = [
        '<!DOCTYPE html>',
        '<html lang="ko">',
        '<head>',
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '    <title>시니어 행복 일자리 찾기</title>',
        '    <style>',
        "        body { font-family: 'Malgun Gothic', dotum, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }",
        '        .container { max-width: 800px; margin: 0 auto; padding: 20px; }',
         '        .header { text-align: center; padding: 35px 0; background: linear-gradient(135deg, #059669, #10b981); color: white; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }',
        '        .header h1 { margin: 0 0 10px 0; font-size: 2.5rem; font-weight: 900; }',
        '        .header p { margin: 0; font-size: 1.4rem; opacity: 0.95; }',
        '        .search-box { display: flex; gap: 10px; margin-bottom: 24px; }',
        '        .search-input { flex: 1; padding: 18px; font-size: 1.4rem; border: 3px solid #cbd5e1; border-radius: 12px; font-weight: bold; }',
        '        .search-input:focus { border-color: #10b981; outline: none; }',
        '        .search-btn { padding: 0 35px; font-size: 1.4rem; background-color: #10b981; color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; }',
        '        .search-btn:hover { background-color: #059669; }',
        '        .no-result { text-align: center; padding: 40px; font-size: 1.3rem; color: #64748b; font-weight: bold; background: white; border-radius: 12px; border: 2px dashed #cbd5e1; }',
        '    </style>',
        '</head>',
        '<body>',
        '    <div class="container">',
        '        <div class="header">',
        '            <h1>👵👴 어르신 맞춤 일자리 찾기</h1>',
        '            <p>원하시는 동네 이름이나 일자리 종류를 검색창에 입력해 보세요!</p>',
        '        </div>',
        '        ',
        '        <form method="get" class="search-box">',
        '            <input type="text" name="search" class="search-input" placeholder="예: 동해시, 청소, 경비, 안내" value="' + search + '">',
        '            <button type="submit" class="search-btn">검색하기</button>',
        '        </form>',
        '        ',
        '        <div class="job-list">',
        '            ' + cards_html,
        '        </div>',
        '    </div>',
        '</body>',
        '</html>'
    ]  # 👈 드디어 눈에 보이는 대괄호 닫기!

    final_html = "\n".join(html_lines)
    return HTMLResponse(content=final_html, status_code=200)