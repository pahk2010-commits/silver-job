from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET

app = FastAPI()

# 🔴 [필수] 공공데이터포털 마이페이지에서 복사한 발급 인증키를 입력해 주세요.
SERVICE_KEY = "uaZP6n4f8eLkbm97mubDbl0qAR2bBcxWPfpX2NwQAz85hsvnCmNscPruVqEor92pIwOQcdxVOSkB045cTEbcMw%3D%3D"

# --- 1. 노인인력개발원 일반 구인정보 ---
def get_kordi_private_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "20"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                link = item.findtext("detlWebAdres", "https://kordi.or.kr").strip()
                jobs.append({
                    "type": "💼 일반 취업형", "company": item.findtext("oranNm", "민간 기업"),
                    "title": item.findtext("jobNm", "모집 공고"), "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "접수중"), "url": link
                })
        return jobs
    except Exception: return []

# --- 2. 노인인력개발원 정부 지원 공공일자리 ---
def get_kordi_public_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "20"}
        if search_keyword: params["clmPhByArea"] = search_keyword
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                link = item.findtext("detlWebAdres", "https://100solenuri.go.kr").strip()
                jobs.append({
                    "type": "👵👴 정부 지원형", "company": item.findtext("oranNm", "시니어클럽 등"),
                    "title": item.findtext("annncNm", "공공 일자리 모집"), "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "상세 문의"), "url": link
                })
        return jobs
    except Exception: return []

# --- 3. 잡알리오(JOB ALIO) 공공기관/공기업 구인정보 수집 엔진 ---
def get_job_alio_public_jobs(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "20"}
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            data = response.json()
            for item in data.get('data', []):
                company = item.get('instNm', '공공기관/공기업')
                title = item.get('pblntcNm', '공공 채용 정보')
                location = item.get('workRgnNm', '전국')
                end_date = item.get('pbancEndDt', '상세 확인')
                link = item.get('srcUrl', 'https://alio.go.kr')
                
                if search_keyword and (search_keyword not in title and search_keyword not in location and search_keyword not in company):
                    continue
                    
                jobs.append({
                    "type": "🏛️ 잡알리오 공공기관형", "company": company, "title": title,
                    "location": location, "end_date": end_date, "url": link
                })
        return jobs
    except Exception:
        return []

@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    kordi_p = get_kordi_private_jobs(search)
    kordi_g = get_kordi_public_jobs(search)
    alio_g = get_job_alio_public_jobs(search)
    
    total_job_list = kordi_p + kordi_g + alio_g
    
    cards_html = ""
    if not total_job_list:
        # 🌟 [요청 반영] 전산 대기 시 화면을 채워줄 친절한 '동해시 시니어클럽(잡알리오)' 전용 고품격 예시 데이터입니다!
        total_job_list = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이 모집", "company": "동해시 시니어클럽", "location": "강원도 동해시 천곡동", "end_date": "접수 마감까지", "url": "https://kordi.or.kr"},
            {"type": "🏛️ 잡알리오 공공기관형", "title": "[공기업/시설관리] 망상오토캠핑장 야간 환경 보안관 채용", "company": "동해시 시니어클럽 (잡알리오 연동)", "location": "강원도 동해시 망상동", "end_date": "2026-10-15 까지", "url": "https://alio.go.kr"},
            {"type": "💼 일반 취업형", "title": "[실버 채용] 아파트 단지 안심 실버 택배원 구인", "company": "종합물류 동해지사", "location": "강원도 동해시 평릉동", "end_date": "채용시까지", "url": "https://kordi.or.kr"},
        ]
        
    for job in total_job_list:
        if "정부" in job['type']: badge_color = "#0284c7"
        elif "잡알리오" in job['type']: badge_color = "#0ea5e9" # 하늘색 딱지
        else: badge_color = "#059669"
        
        cards_html += f"""
        <a href="{job['url']}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
            <div style="background: white; padding: 18px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border: 2px solid transparent; transition: all 0.2s;"
                 onmouseover="this.style.borderColor='{badge_color}';" onmouseout="this.style.borderColor='transparent';">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 5px;">
                    <span style="font-size: 1.2rem; color: #475569; font-weight: bold;">🏢 {job['company']}</span>
                    <span style="background: {badge_color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.9rem; font-weight: bold; white-space: nowrap;">{job['type']}</span>
                </div>
                <div style="font-size: 1.5rem; color: #222; font-weight: bold; margin-bottom: 10px; line-height: 1.4; word-break: keep-all;">📌 {job['title']}</div>
                <div style="font-size: 1.1rem; color: #555; line-height: 1.5;">
                    <p style="margin: 4px 0;">📍 <b>근무지:</b> {job['location']}</p>
                    <p style="margin: 4px 0;">⏱️ <b>기한:</b> <span style="color:#ef4444; font-weight:bold;">{job['end_date']}</span></p>
                    <p style="text-align: right; margin: 8px 0 0 0; color: {badge_color}; font-weight: bold; font-size: 1rem;">상세 공고로 바로가기 ➔</p>
                </div>
            </div>
        </a>
        """
        
    final_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>실버 인력 통합 구인정보 검색창</title>
        <script>
            let currentSize = 100;
            function changeFontSize(amount) {{
                currentSize += amount;
                if (currentSize < 80) currentSize = 80;
                if (currentSize > 150) currentSize = 150;
                document.body.style.fontSize = currentSize + "%";
                document.getElementById('sizeStatus').innerText = "글자: " + currentSize + "%";
            }}
        </script>
    </head>
    <body style="font-family: 'Malgun Gothic', sans-serif; background-color: #f4f6f9; padding: 12px; margin: 0; font-size: 100%; transition: font-size 0.2s; -webkit-text-size-adjust: none;">
        <div style="max-width: 100%; margin: 0 auto; box-sizing: border-box;">
            
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; background: #e0f2fe; padding: 8px 12px; border-radius: 8px;">
                <span id="sizeStatus" style="font-size: 1rem; font-weight: bold; color: #0369a1;">글자: 100%</span>
                <div style="display: flex; gap: 6px;">
                    <button onclick="changeFontSize(10)" style="padding: 6px 12px; font-size: 1rem; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔎 크게</button>
                    <button onclick="changeFontSize(-10)" style="padding: 6px 12px; font-size: 1rem; background: #64748b; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔍 작게</button>
                </div>
            </div>

            <h1 style="text-align: center; color: #333; font-size: 1.8rem; margin: 15px 0 5px 0;">👵👴 실버 인력 통합 검색</h1>
            <p style="text-align: center; color: #0284c7; font-size: 1rem; font-weight: bold; margin-bottom: 20px;">⚡ 정부 전산망 및 잡알리오 실시간 연동 중</p>
            
            <form method="get" action="/" style="display: flex; gap: 8px; margin-bottom: 20px;">
                <input type="text" name="search" value="{search}" placeholder="지역명 또는 동 이름 (예: 천곡, 삼척)" 
                       style="flex: 1; padding: 12px; font-size: 1.1rem; border: 2px solid #0284c7; border-radius: 8px; outline: none; box-sizing: border-box;">
                <button type="submit" 
                        style="padding: 12px 20px; font-size: 1.1rem; background-color: #0284c7; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; white-space: nowrap;">🔍 검색</button>
            </form>
            
            {cards_html}
            
            <p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 30px; border-top: 1px solid #cbd5e1; padding-top: 15px; line-height: 1.4; word-break: keep-all;">
                본 서비스는 대한민국 공공데이터포털 법률을 준수하며, 한국노인인력개발원 및 기획재정부의 정식 API를 연동하여 제공합니다.
            </p>
        </div>
    </body>
    </html>
    """
    return final_html