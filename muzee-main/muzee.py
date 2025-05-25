import os
import json
import requests
import sqlite3
import hashlib
from flask import Flask, request, jsonify, send_from_directory, session
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)

API_KEY = 'AIzaSyDr2o46a-5qhYDle7iHhQGcz8mcBzmVfTI'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'muzee.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')

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

    # 좋아요/싫어요 반응 테이블
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS video_reactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        video_id TEXT NOT NULL,
        title TEXT NOT NULL,
        channel_title TEXT NOT NULL,
        thumbnail TEXT NOT NULL,
        reaction TEXT CHECK(reaction IN ('like', 'dislike')),
        UNIQUE(user_id, video_id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    conn.commit()
    conn.close()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '로그인이 필요합니다.'}), 401
        return f(*args, **kwargs)
    return decorated_function

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
    sort_by_likes = data.get('sortByLikes', False)

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

        # 싫어요 누른 영상 제외
        disliked_ids = []
        if 'user_id' in session:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT video_id FROM video_reactions WHERE user_id=? AND reaction="dislike"', (session['user_id'],))
            disliked_ids = [row[0] for row in cursor.fetchall()]
            conn.close()

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
        if search_response.status_code != 200:
            print(f"API 오류: {search_response.status_code}, 응답: {search_response.text}")
            return jsonify({'error': f'YouTube API 오류: {search_response.status_code}'}), 500
        search_data = search_response.json()

        if 'items' not in search_data or not search_data['items']:
            return jsonify({'videos': []})

        # 비디오 ID 추출
        video_ids = [item['id']['videoId'] for item in search_data['items']]
        # 싫어요 누른 영상 제외
        filtered_video_ids = [vid for vid in video_ids if vid not in disliked_ids]
        if not filtered_video_ids:
            return jsonify({'videos': []})

        # 비디오 상세 정보 요청 (조회수 포함)
        videos_url = "https://www.googleapis.com/youtube/v3/videos"
        videos_params = {
            'key': API_KEY,
            'id': ','.join(filtered_video_ids),
            'part': 'snippet,statistics'
        }

        videos_response = requests.get(videos_url, params=videos_params)
        if videos_response.status_code != 200:
            print(f"API 오류: {videos_response.status_code}, 응답: {videos_response.text}")
            return jsonify({'error': f'YouTube API 오류: {videos_response.status_code}'}), 500
        videos_data = videos_response.json()

        if 'items' not in videos_data or not videos_data['items']:
            return jsonify({'videos': []})

        videos = []
        for video in videos_data['items']:
            view_count = int(video['statistics'].get('viewCount', 0))
            videos.append({
                'id': video['id'],
                'title': video['snippet']['title'],
                'channelTitle': video['snippet']['channelTitle'],
                'viewCount': view_count,
                'formattedViewCount': f"{view_count:,}",
                'thumbnail': video['snippet']['thumbnails']['high']['url']
            })

        # DB에서 좋아요/싫어요 카운트 가져오기
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for v in videos:
            cursor.execute('SELECT COUNT(*) FROM video_reactions WHERE video_id=? AND reaction="like"', (v['id'],))
            v['likes'] = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM video_reactions WHERE video_id=? AND reaction="dislike"', (v['id'],))
            v['dislikes'] = cursor.fetchone()[0]
        conn.close()

        # 정렬 (기본: 조회수순, sortByLikes가 true면 좋아요순)
        if sort_by_likes:
            videos.sort(key=lambda x: (x['likes'], x['viewCount']), reverse=True)
        else:
            videos.sort(key=lambda x: x['viewCount'], reverse=True)

        return jsonify({'videos': videos})

    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return jsonify({'error': f'추천을 가져오는 중 오류가 발생했습니다: {str(e)}'}), 500

# 좋아요/싫어요 반응 API
@app.route('/api/video/reaction', methods=['POST'])
@login_required
def video_reaction():
    data = request.json
    user_id = session['user_id']
    video_id = data['video_id']
    reaction = data['reaction']
    title = data['title']
    channel_title = data['channelTitle']
    thumbnail = data['thumbnail']

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # 좋아요/싫어요 취소 (이미 눌렀던 반응일 경우 삭제)
    if data.get('cancel', False):
        cursor.execute('DELETE FROM video_reactions WHERE user_id=? AND video_id=?', (user_id, video_id))
        conn.commit()
        conn.close()
        return jsonify({'message': '반응이 취소되었습니다.'})
    # 좋아요/싫어요 기록(갱신)
    cursor.execute('INSERT OR REPLACE INTO video_reactions (user_id, video_id, title, channel_title, thumbnail, reaction) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, video_id, title, channel_title, thumbnail, reaction))
    conn.commit()
    conn.close()
    return jsonify({'message': f'{reaction}가 반영되었습니다.'})

# 해당 비디오 좋아요/싫어요 카운트 및 사용자의 반응 조회
@app.route('/api/video/<video_id>/reaction', methods=['GET'])
def get_video_reaction(video_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM video_reactions WHERE video_id=? AND reaction="like"', (video_id,))
    likes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM video_reactions WHERE video_id=? AND reaction="dislike"', (video_id,))
    dislikes = cursor.fetchone()[0]
    user_reaction = None
    if 'user_id' in session:
        cursor.execute('SELECT reaction FROM video_reactions WHERE user_id=? AND video_id=?', (session['user_id'], video_id))
        row = cursor.fetchone()
        user_reaction = row[0] if row else None
    conn.close()
    return jsonify({'likes': likes, 'dislikes': dislikes, 'user_reaction': user_reaction})

# 좋아요/싫어요 누른 노래 목록
@app.route('/api/user/videos/<reaction>', methods=['GET'])
@login_required
def user_reacted_videos(reaction):
    user_id = session['user_id']
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT video_id, title, channel_title, thumbnail FROM video_reactions WHERE user_id=? AND reaction=?', (user_id, reaction))
    videos = [{'id': row[0], 'title': row[1], 'channelTitle': row[2], 'thumbnail': row[3]} for row in cursor.fetchall()]
    conn.close()
    return jsonify({'videos': videos})

# (아래는 기존 회원가입/로그인/플레이리스트 관련 코드 그대로)
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': '사용자 이름과 비밀번호를 모두 입력해주세요.'}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                      (username, hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
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
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': '사용자 이름과 비밀번호를 모두 입력해주세요.'}), 400

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT id, username FROM users WHERE username = ? AND password = ?',
                      (username, hashed_password))
        user = cursor.fetchone()

        if user:
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
    session.clear()
    return jsonify({'message': '로그아웃 되었습니다.'})

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
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