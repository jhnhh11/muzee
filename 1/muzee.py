import os
import json
import requests
from flask import Flask, render_template, request, jsonify, send_from_directory

app = Flask(__name__)

# YouTube API 키
API_KEY = 'AIzaSyA7s7Fz9_o2JgklfJPlPMXYlgbvsza1_L0'


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
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        return jsonify({'error': f'추천을 가져오는 중 오류가 발생했습니다: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5500)