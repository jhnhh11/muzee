from flask import Flask, render_template, request, jsonify
import googleapiclient.discovery
import os
import random
import numpy as np
from scipy import stats
import json

app = Flask(__name__)

# YouTube API 키
API_KEY = 'AIzaSyDr2o46a-5qhYDle7iHhQGcz8mcBzmVfTI'

# YouTube API 클라이언트 생성
def get_youtube_client():
    return googleapiclient.discovery.build('youtube', 'v3', developerKey=API_KEY)

# 확률적 가중치를 적용한 추천 함수
def apply_probabilistic_weights(videos, preference_strength=0.7):
    # 조회수에 따른 확률 분포 생성
    view_counts = np.array([int(video['statistics']['viewCount']) for video in videos])
    
    # 조회수가 높을수록 선택될 확률이 높아지도록 가중치 설정
    weights = stats.rankdata(view_counts) ** preference_strength
    
    # 가중치에 따라 비디오 정렬
    indices = np.argsort(-weights)
    return [videos[i] for i in indices]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    data = request.json
    artist = data.get('artist', '')
    genre = data.get('genre', '')
    mood = data.get('mood', '')
    
    if not any([artist, genre, mood]):
        return jsonify({'error': '최소한 하나의 선호도를 입력해주세요.'}), 400
    
    # 검색어 생성
    search_query = ''
    if artist:
        search_query += f"{artist} "
    if genre:
        search_query += f"{genre} music "
    if mood:
        search_query += f"{mood} music"
    
    try:
        youtube = get_youtube_client()
        
        # 비디오 검색
        search_response = youtube.search().list(
            q=search_query,
            part='id',
            type='video',
            videoCategoryId='10',  # 음악 카테고리
            maxResults=20
        ).execute()
        
        video_ids = [item['id']['videoId'] for item in search_response['items']]
        
        if not video_ids:
            return jsonify({'error': '검색 결과가 없습니다.'}), 404
        
        # 비디오 상세 정보 가져오기 (조회수 포함)
        videos_response = youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids)
        ).execute()
        
        videos = videos_response['items']
        
        # 확률적 가중치를 적용하여 비디오 정렬
        sorted_videos = apply_probabilistic_weights(videos)
        
        # 필요한 정보만 추출
        results = []
        for video in sorted_videos:
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
    app.run(debug=True)