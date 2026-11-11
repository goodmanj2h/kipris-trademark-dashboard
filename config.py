# -*- coding: utf-8 -*-
"""
설정 관리 모듈 (config.py)
----------------------------------------------------------------------
이 모듈은 .env 파일에서 환경 변수(API 키, 서버 포트 등)를 안전하게 읽어와
프로그램 전체에서 사용할 수 있도록 중앙 집중 관리하는 역할을 합니다.
보안상 API 키를 소스코드에 직접 적지 않고 .env 파일에서만 불러옵니다.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 현재 프로젝트 디렉토리 경로를 계산합니다.
BASE_DIR = Path(__file__).resolve().parent

# .env 파일의 내용을 환경변수로 로드합니다.
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ====================================================================
# 주요 환경 설정 변수들
# ====================================================================

# 공공데이터포털 또는 KIPRISPlus API 서비스 키
# .env에 등록된 값을 가져오며, 미등록 시 기본 빈 문자열로 처리됩니다.
KIPRIS_API_KEY = os.getenv("KIPRIS_API_KEY", "").strip()

# 모의 데이터(Mock Data) 사용 플래그
# true일 경우 실제 KIPRIS 서버를 호출하지 않고 사전에 준비된 샘플 데이터로 테스트합니다.
# API 키가 아직 발급되지 않았거나 개발 중일 때 유용하게 쓰입니다.
USE_MOCK = os.getenv("KIPRIS_USE_MOCK", "true").lower() in ("true", "1", "yes")

# 대시보드 웹 서버가 실행될 포트 번호 (기본 8000)
SERVER_PORT = int(os.getenv("PORT", "8000"))

# 공공데이터포털 특허청 상표정보 서비스 엔드포인트 URL
KIPRIS_TRADEMARK_URL = "http://kipo-api.kipi.or.kr/openapi/service/trademarkInfoSearchService/getWordSearch"

# 공공데이터포털 특허청 디자인정보 서비스 엔드포인트 URL
KIPRIS_DESIGN_URL = "http://kipo-api.kipi.or.kr/openapi/service/designInfoSearchService/getDesignSearch"

