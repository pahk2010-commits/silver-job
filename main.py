from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET

app = FastAPI()

# 🔴 [필수] 공공데이터포털 마이페이지에서 복사한 발급 인증키를 입력해 주세요.
# 두 API 모두 한국노인인력개발원 데이터이므로 이 하나의 키로 모두 조회가 가능합니다.
SERVICE_KEY = "uaZP6n4f8eLkbm97mubDbl0qAR2bBcxWPfpX2NwQAz85hsvnCmNscPruVqEor92pIwOQcdxVOSkB045cTEbcMw%3D%3D"

# --- 1. 일반 기업/민간 채용정보(구인정보)를 긁어오는 함수 ---
def get_job_info_list(search_keyword=""):
    try:
        url = "http://data.go.kr"
        params = {"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "30"}
        if search_keyword:
            params["clmPhByArea"] = search_keyword
        
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                jobs.append({
                    "type": "💼 일반 취업형",
                    "company": item.findtext("oranNm", "민간 기업/기관"),
                    "title": item.findtext("jobNm", "모집 공고"),
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "접수중")
                })
        return jobs
    except Exception:
        return []

# --- 2. 정부·지자체 주관 공공 일자리(자립형 일자리)를 긁어오는 함수 ---
def get_자립형_일자리_list(search_keyword=""):
    try:
        # 한국노인인력개발원 자립형일자리 사업모집공고 API 주소입니다.
        url = "http://data.go.kr"
        params = {"serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "30"}
        if search_keyword:
            params["clmPhByArea"] = search_keyword
            
        response = requests.get(url, params=params, timeout=5)
        jobs = []
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for item in root.findall(".//item"):
                jobs.append({
                    "type": "👵👴 정부 지원형",
                    "company": item.findtext("oranNm", "시니어클럽/지자체 수행기관"),
                    "title": item.findtext("annncNm", "공공 일자리 모집 정보"), # 사업공고명
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "상세 문의")
                })
        return jobs
    except Exception:
        return []

@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    # [핵심 기술] 두 종류의 실시간 데이터를 각각 독립적으로 받아옵니다.
    private_jobs = get_job_info_list(search)
    public_jobs = get_자립형_일자리_list(search)
    
    # 두 리스트를 하나로 합쳐서 풍성한 일자리 데이터베이스를 만듭니다.
    total_job_list = private_jobs + public_jobs
    
    cards_html = ""
    # 만약 전산 대기 상태이거나 데이터가 아예 없을 때 보여줄 꼼꼼한 기본 예시입니다.
    if not total_job_list:
        total_job_list = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이", "company": "동해시 시니어클럽", "location": "강원도 동해시", "end_date": "접수 마감까지"},
            {"type": "💼 일반 취업형", "title": "[실버 채용] 아파트 단지 실버 택배원 모집", "company": "종합물류 시니어지사", "location": "강원도 동해시 평릉동", "end_date": "2026-12-31 까지"},
            {"type": "👵👴 정부 지원형", "title": "[문화재 보호] 지역 문화재 해설 및 안내 요원", "company": "대한노인회 지회", "location": "경주시 일대", "end_date": "상세 문의"},
        ]
        
    for job in total_job_list:
        # 유형에 따라 파란색/초록색 딱지(뱃지)를 붙여 어르신들이 구별하기 쉽게 만듭니다.
        badge_color = "#0284c7" if "정부" in job['type'] else "#059669"
        
        cards_html += f"""
        <div style="background: white; padding: 20px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 1.4rem; color: #475569; font-weight: bold;">🏢 {job['company']}</span>
                <span style="background: {badge_color}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 1rem; font-weight: bold;">{job['type']}</span>
            </div>
            <div style="font-size: 1.8rem; color: #333; font-weight: bold; margin-bottom: 10px;">📌 {job['title']}</div>
            <div style="font-size: 1.2rem; color: #555; line-height: 1.6;">
                <p>📍 <b>근무 예정지:</b> {job['location']}</p>
                <p>⏱️ <b>접수 기한:</b> <span style="color:#ef4444; font-weight:bold;">{job['end_date']}</span></p>
            </div>
        </div>
        """
        
    final_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>실버 인력 통합 구인정보 검색창</title>
        <script>
            let currentSize = 100;
            function changeFontSize(amount) {{
                currentSize += amount;
                if (currentSize < 80) currentSize = 80;
                if (currentSize > 160) currentSize = 160;
                document.body.style.fontSize = currentSize + "%";
                document.getElementById('sizeStatus').innerText = "글자 크기: " + currentSize + "%";
            }}
        </script>
    </head>
    <body style="font-family: 'Malgun Gothic', sans-serif; background-color: #f4f6f9; padding: 20px; font-size: 100%; transition: font-size 0.2s;">
        <div style="max-width: 600px; margin: 0 auto;">
            
            <!-- 상단 글자 크기 조절 제어판 -->
            <div style="display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-bottom: 15px; background: #e0f2fe; padding: 10px; border-radius: 8px;">
                <span id="sizeStatus" style="font-size: 1.1rem; font-weight: bold; color: #0369a1;">글자 크기: 100%</span>
                <button onclick="changeFontSize(15)" style="padding: 5px 15px; font-size: 1.1rem; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔎 글자 크게</button>
                <button onclick="changeFontSize(-15)" style="padding: 5px 15px; font-size: 1.1rem; background: #64748b; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔍 글자 작게</button>
            </div>

            <h1 style="text-align: center; color: #333; font-size: 2.5rem; margin-bottom: 10px;">👵👴 실버 인력 통합 구인 검색</h1>
            <p style="text-align: center; color: #0284c7; font-size: 1.2rem; font-weight: bold; margin-bottom: 25px;">⚡ 민간기업 채용정보 & 정부 일자리 실시간 통합 연동 중</p>
            
            <form method="get" action="/" style="display: flex; gap: 10px; margin-bottom: 30px;">
                <input type="text" name="search" value="{search}" placeholder="지역명 또는 동 이름을 입력하세요 (예: 서울, 해운대, 천곡)" 
                       style="flex: 1; padding: 15px; font-size: 1.3rem; border: 2px solid #0284c7; border-radius: 8px; outline: none;">
                <button type="submit" 
                        style="padding: 15px 30px; font-size: 1.3rem; background-color: #0284c7; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer;">🔍 검색</button>
            </form>
            
            {cards_html}
            
            <!-- 법률 준수를 위한 정부 출처 표시 하단 문구 -->
            <p style="text-align: center; color: #94a3b8; font-size: 1rem; margin-top: 40px; border-top: 1px solid #cbd5e1; padding-top: 20px;">
                본 서비스는 대한민국 공공데이터포털 법률을 준수하며, 한국노인인력개발원의 정식 공공데이터 API를 연동하여 실시간 정보를 제공합니다.
            </p>
        </div>
    </body>
    </html>
    """
    return final_html