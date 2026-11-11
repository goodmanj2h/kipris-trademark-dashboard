-- ==============================================================================
-- 001_create_kipris_tables.sql
-- KIPRIS 지식재산정보 상표·로고 검증 대시보드 데이터베이스 스키마
-- ==============================================================================
-- 본 스크립트는 Supabase SQL Editor에서 실행하여 필요한 테이블과 보안 정책을 생성합니다.
-- 규칙 7 및 규칙 8(보안 및 암호화)을 엄격히 준수합니다.
-- ==============================================================================

-- 1. UUID 확장 기능 활성화 (고유 식별자 생성용)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 2. 사용자 관심 상표 보관함 (마이폴더) 테이블
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.kipris_bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,  -- 로그인한 사용자 식별자
    title VARCHAR(255) NOT NULL,                               -- 상표/가게명
    application_number VARCHAR(50) NOT NULL,                  -- 출원번호 (예: 4020220194821)
    application_date VARCHAR(20),                             -- 출원일자
    registration_date VARCHAR(20),                            -- 등록일자
    register_status VARCHAR(50) NOT NULL,                     -- 상태 (등록, 출원, 거절, 소멸 등)
    classification VARCHAR(50),                               -- 상품분류 (제43류 등)
    applicant_name VARCHAR(255),                              -- 출원인 명칭
    drawing_url TEXT,                                         -- 상표/로고 이미지 URL
    risk_level VARCHAR(20) DEFAULT 'SAFE',                    -- 위험도 판별 (DANGER, WARNING, SAFE)
    risk_reason TEXT,                                         -- 위험도 사유 설명
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 인덱스 생성 (조회 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_kipris_bookmarks_user ON public.kipris_bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_kipris_bookmarks_app_num ON public.kipris_bookmarks(application_number);

-- ------------------------------------------------------------------------------
-- 3. 검색 로그 및 통계 테이블 (규칙 8 보안 강화: 개인식별정보 배제)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.kipris_search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    search_query VARCHAR(255) NOT NULL,                       -- 검색한 가게명
    classification_code VARCHAR(20),                          -- 선택한 업종 분류코드
    result_count INT DEFAULT 0,                               -- 검색된 결과 수
    danger_count INT DEFAULT 0,                               -- 위험(등록) 건수
    warning_count INT DEFAULT 0,                              -- 주의(출원) 건수
    safe_count INT DEFAULT 0,                                 -- 안전(거절/소멸) 건수
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ------------------------------------------------------------------------------
-- 4. 보안 정책 (Row Level Security - RLS 활성화)
-- 사용자 본인의 북마크 데이터만 읽고 쓸 수 있도록 격리합니다.
-- ------------------------------------------------------------------------------
ALTER TABLE public.kipris_bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.kipris_search_logs ENABLE ROW LEVEL SECURITY;

-- 북마크 테이블 RLS 정책: 본인 소유 데이터만 접근 허용
CREATE POLICY "사용자는 자신의 북마크만 조회할 수 있습니다."
    ON public.kipris_bookmarks FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "사용자는 자신의 북마크만 추가할 수 있습니다."
    ON public.kipris_bookmarks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "사용자는 자신의 북마크만 삭제할 수 있습니다."
    ON public.kipris_bookmarks FOR DELETE
    USING (auth.uid() = user_id);

