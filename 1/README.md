# AI 음악 추천 플레이리스트 웹 애플리케이션

YouTube API를 활용한 AI 음악 추천 플레이리스트 웹 애플리케이션입니다.

## 기능

- 사용자의 선호하는 아티스트, 장르, 기분에 따라 음악 추천
- YouTube API를 통한 실시간 음악 검색
- 추천된 음악을 웹 페이지에서 바로 재생 가능

## 설치 및 실행 방법

1. YouTube Data API v3 키 발급하기
   - [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
   - YouTube Data API v3 활성화
   - API 키 발급

2. API 키 설정
   - `app.js` 파일의 `API_KEY` 변수에 발급받은 API 키 입력

3. 웹 서버 실행
   - 로컬 웹 서버를 통해 `index.html` 파일 실행
   - 또는 VS Code의 Live Server 확장 프로그램 등을 사용하여 실행

## 주의사항

- YouTube API는 일일 할당량이 제한되어 있으므로 과도한 요청을 피해주세요.
- 실제 서비스 배포 시에는 API 키를 클라이언트 측 코드에 직접 포함하지 말고, 서버 측에서 안전하게 관리해야 합니다.