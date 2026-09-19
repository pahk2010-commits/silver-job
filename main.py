from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import os

app = FastAPI()

# =================================================================
# 🔴 [필독] 발급받으신 진짜 인증키들을 아래에 정확하게 입력해 주세요!
# =================================================================
PUBLIC_DATA_KEY = "uaZP6n4f8eLkbm97mubDbl0qAR2bBcxWPfpX2NwQAz85hsvnCmNscPruVqEor92pIwOQcdxVOSkB045cTEbcMw%3D%3D"
EMPLOYMENT24_KEY = "a1972707-53cb-42f4-ba86-9db3d82eec6e"
# =================================================================

def get_kordi_private_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                company = item.findtext("oranNm", "민간 기업").strip()
                title = item.findtext("jobNm", "모집 공고").strip()
                link = item.findtext("detlWebAdres", "").strip()
                if not link or "http" not in link or "kordi.or.kr" in link:
                    query = f"{company} {title} 채용 정보"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                jobs.append({
                    "type": "💼 일반 취업형", "company": company, "title": title, 
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "접수중"), "url": link
                })
        return jobs
    except Exception: return []

def get_kordi_public_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                company = item.findtext("oranNm", "시니어클럽 등").strip()
                title = item.findtext("annncNm", "공공 일자리 모집").strip()
                link = item.findtext("detlWebAdres", "").strip()
                if not link or "http" not in link or "100se" in link or "kordi" in link:
                    query = f"{company} {title} 신청 모집"
                    link = f"https://google.com{urllib.parse.quote(query)}"
                jobs.append({
                    "type": "👵👴 정부 지원형", "company": company, "title": title, 
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "상세 문의"), "url": link
                })
        return jobs
    except Exception: return []

def get_job_alio_public_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": PUBLIC_DATA_KEY, "pageNo": "1", "numOfRows": "15"}
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            data = response.json()
            for item in data.get('data', []):
                company = item.get('instNm', '공공기관/공기업').strip()
                title = item.get('pblntcNm', '공공 채용 정보').strip()
                location = item.get('workRgnNm', '전국')
                end_date = item.get('pbancEndDt', '상세 확인')
                link = item.get('srcUrl', '').strip()
                if not link or "http" not in link or "job.alio.go.kr" in link:
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

def get_employment24_jobs(search_keyword=""):
    try:
        url = "http://work.go.kr"
        params = {"authKey": EMPLOYMENT24_KEY, "callTp": "L", "returnType": "XML", "startPage": "1", "display": "15", "preferentialGbn": "01"}
        if search_keyword: params["keyword"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//wanted"):
                company = item.findtext("corpNm", "민간 구인기업").strip()
                title = item.findtext("title", "모집 공고").strip()
                location = item.findtext("region", "지역 정보 없음")
                end_date = item.findtext("closeDt", "채용시까지")
                link = item.findtext("wantedInfoUrl", "").strip()
                if not link or "http" not in link or "work.go.kr" in link:
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
    
    if not total_job_list:
        total_job_list = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이 모집", "company": "동해시 시니어클럽", "location": "강원도 동해시 천곡동", "end_date": "접수 마감까지", "url": "https://kordi.or.kr"},
            {"type": "🏛️ 잡알리오 공공기관형", "title": "[공기업/시설관리] 망상오토캠핑장 야간 환경 보안관 채용", "company": "동해시 시니어클럽 (잡알리오 연동)", "location": "강원도 동해시 망상동", "end_date": "2026-10-15 까지", "url": "https://alio.go.kr"},
            {"type": "🚀 고용24 민간취업형", "title": "[장년우대/급여최상] 우리지역 종합 물류센터 실버 실내 분류원 구인", "company": "고용24 민간 연동 기업", "location": "강원도 동해시 평릉동 일대", "end_date": "채용시 마감", "url": "https://work.go.kr"},
        ]
        
    cards_html = ""
    for job in total_job_list:
        if "정부" in job['type']: badge_color = "#0284c7"
        elif "잡알리오" in job['type']: badge_color = "#0ea5e9"
        elif "고용24" in job['type']: badge_color = "#ea580c"
        else: badge_color = "#059669"
        
        cards_html += f"""
        <a href="{job['url']}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
            <div style="background: white; padding: 22px; margin-bottom: 16px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 2px solid #e2e8f0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">
                    <span style="font-size: 1.3rem; color: #475569; font-weight: bold;">🏢 {job['company']}</span>
                    <span style="background: {badge_color}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 1rem; font-weight: bold; white-space: nowrap;">{job['type']}</span>
                </div>
                <h2 style="font-size: 1.6rem; color: #1e293b; margin: 0 0 12px 0; font-weight: 800; line-height: 1.4;">{job['title']}</h2>
                <div style="display: flex; justify-content: space-between; font-size: 1.1rem; color: #64748b; flex-wrap: wrap; gap: 10px;">
                    <span>📍 {job['location']}</span>
                    <span style="color: #ef4444; font-weight: bold;">📅 마감일: {job['end_date']}</span>
                </div>
            </div>
        </a>
        """

    # 외부 HTML 파일을 읽어와서 데이터 매핑 후 출력
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_template = f.read()
        
    final_html = html_template.replace("{{ search_keyword }}", search).replace("{{ cards_html | safe }}", cards_html)
    return HTMLResponse(content=final_html, status_code=200)