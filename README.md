# Spotify Music Recommender

이 프로젝트는 Spotify API를 활용한 음악 추천 웹 애플리케이션입니다. 확률과 통계, 머신러닝 기법을 활용하여 사용자의 음악 취향을 분석하고 개인화된 음악을 추천합니다.

## 주요 기능

- Spotify 계정 연동
- 사용자의 최근 재생 기록 분석
- 음악 특성(오디오 피처) 기반 추천
- 협업 필터링을 통한 추천
- 장르 기반 통계적 분석

## 설치 방법

1. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

2. Spotify Developer 계정 설정:
- [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)에서 새 앱 생성
- Client ID와 Client Secret 발급
- Redirect URI 설정 (예: http://localhost:5000/callback)

3. 환경 변수 설정:
`.env` 파일을 생성하고 다음 내용을 입력:
```
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:5000/callback
```

4. 애플리케이션 실행:
```bash
python app.py
```

## 기술 스택

- Flask: 웹 프레임워크
- Spotipy: Spotify API 래퍼
- scikit-learn: 머신러닝 알고리즘
- pandas: 데이터 분석
- NumPy: 수치 계산 