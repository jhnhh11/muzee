// YouTube API 키 (실제 사용 시 본인의 API 키로 교체해야 합니다)
const API_KEY = 'AIzaSyA7s7Fz9_o2JgklfJPlPMXYlgbvsza1_L0';

// YouTube API 로드
function loadYouTubeApi() {
    console.log('YouTube API 로드 시작...');
    gapi.load('client', initClient);
}

// API 클라이언트 초기화
function initClient() {
    console.log('YouTube API 클라이언트 초기화 시작...');
    gapi.client.init({
        apiKey: API_KEY,
        discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/youtube/v3/rest']
    }).then(() => {
        console.log('YouTube API 클라이언트가 초기화되었습니다.');
        document.getElementById('recommend-btn').addEventListener('click', getRecommendations);
        
        // API 키가 유효한지 테스트
        testApiKey();
    }).catch(error => {
        console.error('YouTube API 클라이언트 초기화 중 오류 발생:', error);
        alert('YouTube API 초기화 중 오류가 발생했습니다: ' + error.message + '\n\nAPI 키를 확인해주세요.');
    });
}

// API 키 테스트
function testApiKey() {
    gapi.client.youtube.channels.list({
        part: 'snippet',
        id: 'UC_x5XG1OV2P6uZZ5FSM9Ttw' // Google Developers 채널 ID
    }).then(response => {
        console.log('API 키 테스트 성공:', response);
    }).catch(error => {
        console.error('API 키 테스트 실패:', error);
        if (error.result && error.result.error) {
            if (error.result.error.code === 403) {
                alert('YouTube API 키가 유효하지 않거나 할당량이 초과되었습니다. API 키를 확인해주세요.');
            }
        }
    });
}

// 추천 받기 버튼 클릭 시 실행되는 함수
async function getRecommendations() {
    const artist = document.getElementById('favorite-artist').value;
    const genre = document.getElementById('favorite-genre').value;
    const mood = document.getElementById('mood').value;
    
    if (!artist && !genre && !mood) {
        alert('최소한 하나의 선호도를 입력해주세요.');
        return;
    }
    
    // 로딩 표시
    const playlistContainer = document.getElementById('playlist-container');
    playlistContainer.innerHTML = '<p>음악을 검색 중입니다...</p>';
    
    try {
        // 검색어 생성
        let searchQuery = '';
        if (artist) searchQuery += `${artist} `;
        if (genre) searchQuery += `${genre} music `;
        if (mood) searchQuery += `${mood} music`;
        
        console.log('검색어:', searchQuery);
        
        // YouTube API가 초기화되었는지 확인
        if (!gapi.client.youtube) {
            throw new Error('YouTube API가 초기화되지 않았습니다. 페이지를 새로고침하고 다시 시도해주세요.');
        }
        
        // YouTube API 검색 요청
        const response = await gapi.client.youtube.search.list({
            part: 'snippet',
            q: searchQuery,
            type: 'video',
            videoCategoryId: '10', // 음악 카테고리
            maxResults: 10
        });
        
        console.log('API 응답:', response);
        
        // 검색 결과 표시
        displayResults(response.result.items);
    } catch (error) {
        console.error('추천 검색 중 오류 발생:', error);
        alert('추천을 가져오는 중 오류가 발생했습니다: ' + error.message);
        playlistContainer.innerHTML = '<p>오류가 발생했습니다. 다시 시도해주세요.</p>';
    }
}

// 검색 결과 표시 함수
function displayResults(videos) {
    const playlistContainer = document.getElementById('playlist-container');
    playlistContainer.innerHTML = '';
    
    if (videos.length === 0) {
        playlistContainer.innerHTML = '<p>검색 결과가 없습니다. 다른 선호도를 입력해보세요.</p>';
        return;
    }
    
    videos.forEach(video => {
        const videoId = video.id.videoId;
        const title = video.snippet.title;
        const channelTitle = video.snippet.channelTitle;
        const thumbnail = video.snippet.thumbnails.high.url;
        
        const videoElement = document.createElement('div');
        videoElement.className = 'playlist-item';
        videoElement.innerHTML = `
            <div class="video-container">
                <iframe src="https://www.youtube.com/embed/${videoId}" 
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                </iframe>
            </div>
            <div class="video-info">
                <h3>${title}</h3>
                <p>${channelTitle}</p>
            </div>
        `;
        
        playlistContainer.appendChild(videoElement);
    });
}

// 페이지 로드 시 YouTube API 로드
window.onload = loadYouTubeApi;