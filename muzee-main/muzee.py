import os
import json
import requests
import sqlite3
import uuid
import hashlib
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 세션을 위한 비밀 키

# YouTube API 키
API_KEY = 'AIzaSyAWIkZsAAP_iwVss9AMo-roR-bMJFY1baQ'

# 데이터베이스 설정
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'muzee.db')

# 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 사용자 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 플레이리스트 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 플레이리스트 비디오 테이블 생성
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS playlist_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        channel_title TEXT NOT NULL,
        view_count INTEGER NOT NULL,
        thumbnail TEXT NOT NULL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playlist_id) REFERENCES playlists (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# 데이터베이스 초기화 실행
init_db()

# 로그인 필요 데코레이터
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '로그인이 필요합니다.'}), 401
        return f(*args, **kwargs)
    return decorated_function


# 현재 디렉토리 경로
current_dir = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def index():
    return send_from_directory(current_dir, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(current_dir, path)

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    artist = data.get('artist', '')
    genre = data.get('genre', '')
    mood = data.get('mood', '')
    
    if not any([artist, genre, mood]):
        return jsonify({'error': '최소한 하나의 선호도를 입력해주세요.'}), 400
    
    try:
        # 검색어 생성
        search_query = ''
        if artist:
            search_query += f"{artist} "
        if genre:
            search_query += f"{genre} music "
        if mood:
            search_query += f"{mood} music"
        
        # YouTube API 검색 요청
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            'key': API_KEY,
            'q': search_query,
            'part': 'snippet',
            'type': 'video',
            'videoCategoryId': '10',  # 음악 카테고리
            'maxResults': 10
        }
        
        search_response = requests.get(search_url, params=search_params)
        # 응답 상태 확인 및 디버깅
        if search_response.status_code != 200:
            print(f"API 오류: {search_response.status_code}, 응답: {search_response.text}")
            return jsonify({'error': f'YouTube API 오류: {search_response.status_code}'}), 500
        search_data = search_response.json()
        
        if 'items' not in search_data or not search_data['items']:
            return jsonify({'error': '검색 결과가 없습니다.'}), 404
        
        # 비디오 ID 추출
        video_ids = [item['id']['videoId'] for item in search_data['items']]
        
        # 비디오 상세 정보 요청 (조회수 포함)
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            'key': API_KEY,
            'id': ','.join(video_ids),
            'part': 'snippet,statistics'
        }
        
        videos_response = requests.get(videos_url, params=videos_params)
        # 응답 상태 확인 및 디버깅
        if videos_response.status_code != 200:
            print(f"API 오류: {videos_response.status_code}, 응답: {videos_response.text}")
            return jsonify({'error': f'YouTube API 오류: {videos_response.status_code}'}), 500
        videos_data = videos_response.json()
        
        if 'items' not in videos_data or not videos_data['items']:
            return jsonify({'error': '비디오 정보를 가져올 수 없습니다.'}), 404
        
        # 조회수에 따라 정렬
        videos = videos_data['items']
        videos.sort(key=lambda x: int(x['statistics'].get('viewCount', 0)), reverse=True)
        
        # 필요한 정보만 추출
        results = []
        for video in videos:
            view_count = int(video['statistics'].get('viewCount', 0))
            formatted_view_count = f"{view_count:,}"
            
            results.append({
                'id': video['id'],
                'title': video['snippet']['title'],
                'channelTitle': video['snippet']['channelTitle'],
                'viewCount': view_count,
                'formattedViewCount': formatted_view_count,
                'thumbnail': video['snippet']['thumbnails']['high']['url']
            })
        
        return jsonify({'videos': results})
    
    except json.JSONDecodeError as je:
        print(f"JSON 파싱 오류: {str(je)}")
        return jsonify({'error': 'API 응답을 처리하는 중 오류가 발생했습니다. API 키를 확인해주세요.'}), 500
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return jsonify({'error': f'추천을 가져오는 중 오류가 발생했습니다: {str(e)}'}), 500

# 사용자 관련 API
@app.route('/api/auth/register', methods=['POST'])
def register():
    """사용자 등록"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': '사용자 이름과 비밀번호를 모두 입력해주세요.'}), 400
    
    # 비밀번호 해싱
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                      (username, hashed_password))
        conn.commit()
        
        # 새 사용자 ID 가져오기
        user_id = cursor.lastrowid
        
        # 세션에 사용자 정보 저장
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'message': '회원가입이 완료되었습니다.',
            'user_id': user_id,
            'username': username
        })
    except sqlite3.IntegrityError:
        return jsonify({'error': '이미 사용 중인 사용자 이름입니다.'}), 400
    finally:
        conn.close()

@app.route('/api/auth/login', methods=['POST'])
def login():
    """사용자 로그인"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'error': '사용자 이름과 비밀번호를 모두 입력해주세요.'}), 400
    
    # 비밀번호 해싱
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, username FROM users WHERE username = ? AND password = ?', 
                      (username, hashed_password))
        user = cursor.fetchone()
        
        if user:
            # 세션에 사용자 정보 저장
            session['user_id'] = user[0]
            session['username'] = user[1]
            
            return jsonify({
                'message': '로그인 성공',
                'user_id': user[0],
                'username': user[1]
            })
        else:
            return jsonify({'error': '사용자 이름 또는 비밀번호가 올바르지 않습니다.'}), 401
    finally:
        conn.close()

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """사용자 로그아웃"""
    session.clear()
    return jsonify({'message': '로그아웃 되었습니다.'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    """현재 로그인 상태 확인"""
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user_id': session['user_id'],
            'username': session['username']
        })
    else:
        return jsonify({'logged_in': False})

# 플레이리스트 관련 API
@app.route('/api/playlists', methods=['GET'])
@login_required
def get_playlists():
    """현재 로그인한 사용자의 플레이리스트 목록 반환"""
    user_id = session['user_id']
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT p.id, p.name, COUNT(pv.id) as video_count
        FROM playlists p
        LEFT JOIN playlist_videos pv ON p.id = pv.playlist_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.created_at DESC
        ''', (user_id,))
        
        playlists = []
        for row in cursor.fetchall():
            playlists.append({
                'id': row['id'],
                'name': row['name'],
                'count': row['video_count']
            })
        
        return jsonify({'playlists': playlists})
    finally:
        conn.close()

@app.route('/api/playlists', methods=['POST'])
@login_required
def create_playlist():
    """새 플레이리스트 생성"""
    user_id = session['user_id']
    data = request.json
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': '플레이리스트 이름을 입력해주세요.'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO playlists (user_id, name) VALUES (?, ?)', 
                      (user_id, name))
        conn.commit()
        
        playlist_id = cursor.lastrowid
        
        return jsonify({
            'id': playlist_id,
            'name': name,
            'message': '플레이리스트가 생성되었습니다.'
        })
    finally:
        conn.close()

@app.route('/api/playlists/<int:playlist_id>', methods=['GET'])
@login_required
def get_playlist(playlist_id):
    """특정 플레이리스트 정보 반환"""
    user_id = session['user_id']
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 플레이리스트 소유자 확인
        cursor.execute('SELECT id, name FROM playlists WHERE id = ? AND user_id = ?', 
                      (playlist_id, user_id))
        playlist = cursor.fetchone()
        
        if not playlist:
            return jsonify({'error': '플레이리스트를 찾을 수 없습니다.'}), 404
        
        # 플레이리스트 비디오 가져오기
        cursor.execute('''
        SELECT video_id, title, channel_title, view_count, thumbnail
        FROM playlist_videos
        WHERE playlist_id = ?
        ORDER BY added_at DESC
        ''', (playlist_id,))
        
        videos = []
        for row in cursor.fetchall():
            videos.append({
                'id': row['video_id'],
                'title': row['title'],
                'channelTitle': row['channel_title'],
                'viewCount': row['view_count'],
                'formattedViewCount': f"{row['view_count']:,}",
                'thumbnail': row['thumbnail']
            })
        
        return jsonify({
            'id': playlist['id'],
            'name': playlist['name'],
            'videos': videos
        })
    finally:
        conn.close()

@app.route('/api/playlists/<int:playlist_id>/videos', methods=['POST'])
@login_required
def add_video_to_playlist(playlist_id):
    """플레이리스트에 비디오 추가"""
    user_id = session['user_id']
    data = request.json
    video = data.get('video')
    
    if not video:
        return jsonify({'error': '비디오 정보가 필요합니다.'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 플레이리스트 소유자 확인
        cursor.execute('SELECT id, name FROM playlists WHERE id = ? AND user_id = ?', 
                      (playlist_id, user_id))
        playlist = cursor.fetchone()
        
        if not playlist:
            return jsonify({'error': '플레이리스트를 찾을 수 없습니다.'}), 404
        
        # 중복 확인
        cursor.execute('SELECT id FROM playlist_videos WHERE playlist_id = ? AND video_id = ?', 
                      (playlist_id, video['id']))
        if cursor.fetchone():
            return jsonify({'error': '이미 플레이리스트에 추가된 비디오입니다.'}), 400
        
        # 비디오 추가
        cursor.execute('''
        INSERT INTO playlist_videos 
        (playlist_id, video_id, title, channel_title, view_count, thumbnail) 
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            playlist_id, 
            video['id'], 
            video['title'], 
            video['channelTitle'], 
            video['viewCount'], 
            video['thumbnail']
        ))
        conn.commit()
        
        # 비디오 수 가져오기
        cursor.execute('SELECT COUNT(*) FROM playlist_videos WHERE playlist_id = ?', (playlist_id,))
        count = cursor.fetchone()[0]
        
        return jsonify({
            'message': '비디오가 플레이리스트에 추가되었습니다.',
            'playlist': {
                'id': playlist_id,
                'name': playlist[1],
                'count': count
            }
        })
    finally:
        conn.close()

@app.route('/api/playlists/<int:playlist_id>', methods=['DELETE'])
@login_required
def delete_playlist(playlist_id):
    """플레이리스트 삭제"""
    user_id = session['user_id']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 플레이리스트 소유자 확인
        cursor.execute('SELECT id, name FROM playlists WHERE id = ? AND user_id = ?', 
                      (playlist_id, user_id))
        playlist = cursor.fetchone()
        
        if not playlist:
            return jsonify({'error': '플레이리스트를 찾을 수 없습니다.'}), 404
        
        # 먼저 플레이리스트의 모든 비디오 삭제
        cursor.execute('DELETE FROM playlist_videos WHERE playlist_id = ?', (playlist_id,))
        
        # 플레이리스트 삭제
        cursor.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
        conn.commit()
        
        return jsonify({'message': f'플레이리스트 "{playlist[1]}"가 삭제되었습니다.'})
    finally:
        conn.close()

@app.route('/api/playlists/<int:playlist_id>/videos/<video_id>', methods=['DELETE'])
@login_required
def remove_video_from_playlist(playlist_id, video_id):
    """플레이리스트에서 비디오 제거"""
    user_id = session['user_id']
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 플레이리스트 소유자 확인
        cursor.execute('SELECT id FROM playlists WHERE id = ? AND user_id = ?', 
                      (playlist_id, user_id))
        if not cursor.fetchone():
            return jsonify({'error': '플레이리스트를 찾을 수 없습니다.'}), 404
        
        # 비디오 제거
        cursor.execute('''
        DELETE FROM playlist_videos 
        WHERE playlist_id = ? AND video_id = ?
        ''', (playlist_id, video_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'error': '비디오를 찾을 수 없습니다.'}), 404
        
        return jsonify({'message': '비디오가 플레이리스트에서 제거되었습니다.'})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5500)