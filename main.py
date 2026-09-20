from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import xml.etree.ElementTree as ET
import urllib.parse
import os
import asyncio

app = FastAPI()

# 전역 실시간 업데이트 일자리 저장소
LIVE_JOB_CACHE = []

def fetch_all_live_jobs():
    global LIVE_JOB_CACHE
    PUBLIC_DATA_KEY = os.getenv("PUBLIC_DATA_KEY", "").strip()
    EMPLOYMENT24_KEY = os.getenv("EMPLOYMENT24_KEY", "").strip()
    
    # 인증키 미입력 혹은 연동 장애 시 작동할 동해/삼척 예비 클린 데이터셋
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
    
    # 1. 노인인력개발원 민간 API 수집
    if PUBLIC_DATA_KEY:
        try:
            url = "http://data.go.kr"
            res = requests.get(url, params={"serviceKey": urllib.parse.unquote(PUBLIC_DATA_KEY), "pageNo": "1", "numOfRows": "40"}, timeout=3)
            if res.status_code == 200:
                for item in ET.fromstring(res.content).findall(".//item"):
                    c = item.findtext("oranNm", "민간 기업").strip()
                    t = item.findtext("jobNm", "모집 공고").strip()
                    l = item.findtext("plmPhByArea", "지역 정보").strip()
                    temp_jobs.append({"type": "💼 일반 취업형", "company": c, "title": t, "location": l, "end_date": item.findtext("rcritEndDe", "접수중"), "url": f"https://google.com{urllib.parse.quote(l+' '+c+' '+t)}"})
        except Exception: pass

    # 2. 노인인력개발원 정부공공 API 수집
    if PUBLIC_DATA_KEY:
        try:
            url = "http://data.go.kr"
            res = requests.get(url, params={"serviceKey": urllib.parse.unquote(PUBLIC_DATA_KEY), "pageNo": "1", "numOfRows": "40"}, timeout=3)
            if res.status_code == 200:
                for item in ET.fromstring(res.content).findall(".//item"):
                    c = item.findtext("oranNm", "시니어클럽").strip()
                    t = item.findtext("annncNm", "공공 일자리").strip()
                    l = item.findtext("plmPhByArea", "지역 정보").strip()
                    temp_jobs.append({"type": "👵👴 정부 지원형", "company": c, "title": t, "location": l, "end_date": item.findtext("rcritEndDe", "상세 문의"), "url": f"https://google.com{urllib.parse.quote(l+' '+c+' '+t+' 모집')}"})
        except Exception: pass

    # 3. 고용24 (워크넷) 실버 API 수집
    if EMPLOYMENT24_KEY:
        try:
            url = "http://work.go.kr"
            res = requests.get(url, params={"authKey": EMPLOYMENT24_KEY, "callTp": "L", "returnType": "XML", "startPage": "1", "display": "40", "preferentialGbn": "01"}, timeout=3)
            if res.status_code == 200:
                for item in ET.fromstring(res.content).findall(".//wanted"):
                    c = item.findtext("corpNm", "민간 기업").strip()
                    t = item.findtext("title", "모집 공고").strip()
                    l = item.findtext("region", "지역 정보").strip()
                    temp_jobs.append({"type": "🚀 고용24 민간취업형", "company": c, "title": t, "location": l, "end_date": item.findtext("closeDt", "채용시까지"), "url": f"https://google.com{urllib.parse.quote(c+' '+t+' 구인공고')}"})
        except Exception: pass

    if temp_jobs:
        LIVE_JOB_CACHE = temp_jobs

# 1시간 주기 실시간 데이터 백그라운드 갱신 자동화
async def job_scheduler():
    while True:
        fetch_all_live_jobs()
        await asyncio.sleep(3600)

@app.on_event("startup")
def startup_event():
    fetch_all_live_jobs()
    asyncio.create_task(job_scheduler())


@app.get("/", response_class=HTMLResponse)
def home(search: str = ""):
    global LIVE_JOB_CACHE
    kwd = search.strip()
    flist = [j for j in LIVE_JOB_CACHE if kwd in j['title'] or kwd in j['company'] or kwd in j['location'] or kwd in j['type']] if kwd else LIVE_JOB_CACHE
        
    cards = ""
    for j in flist:
        col = "#0284c7" if "정부" in j['type'] else ("#0ea5e9" if "잡알리오" in j['type'] else ("#ea580c" if "고용24" in j['type'] else "#059669"))
        cards += f'<a href="{j["url"]}" target="_blank" style="text-decoration:none;color:inherit;display:block;">' + \
                 f'  <div style="background:white;padding:22px;margin-bottom:16px;border-radius:12px;box-shadow:0 4px 6px rgba(0,0,0,0.05);border:2px solid #e2e8f0;">' + \
                 f'    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">' + \
                 f'      <span style="font-size:1.3rem;color:#475569;font-weight:bold;">🏢 {j["company"]}</span>' + \
                 f'      <span style="background:{col};color:white;padding:4px 10px;border-radius:6px;font-size:1rem;font-weight:bold;white-space:nowrap;">{j["type"]}</span>' + \
                 f'    </div>' + \
                 f'    <h2 style="font-size:1.6rem;color:#1e293b;margin:0 0 12px 0;font-weight:800;line-height:1.4;">{j["title"]}</h2>' + \
                 f'    <div style="display:flex;justify-content:space-between;font-size:1.1rem;color:#64748b;flex-wrap:wrap;gap:10px;">' + \
                 f'      <span>📍 {j["location"]}</span>' + \
                 f'      <span style="color:#ef4444;font-weight:bold;">📅 마감일: {j["end_date"]}</span>' + \
                 f'    </div>' + \
                 f'  </div>' + \
                 f'</a>'

    if not cards:
        cards = '<div class="no-result">검색 결과에 맞는 실시간 일자리가 없습니다. 다른 검색어를 입력해 보세요.</div>'

    # 파이썬 3.14 문자열 무력화 전용 슬래시 결합형 디자인 스킨 코드
    html = '<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">' + \
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">' + \
    '<title>시니어 행복 일자리 찾기</title><style>' + \
    "body { font-family:'Malgun Gothic',dotum,sans-serif;background-color:#f8fafc;margin:0;padding:0; }" + \
    ".container { max-width:800px;margin:0 auto;padding:20px; }" + \
    ".header { text-align:center;padding:35px 0;background:linear-gradient(135deg,#059669,#10b981);color:white;border-radius:16px;margin-bottom:24px;box-shadow:0 4px 10px rgba(0,0,0,0.1); }" + \
    ".header h1 { margin:0 0 10px 0;font-size:2.5rem;font-weight:900; }" + \
    ".header p { margin:0;font-size:1.4rem;opacity:0.95; }" + \
    ".search-box { display:flex;gap:10px;margin-bottom:24px; }" + \
    f'.search-input {{ flex:1;padding:18px;font-size:1.4rem;border:3px solid #cbd5e1;border-radius:12px;font-weight:bold; }}' + \
    ".search-input:focus { border-color:#10b981;outline:none; }" + \
    ".search-btn { padding: 0 35px;font-size:1.4rem;background-color:#10b981;color:white;border:none;border-radius:12px;font-weight:bold;cursor:pointer; }" + \
    ".search-btn:hover { background-color:#059669; }" + \
    ".no-result { text-align:center;padding:40px;font-size:1.3rem;color:#64748b;font-weight:bold;background:white;border-radius:12px;border:2px dashed #cbd5e1; }" + \
    f'</style></head><body><div class="container"><div class="header"><h1>👵👴 어르신 맞춤 일자리 찾기</h1><p>원하시는 동네 이름이나 일자리 종류를 검색창에 입력해 보세요!</p></div>' + \
    f'<form method="get" class="search-box"><input type="text" name="search" class="search-input" placeholder="예: 삼척, 동해, 청소, 경비" value="{kwd}">' + \
    f'<button type="submit" class="search-btn">검색하기</button></form><div class="job-list">{cards}</div></div></body></html>'
    
    return HTMLResponse(content=html, status_code=200)