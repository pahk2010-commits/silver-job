from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import uvicorn
import os
from contextlib import asynccontextmanager
import asyncio

# 전 세계 사용자를 위한 실시간 메모리 데이터 저장소 (캐시)
LIVE_JOB_CACHE = []

# --- 1. 정부 오픈 API 실시간 수집 엔진 ---
def fetch_all_live_jobs():
    global LIVE_JOB_CACHE
    
    # Render 환경변수(Environment Variables)창에 적으신 진짜 키들을 자동으로 읽어옵니다.
    PUBLIC_DATA_KEY = os.getenv("PUBLIC_DATA_KEY", "").strip()
    EMPLOYMENT24_KEY = os.getenv("EMPLOYMENT24_KEY", "").strip()
    
    # 인증키가 등록되지 않았다면 임시로 가동할 고품질 테스트 데이터셋
    if not PUBLIC_DATA_KEY and not EMPLOYMENT24_KEY:
        LIVE_JOB_CACHE = [
            {"type": "👵👴 정부 지원형", "title": "[우리동네] 초등학교 등하교 안심 지킴이 모집", "company": "동해시 시니어클럽", "location": "강원도 동해시", "end_date": "접수 마감까지", "url": "https://kordi.or.kr"},
            {"type": "👵👴 정부 지원형", "title": "[삼척시 주관] 공원 녹지대 가꾸기 및 환경 정화 지원원 모집", "company": "삼척시니어클럽", "location": "강원도 삼척시", "end_date": "선착순 마감", "url": "https://google.com" + urllib.parse.quote("삼척시 노인 일자리")},
            {"type": "🏛️ 잡알리오 공공기관형", "title": "[공기업/시설관리] 망상오토캠핑장 야간 환경 보안관 채용", "company": "동해시 시설관리공단", "location": "강원도 동해시", "end_date": "2026-10-15 까지", "url": "https://alio.go.kr"},
            {"type": "🚀 고용24 민간취업형", "title": "[장년우대/급여최상] 우리지역 종합 물류센터 실버 실내 분류원 구인", "company": "동해항 물류 연동 기업", "location": "강원도 동해시", "end_date": "채용시 마감", "url": "https://work.go.kr"},
            {"type": "💼 일반 취업형", "title": "[시니어 환영] 아파트 단지 실버 택배 배송 및 관리원 모집", "company": "행복종합관리", "location": "강원도 동해시", "end_date": "수시 채용", "url": "https://google.com" + urllib.parse.quote("동해시 아파트 실버 택배 채용")},
            {"type": "🚀 고용24 민간취업형", "title": "[시니어 우대] 삼척 근덕 종합 마트 주차 안내 요원 모집", "company": "삼척 유통상사", "location": "강원도 삼척시", "end_date": "채용시 마감", "url": "https://google.com" + urllib.parse.quote("삼척 마트 주차 채용")}
        ]
        return

    temp_jobs = []
    
    # A. 노인인력개발원 민간형 API 수집
    if PUBLIC_DATA_KEY:
        try:
            url = "http://data.go.kr"
            api_key = urllib.parse.unquote(PUBLIC_DATA_KEY)
            response = requests.get(url, params={"serviceKey": api_key, "pageNo": "1", "numOfRows": "50"}, timeout=4)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall(".//item"):
                    comp = item.findtext("oranNm", "민간 기업").strip()
                    tit = item.findtext("jobNm", "모집 공고").strip()
                    loc = item.findtext("plmPhByArea", "지역 정보").strip()
                    temp_jobs.append({"type": "💼 일반 취업형", "company": comp, "title": tit, "location": loc, "end_date": item.findtext("rcritEndDe", "접수중"), "url": f"https://google.com{urllib.parse.quote(loc + ' ' + comp + ' ' + tit)}"})
        except Exception: pass

    # B. 노인인력개발원 정부공공형 API 수집
    if PUBLIC_DATA_KEY:
        try:
            url = "http://data.go.kr"
            api_key = urllib.parse.unquote(PUBLIC_DATA_KEY)
            response = requests.get(url, params={"serviceKey": api_key, "pageNo": "1", "numOfRows": "50"}, timeout=4)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall(".//item"):
                    comp = item.findtext("oranNm", "시니어클럽 등").strip()
                    tit = item.findtext("annncNm", "공공 일자리 모집").strip()
                    loc = item.findtext("plmPhByArea", "지역 정보").strip()
                    temp_jobs.append({"type": "👵👴 정부 지원형", "company": comp, "title": tit, "location": loc, "end_date": item.findtext("rcritEndDe", "상세 문의"), "url": f"https://google.com{urllib.parse.quote(loc + ' ' + comp + ' ' + tit + ' 모집')}"})
        except Exception: pass

    # C. 잡알리오 공공기관 API 수집
    if PUBLIC_DATA_KEY:
        try:
            url = "http://data.go.kr"
            api_key = urllib.parse.unquote(PUBLIC_DATA_KEY)
            response = requests.get(url, params={"serviceKey": api_key, "pageNo": "1", "numOfRows": "40"}, timeout=4)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall(".//item"):
                    comp = item.findtext("instNm", "공공기관").strip()
                    tit = item.findtext("pblntcNm", "공공 채용").strip()
                    loc = item.findtext("workRgnNm", "전국").strip()
                    temp_jobs.append({"type": "🏛️ 잡알리오 공공기관형", "company": comp, "title": tit, "location": loc, "end_date": item.findtext("pbancEndDt", "상세 확인"), "url": f"https://google.com{urllib.parse.quote(comp + ' ' + tit + ' 채용공고')}"})
        except Exception: pass

    # D. 고용24 (워크넷) 실버 우대 API 수집
    if EMPLOYMENT24_KEY:
        try:
            url = "http://work.go.kr"
            params = {"authKey": EMPLOYMENT24_KEY, "callTp": "L", "returnType": "XML", "startPage": "1", "display": "50", "preferentialGbn": "01"}
            response = requests.get(url, params=params, timeout=4)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                for item in root.findall(".//wanted"):
                    comp = item.findtext("corpNm", "민간 기업").strip()
                    tit = item.findtext("title", "모집 공고").strip()
                    loc = item.findtext("region", "지역 정보").strip()
                    temp_jobs.append({"type": "🚀 고용24 민간취업형", "company": comp, "title": tit, "location": loc, "end_date": item.findtext("closeDt", "채용시까지"), "url": f"https://google.com{urllib.parse.quote(comp + ' ' + tit + ' 구인공고')}"})
        except Exception: pass

    if temp_jobs:
        LIVE_JOB_CACHE = temp_jobs

# --- 2. 실시간 자동 업데이트 루프 스케줄러 (1시간 마다 정부 서버 갱신) ---
async def job_update_scheduler():
    while True:
        fetch_all_live_jobs()
        await asyncio.sleep(3600) # 3600초 = 1시간 주기 자동 갱신

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 웹 사이트가 켜질 때 전국 실시간 수집을 즉시 1회 작동시킵니다.
    fetch_all_live_jobs()
    asyncio.create_task(job_update_scheduler())
    yield

# 시스템 라이프사이클 바인딩
app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    global LIVE_JOB_CACHE
    
    # 검색어 정제 및 필터링
    search_keyword = search.strip()
    if search_keyword:
        filtered_list = [j for j in LIVE_JOB_CACHE if search_keyword in j['title'] or search_keyword in j['company'] or search_keyword in j['location'] or search_keyword in j['type']]
    else:
        filtered_list = LIVE_JOB_CACHE
        
    cards_html = ""
    for job in filtered_list:
        if "정부" in job['type']: badge_color = "#0284c7"
        elif "잡알리오" in job['type']: badge_color = "#0ea5e9"
        elif "고용24" in job['type']: badge_color = "#ea580c"
        else: badge_color = "#059669"
        
        cards_html += '<a href="' + job["url"] + '" target="_blank" style="text-decoration: none; color: inherit; display: block;">' + \
        '  <div style="background: white; padding: 22px; margin-bottom: 16px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 2px solid #e2e8f0;">' + \
        '    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 8px;">' + \
        '      <span style="font-size: 1.3rem; color: #475569; font-weight: bold;">🏢 ' + job["company"] + '</span>' + \
        '      <span style="background: ' + badge_color + '; color: white; padding: 4px 10px; border-radius: 6px; font-size: 1rem; font-weight: bold; white-space: nowrap;">' + job["type"] + '</span>' + \
        '    </div>' + \
        '    <h2 style="font-size: 1.6rem; color: #1e293b; margin: 0 0 12px 0; font-weight: 800; line-height: 1.4;">' + job["title"] + '</h2>' + \
        '    <div style="display: flex; justify-content: space-between; font-size: 1.1rem; color: #64748b; flex-wrap: wrap; gap: 10px;">' + \
        '      <span>📍 ' + job["location"] + '</span>' + \
        '      <span style="color: #ef4444; font-weight: bold;">📅 마감일: ' + job["end_date"] + '</span>' + \
        '    </div>' + \
        '  </div>' + \
        '</a>'

    if not cards_html:
        cards_html = '<div class="no-result">검색 결과에 맞는 실시간 일자리가 없습니다. 다른 검색어를 입력해 보세요.</div>'

    # 파이썬 3.14 호환 전용 문자열 세척 조립식 렌더링 레이아웃
    final_html = '<!DOCTYPE html>' + \
    '<html lang="ko">' + \
    '<head>' + \
    '    <meta charset="UTF-8">' + \
    '    <meta name="viewport" content="width=device-width, initial-scale=1.0">' + \
    '    <title>시니어 행복 일자리 찾기</title>' + \
    '    <style>' + \
    "        body { font-family: 'Malgun Gothic', dotum, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; }" + \
    '        .container { max-width: 800px; margin: 0 auto; padding: 20px; }' + \
    '        .header { text-align: center; padding: 35px 0; background: linear-gradient(135deg, #059669, #10b981); color: white; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }' + \
    '        .header h1 { margin: 0 0 10px 0; font-size: 2.5rem; font-weight: 900; }' + \
    '        .header p { margin: 0; font-size: 1.4rem; opacity: 0.95; }' + \
    '        .search-box { display: flex; gap: 10px; margin-bottom: 24px; }' + \
    '        .search-input { flex: 1; padding: 18px; font-size: 1.4rem; border: 3px solid #cbd5e1; border-radius: 12px; font-weight: bold; }' + \
    '        .search-input:focus { border-color: #10b981; outline: none; }' + \
    '        .search-btn { padding: 0 35px; font-size: 1.4rem; background-color: #10b981; color: white; border: none; border-radius: 12px; font-weight: bold; cursor: pointer; }' + \