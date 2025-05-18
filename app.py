import os
import logging
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
import pandas as pd
from sklearn.preprocessing import StandardScaler

logging.getLogger('spotipy').setLevel(logging.DEBUG)

load_dotenv()
print("Redirect URI:", os.getenv('SPOTIPY_REDIRECT_URI'))

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify API 설정
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')
SCOPE = 'user-library-read user-top-read playlist-read-private user-read-recently-played user-read-currently-playing user-read-playback-state streaming user-modify-playback-state'

# Spotify 인증 객체 생성
auth_manager = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE
)

@app.route('/')
def index():
    if not session.get('token_info'):
        return render_template('login.html')
    return redirect(url_for('recommendations'))

@app.route('/login')
def login():
    auth_url = auth_manager.get_authorize_url()
    print("Auth URL:", auth_url)
    return redirect(auth_url)

@app.route('/callback')
def callback():
    print("Callback args:", request.args)
    if request.args.get("code"):
        token_info = auth_manager.get_access_token(request.args["code"], check_cache=False)
        print("Token Info:", token_info)
        session["token_info"] = token_info
        return redirect(url_for('recommendations'))
    return redirect(url_for('index'))

@app.route('/recommendations')
def recommendations():
    if not session.get('token_info'):
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # 현재 재생 중인 곡 확인
    current_track = sp.current_user_playing_track()
    print("Current Track:", current_track)
    
    # 최근 재생 곡 가져오기
    recent_tracks = sp.current_user_recently_played(limit=50)
    print("Recent Tracks:", recent_tracks)
    
    track_ids = [track['track']['id'] for track in recent_tracks['items'] if track['track']['id']]
    print("Track IDs:", track_ids)
    
    if not track_ids:
        return render_template('recommendations.html', 
                             recommendations=[],
                             recent_tracks=[],
                             error="최근 재생 곡이 없습니다. Spotify에서 음악을 재생한 후 다시 시도하세요.")
    
    # 개별 트랙으로 오디오 특성 요청
    audio_features = []
    for track_id in track_ids:
        try:
            feature = sp.audio_features([track_id])[0]
            audio_features.append(feature)
            print(f"Audio Feature for {track_id}:", feature)
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error for track {track_id}:", e)
            continue
    
    if not audio_features:
        return render_template('recommendations.html', 
                             recommendations=[],
                             recent_tracks=recent_tracks['items'],
                             error="오디오 특성을 가져올 수 없습니다.")
    
    features_df = pd.DataFrame(audio_features)
    recommendations = get_recommendations(sp, features_df, track_ids)
    
    return render_template('recommendations.html', 
                         recommendations=recommendations,
                         recent_tracks=recent_tracks['items'])

def get_recommendations(sp, features_df, seed_tracks, n_recommendations=10):
    features_to_normalize = ['danceability', 'energy', 'loudness', 'speechiness', 
                           'acousticness', 'instrumentalness', 'liveness', 'valence', 'tempo']
    
    scaler = StandardScaler()
    features_df[features_to_normalize] = scaler.fit_transform(features_df[features_to_normalize])
    
    mean_features = features_df[features_to_normalize].mean()
    
    recommendations = sp.recommendations(
        seed_tracks=seed_tracks[:5],
        limit=n_recommendations,
        target_danceability=mean_features['danceability'],
        target_energy=mean_features['energy'],
        target_valence=mean_features['valence']
    )
    
    return recommendations['tracks']

@app.route('/recommendations_by_mood/<mood>')
def recommendations_by_mood(mood):
    if not session.get('token_info'):
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    try:
        # 사용자 시장
        user_profile = sp.current_user()
        market = user_profile.get('country', 'KR')
        print("User Market:", market)
        
        # 한국 시장 장르
        genres = {
            'happy': ['pop', 'dance', 'k-pop', 'happy'],
            'sad': ['acoustic', 'piano', 'ballad', 'sad']
        }
        
        # 시드 트랙 유효성 검증
        recent_tracks = sp.current_user_recently_played(limit=10)
        seed_tracks = []
        for track in recent_tracks['items']:
            track_id = track['track']['id']
            try:
                sp.track(track_id)  # 트랙 접근 가능 여부 확인
                seed_tracks.append(track_id)
                if len(seed_tracks) >= 2:  # 최대 5개, 2개로 제한
                    break
            except spotipy.exceptions.SpotifyException as e:
                print(f"Invalid track {track_id}:", e)
                continue
        print("Seed Tracks:", seed_tracks)
        
        # 시드 트랙 없으면 장르에만 의존
        if not seed_tracks:
            seed_tracks = None
        
        # 추천 요청
        if mood == 'happy':
            recommendations = sp.recommendations(
                seed_genres=genres['happy'][:2],
                seed_tracks=seed_tracks,
                limit=20,
                market=market,
                target_valence=0.6,  # 완화
                target_energy=0.6,
                min_tempo=80,  # 범위 확장
                target_danceability=0.6
            )
        else:  # sad
            recommendations = sp.recommendations(
                seed_genres=genres['sad'][:2],
                seed_tracks=seed_tracks,
                limit=20,
                market=market,
                target_valence=0.4,
                target_energy=0.4,
                max_tempo=120,
                target_danceability=0.4
            )

        print("Recommendations:", recommendations)
        
        if not recommendations['tracks']:
            return render_template('mood_recommendations.html',
                                 recommendations=[],
                                 mood=mood,
                                 error="추천할 노래를 찾지 못했습니다. 다른 감정을 시도하거나 Spotify에서 음악을 재생하세요.")

        # 오디오 특성 가져오기
        tracks_with_features = []
        for track in recommendations['tracks']:
            try:
                features = sp.audio_features([track['id']])[0]
                if features:
                    track['audio_features'] = {
                        'valence': round(features['valence'] * 100),
                        'energy': round(features['energy'] * 100),
                        'tempo': round(features['tempo']),
                        'danceability': round(features['danceability'] * 100)
                    }
                    tracks_with_features.append(track)
                print(f"Audio Feature for {track['id']}:", features)
            except spotipy.exceptions.SpotifyException as e:
                print(f"Error for track {track['id']}:", e)
                continue

        if not tracks_with_features:
            return render_template('mood_recommendations.html',
                                 recommendations=[],
                                 mood=mood,
                                 error="오디오 특성을 가져올 수 없습니다.")

        return render_template('mood_recommendations.html',
                             recommendations=tracks_with_features,
                             mood=mood)

    except spotipy.exceptions.SpotifyException as e:
        print("Recommendation error:", str(e))
        return render_template('mood_recommendations.html',
                             recommendations=[],
                             mood=mood,
                             error=f"추천 요청 실패: {str(e)}")
    except Exception as e:
        print("General error:", str(e))
        return render_template('mood_recommendations.html',
                             recommendations=[],
                             mood=mood,
                             error="일시적인 오류가 발생했습니다. 다시 시도해주세요.")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
