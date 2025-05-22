// YouTube API 없이 작동하는 대체 기능
// 미리 정의된 플레이리스트 데이터

const fallbackPlaylists = {
    "kpop": [
        {
            id: "dYRs7Q1vQ24",
            title: "NewJeans - Super Shy",
            channel: "NewJeans"
        },
        {
            id: "pyf8cbqyfPs",
            title: "IU - Celebrity",
            channel: "IU Official"
        },
        {
            id: "gdZLi9oWNZg",
            title: "BTS - Dynamite",
            channel: "HYBE LABELS"
        }
    ],
    "pop": [
        {
            id: "kTJczUoc26U",
            title: "The Weeknd - Blinding Lights",
            channel: "The Weeknd"
        },
        {
            id: "JGwWNGJdvx8",
            title: "Ed Sheeran - Shape of You",
            channel: "Ed Sheeran"
        },
        {
            id: "RsEZmictANA",
            title: "Taylor Swift - All Too Well",
            channel: "Taylor Swift"
        }
    ],
    "rock": [
        {
            id: "fJ9rUzIMcZQ",
            title: "Queen - Bohemian Rhapsody",
            channel: "Queen Official"
        },
        {
            id: "1w7OgIMMRc4",
            title: "Imagine Dragons - Believer",
            channel: "ImagineDragons"
        }
    ]
};

// 대체 추천 함수
function getFallbackRecommendations() {
    const artist = document.getElementById('favorite-artist').value.toLowerCase();
    const genre = document.getElementById('favorite-genre').value;
    const mood = document.getElementById('mood').value;
    
    if (!artist && !genre && !mood) {
        alert('최소한 하나의 선호도를 입력해주세요.');
        return;
    }
    
    // 로딩 표시
    const playlistContainer = document.getElementById('playlist-container');
    playlistContainer.innerHTML = '<p>음악을 검색 중입니다...</p>';
    
    // 간단한 추천 로직
    let recommendedVideos = [];
    
    if (genre && fallbackPlaylists[genre]) {
        recommendedVideos = fallbackPlaylists[genre];
    } else if (artist.includes('bts') || artist.includes('방탄')) {
        recommendedVideos = fallbackPlaylists['kpop'];
    } else if (artist.includes('taylor') || artist.includes('ed sheeran')) {
        recommendedVideos = fallbackPlaylists['pop'];
    } else if (artist.includes('queen') || artist.includes('imagine dragons')) {
        recommendedVideos = fallbackPlaylists['rock'];
    } else {
        // 기본값으로 kpop 반환
        recommendedVideos = fallbackPlaylists['kpop'];
    }
    
    // 결과 표시
    displayFallbackResults(recommendedVideos);
}

// 대체 결과 표시 함수
function displayFallbackResults(videos) {
    const playlistContainer = document.getElementById('playlist-container');
    playlistContainer.innerHTML = '';
    
    if (videos.length === 0) {
        playlistContainer.innerHTML = '<p>검색 결과가 없습니다. 다른 선호도를 입력해보세요.</p>';
        return;
    }
    
    videos.forEach(video => {
        const videoElement = document.createElement('div');
        videoElement.className = 'playlist-item';
        videoElement.innerHTML = `
            <div class="video-container">
                <iframe src="https://www.youtube.com/embed/${video.id}" 
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                </iframe>
            </div>
            <div class="video-info">
                <h3>${video.title}</h3>
                <p>${video.channel}</p>
            </div>
        `;
        
        playlistContainer.appendChild(videoElement);
    });
}