# -*- coding: utf-8 -*-
"""
지식재산처 KIPRIS 지식재산정보 검색 대시보드 서버 (server.py)
----------------------------------------------------------------------
이 파일은 파이썬 표준 내장 웹 서버(http.server)를 확장하여 제작된 경량 서버입니다.
추가적인 복잡한 프레임워크 설치 없이 `python3 server.py` 명령만으로 즉시 구동됩니다.

[주요 역할]
1. 프론트엔드 정적 웹 페이지(index.html) 서빙
2. 백엔드 REST API 라우팅:
   - GET /api/status : API 키 연결 상태 및 시뮬레이션 모드 확인
   - GET /api/search/trademark : 상표명/가게명 검색 및 위험도 판별
   - GET /api/search/design : 디자인/로고 공보 검색
"""

import http.server
import socketserver
import json
import urllib.parse
from pathlib import Path
from config import SERVER_PORT, KIPRIS_API_KEY, USE_MOCK
from kipris_service import search_trademark, search_design

# 프로젝트 루트 및 정적 파일 경로
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class KiprisDashboardHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP 요청을 가로채서 API 라우트와 정적 파일을 분기 처리하는 핸들러 클래스입니다.
    """

    def do_GET(self):
        """클라이언트의 GET 요청을 처리합니다."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # ------------------------------------------------------------------
        # 1. API: 시스템 및 API 키 상태 확인 엔드포인트
        # ------------------------------------------------------------------
        if path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            has_valid_key = bool(KIPRIS_API_KEY and KIPRIS_API_KEY != "your_kipris_api_key_here")
            masked_key = (KIPRIS_API_KEY[:4] + "****" + KIPRIS_API_KEY[-4:]) if has_valid_key and len(KIPRIS_API_KEY) > 8 else "미설정"

            status_payload = {
                "serverStatus": "RUNNING",
                "useMock": USE_MOCK or not has_valid_key,
                "hasApiKey": has_valid_key,
                "maskedApiKey": masked_key,
                "message": "모의(Mock) 시뮬레이션 모드로 안전하게 작동 중입니다." if USE_MOCK or not has_valid_key else "KIPRIS 실시간 API 연결 모드입니다."
            }
            self.wfile.write(json.dumps(status_payload, ensure_ascii=False).encode("utf-8"))
            return

        # ------------------------------------------------------------------
        # 2. API: 상표(가게명) 검색 엔드포인트
        # ------------------------------------------------------------------
        elif path == "/api/search/trademark":
            search_query = query_params.get("query", [""])[0]
            classification_code = query_params.get("class", [""])[0]

            results = search_trademark(search_query, classification_code)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode("utf-8"))
            return

        # ------------------------------------------------------------------
        # 3. API: 디자인/로고 공보 검색 엔드포인트
        # ------------------------------------------------------------------
        elif path == "/api/search/design":
            keyword = query_params.get("keyword", [""])[0]
            shape_tag = query_params.get("shape", [""])[0]

            results = search_design(keyword, shape_tag)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(results, ensure_ascii=False).encode("utf-8"))
            return

        # ------------------------------------------------------------------
        # 4. 정적 웹 페이지(HTML/CSS/JS) 서빙 (루트 index.html 우선 확인)
        # ------------------------------------------------------------------
        elif path in ("/", "/index.html"):
            root_index = BASE_DIR / "index.html"
            static_index = STATIC_DIR / "index.html"
            target_path = root_index if root_index.exists() else static_index

            if target_path.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(target_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "index.html 파일을 찾을 수 없습니다.")
                return

        # 정의되지 않은 경로 요청 시 기본 처리
        return super().do_GET()


def run_server():
    """
    웹 서버를 초기화하고 지정된 포트에서 수신 대기합니다.
    """
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", SERVER_PORT), KiprisDashboardHandler) as httpd:
        print("=" * 70)
        print("  [KIPRIS 지식재산정보] 가게명/로고 상표 중복 검증 대시보드 서버 재시작 완료")
        print("=" * 70)
        print(f"  • 대시보드 주소: http://localhost:{SERVER_PORT}")
        print(f"  • API 상태 확인: http://localhost:{SERVER_PORT}/api/status")
        print("=" * 70)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()


if __name__ == "__main__":
    run_server()
