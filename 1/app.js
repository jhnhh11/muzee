// DOM 요소
const artistInput = document.getElementById('favorite-artist');
const genreSelect = document.getElementById('favorite-genre');
const moodSelect = document.getElementById('mood');
const recommendBtn = document.getElementById('recommend-btn');
const playlistContainer = document.getElementById('playlist-container');
const statsChartElement = document.getElementById('stats-chart');

// 차트 객체
let viewsChart = null;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // 추천 버튼 클릭 이벤트
    recommendBtn.addEventListener('click', getRecommendations);
    
    // DOM 요소 확인
    if (statsChartElement && statsChartElement.getContext) {
        // 초기 차트 생성
        createEmptyChart();
    } else {
        console.error('Canvas 요소를 찾을 수 없거나 getContext를 지원하지 않습니다.');
    }
});

// 빈 차트 생성
function createEmptyChart() {
    const ctx = statsChartElement.getContext('2d');
    viewsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['데이터 없음'],
            datasets: [{
                label: '조회수 분포',
                data: [0],
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '조회수'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '추천 영상'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: '추천 영상 조회수 분포'
                }
            }
        }
    });
}

// 추천 받기
async function getRecommendations() {
    const artist = artistInput.value;
    const genre = genreSelect.value;
    const mood = moodSelect.value;
    
    if (!artist && !genre && !mood) {
        alert('최소한 하나의 선호도를 입력해주세요.');
        return;
    }
    
    // 로딩 표시
    playlistContainer.innerHTML = '<p>음악을 검색 중입니다...</p>';
    
    try {
        // 파이썬 서버에 요청
        const response = await fetch('/api/recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                artist: artist,
                genre: genre,
                mood: mood
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data.videos);
            updateStatsChart(data.videos);
            
            // 콘솔에 결과 출력 (디버깅용)
            console.log('추천 결과:', data.videos);
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('추천 검색 중 오류 발생:', error);
        playlistContainer.innerHTML = `<p>오류가 발생했습니다: ${error.message}</p>`;
        
        // 오류 발생 시 YouTube API 키 문제일 가능성이 높으므로 안내 메시지 추가
        if (error.message.includes('API')) {
            playlistContainer.innerHTML += `<p>YouTube API 키를 확인해주세요. API 키가 유효하지 않거나 할당량이 초과되었을 수 있습니다.</p>`;
        }
    }
}

// 검색 결과 표시
function displayResults(videos) {
    playlistContainer.innerHTML = '';
    
    if (videos.length === 0) {
        playlistContainer.innerHTML = '<p>검색 결과가 없습니다. 다른 선호도를 입력해보세요.</p>';
        return;
    }
    
    videos.forEach(video => {
        const videoElement = document.createElement('div');
        videoElement.className = 'playlist-item';
        
        // 실제 YouTube 임베드 사용
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
                <p class="channel-name">${video.channelTitle}</p>
                <p class="view-count">조회수: ${video.formattedViewCount}회</p>
            </div>
        `;
        
        playlistContainer.appendChild(videoElement);
    });
}

// 통계 차트 업데이트
function updateStatsChart(videos) {
    // Canvas 요소 확인
    if (!statsChartElement || !statsChartElement.getContext) {
        console.error('Canvas 요소를 찾을 수 없거나 getContext를 지원하지 않습니다.');
        return;
    }
    
    // 기존 차트 제거
    if (viewsChart) {
        viewsChart.destroy();
    }
    
    // 차트 데이터 준비
    const labels = videos.map(video => video.title.substring(0, 15) + '...');
    const viewCounts = videos.map(video => video.viewCount);
    
    // 새 차트 생성
    const ctx = statsChartElement.getContext('2d');
    viewsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '조회수',
                data: viewCounts,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: '조회수'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '추천 영상'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: '추천 영상 조회수 분포'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += new Intl.NumberFormat().format(context.parsed.y) + '회';
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
}