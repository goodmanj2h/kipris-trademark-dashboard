# -*- coding: utf-8 -*-
"""
KIPRIS 지식재산정보 연동 서비스 모듈 (kipris_service.py)
----------------------------------------------------------------------
이 모듈은 특허청/공공데이터포털의 KIPRIS Open API(상표 및 디자인 정보)와 통신하거나,
초보자 교육 및 테스트를 위한 모의(Mock) 데이터를 생성하여 반환합니다.

[주요 기능]
1. search_trademark: 가게명(문자상표) 검색 및 위험도 판별
2. search_design: 로고마크 및 간판 디자인(디자인권) 검색
3. get_vienna_recommendations: 로고 키워드 기반 비엔나 도형코드 자동 추천
"""

import urllib.parse
import xml.etree.ElementTree as ET
import requests
from config import KIPRIS_API_KEY, USE_MOCK, KIPRIS_TRADEMARK_URL, KIPRIS_DESIGN_URL

# ====================================================================
# [비엔나 도형분류 사전]
# 로고 이미지의 형상 특징(동물, 별, 달, 커피 등)을 특허청 비엔나 코드로 매핑
# ====================================================================
VIENNA_CATEGORY_MAP = {
    "달": {"code": "01.07.01", "name": "초승달, 반달, 달의 형상", "description": "달 모양을 형상화한 로고 및 심볼마크"},
    "별": {"code": "01.01.01", "name": "별, 항성, 광채", "description": "다각별 및 반짝이는 별빛 형태의 도형"},
    "태양": {"code": "01.03.01", "name": "태양, 일출", "description": "해, 햇살, 태양을 모티브로 한 로고"},
    "커피": {"code": "11.01.01", "name": "찻잔, 커피잔, 머그잔", "description": "따뜻한 음료 또는 증기가 피어오르는 컵 형상"},
    "빵": {"code": "08.01.01", "name": "식빵, 바게트, 크루아상, 제과류", "description": "베이커리 및 디저트 형상"},
    "나무": {"code": "05.01.01", "name": "나무, 숲, 가지", "description": "자연주의, 친환경을 상징하는 나무 형상"},
    "꽃": {"code": "05.05.01", "name": "꽃, 꽃잎, 부케", "description": "꽃이나 식물의 꽃잎을 모티브로 한 심볼"},
    "왕관": {"code": "24.09.01", "name": "왕관, 티아라", "description": "권위, 프리미엄을 상징하는 왕관 모양"},
    "고양이": {"code": "03.01.08", "name": "고양이, 고양이과 동물", "description": "귀여운 고양이 및 반려묘 캐릭터"},
    "강아지": {"code": "03.01.09", "name": "개, 강아지, 늑대", "description": "반려견 및 친근한 강아지 심볼"},
    "물고기": {"code": "03.09.01", "name": "어류, 물고기, 수산물", "description": "수산물 및 바다 생물 모티브 형상"},
    "하트": {"code": "02.09.01", "name": "심장, 하트 모양", "description": "사랑, 호의를 표현하는 하트 심볼"},
    "원": {"code": "26.01.01", "name": "원, 동심원, 원반", "description": "안정감을 주는 원형 엠블럼 형태"},
    "삼각형": {"code": "26.03.01", "name": "삼각형, 피라미드", "description": "역동성과 전진을 상징하는 삼각 형상"}
}

# ====================================================================
# [교육용 샘플] 실감나는 모의(Mock) 상표 데이터베이스
# ====================================================================
SAMPLE_TRADEMARKS = [
    {
        "title": "달빛카페 (MOONLIGHT CAFE)",
        "applicationNumber": "4020220194821",
        "applicationDate": "2022-09-15",
        "registrationDate": "2023-11-20",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "음식점업, 카페업, 제과점업",
        "applicantName": "(주)달빛에프앤비",
        "bigDrawing": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "01.07.01",
        "viennaDescription": "초승달 또는 반달",
        "designatedGoods": "커피전문점업, 디저트카페업, 테이크아웃커피점업, 제과점업",
        "agent": "특허법인 한빛 (담당변리사 홍길동)",
        "riskLevel": "DANGER",
        "riskReason": "동일 업종(제43류)에 이미 '등록'되어 있어 동일/유사 상호 사용 시 상표권 침해 소송 위험이 매우 높습니다."
    },
    {
        "title": "달빛베이커리",
        "applicationNumber": "4020230081234",
        "applicationDate": "2023-04-10",
        "registrationDate": "-",
        "registerStatus": "출원",
        "classification": "제30류",
        "classificationName": "빵, 과자, 케이크, 제과",
        "applicantName": "홍길동 (개인사업자)",
        "bigDrawing": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "01.07.06",
        "viennaDescription": "달과 풍경",
        "designatedGoods": "단팥빵, 크루아상, 조각케이크, 쿠키, 식빵",
        "agent": "본인 직접 출원",
        "riskLevel": "WARNING",
        "riskReason": "현재 심사진행(출원) 중인 상표입니다. 등록 결정 시 향후 분쟁 소지가 있으니 주시해야 합니다."
    },
    {
        "title": "달빛식당",
        "applicationNumber": "4020190012984",
        "applicationDate": "2019-01-22",
        "registrationDate": "-",
        "registerStatus": "거절",
        "classification": "제43류",
        "classificationName": "일반한식점업",
        "applicantName": "김철수",
        "bigDrawing": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "",
        "viennaDescription": "문자만 존재",
        "designatedGoods": "한식점업, 백반전문점업",
        "agent": "대리인 없음",
        "riskLevel": "SAFE",
        "riskReason": "과거에 등록 거절된 이력이 있습니다. 독점 권리자가 존재하지 않으므로 사용 가능성이 비교적 높습니다."
    },
    {
        "title": "골든스타 로스팅 (GOLDEN STAR)",
        "applicationNumber": "4020180054321",
        "applicationDate": "2018-05-18",
        "registrationDate": "2019-08-30",
        "registerStatus": "소멸",
        "classification": "제43류",
        "classificationName": "커피전문점업",
        "applicantName": "(주)골든글로벌",
        "bigDrawing": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "01.01.01",
        "viennaDescription": "별, 항성",
        "designatedGoods": "원두커피전문점, 핸드드립전문점",
        "agent": "태평양특허법률사무소",
        "riskLevel": "SAFE",
        "riskReason": "과거 등록되었으나 갱신료 미납 등으로 권리가 소멸(말소)되었습니다. 현재 유효한 독점 권리는 없습니다."
    },
    {
        "title": "바다향기 횟집",
        "applicationNumber": "4020210034112",
        "applicationDate": "2021-03-05",
        "registrationDate": "2022-04-12",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "수산물요리전문점업",
        "applicantName": "이영희",
        "bigDrawing": "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "03.09.01",
        "viennaDescription": "어류, 물고기",
        "designatedGoods": "생선회전문식당업, 해산물요리전문점업",
        "agent": "특허법인 세종",
        "riskLevel": "DANGER",
        "riskReason": "동일 업종에 등록되어 권리자가 영업 중인 상표입니다."
    },
    {
        "title": "숲속의 오븐",
        "applicationNumber": "4020200155231",
        "applicationDate": "2020-10-12",
        "registrationDate": "2021-12-05",
        "registerStatus": "등록",
        "classification": "제43류",
        "classificationName": "디저트카페, 제과점업",
        "applicantName": "(주)그린테이블",
        "bigDrawing": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&auto=format&fit=crop&q=80",
        "viennaCode": "05.01.01",
        "viennaDescription": "나무, 숲",
        "designatedGoods": "유기농빵집업, 숲카페업",
        "agent": "정진특허법률사무소",
        "riskLevel": "DANGER",
        "riskReason": "유효하게 등록된 상표입니다."
    }
]

# ====================================================================
# [교육용 샘플] 등록 디자인 및 로고 공보 데이터베이스 (KIPRIS 디자인정보)
# ====================================================================
SAMPLE_DESIGNS = [
    {
        "articleName": "카페용 간판 (초승달 형상)",
        "designNumber": "3020220045123",
        "registrationDate": "2023-05-18",
        "applicantName": "(주)문라이트디자인",
        "drawingUrl": "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=400&auto=format&fit=crop&q=80",
        "category": "제20류 (간판 및 옥외광고물)",
        "shapeTags": ["달", "원", "네온사인"],
        "registerStatus": "등록",
        "similarityScore": "92%",
        "similarityLevel": "HIGH",
        "comment": "초승달 외곽선 및 조명 배치 디자인이 매우 유사합니다. 간판 제작 시 모방 시비 주의가 필요합니다."
    },
    {
        "articleName": "커피 테이크아웃 컵 표면 로고 디자인",
        "designNumber": "3020210089456",
        "registrationDate": "2022-03-10",
        "applicantName": "(주)스타빈스코리아",
        "drawingUrl": "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=400&auto=format&fit=crop&q=80",
        "category": "제09류 (포장용 용기 및 컵)",
        "shapeTags": ["커피", "원", "별"],
        "registerStatus": "등록",
        "similarityScore": "78%",
        "similarityLevel": "MEDIUM",
        "comment": "컵 홀더 및 표면의 원형 엠블럼 구도가 유사군에 속합니다."
    },
    {
        "articleName": "베이커리 포장 상자용 심볼 디자인",
        "designNumber": "3020230012789",
        "registrationDate": "2023-09-01",
        "applicantName": "브레드하우스",
        "drawingUrl": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&auto=format&fit=crop&q=80",
        "category": "제09류 (포장용 상자)",
        "shapeTags": ["빵", "집", "갈색"],
        "registerStatus": "등록",
        "similarityScore": "65%",
        "similarityLevel": "LOW",
        "comment": "빵 형상의 모티브를 활용한 패키지 디자인 공보입니다."
    },
    {
        "articleName": "원형 엠블럼 형태의 매장 입구 현판",
        "designNumber": "3020200034567",
        "registrationDate": "2021-02-14",
        "applicantName": "(주)클래식로스터리",
        "drawingUrl": "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=400&auto=format&fit=crop&q=80",
        "category": "제20류 (간판 및 현판)",
        "shapeTags": ["나무", "원", "자연"],
        "registerStatus": "소멸",
        "similarityScore": "54%",
        "similarityLevel": "SAFE",
        "comment": "나무 심볼과 원형 테두리를 조합한 디자인으로, 현재는 등록 권리가 소멸되었습니다."
    }
]


def search_trademark(search_query: str, classification_code: str = "") -> dict:
    """
    상표(가게명)를 검색하고 위험도를 분석하여 반환하는 함수입니다.
    """
    search_query = search_query.strip()
    if not search_query:
        return {"items": [], "totalCount": 0, "summary": {"danger": 0, "warning": 0, "safe": 0}}

    # 1. 모의 데이터 모드이거나 API 키가 설정되지 않은 경우 샘플 데이터에서 필터링
    if USE_MOCK or not KIPRIS_API_KEY or KIPRIS_API_KEY == "your_kipris_api_key_here":
        results = []
        query_lower = search_query.lower()

        # 검색어가 포함된 상표들을 추출합니다.
        for item in SAMPLE_TRADEMARKS:
            title_match = (query_lower in item["title"].lower())
            class_match = (not classification_code or classification_code in item["classification"])
            if title_match and class_match:
                results.append(item)

        # 검색어가 샘플에 없을 때 신규 미등록 상표로 간주하여 가이드 생성
        if not results:
            results.append({
                "title": f"{search_query}",
                "applicationNumber": "-",
                "applicationDate": "-",
                "registrationDate": "-",
                "registerStatus": "미등록 (새로운 이름)",
                "classification": f"제{classification_code or '43'}류" if classification_code else "분류 미지정",
                "classificationName": "신규 출원 가능 대상",
                "applicantName": "-",
                "bigDrawing": "",
                "viennaCode": "",
                "viennaDescription": "-",
                "designatedGoods": "희망 업종 지정상품 출원 가능",
                "agent": "-",
                "riskLevel": "SAFE",
                "riskReason": f"'{search_query}'에 대한 동일 상표 등록 내역이 발견되지 않았습니다. 신규 상표 출원 및 간판 사용 가능성이 매우 높습니다!"
            })

        # 통계 집계
        summary = {"danger": 0, "warning": 0, "safe": 0}
        for r in results:
            level = r.get("riskLevel", "SAFE").lower()
            if level in summary:
                summary[level] += 1

        return {
            "mode": "MOCK_SIMULATION",
            "searchQuery": search_query,
            "totalCount": len(results),
            "summary": summary,
            "items": results
        }

    # 2. 실제 KIPRIS Open API 호출 모드
    try:
        params = {
            "serviceKey": KIPRIS_API_KEY,
            "searchString": search_query,
            "numOfRows": 30,
            "pageNo": 1
        }
        if classification_code:
            params["productClassification"] = classification_code

        response = requests.get(KIPRIS_TRADEMARK_URL, params=params, timeout=10)
        response.encoding = 'utf-8'

        root = ET.fromstring(response.text)
        items = []
        summary = {"danger": 0, "warning": 0, "safe": 0}

        for item_node in root.findall(".//item"):
            title = item_node.findtext("title", "").strip()
            app_num = item_node.findtext("applicationNumber", "-").strip()
            app_date = item_node.findtext("applicationDate", "-").strip()
            reg_date = item_node.findtext("registrationDate", "-").strip()
            reg_status = item_node.findtext("registerStatus", "미상").strip()
            class_code = item_node.findtext("classificationCode", "").strip()
            applicant = item_node.findtext("applicantName", "-").strip()
            drawing_url = item_node.findtext("bigDrawing", "").strip()
            vienna = item_node.findtext("viennaCode", "").strip()

            if "등록" in reg_status:
                risk_level = "DANGER"
                risk_reason = "특허청에 유효하게 등록된 상표입니다. 무단 사용 시 상표권 침해 위험이 있습니다."
                summary["danger"] += 1
            elif any(s in reg_status for s in ["출원", "공고", "심사"]):
                risk_level = "WARNING"
                risk_reason = "심사가 진행 중인 상표입니다. 등록 결정 시 분쟁 대상이 될 수 있습니다."
                summary["warning"] += 1
            else:
                risk_level = "SAFE"
                risk_reason = f"상태({reg_status})로 인해 현재 배타적 독점권이 없거나 소멸된 상태입니다."
                summary["safe"] += 1

            items.append({
                "title": title,
                "applicationNumber": app_num,
                "applicationDate": app_date,
                "registrationDate": reg_date,
                "registerStatus": reg_status,
                "classification": f"제{class_code}류" if class_code else "-",
                "classificationName": "",
                "applicantName": applicant,
                "bigDrawing": drawing_url,
                "viennaCode": vienna,
                "viennaDescription": "",
                "designatedGoods": "KIPRIS 상세공보 참조",
                "agent": "KIPRIS 상세공보 참조",
                "riskLevel": risk_level,
                "riskReason": risk_reason
            })

        return {
            "mode": "REAL_KIPRIS_API",
            "searchQuery": search_query,
            "totalCount": len(items),
            "summary": summary,
            "items": items
        }

    except Exception as e:
        return {
            "mode": "ERROR",
            "error": str(e),
            "searchQuery": search_query,
            "totalCount": 0,
            "summary": {"danger": 0, "warning": 0, "safe": 0},
            "items": [],
            "message": "KIPRIS API 통신 오류가 발생했습니다. 네트워크 및 API 키를 점검하세요."
        }


def search_design(keyword: str = "", shape_tag: str = "") -> dict:
    """
    로고, 간판, 용기 등의 디자인 공보를 검색하는 함수입니다.

    :param keyword: 검색 키워드 (예: '간판', '로고', '카페')
    :param shape_tag: 도형 형상 태그 (예: '달', '커피', '별')
    :return: 디자인 공보 리스트 및 매칭 정보
    """
    keyword = (keyword or "").strip().lower()
    shape_tag = (shape_tag or "").strip().lower()

    # 1. 모의 시뮬레이션 모드
    if USE_MOCK or not KIPRIS_API_KEY or KIPRIS_API_KEY == "your_kipris_api_key_here":
        results = []
        for d in SAMPLE_DESIGNS:
            match = True
            if keyword and not (keyword in d["articleName"].lower() or keyword in d["category"].lower()):
                match = False
            if shape_tag and not any(shape_tag in tag.lower() for tag in d["shapeTags"]):
                match = False
            if match or (not keyword and not shape_tag):
                results.append(d)

        # 결과가 없으면 전체 반환하여 비교할 수 있도록 지원
        if not results:
            results = SAMPLE_DESIGNS

        return {
            "mode": "MOCK_SIMULATION",
            "keyword": keyword,
            "shapeTag": shape_tag,
            "totalCount": len(results),
            "items": results
        }

    # 2. 실제 KIPRIS 디자인정보 검색 API 연동 모드
    try:
        params = {
            "serviceKey": KIPRIS_API_KEY,
            "articleName": keyword or shape_tag or "간판",
            "numOfRows": 20,
            "pageNo": 1
        }
        res = requests.get(KIPRIS_DESIGN_URL, params=params, timeout=10)
        res.encoding = 'utf-8'
        root = ET.fromstring(res.text)

        items = []
        for node in root.findall(".//item"):
            name = node.findtext("articleName", "디자인 공보").strip()
            num = node.findtext("applicationNumber", "-").strip()
            reg_date = node.findtext("registrationDate", "-").strip()
            applicant = node.findtext("applicantName", "-").strip()
            drawing = node.findtext("bigDrawing", "").strip()

            items.append({
                "articleName": name,
                "designNumber": num,
                "registrationDate": reg_date,
                "applicantName": applicant,
                "drawingUrl": drawing,
                "category": "디자인 공보",
                "shapeTags": [shape_tag] if shape_tag else ["일반"],
                "registerStatus": "공보",
                "similarityScore": "분석중",
                "similarityLevel": "MEDIUM",
                "comment": "특허청 공식 디자인 공보 도면입니다."
            })

        return {
            "mode": "REAL_KIPRIS_API",
            "keyword": keyword,
            "totalCount": len(items),
            "items": items
        }
    except Exception as e:
        return {
            "mode": "ERROR",
            "error": str(e),
            "totalCount": 0,
            "items": SAMPLE_DESIGNS
        }


def get_vienna_recommendations(keyword: str) -> list:
    """
    사용자가 입력한 형상 키워드(예: '달', '커피')를 바탕으로
    특허청 비엔나 분류 코드 정보를 매핑하여 추천합니다.
    """
    keyword = keyword.strip()
    recommendations = []

    for key, val in VIENNA_CATEGORY_MAP.items():
        if keyword in key or key in keyword:
            recommendations.append(val)

    if not recommendations:
        # 매칭되는 것이 없으면 대표 카테고리 3개 기본 추천
        recommendations = [
            VIENNA_CATEGORY_MAP["달"],
            VIENNA_CATEGORY_MAP["커피"],
            VIENNA_CATEGORY_MAP["나무"]
        ]

    return recommendations
