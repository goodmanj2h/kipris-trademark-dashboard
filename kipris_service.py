# -*- coding: utf-8 -*-
"""
KIPRIS 지식재산정보 연동 서비스 모듈 (kipris_service.py)
----------------------------------------------------------------------
이 모듈은 특허청/공공데이터포털의 KIPRIS Open API(상표 및 디자인 정보)와 통신하거나,
프랜차이즈 창업(밀키트, 소스, 굿즈 확장)에 특화된 다중 업종 복합 검증 모의 데이터를 반환합니다.

[주요 기능]
1. search_trademark: 복수 상품분류(NICE 분류) 멀티 선택 지원 상표 검색 및 확장성 진단
2. search_design: 로고마크 및 간판 디자인(디자인권) 검색
3. get_vienna_recommendations: 로고 키워드 기반 비엔나 도형코드 자동 추천
"""

import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import KIPRIS_API_KEY, USE_MOCK, KIPRIS_TRADEMARK_URL, KIPRIS_DESIGN_URL

# ====================================================================
# [프랜차이즈 확장 분류 표준 사전]
# 외식 창업부터 밀키트, 소스, 굿즈까지의 NICE 상품분류 정보
# ====================================================================
FRANCHISE_CLASSES = {
    "43": {"name": "외식·카페 매장", "desc": "음식점업, 카페업, 제과점업, 주점업 (프랜차이즈 본점/가맹점 매장 운영)", "group": "기본 매장"},
    "35": {"name": "가맹사업·유통·쇼핑몰", "desc": "프랜차이즈 가맹관리업, 식음료 도소매업, 온라인 쇼핑몰 운영", "group": "프랜차이즈 유통"},
    "29": {"name": "밀키트·육류가공식품", "desc": "육류, 가공식품, 냉동 간편조리식품, HMR 밀키트, 국/찌개류", "group": "간편식·밀키트"},
    "30": {"name": "소스·양념·원두·제과", "desc": "비법 소스류, 시즈닝, 복합조미료, 양념장, 커피원두, 빵/과자", "group": "소스·양념"},
    "21": {"name": "굿즈 (텀블러·식기류)", "desc": "브랜드 텀블러, 머그컵, 글라스잔, 조리용 식기, 주방용기", "group": "브랜드 굿즈"},
    "25": {"name": "굿즈 (의류·앞치마·유니폼)", "desc": "직원 유니폼, 앞치마, 티셔츠, 모자, 에이프런", "group": "브랜드 굿즈"},
    "16": {"name": "굿즈 (포장용기·문구·스티커)", "desc": "배달 포장용 종이박스, 포장백, 로고 스티커, 브랜드 다이어리/볼펜", "group": "브랜드 굿즈"},
    "18": {"name": "굿즈 (에코백·가방·파우치)", "desc": "브랜드 에코백, 캔버스 가방, 보냉백, 파우치", "group": "브랜드 굿즈"},
    "32": {"name": "완제음료·생수·주스", "desc": "RTD 캔/보틀 완제음료, 과일주스, 탄산음료, 생수", "group": "음료·패키지"}
}

# ====================================================================
# [교육용 샘플] 프랜차이즈 확장 영역까지 포괄하는 모의(Mock) 상표 데이터
# ====================================================================
SAMPLE_TRADEMARKS = [
    # 1. 외식업 (제43류)
    {
        "title": "달빛카페 (MOONLIGHT CAFE)",
        "applicationNumber": "4020220194821",
        "applicationDate": "2022-09-15",
        "registrationDate": "2023-11-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "음식점업, 카페업, 제과점업",
        "applicantName": "(주)달빛에프앤비",
        "bigDrawing": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "커피전문점업, 디저트카페업, 테이크아웃커피점업, 제과점업",
        "agent": "특허법인 한빛",
        "riskLevel": "DANGER",
        "riskReason": "동일 업종(제43류)에 이미 '등록'되어 있어 매장 간판 사용 시 상표권 침해 위험이 큽니다."
    },
    # 2. 가맹사업 및 유통 (제35류)
    {
        "title": "달빛프랜차이즈",
        "applicationNumber": "4020230045678",
        "applicationDate": "2023-03-20",
        "registrationDate": "2024-04-15",
        "registerStatus": "등록",
        "classification": "제35류",
        "classificationName": "프랜차이즈 가맹사업경영업, 식음료 도소매업",
        "applicantName": "(주)달빛에프앤비",
        "bigDrawing": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "프랜차이즈 가맹사업경영업, 식음료 체인점 운영업, 가맹점 지원업",
        "agent": "특허법인 한빛",
        "riskLevel": "DANGER",
        "riskReason": "가맹사업 및 유통(제35류)에 이미 등록되어 프랜차이즈 본사 설립 시 상표권 충돌이 발생합니다."
    },
    # 3. 소스 및 양념 (제30류) - 출원 심사진행 중 예시
    {
        "title": "달빛베이커리 소스",
        "applicationNumber": "4020230081234",
        "applicationDate": "2023-04-10",
        "registrationDate": "-",
        "registerStatus": "출원",
        "classification": "제30류",
        "classificationName": "소스류, 시즈닝, 제과",
        "applicantName": "홍길동 (개인사업자)",
        "bigDrawing": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "복합조미료, 디저트용 시럽, 빵용 소스, 케이크, 식빵",
        "agent": "본인 직접 출원",
        "riskLevel": "WARNING",
        "riskReason": "소스/제과(제30류)에 출원 심사진행 중입니다. 등록 결정 시 소스 납품 시비가 생길 수 있습니다."
    },
    # 4. 밀키트 및 간편조리식품 (제29류) - 거절된 예시 (안전)
    {
        "title": "달빛간편식 밀키트",
        "applicationNumber": "4020190012984",
        "applicationDate": "2019-01-22",
        "registrationDate": "-",
        "registerStatus": "거절",
        "classification": "제29류",
        "classificationName": "간편조리식품, 냉동 가공육, 국/탕류",
        "applicantName": "김철수",
        "bigDrawing": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "밀키트(간편조리세트), 조리된 국류, 가공된 육류",
        "agent": "대리인 없음",
        "riskLevel": "SAFE",
        "riskReason": "과거 거절되어 현재 독점 권리자가 없습니다. 밀키트 분야로 신규 출원 선점 가능성이 높습니다!"
    },
    # 5. 브랜드 굿즈 텀블러/머그잔 (제21류) - 등록된 상표 예시
    {
        "title": "달빛글라스 (MOONLIGHT)",
        "applicationNumber": "4020200054321",
        "applicationDate": "2020-05-18",
        "registrationDate": "2021-08-30",
        "registerStatus": "등록",
        "classification": "제21류",
        "classificationName": "텀블러, 머그컵, 유리식기류",
        "applicantName": "(주)문라이트키친",
        "bigDrawing": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "휴대용 텀블러, 커피 머그잔, 유리컵, 세라믹 식기",
        "agent": "특허법인 세종",
        "riskLevel": "DANGER",
        "riskReason": "굿즈(제21류) 텀블러/머그잔에 이미 타사가 등록을 마쳤습니다. 매장 굿즈 출시 시 주의해야 합니다."
    },
    # 6. 브랜드 굿즈 의류/앞치마 (제25류) - 미등록/안전 예시
    {
        "title": "골든스타 로스팅",
        "applicationNumber": "4020180054321",
        "applicationDate": "2018-05-18",
        "registrationDate": "2019-08-30",
        "registerStatus": "소멸",
        "classification": "제43류",
        "classificationName": "커피전문점업",
        "applicantName": "(주)골든글로벌",
        "bigDrawing": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=300&auto=format&fit=crop&q=80",
        "designatedGoods": "원두커피전문점",
        "agent": "태평양특허법률사무소",
        "riskLevel": "SAFE",
        "riskReason": "과거 등록되었으나 권리가 소멸되었습니다."
    }
]

# 디자인 샘플
SAMPLE_DESIGNS = [
    {
        "articleName": "카페용 간판 (초승달 형상)",
        "designNumber": "3020220045123",
        "registrationDate": "2023-05-18",
        "applicantName": "(주)문라이트디자인",
        "drawingUrl": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=300&auto=format&fit=crop&q=80",
        "category": "제20류 (간판 및 옥외광고물)",
        "status": "등록",
        "vienna": "01.07.01 (달)",
        "comment": "초승달 조명 디자인 유사군"
    },
    {
        "articleName": "밀키트 패키지용 포장 박스 디자인",
        "designNumber": "3020230055112",
        "registrationDate": "2024-01-10",
        "applicantName": "(주)신선키트",
        "drawingUrl": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=300&auto=format&fit=crop&q=80",
        "category": "제09류 (식품 포장 상자)",
        "status": "등록",
        "vienna": "08.01.01 (식품용기)",
        "comment": "간편조리 밀키트 냉장 패키지 디자인 공보"
    },
    {
        "articleName": "시그니처 비법 소스 보틀 용기 디자인",
        "designNumber": "3020220098456",
        "registrationDate": "2023-06-25",
        "applicantName": "(주)맛있는소스",
        "drawingUrl": "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=300&auto=format&fit=crop&q=80",
        "category": "제09류 (유리병/소스용기)",
        "status": "등록",
        "vienna": "19.04.01 (병/용기)",
        "comment": "프랜차이즈 납품용 소스 병 디자인"
    },
    {
        "articleName": "브랜드 굿즈 보온 텀블러 디자인",
        "designNumber": "3020210089456",
        "registrationDate": "2022-03-10",
        "applicantName": "(주)스타빈스코리아",
        "drawingUrl": "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=300&auto=format&fit=crop&q=80",
        "category": "제07류 (휴대용 보온병)",
        "status": "등록",
        "vienna": "11.01.01 (커피잔)",
        "comment": "매장 판매용 로고 각인 텀블러"
    }
]


def search_trademark(search_query: str, classification_codes: str = "") -> dict:
    """
    상표(가게명)를 검색하고, 프랜차이즈 확장 영역별(멀티 선택된 상품분류들)로 종합 위험도를 분석합니다.

    :param search_query: 사용자가 입력한 검색 가게명 (예: '달빛카페')
    :param classification_codes: 콤마로 구분된 복수 상품분류 코드 (예: '43,35,29,30,21')
    :return: 종합 결과, 분류별 매트릭스 분석표, 위험도 통계
    """
    search_query = search_query.strip()
    if not search_query:
        return {
            "items": [], 
            "totalCount": 0, 
            "summary": {"danger": 0, "warning": 0, "safe": 0},
            "matrix": []
        }

    # 선택된 분류 리스트화 (빈 문자열이면 전체)
    target_classes = [c.strip() for c in classification_codes.split(",") if c.strip()]

    # 1. 모의 데이터 모드이거나 API 키가 설정되지 않은 경우
    if USE_MOCK or not KIPRIS_API_KEY or KIPRIS_API_KEY == "your_kipris_api_key_here":
        results = []
        query_lower = search_query.lower()

        # 샘플 중에서 검색어가 일치하거나 유사한 항목 추출
        for item in SAMPLE_TRADEMARKS:
            title_match = (query_lower in item["title"].lower())
            
            # 분류 필터: target_classes가 지정된 경우 해당 분류 중 하나라도 매칭되면 포함
            class_match = True
            if target_classes:
                class_match = any(f"제{code}류" in item["classification"] or code in item["classification"] for code in target_classes)

            if title_match and class_match:
                results.append(item)

        # 사용자가 선택한 확장 분류군 중 샘플에 없는 분류에 대해 신규 출원 가능 여부(안전) 항목 생성
        if target_classes:
            for code in target_classes:
                has_item_in_class = any(code in r.get("classification", "") for r in results)
                if not has_item_in_class:
                    cls_info = FRANCHISE_CLASSES.get(code, {"name": f"제{code}류", "desc": "확장 분야", "group": "기타"})
                    results.append({
                        "title": f"{search_query}",
                        "applicationNumber": "-",
                        "applicationDate": "-",
                        "registrationDate": "-",
                        "registerStatus": "미등록 (새로운 영역)",
                        "classification": f"제{code}류",
                        "classificationName": f"{cls_info['name']} ({cls_info['desc']})",
                        "applicantName": "-",
                        "bigDrawing": "",
                        "designatedGoods": cls_info["desc"],
                        "agent": "-",
                        "riskLevel": "SAFE",
                        "riskReason": f"'{search_query}'에 대한 제{code}류({cls_info['name']}) 등록 내역이 없습니다. 신규 출원 및 프랜차이즈 독점 권리 확보가 매우 유망합니다!"
                    })

        # 고정 샘플에도 없고 선택 분류도 없을 때 기본 신규 항목 생성
        if not results:
            results.append({
                "title": f"{search_query}",
                "applicationNumber": "-",
                "applicationDate": "-",
                "registrationDate": "-",
                "registerStatus": "미등록 (새로운 이름)",
                "classification": "전체 분류",
                "classificationName": "신규 프랜차이즈 출원 가능 대상",
                "applicantName": "-",
                "bigDrawing": "",
                "designatedGoods": "외식업 및 프랜차이즈 굿즈/밀키트 전 영역",
                "agent": "-",
                "riskLevel": "SAFE",
                "riskReason": f"'{search_query}'에 대한 등록 내역이 전혀 발견되지 않았습니다. 프랜차이즈 본사 및 가맹사업 출원을 적극 권장합니다!"
            })

        # 통계 집계
        summary = {"danger": 0, "warning": 0, "safe": 0}
        for r in results:
            level = r.get("riskLevel", "SAFE").lower()
            if level in summary:
                summary[level] += 1

        # 프랜차이즈 확장 매트릭스(Matrix) 생성
        matrix = build_franchise_matrix(results, target_classes)

        return {
            "mode": "MOCK_SIMULATION",
            "searchQuery": search_query,
            "targetClasses": target_classes,
            "totalCount": len(results),
            "summary": summary,
            "matrix": matrix,
            "items": results
        }

    # 2. 실제 KIPRIS Open API 호출 모드
    try:
        items = []
        summary = {"danger": 0, "warning": 0, "safe": 0}

        # KIPRIS API는 분류별로 각각 질의하거나 대표 질의 수행
        query_classes = target_classes if target_classes else [""]
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
                    risk_reason = "유효하게 등록된 상표입니다. 무단 사용 시 상표권 침해 위험이 큽니다."
                    summary["danger"] += 1
                elif any(s in reg_status for s in ["출원", "공고", "심사"]):
                    risk_level = "WARNING"
                    risk_reason = "심사진행 중인 상표입니다. 등록 결정 시 분쟁 대상이 될 수 있습니다."
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

        matrix = build_franchise_matrix(items, target_classes)

        return {
            "mode": "REAL_KIPRIS_API",
            "searchQuery": search_query,
            "targetClasses": target_classes,
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
            "targetClasses": target_classes,
            "totalCount": 0,
            "summary": {"danger": 0, "warning": 0, "safe": 0},
            "matrix": [],
            "items": [],
            "message": "KIPRIS API 통신 오류 발생"
        }


def build_franchise_matrix(items: list, selected_classes: list) -> list:
    """
    각 프랜차이즈 확장 영역(분류)별로 가장 위험한 상표 상태를 종합 판별하여
    '확장 가능 여부(신호등)' 매트릭스를 생성합니다.
    """
    check_classes = selected_classes if selected_classes else list(FRANCHISE_CLASSES.keys())
    matrix = []

    for code in check_classes:
        info = FRANCHISE_CLASSES.get(code, {"name": f"제{code}류", "desc": "확장 분야", "group": "기타"})
        
        # 해당 분류에 속한 아이템들 추출
        class_items = [it for it in items if code in it.get("classification", "")]

        if not class_items:
            status = "안전"
            level = "SAFE"
            comment = "동일 상표 등록 없음 (신규 출원 선점 권장)"
        else:
            has_danger = any(it.get("riskLevel") == "DANGER" for it in class_items)
            has_warning = any(it.get("riskLevel") == "WARNING" for it in class_items)
            
            if has_danger:
                status = "위험 (침해 주의)"
                level = "DANGER"
                comment = "동일/유사 등록 상표 존재 (이 영역 단독 브랜드명 변경 필요)"
            elif has_warning:
                status = "주의 (심사 진행 중)"
                level = "WARNING"
                comment = "타인의 출원 건 심사 중 (심사 결과 모니터링 필요)"
            else:
                status = "안전 (출원 가능)"
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
    keyword = (keyword or "").strip().lower()
    shape_tag = (shape_tag or "").strip().lower()

    results = []
    for d in SAMPLE_DESIGNS:
        match = True
        if keyword and not (keyword in d["articleName"].lower() or keyword in d["category"].lower()):
            match = False
        if match:
            results.append(d)

    return {
        "mode": "MOCK_SIMULATION",
        "keyword": keyword,
        "totalCount": len(results) if results else len(SAMPLE_DESIGNS),
        "items": results if results else SAMPLE_DESIGNS
    }
