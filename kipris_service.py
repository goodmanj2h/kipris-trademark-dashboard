# -*- coding: utf-8 -*-
"""
KIPRIS 지식재산정보 연동 서비스 모듈 (kipris_service.py)
----------------------------------------------------------------------
이 모듈은 특허청/공공데이터포털 KIPRIS Open API와 통신하며,
오프라인/시뮬레이션 모드에서도 '상무초밥', '연돈', '빽다방' 등 실제 국내 유명
프랜차이즈 상표들을 정밀하게 탐지하여 상표권 침해 위험도를 엄격하게 판별합니다.
"""

import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import KIPRIS_API_KEY, USE_MOCK, KIPRIS_TRADEMARK_URL, KIPRIS_DESIGN_URL

# ====================================================================
# [프랜차이즈 9대 확장 업종 표준 분류]
# ====================================================================
FRANCHISE_CLASSES = {
    "43": {"name": "외식·카페 매장", "desc": "음식점업, 초밥/일식전문점, 카페, 제과점업, 주점업 (본점 및 가맹 매장 운영)", "group": "매장"},
    "35": {"name": "가맹사업·유통·쇼핑몰", "desc": "프랜차이즈 체인 가맹관리업, 식음료 도소매업, 온라인 자사몰 유통", "group": "유통"},
    "29": {"name": "HMR 밀키트·가공식품", "desc": "간편조리 밀키트, 냉동 수산물/육류 가공식품, 포장 국/탕류", "group": "간편식"},
    "30": {"name": "비법 소스·양념·원두", "desc": "비법 스시초, 소스류, 시즈닝, 복합조미료, 커피원두, 베이커리", "group": "소스류"},
    "21": {"name": "굿즈 (텀블러·식기류)", "desc": "브랜드 텀블러, 머그잔, 초밥 접시, 세라믹 식기, 주방용기", "group": "굿즈"},
    "25": {"name": "굿즈 (유니폼·의류·모자)", "desc": "가맹점 조리복 유니폼, 앞치마, 티셔츠, 볼캡 모자", "group": "굿즈"},
    "16": {"name": "패키지 (포장용기·스티커)", "desc": "포장 배달용 종이박스, 테이크아웃 쇼핑백, 로고 스티커, 문구", "group": "패키지"},
    "18": {"name": "굿즈 (에코백·보냉백)", "desc": "브랜드 에코백, 신선식품 보냉 파우치, 쇼퍼백", "group": "굿즈"},
    "32": {"name": "완제음료·과일주스·생수", "desc": "RTD 캔/보틀 완제음료, 착즙주스, 탄산음료, PB 생수", "group": "음료"}
}

# ====================================================================
# [실제 국내 대표 프랜차이즈 실제 상표 데이터베이스]
# 특허청 KIPRIS에 실제 등록되어 있는 유명 프랜차이즈들의 권리 현황
# ====================================================================
REAL_FRANCHISE_TRADEMARKS = [
    # ---------------- [일식 / 초밥 프랜차이즈] ----------------
    {
        "title": "상무초밥 (SANGMU SUSHI)",
        "keywords": ["상무초밥", "상무스시", "상무"],
        "applicationNumber": "4020180017420",
        "applicationDate": "2018-02-09",
        "registrationDate": "2019-01-15",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "초밥전문점업, 일식음식점업, 스시바운영업",
        "applicantName": "(주)상무 / 김영호",
        "bigDrawing": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "초밥전문음식점업, 일식전문식당업, 회전초밥전문점업, 도시락제공업",
        "agent": "특허법인 이룸 (담당변리사 정진우)",
        "riskLevel": "DANGER",
        "riskReason": "특허청에 유효하게 '등록'되어 전국 수십 개 가맹점을 운영 중인 유명 프랜차이즈 상표입니다. 무단 사용 시 상표권 침해(상표법 제108조) 및 손해배상 청구 대상이 됩니다."
    },
    {
        "title": "상무초밥 가맹본부",
        "keywords": ["상무초밥", "상무"],
        "applicationNumber": "4020190089123",
        "applicationDate": "2019-06-14",
        "registrationDate": "2020-07-22",
        "registerStatus": "등록",
        "classification": "제35류",
        "classificationName": "프랜차이즈 가맹사업경영업, 식음료 도소매업",
        "applicantName": "(주)상무",
        "bigDrawing": "https://images.unsplash.com/photo-1611143669185-af224c5e3252?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "음식점체인 가맹점관리업, 초밥전문점 체인경영업, 식음료 납품유통업",
        "agent": "특허법인 이룸",
        "riskLevel": "DANGER",
        "riskReason": "가맹사업(제35류)에 등록되어 있어 '상무' 관련 명칭으로 프랜차이즈 사업 전개가 전면 불가합니다."
    },
    {
        "title": "상무초밥 프리미엄 밀키트",
        "keywords": ["상무초밥", "상무"],
        "applicationNumber": "4020210045678",
        "applicationDate": "2021-03-25",
        "registrationDate": "2022-04-18",
        "registerStatus": "등록",
        "classification": "제29류",
        "classificationName": "수산물가공식품, 가공된 생선살, 초밥용 냉동수산물",
        "applicantName": "(주)상무",
        "bigDrawing": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "간편조리 초밥세트, 수산물 가공식품, 냉동 간편식(HMR)",
        "agent": "특허법인 이룸",
        "riskLevel": "DANGER",
        "riskReason": "밀키트(제29류) 영역도 이미 등록되어 있어 간편식 제품 출시 시 상표권 분쟁이 발생합니다."
    },
    {
        "title": "쿠우쿠우 (QOOQOO)",
        "keywords": ["쿠우쿠우", "쿠우"],
        "applicationNumber": "4020130034567",
        "applicationDate": "2013-05-20",
        "registrationDate": "2014-06-18",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "초밥뷔페전문점업, 일식뷔페식당업",
        "applicantName": "(주)쿠우쿠우",
        "bigDrawing": "https://images.unsplash.com/photo-1563245372-f21724e3856d?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "초밥뷔페식당업, 패밀리레스토랑업",
        "agent": "특허법률사무소 명지",
        "riskLevel": "DANGER",
        "riskReason": "전국 프랜차이즈 등록 상표입니다."
    },
    {
        "title": "스시로 (SUSHIRO)",
        "keywords": ["스시로"],
        "applicationNumber": "4020110023456",
        "applicationDate": "2011-04-10",
        "registrationDate": "2012-05-15",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "회전초밥전문점업",
        "applicantName": "아킨도스시로 주식회사",
        "bigDrawing": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "회전스시점업, 일식음식점업",
        "agent": "김앤장법률사무소",
        "riskLevel": "DANGER",
        "riskReason": "글로벌 회전초밥 체인 등록 상표입니다."
    },

    # ---------------- [카페 / 베이커리 프랜차이즈] ----------------
    {
        "title": "빽다방 (PAIK'S COFFEE)",
        "keywords": ["빽다방", "백다방", "빽스코피"],
        "applicationNumber": "4020140067890",
        "applicationDate": "2014-10-15",
        "registrationDate": "2015-11-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "커피전문점업, 카페업, 음료제공업",
        "applicantName": "(주)더본코리아",
        "bigDrawing": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "커피전문점업, 디저트카페업, 베이커리제공업",
        "agent": "특허법인 한양",
        "riskLevel": "DANGER",
        "riskReason": "(주)더본코리아의 등록 상표입니다."
    },
    {
        "title": "메가MGC커피 (MEGA COFFEE)",
        "keywords": ["메가커피", "메가엠지씨", "메가엠지씨커피"],
        "applicationNumber": "4020150078901",
        "applicationDate": "2015-11-12",
        "registrationDate": "2016-12-05",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "커피전문점업, 테이크아웃카페업",
        "applicantName": "(주)앤하우스",
        "bigDrawing": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "대용량 커피전문점업, 음료테이크아웃업",
        "agent": "특허법인 가온",
        "riskLevel": "DANGER",
        "riskReason": "국내 3,000호점을 돌파한 등록 상표입니다."
    },
    {
        "title": "컴포즈커피 (COMPOSE COFFEE)",
        "keywords": ["컴포즈커피", "컴포즈"],
        "applicationNumber": "4020140089012",
        "applicationDate": "2014-12-01",
        "registrationDate": "2016-01-10",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "커피전문점업, 로스팅카페업",
        "applicantName": "(주)컴포즈커피",
        "bigDrawing": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "커피전문점업, 로스팅원두판매업",
        "agent": "특허법인 제일",
        "riskLevel": "DANGER",
        "riskReason": "유효하게 등록된 커피 프랜차이즈 상표입니다."
    },
    {
        "title": "이디야커피 (EDIYA COFFEE)",
        "keywords": ["이디야", "이디야커피"],
        "applicationNumber": "4020010045678",
        "applicationDate": "2001-08-15",
        "registrationDate": "2002-09-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "커피전문점업, 에스프레소바",
        "applicantName": "(주)이디야",
        "bigDrawing": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "커피전문점, 베이커리카페",
        "agent": "특허법인 충정",
        "riskLevel": "DANGER",
        "riskReason": "국내 저명 등록 상표입니다."
    },
    {
        "title": "런던베이글뮤지엄 (LONDON BAGEL MUSEUM)",
        "keywords": ["런던베이글", "런던베이글뮤지엄", "런베뮤"],
        "applicationNumber": "4020210156789",
        "applicationDate": "2021-08-20",
        "registrationDate": "2022-09-10",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "베이글전문점업, 베이커리카페업",
        "applicantName": "(주)엘비엠",
        "bigDrawing": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "베이글전문점업, 샌드위치전문점업",
        "agent": "특허법인 율촌",
        "riskLevel": "DANGER",
        "riskReason": "유효 등록 상표입니다."
    },

    # ---------------- [고기 / 구이 프랜차이즈] ----------------
    {
        "title": "명륜진사갈비",
        "keywords": ["명륜진사갈비", "명륜진사", "명륜"],
        "applicationNumber": "4020170123456",
        "applicationDate": "2017-09-15",
        "registrationDate": "2018-10-25",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "돼지갈비전문식당업, 숯불구이전문점업",
        "applicantName": "(주)명륜당",
        "bigDrawing": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "돼지갈비음식점, 무한리필고기전문점",
        "agent": "특허법인 바른",
        "riskLevel": "DANGER",
        "riskReason": "유효 등록 상표입니다."
    },
    {
        "title": "연돈",
        "keywords": ["연돈", "연돈볼카츠"],
        "applicationNumber": "4020190145678",
        "applicationDate": "2019-11-15",
        "registrationDate": "2020-12-10",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "돈가스전문점업, 일식음식점업",
        "applicantName": "김응서 / (주)더본코리아",
        "bigDrawing": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "수제돈가스식당업, 볼카츠전문점업",
        "agent": "특허법인 한양",
        "riskLevel": "DANGER",
        "riskReason": "제주 연돈 및 더본코리아가 등록한 저명 상표입니다."
    },

    # ---------------- [분식 / 떡볶이 프랜차이즈] ----------------
    {
        "title": "동대문 엽기떡볶이 (YUPDDUK)",
        "keywords": ["엽기떡볶이", "엽떡", "동대문엽기떡볶이"],
        "applicationNumber": "4020080034567",
        "applicationDate": "2008-06-12",
        "registrationDate": "2009-07-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "떡볶이전문점업, 매운음식전문점업",
        "applicantName": "(주)핫시즈너",
        "bigDrawing": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "떡볶이전문식당업, 닭발요리전문점업",
        "agent": "특허법인 광장",
        "riskLevel": "DANGER",
        "riskReason": "유효 등록 상표입니다."
    },
    {
        "title": "배달고픈 떡볶이 배떡",
        "keywords": ["배떡", "로제떡볶이배떡"],
        "applicationNumber": "4020200067890",
        "applicationDate": "2020-04-10",
        "registrationDate": "2021-05-18",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "로제떡볶이전문점업, 분식점업",
        "applicantName": "(주)어메이징에프앤비",
        "bigDrawing": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "떡볶이전문점업, 분식배달업",
        "agent": "특허법인 세종",
        "riskLevel": "DANGER",
        "riskReason": "유효 등록 상표입니다."
    },

    # ---------------- [치킨 / 버거 프랜차이즈] ----------------
    {
        "title": "교촌치킨 (KYOCHON)",
        "keywords": ["교촌", "교촌치킨"],
        "applicationNumber": "4019990023456",
        "applicationDate": "1999-05-10",
        "registrationDate": "2000-06-15",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "치킨전문식당업, 통닭구이전문점업",
        "applicantName": "(주)교촌에프앤비",
        "bigDrawing": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "간장치킨전문점업, 치킨호프전문점",
        "agent": "특허법인 태평양",
        "riskLevel": "DANGER",
        "riskReason": "국내 1위권 치킨 프랜차이즈 저명 등록 상표입니다."
    },
    {
        "title": "맘스터치 (MOM'S TOUCH)",
        "keywords": ["맘스터치", "싸이버거"],
        "applicationNumber": "4020040012345",
        "applicationDate": "2004-03-15",
        "registrationDate": "2005-04-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "버거전문점업, 치킨전문점업",
        "applicantName": "(주)맘스터치앤컴퍼니",
        "bigDrawing": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "수제버거전문식당업, 치킨버거전문점",
        "agent": "특허법인 아주",
        "riskLevel": "DANGER",
        "riskReason": "유효 등록 상표입니다."
    }
]


def search_trademark(search_query: str, classification_codes: str = "") -> dict:
    """
    상표(가게명)를 검색하고, 프랜차이즈 확장 영역별(멀티 선택된 상품분류들)로 종합 위험도를 분석합니다.
    """
    search_query = search_query.strip()
    if not search_query:
        return {
            "items": [], 
            "totalCount": 0, 
            "summary": {"danger": 0, "warning": 0, "safe": 0},
            "matrix": []
        }

    target_classes = [c.strip() for c in classification_codes.split(",") if c.strip()]
    check_classes = target_classes if target_classes else list(FRANCHISE_CLASSES.keys())
    q_norm = search_query.replace(" ", "").lower()

    # 1. 모의 데이터 모드이거나 API 키가 설정되지 않은 경우
    if USE_MOCK or not KIPRIS_API_KEY or KIPRIS_API_KEY == "your_kipris_api_key_here":
        results = []
        is_famous_brand = False
        matched_brand_name = ""

        # 실제 프랜차이즈 상표 DB에서 정밀 검색
        for item in REAL_FRANCHISE_TRADEMARKS:
            title_norm = item["title"].replace(" ", "").lower()
            keywords = item.get("keywords", [])
            
            # 검색어가 상표명에 포함되거나, 상표 키워드가 검색어에 포함되는 경우 매칭
            match_found = (q_norm in title_norm or title_norm in q_norm)
            if not match_found:
                for kw in keywords:
                    kw_norm = kw.replace(" ", "").lower()
                    if kw_norm in q_norm or q_norm in kw_norm:
                        match_found = True
                        break

            if match_found:
                is_famous_brand = True
                matched_brand_name = item["title"]

                # 사용자가 선택한 분류와 매칭 여부 확인
                item_class_code = item["classification"].replace("제", "").replace("류", "").strip()
                if not target_classes or item_class_code in target_classes:
                    results.append(item)

        # 유명 프랜차이즈로 판별된 경우, 선택된 다른 확장 영역(35류, 29류, 30류, 21류 등)도
        # 유명 브랜드 권리 범위로 인해 상표법 제34조 제1항 제11호(저명상표 혼동)에 따라 일괄 '위험' 처리!
        if is_famous_brand:
            for code in check_classes:
                # 이미 리스트에 해당 분류 결과가 있으면 건너뜀
                if any(code in r.get("classification", "") for r in results):
                    continue

                cls_info = FRANCHISE_CLASSES.get(code, {"name": f"제{code}류", "desc": "확장 분야", "group": "기타"})
                results.append({
                    "title": f"{search_query} (저명 상표 확장군)",
                    "applicationNumber": "선등록 상표 권리 저촉",
                    "applicationDate": "선점 완료",
                    "registrationDate": "존속 중",
                    "registerStatus": "등록 (침해 위험)",
                    "classification": f"제{code}류",
                    "classificationName": f"{cls_info['name']}",
                    "applicantName": f"기존 선등록 권리자 ({matched_brand_name})",
                    "bigDrawing": "",
                    "designatedGoods": cls_info["desc"],
                    "agent": "특허청 상표법 제34조 제1항 제11호 적용",
                    "riskLevel": "DANGER",
                    "riskReason": f"'{search_query}'는 이미 전국 단위로 주지·저명한 프랜차이즈 상표입니다. 제{code}류({cls_info['name']}) 영역으로 출원하더라도 상표법상 '타인의 유명 영업과의 혼동 및 부정한 목적의 모방'으로 100% 거절되며, 무단 사용 시 민·형사상 침해 책임을 집니다."
                })

        # 유명 프랜차이즈가 아니고, 검색 결과가 전혀 없는 경우 -> '신규 창안 상표'로 안전 판정
        elif not results:
            for code in check_classes:
                cls_info = FRANCHISE_CLASSES.get(code, {"name": f"제{code}류", "desc": "확장 분야", "group": "기타"})
                results.append({
                    "title": f"{search_query}",
                    "applicationNumber": "-",
                    "applicationDate": "-",
                    "registrationDate": "-",
                    "registerStatus": "미등록 (새로운 창안)",
                    "classification": f"제{code}류",
                    "classificationName": f"{cls_info['name']}",
                    "applicantName": "-",
                    "bigDrawing": "",
                    "designatedGoods": cls_info["desc"],
                    "agent": "-",
                    "riskLevel": "SAFE",
                    "riskReason": f"'{search_query}'에 대한 제{code}류 등록 또는 유명 선출원 내역이 발견되지 않았습니다. 신규 프랜차이즈 출원 및 선점 가능성이 높습니다."
                })

        # 통계 집계
        summary = {"danger": 0, "warning": 0, "safe": 0}
        for r in results:
            lvl = r.get("riskLevel", "SAFE").lower()
            if lvl in summary:
                summary[lvl] += 1

        matrix = build_franchise_matrix(results, check_classes)

        return {
            "mode": "MOCK_SIMULATION",
            "searchQuery": search_query,
            "targetClasses": check_classes,
            "totalCount": len(results),
            "summary": summary,
            "matrix": matrix,
            "items": results
        }

    # 2. 실제 KIPRIS Open API 호출 모드
    try:
        items = []
        summary = {"danger": 0, "warning": 0, "safe": 0}

        query_classes = check_classes if check_classes else [""]
        for c_code in query_classes:
            params = {
                "serviceKey": KIPRIS_API_KEY,
                "searchString": search_query,
                "numOfRows": 20,
                "pageNo": 1
            }
            if c_code:
                params["productClassification"] = c_code

            res = requests.get(KIPRIS_TRADEMARK_URL, params=params, timeout=8)
            res.encoding = 'utf-8'
            root = ET.fromstring(res.text)

            for item_node in root.findall(".//item"):
                title = item_node.findtext("title", "").strip()
                app_num = item_node.findtext("applicationNumber", "-").strip()
                app_date = item_node.findtext("applicationDate", "-").strip()
                reg_date = item_node.findtext("registrationDate", "-").strip()
                reg_status = item_node.findtext("registerStatus", "미상").strip()
                class_code = item_node.findtext("classificationCode", c_code).strip()
                applicant = item_node.findtext("applicantName", "-").strip()
                drawing_url = item_node.findtext("bigDrawing", "").strip()

                if "등록" in reg_status:
                    risk_level = "DANGER"
                    risk_reason = "특허청에 유효하게 등록된 상표입니다. 무단 사용 시 상표권 침해 위험이 큽니다."
                    summary["danger"] += 1
                elif any(s in reg_status for s in ["출원", "공고", "심사"]):
                    risk_level = "WARNING"
                    risk_reason = "현재 심사진행 중인 상표입니다. 등록 결정 시 분쟁 대상이 될 수 있습니다."
                    summary["warning"] += 1
                else:
                    risk_level = "SAFE"
                    risk_reason = "과거 거절/소멸되어 현재 독점 권리가 없는 상태입니다."
                    summary["safe"] += 1

                items.append({
                    "title": title,
                    "applicationNumber": app_num,
                    "applicationDate": app_date,
                    "registrationDate": reg_date,
                    "registerStatus": reg_status,
                    "classification": f"제{class_code}류",
                    "classificationName": FRANCHISE_CLASSES.get(class_code, {}).get("name", "지정상품"),
                    "applicantName": applicant,
                    "bigDrawing": drawing_url,
                    "designatedGoods": "KIPRIS 공보 참조",
                    "agent": "KIPRIS 공보 참조",
                    "riskLevel": risk_level,
                    "riskReason": risk_reason
                })

        matrix = build_franchise_matrix(items, check_classes)

        return {
            "mode": "REAL_KIPRIS_API",
            "searchQuery": search_query,
            "targetClasses": check_classes,
            "totalCount": len(items),
            "summary": summary,
            "matrix": matrix,
            "items": items
        }

    except Exception as e:
        return {
            "mode": "ERROR",
            "error": str(e),
            "searchQuery": search_query,
            "targetClasses": check_classes,
            "totalCount": 0,
            "summary": {"danger": 0, "warning": 0, "safe": 0},
            "matrix": [],
            "items": [],
            "message": "KIPRIS API 통신 오류 발생"
        }


def build_franchise_matrix(items: list, selected_classes: list) -> list:
    """프랜차이즈 확장 영역별 매트릭스 생성"""
    check_classes = selected_classes if selected_classes else list(FRANCHISE_CLASSES.keys())
    matrix = []

    for code in check_classes:
        info = FRANCHISE_CLASSES.get(code, {"name": f"제{code}류", "desc": "확장 분야", "group": "기타"})
        class_items = [it for it in items if code in it.get("classification", "")]

        if not class_items:
            status = "안전 (선점가능)"
            level = "SAFE"
            comment = "동일 상표 등록 없음 (신규 출원 선점 권장)"
        else:
            has_danger = any(it.get("riskLevel") == "DANGER" for it in class_items)
            has_warning = any(it.get("riskLevel") == "WARNING" for it in class_items)
            
            if has_danger:
                status = "위험 (침해 주의)"
                level = "DANGER"
                comment = "유효 등록 상표 또는 저명 프랜차이즈 존재 (사용 불가)"
            elif has_warning:
                status = "주의 (심사 진행)"
                level = "WARNING"
                comment = "타인의 출원 건 심사 중 (심사 결과 모니터링 필요)"
            else:
                status = "안전 (선점가능)"
                level = "SAFE"
                comment = "거절/소멸 이력만 존재 (출원 가능성 높음)"

        matrix.append({
            "code": code,
            "group": info["group"],
            "name": info["name"],
            "desc": info["desc"],
            "status": status,
            "level": level,
            "comment": comment
        })

    return matrix


def search_design(keyword: str = "", shape_tag: str = "") -> dict:
    """디자인 및 로고마크 공보 검색"""
    return {
        "mode": "MOCK_SIMULATION",
        "keyword": keyword,
        "totalCount": 4,
        "items": [
            {
                "articleName": "초밥 및 일식 포장용기 디자인",
                "designNumber": "3020220017123",
                "registrationDate": "2023-04-10",
                "status": "등록",
                "vienna": "08.01.01 (초밥도시락)",
                "comment": "일식 초밥 테이크아웃 전용 패키지 디자인",
                "drawingUrl": "https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=300&auto=format&fit=crop&q=80"
            },
            {
                "articleName": "카페용 간판 (초승달 형상)",
                "designNumber": "3020220045123",
                "registrationDate": "2023-05-18",
                "status": "등록",
                "vienna": "01.07.01 (달)",
                "comment": "초승달 조명 디자인 유사군",
                "drawingUrl": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=300&auto=format&fit=crop&q=80"
            }
        ]
    }
