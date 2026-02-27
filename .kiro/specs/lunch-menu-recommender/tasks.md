# 구현 계획: 점심 메뉴 추천 앱

## 개요

백엔드(Python FastAPI, Docker)와 iOS 앱(Swift/SwiftUI)을 함께 구현한다. 백엔드에서 추천 API를 노출하고, iOS에서 사용자 입력을 받아 API를 호출하여 메뉴 추천 결과를 표시한다. 요구사항 기반으로 단계별로 구현하고, 각 단계별 검증 포인트를 체크리스트로 관리한다.

## Tasks

- [x] 1. 백엔드 구조 및 모델 기본 구현
  - [x] 1.1 백엔드 디렉터리 구조 생성 및 정리
    - `backend/` 하위 `app/`, `app/models/`, `app/services/`, `app/routers/`, `app/middleware/`, `app/tests/` 생성
    - `requirements.txt` 작성: fastapi, uvicorn, httpx, pydantic, hypothesis, pytest, pytest-asyncio
    - `app/__init__.py`, `app/models/__init__.py`, `app/services/__init__.py`, `app/routers/__init__.py`, `app/middleware/__init__.py` 생성
    - _Requirements: 7.1, 7.2_

  - [x] 1.2 Pydantic 모델 구현
    - `app/models/schemas.py`에 Weather, Mood, Event, PriceRange Enum 구현
    - RecommendationRequest, Restaurant, ScoredRestaurant, RecommendationResponse, HealthResponse 모델 구현
    - 요구사항 문서 기준으로 필드와 타입, 유효성 반영
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 3.3, 7.2, 7.3_

  - [x]* 1.3 백엔드 모델 직렬화/역직렬화 속성 테스트 구현
    - **Property 9: 요청/응답 직렬화-역직렬화(백엔드)**
    - Hypothesis를 사용해 RecommendationRequest, RecommendationResponse 객체 생성
    - JSON 인코딩/디코딩 일관성 검증
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 7.2, 7.3**

- [x] 2. 백엔드 핵심 비즈니스 구현
  - [x] 2.1 NaverMapService 구현
    - `app/services/naver_map_service.py`에 NaverMapService 구현
    - httpx 사용 비동기 API 호출 (`/v1/search/local`)
    - 환경변수 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET` 로드
    - 반경 200m 고정, 검색 개수 5개 기본값 지정
    - 네트워크 실패/타임아웃 예외 처리
    - _Requirements: 2.2, 7.4_

  - [x]* 2.2 NaverMapService 반경 파라미터 테스트
    - **Property 3: 반경 200m 고정**
    - Hypothesis 유효 GPS 좌표 생성
    - API 요청 시 radius 파라미터가 항상 200인지 검증 (httpx mock 활용)
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 2.2**

  - [x] 2.3 RecommendationEngine 구현
    - `app/services/recommendation_engine.py`에 RecommendationEngine 구현
    - 날씨/기분/이벤트 조합 기반 카테고리 매핑
    - 점수 계산: 가격(40%) + 카테고리 적합도(30%) + 거리(20%) + 랜덤 보정(10%)
    - exclude_ids 기반 중복 제외 처리
    - 상위 N개 기본 3개 반환, 점수 내림차순 정렬
    - _Requirements: 3.1, 3.2, 3.4, 3.6_

  - [x]* 2.4 추천 결과 정렬/개수 속성 테스트
    - **Property 4: 추천 결과 정렬/개수 일관성**
    - Hypothesis로 다양한 추천 목록/조건 생성
    - 점수 내림차순 정렬 및 최대 3개, 점수 0~1 범위 검증
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 3.1, 3.2**

  - [x]* 2.5 추천 결과 필수 필드 존재성 속성 테스트
    - **Property 5: 추천 결과 필수 필드 존재성**
    - name/category/distance/price_range 누락/비어 있음 여부 검증
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 3.3, 5.2**

  - [x]* 2.6 중복 추천 제외 예외 처리 속성 테스트
    - **Property 6: 중복 추천 제외**
    - exclude_ids를 포함한 목록에서 이전 추천이 결과에 재노출되지 않음 검증
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 3.6**

- [x] 3. 백엔드 API 라우팅 및 로깅 구현
  - [x] 3.1 FastAPI 라우터 구현
    - `app/main.py` FastAPI 객체 생성, 미들웨어 등록
    - `app/routers/recommend.py`에 `POST /api/v1/recommend` 구현
    - `app/routers/health.py`에 `GET /api/v1/health` 구현
    - NaverMapService + RecommendationEngine 결합 추천 플로우 구현
    - 에러 처리: 422(입력 오류), 502(상위 API 실패), 504(타임아웃), 500(예상 외 오류)
    - _Requirements: 7.2, 7.3, 7.5_

  - [x] 3.2 요청/응답 로깅 미들웨어 구현
    - `app/middleware/logging.py` 구조화 JSON 로깅 미들웨어 구현
    - `LOG_LEVEL` 환경변수로 로그 레벨 제어
    - 민감정보 마스킹 처리
    - 예외 발생 시 ERROR 레벨 로그
    - _Requirements: 7.7_

  - [x]* 3.3 API 비동기성 속성 테스트
    - **Property 8: API 비동기성**
    - 무작위 유효 추천 요청 생성
    - 응답 JSON에 NAVER API 키값이 포함되지 않음 검증
    - FastAPI TestClient로 응답 응답성 검증
    - `tests/test_properties.py` 생성
    - **Validates: Requirements 7.4**

  - [x]* 3.4 백엔드 단위 테스트
    - 카테고리 매핑 조합 검증 (예: 맑음+행복+팀 식사)
    - 입력 식당 목록에 대한 결과 반환 검증
    - 매칭 3건 미만이면 가능한 만큼 반환 검증
    - 상위 API 실패 시 502 응답 검증
    - 스모크 테스트: 상태코드/응답 형식
    - 잘못된 요청 파라미터에 422 응답 검증
    - `tests/test_unit.py` 생성
    - _Requirements: 2.5, 2.6, 3.4, 3.5, 7.5, 7.7_

- [x] 4. 백엔드 Docker 컨테이너 구성
  - [x] 4.1 Dockerfile 및 실행 환경 정리
    - `backend/Dockerfile` 작성: python:3.12-slim 기반, uvicorn 실행
    - HEALTHCHECK 설정: 30초 간격, 5초 타임아웃, 3회 재시도
    - `.env.example` 작성: NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, LOG_LEVEL
    - `.dockerignore` 작성
    - _Requirements: 7.1, 7.4, 7.5_

- [x] 5. 체크리스트-백엔드 검증
  - 모든 백엔드 작업 항목 완료 여부 확인 후 다음 단계 진행 여부 판단

- [x] 6. iOS 아키텍처 및 모델 구현
  - [x] 6.1 iOS 디렉터리 구조 생성
    - `ios/LunchMenuRecommender/` 하위 `Models/`, `Services/`, `ViewModels/`, `Views/` 생성
    - 테스트 스위트 준비 (`Tests/`, Swift 테스트 타겟)
    - _Requirements: 1.1_

  - [x] 6.2 iOS 핵심 모델 구현
    - `Models/Enums.swift`에 Weather, Mood, Event, PriceRange, CriteriaField enum 구현
    - `Models/DataModels.swift`에 Coordinate, RecommendationRequest, RecommendationCriteria, ScoredRestaurant, RecommendationResponse 구현
    - `Models/Errors.swift`에 LocationError, APIError, NotificationError 구현
    - CodingKeys 통해 snake_case ↔ camelCase 변환 처리
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 3.3_

  - [x]* 6.3 iOS 모델 직렬화/역직렬화 속성 테스트
    - **Property 9: 요청/응답 직렬화-역직렬화(iOS)**
    - SwiftCheck로 RecommendationRequest/RecommendationResponse 생성 및 JSON 인코딩/디코딩 비교
    - `Tests/PropertyTests.swift` 생성
    - **Validates: Requirements 7.2, 7.3**

- [x] 7. iOS 서비스 구현
  - [x] 7.1 LocationService 구현
    - `Services/LocationService.swift`에 프로토콜/구현
    - CLLocationManager 기반 현재 좌표 획득
    - 권한 상태 처리
    - `permissionDenied` 예외 처리
    - _Requirements: 2.1, 2.3, 2.4, 6.1, 6.4_

  - [x] 7.2 APIClient 구현
    - `Services/APIClient.swift`에 프로토콜/구현
    - URLSession 기반 비동기 요청
    - POST `/api/v1/recommend` 및 GET `/api/v1/health`
    - 요청 타임아웃 10초
    - 서버 무응답 시 `APIError.serverUnavailable`
    - _Requirements: 1.6, 2.2, 2.5, 7.2, 7.6_

  - [x] 7.3 NotificationService 구현
    - `Services/NotificationService.swift`에 프로토콜/구현
    - UNUserNotificationCenter 기반 매일 반복 로컬 알림 예약
    - 알림 식별자: `lunch-menu-daily-reminder`
    - 알림 제목/본문 기본값 설정
    - 권한 요청 처리 및 비활성화 시 전체 알림 취소
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 4.7_

  - [x]* 7.4 알림 예약 유효성 속성 테스트
    - **Property 7: 알림 예약 유효성**
    - SwiftCheck로 유효 시간(hour 0~23, minute 0~59) 생성
    - 예약 파라미터 반영 및 대기열 전달값 검증
    - `Tests/PropertyTests.swift` 생성
    - **Validates: Requirements 4.2**

- [x] 8. iOS ViewModel 구현
  - [x] 8.1 RecommendationViewModel 구현
    - `ViewModels/RecommendationViewModel.swift`에 @MainActor 기반 ViewModel
    - state: weather, mood, event, priceRange, recommendations, errorMessage, isLoading, validationErrors
    - validateCriteria(): nil 검사 및 validationErrors 집계
    - requestRecommendation(): 현재 위치/조건 기반 추천 요청 및 결과 바인딩
    - requestNewRecommendation(): 이전 추천 ID를 exclude_ids로 반영
    - 에러 메시지 처리 규칙 정리
    - _Requirements: 1.6, 1.7, 2.1, 3.1, 3.5, 3.6_

  - [x]* 8.2 불완전한 입력 상태 검증 속성 테스트
    - **Property 1: 불완전 조건 입력 실패**
    - nil/누락 조건 조합에 대해 validateCriteria() false 반환 및 validationErrors 포함 여부 검증
    - `Tests/PropertyTests.swift` 생성
    - **Validates: Requirements 1.7**

  - [x]* 8.3 유효 조건 구성 검증 속성 테스트
    - **Property 2: 유효 조건으로 요청 구성**
    - 유효 조건 및 GPS 좌표로 생성한 요청 객체의 필드 일관성 검증
    - `Tests/PropertyTests.swift` 생성
    - **Validates: Requirements 1.6**

  - [x] 8.4 SettingsViewModel 구현
    - `ViewModels/SettingsViewModel.swift`에 @MainActor 기반 상태/로직
    - @Published: notificationHour(기본 11), notificationMinute(기본 30), isNotificationEnabled
    - saveNotificationSettings(), disableNotification() 구현
    - _Requirements: 4.1, 4.2, 4.7_

- [x] 9. 체크리스트-iOS ViewModel 검증
  - 모든 iOS ViewModel 구현 항목 완료 여부 확인 및 동작 점검

- [x] 10. iOS View 구현
  - [x] 10.1 OnboardingView 구현
    - `Views/OnboardingView.swift` 초깃값 안내 화면 구현
    - 권한 요청 흐름/권장권한 안내 배너
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 10.2 CriteriaInputView 구현
    - `Views/CriteriaInputView.swift` 추천 조건 입력 화면 구현
    - 날씨/기분/이벤트/가격 구간 선택 UI
    - 미선택 항목 강조 표시
    - "추천받기" 버튼
    - 위치 권한 미허용 시 안내 배너
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.7, 6.5_

  - [x] 10.3 RecommendationResultView 구현
    - `Views/RecommendationResultView.swift` 추천 결과 표시 화면 구현
    - 추천 카드(이름, 카테고리, 거리, 가격) 표시
    - 카드 탭 시 Safari 열기
    - "다시 추천받기" 버튼
    - 로딩/에러/빈 결과 메시지 표시
    - _Requirements: 3.3, 3.5, 5.1, 5.2, 5.3, 5.4_

  - [x] 10.4 SettingsView 구현
    - `Views/SettingsView.swift` 알림 시간 설정 화면 구현
    - DatePicker 및 알림 ON/OFF 토글
    - _Requirements: 4.1_

- [x] 11. iOS 통합 뷰 구성
  - [x] 11.1 앱 진입점 및 내비게이션 구성
    - `LunchMenuRecommenderApp.swift` 엔트리 구현
    - 첫 실행 Onboarding/입력 화면 분기 처리
    - 추천/설정 화면 분기 구성
    - TabView 및 NavigationStack 기반 내비게이션
    - _Requirements: 4.4, 6.1, 6.2_

  - [x]* 11.2 iOS 통합 테스트
    - 위치 권한 거부, API 무응답, 네트워크 실패, 결과 없음, 알림 거부/해제 시 메시지 검증
    - Mock 객체 기반 단위 테스트 작성
    - `Tests/UnitTests.swift` 생성
    - _Requirements: 2.4, 2.5, 2.6, 3.5, 4.6, 4.7, 7.6_

- [x] 12. 최종 체크리스트-전체 검증
  - 백엔드 및 iOS 모든 항목 완료 상태 확인 후 종료 판단

## 디렉터리 구조 지침

코드와 테스트를 반드시 분리한다.

### 백엔드(Python)

```
backend/
  app/
    models/
    services/
    routers/
    middleware/
    main.py
  tests/
    test_properties.py
    test_unit.py
  requirements.txt
  Dockerfile
```

### iOS (Swift)

```
ios/LunchMenuRecommender/
  Sources/
    Models/
    Services/
    ViewModels/
    Views/
    LunchMenuRecommenderApp.swift
  Tests/
    PropertyTests.swift
    UnitTests.swift
```

## 참고 항목

- `*` 표시는 선택 항목이며, MVP에서는 우선순위에 따라 생략 가능
- 체크리스트만 갱신하여 진행률을 추적한다
- 속성 기반 테스트는 보편 케이스에 대한 검증, 단위 테스트는 구체 케이스 검증을 보완한다
