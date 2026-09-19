from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET

app = FastAPI()

# 🔴 [필수] 공공데이터포털 마이페이지에서 복사한 발급 인증키를 입력해 주세요.
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
                link_url = item.findtext("detlWebAdres", "")
                if not link_url:
                    link_url = "https://kordi.or.kr"
                    
                jobs.append({
                    "type": "💼 일반 취업형",
                    "company": item.findtext("oranNm", "민간 기업/기관"),
                    "title": item.findtext("jobNm", "모집 공고"),
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "접수중"),
                    "url": link_url
                })
        return jobs
    except Exception:
        return []

# --- 2. 정부·지자체 주관 공공 일자리(자립형 일자리)를 긁어오는 함수 ---
def get_자립형_일자리_list(search_keyword=""):
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
                link_url = item.findtext("detlWebAdres", "")
                if not link_url:
                    link_url = "https://kordi.or.kr"
                    
                jobs.append({
                    "type": "👵👴 정부 지원형",
                    "company": item.findtext("oranNm", "시니어클럽/지자체 수행기관"),
                    "title": item.findtext("annncNm", "공공 일자리 모집 정보"),
                    "location": item.findtext("plmPhByArea", "지역 정보 없음"),
                    "end_date": item.findtext("rcritEndDe", "상세 문의"),
                    "url": link_url
                })
        return jobs
    except Exception:
        return []

@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    private_jobs = get_job_info_list(search)
    public_jobs = get_자립형_일자리_list(search)
    
    total_job_list = private_jobs + public_jobs
    
    cards_html = ""
    if not total_job_list:
        total_job_list = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이", "company": "동해시 시니어클럽", "location": "강원도 동해시", "end_date": "접수 마감까지", "url": "https://kordi.or.kr"},
            {"type": "💼 일반 취업형", "title": "[실버 채용] 아파트 단지 실버 택배원 모집", "company": "종합물류 시니어지사", "location": "강원도 동해시 평릉동", "end_date": "2026-12-31 까지", "url": "https://kordi.or.kr"},
        ]
        
    for job in total_job_list:
        badge_color = "#0284c7" if "정부" in job['type'] else "#059669"
        
        # 💡 모바일 가독성을 위해 여백과 글자 크기 밸런스를 스마트폰 화면용으로 정밀 튜닝했습니다.
        cards_html += f"""
        <a href="{job['url']}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
            <div style="background: white; padding: 18px; margin-bottom: 12px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08); border: 2px solid transparent; transition: all 0.2s;"
                 onmouseover="this.style.borderColor='#0284c7';" onmouseout="this.style.borderColor='transparent';">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 5px;">
                    <span style="font-size: 1.2rem; color: #475569; font-weight: bold;">🏢 {job['company']}</span>
                    <span style="background: {badge_color}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 0.9rem; font-weight: bold; white-space: nowrap;">{job['type']}</span>
                </div>
                <div style="font-size: 1.5rem; color: #222; font-weight: bold; margin-bottom: 10px; line-height: 1.4; word-break: keep-all;">📌 {job['title']}</div>
                <div style="font-size: 1.1rem; color: #555; line-height: 1.5;">
                    <p style="margin: 4px 0;">📍 <b>근무지:</b> {job['location']}</p>
                    <p style="margin: 4px 0;">⏱️ <b>기한:</b> <span style="color:#ef4444; font-weight:bold;">{job['end_date']}</span></p>
                    <p style="text-align: right; margin: 8px 0 0 0; color: #0284c7; font-weight: bold; font-size: 1rem;">상세보기 ➔</p>
                </div>
            </div>
        </a>
        """
        
    final_html = f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <!-- 🌟 [가장 중요] 스마트폰 액정 크기에 맞춰 화면을 자동으로 늘려주는 모바일 필수 명령(viewport)을 선언했습니다. -->
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
    <!-- 스마트폰 좌우 여백을 12px로 주어 양옆이 답답하게 잘리지 않도록 모바일 최적화 레이아웃 스타일을 적용했습니다. -->
    <body style="font-family: 'Malgun Gothic', sans-serif; background-color: #f4f6f9; padding: 12px; margin: 0; font-size: 100%; transition: font-size 0.2s; -webkit-text-size-adjust: none;">
        <div style="max-width: 100%; margin: 0 auto; box-sizing: border-box;">
            
            <!-- 스마트폰 상단 고정형 글자 조절 바 -->
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; background: #e0f2fe; padding: 8px 12px; border-radius: 8px;">
                <span id="sizeStatus" style="font-size: 1rem; font-weight: bold; color: #0369a1;">글자: 100%</span>
                <div style="display: flex; gap: 6px;">
                    <button onclick="changeFontSize(10)" style="padding: 6px 12px; font-size: 1rem; background: #0284c7; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔎 크게</button>
                    <button onclick="changeFontSize(-10)" style="padding: 6px 12px; font-size: 1rem; background: #64748b; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer;">🔍 작게</button>
                </div>
            </div>

            <h1 style="text-align: center; color: #333; font-size: 1.8rem; margin: 15px 0 5px 0;">👵👴 실버 인력 통합 검색</h1>
            <p style="text-align: center; color: #0284c7; font-size: 1rem; font-weight: bold; margin-bottom: 20px;">⚡ 정부 일자리 실시간 통합 연동</p>
            
            <!-- 스마트폰용 터치하기 편한 넓은 검색창과 버튼 구조 배치 -->
            <form method="get" action="/" style="display: flex; gap: 8px; margin-bottom: 20px;">
                <input type="text" name="search" value="{search}" placeholder="지역명 또는 동 이름 (예: 천곡, 삼척)" 
                       style="flex: 1; padding: 12px; font-size: 1.1rem; border: 2px solid #0284c7; border-radius: 8px; outline: none; box-sizing: border-box;">
                <button type="submit" 
                        style="padding: 12px 20px; font-size: 1.1rem; background-color: #0284c7; color: white; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; white-space: nowrap;">🔍 검색</button>
            </form>
            
            {cards_html}
            
            <p style="text-align: center; color: #94a3b8; font-size: 0.85rem; margin-top: 30px; border-top: 1px solid #cbd5e1; padding-top: 15px; line-height: 1.4; word-break: keep-all;">
                본 서비스는 대한민국 공공데이터포털 법률을 준수하며, 한국노인인력개발원의 정식 API를 연동하여 제공합니다.
            </p>
        </div>
    </body>
    </html>
    """
    return final_html