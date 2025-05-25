// DOM 요소
const artistInput = document.getElementById('favorite-artist');
const genreSelect = document.getElementById('favorite-genre');
const moodSelect = document.getElementById('mood');
const recommendBtn = document.getElementById('recommend-btn');
const playlistContainer = document.getElementById('playlist-container');
const statsChartElement = document.getElementById('stats-chart');
const playlistNameInput = document.getElementById('playlist-name');
const createPlaylistBtn = document.getElementById('create-playlist-btn');
const playlistSelect = document.getElementById('playlist-select');
const viewPlaylistBtn = document.getElementById('view-playlist-btn');
const myPlaylistContainer = document.getElementById('my-playlist-container');

// 인증 관련 DOM 요소
const authButton = document.getElementById('auth-button');
const userInfo = document.getElementById('user-info');
const authModal = document.getElementById('auth-modal');
const closeModalBtn = document.querySelector('.close');
const authTabs = document.querySelectorAll('.auth-tab');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const loginBtn = document.getElementById('login-btn');
const registerBtn = document.getElementById('register-btn');
const loginError = document.getElementById('login-error');
const registerError = document.getElementById('register-error');
const playlistSection = document.getElementById('playlist-section');
const playlistLoginMessage = document.getElementById('playlist-login-message');
const playlistControls = document.getElementById('playlist-controls');
const playlistLoginBtn = document.getElementById('playlist-login-btn');

// 페이지 관련 DOM 요소
const navLinks = document.querySelectorAll('.nav-link');
const homePage = document.getElementById('home-page');
const playlistsPage = document.getElementById('playlists-page');

// 좋아요/싫어요 목록/정렬 버튼 DOM
const likedVideosBtn = document.getElementById('liked-videos-btn');
const dislikedVideosBtn = document.getElementById('disliked-videos-btn');
const sortLikesBtn = document.getElementById('sort-likes-btn');

// 차트 객체
let viewsChart = null;

// 현재 선택된 플레이리스트 ID
let currentPlaylistId = null;

// 사용자 인증 상태
let isLoggedIn = false;
let currentUser = null;

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
    // 추천 버튼 클릭 이벤트
    recommendBtn.addEventListener('click', () => getRecommendations(false));

    likedVideosBtn.addEventListener('click', () => loadReactionVideos('like'));
    dislikedVideosBtn.addEventListener('click', () => loadReactionVideos('dislike'));
    sortLikesBtn.addEventListener('click', () => getRecommendations(true));
    
    // 플레이리스트 관련 이벤트
    createPlaylistBtn.addEventListener('click', createPlaylist);
    viewPlaylistBtn.addEventListener('click', viewPlaylist);
    
    // 인증 관련 이벤트
    authButton.addEventListener('click', toggleAuthModal);
    closeModalBtn.addEventListener('click', closeAuthModal);
    authTabs.forEach(tab => {
        tab.addEventListener('click', () => switchAuthTab(tab.dataset.tab));
    });
    loginBtn.addEventListener('click', login);
    registerBtn.addEventListener('click', register);
    playlistLoginBtn.addEventListener('click', toggleAuthModal);
    
    // 내비게이션 이벤트
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.dataset.page;
            switchPage(page);
        });
    });
    
    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target === authModal) {
            closeAuthModal();
        }
    });
    
    // 인증 상태 확인
    checkAuthStatus();
    
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
async function getRecommendations(sortByLikes = false) {
    const artist = artistInput.value;
    const genre = genreSelect.value;
    const mood = moodSelect.value;

    if (!artist && !genre && !mood) {
        alert('최소한 하나의 선호도를 입력해주세요.');
        return;
    }

    playlistContainer.innerHTML = '<p>음악을 검색 중입니다...</p>';

    try {
        const response = await fetch('/api/recommendations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({artist, genre, mood, sortByLikes})
        });

        const data = await response.json();

        if (response.ok) {
            displayResults(data.videos);
            updateStatsChart(data.videos);
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('추천 검색 중 오류 발생:', error);
        playlistContainer.innerHTML = `<p>오류가 발생했습니다: ${error.message}</p>`;
        if (error.message.includes('API')) {
            playlistContainer.innerHTML += `<p>YouTube API 키를 확인해주세요. API 키가 유효하지 않거나 할당량이 초과되었을 수 있습니다.</p>`;
        }
    }
}

// 검색 결과 표시
// 좋아요/싫어요/플레이리스트 버튼 포함해서 결과 출력
function displayResults(videos) {
    playlistContainer.innerHTML = '';

    if (videos.length === 0) {
        playlistContainer.innerHTML = '<p>검색 결과가 없습니다. 다른 선호도를 입력해보세요.</p>';
        return;
    }

    // 최대 9개까지만 보여주기!
    videos.slice(0, 9).forEach(video => {
        const videoElement = document.createElement('div');
        videoElement.className = 'playlist-item';

        // 이하 기존 코드 그대로
        fetch(`/api/video/${video.id}/reaction`)
            .then(res => res.json())
            .then(reactionData => {
                let likeActive = reactionData.user_reaction === "like" ? "active-btn" : "";
                let dislikeActive = reactionData.user_reaction === "dislike" ? "active-btn" : "";
                videoElement.innerHTML = `
                    <div class="video-container">
                        <iframe src="https://www.youtube.com/embed/${video.id}" allowfullscreen></iframe>
                    </div>
                    <div class="video-info">
                        <h3>${video.title}</h3>
                        <p class="channel-name">${video.channelTitle}</p>
                        <p class="view-count">조회수: ${video.formattedViewCount}회</p>
                        <div class="video-actions">
                            <button class="like-btn ${likeActive}" data-video='${JSON.stringify(video)}'>
                                👍 <span class="like-count">${reactionData.likes}</span>
                            </button>
                            <button class="dislike-btn ${dislikeActive}" data-video='${JSON.stringify(video)}'>
                                👎 <span class="dislike-count">${reactionData.dislikes}</span>
                            </button>
                            <button class="add-to-playlist-btn" data-video='${JSON.stringify(video).replace(/'/g, "&#39;")}'>
                                플레이리스트에 추가
                            </button>
                        </div>
                    </div>
                `;

                videoElement.querySelector('.like-btn').onclick = function() {
                    handleReaction(video, "like", reactionData.user_reaction === "like");
                };
                videoElement.querySelector('.dislike-btn').onclick = function() {
                    handleReaction(video, "dislike", reactionData.user_reaction === "dislike");
                };
                videoElement.querySelector('.add-to-playlist-btn').onclick = function() {
                    showPlaylistSelector(video);
                };
            });

        playlistContainer.appendChild(videoElement);
    });
}


async function handleReaction(video, reaction, cancel) {
    const response = await fetch('/api/video/reaction', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            video_id: video.id,
            title: video.title,
            channelTitle: video.channelTitle,
            thumbnail: video.thumbnail,
            reaction,
            cancel
        })
    });
    const result = await response.json();
    if (response.ok) {
        getRecommendations(); // 다시 불러오기(카운트 및 상태 반영)
    } else {
        alert(result.error);
    }
}

async function loadReactionVideos(reaction) {
    const response = await fetch(`/api/user/videos/${reaction}`);
    const data = await response.json();
    displayResults(data.videos);
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

// 인증 관련 함수들
// 인증 상태 확인
async function checkAuthStatus() {
    try {
        const response = await fetch('/api/auth/status');
        const data = await response.json();
        
        if (data.logged_in) {
            isLoggedIn = true;
            currentUser = {
                id: data.user_id,
                username: data.username
            };
            updateAuthUI(true);
            loadPlaylists();
        } else {
            isLoggedIn = false;
            currentUser = null;
            updateAuthUI(false);
        }
    } catch (error) {
        console.error('인증 상태 확인 중 오류 발생:', error);
        isLoggedIn = false;
        currentUser = null;
        updateAuthUI(false);
    }
}

// 페이지 전환
function switchPage(page) {
    // 모든 페이지 숨기기
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    
    // 모든 내비게이션 링크 비활성화
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // 선택한 페이지 표시
    document.getElementById(`${page}-page`).classList.add('active');
    
    // 선택한 내비게이션 링크 활성화
    document.querySelector(`.nav-link[data-page="${page}"]`).classList.add('active');
    
    // 플레이리스트 페이지로 이동하면 플레이리스트 로드 및 자동으로 첫 번째 플레이리스트 표시
    if (page === 'playlists' && isLoggedIn) {
        myPlaylistContainer.innerHTML = ''; // 기존 내용 초기화
        loadPlaylists().then((playlists) => {
            // 이미 선택된 플레이리스트가 있으면 그것을 표시
            if (currentPlaylistId) {
                viewPlaylist();
            } 
            // 없으면서 플레이리스트가 있으면 첫 번째 플레이리스트 자동 선택
            else if (playlistSelect.options.length > 1) {
                playlistSelect.selectedIndex = 1; // 첫 번째 실제 플레이리스트 선택
                viewPlaylist();
            }
            // 플레이리스트가 없을 때만 안내 메시지 표시
            else if (playlists.length === 0) {
                myPlaylistContainer.innerHTML = '<p>플레이리스트가 없습니다. 새 플레이리스트를 생성해보세요.</p>';
            }
        });
    }
}

// 인증 UI 업데이트
function updateAuthUI(loggedIn) {
    if (loggedIn) {
        userInfo.textContent = `${currentUser.username}님`;
        authButton.textContent = '로그아웃';
        playlistLoginMessage.style.display = 'none';
        playlistControls.style.display = 'flex';
    } else {
        userInfo.textContent = '로그인이 필요합니다';
        authButton.textContent = '로그인';
        playlistLoginMessage.style.display = 'block';
        playlistControls.style.display = 'none';
        myPlaylistContainer.innerHTML = '';
    }
}

// 인증 모달 토글
function toggleAuthModal() {
    if (isLoggedIn) {
        logout();
    } else {
        authModal.style.display = 'block';
        switchAuthTab('login');
    }
}

// 인증 모달 닫기
function closeAuthModal() {
    authModal.style.display = 'none';
    loginError.textContent = '';
    registerError.textContent = '';
}

// 인증 탭 전환
function switchAuthTab(tab) {
    authTabs.forEach(t => {
        t.classList.remove('active');
        if (t.dataset.tab === tab) {
            t.classList.add('active');
        }
    });
    
    document.querySelectorAll('.auth-form').forEach(form => {
        form.classList.remove('active');
    });
    
    if (tab === 'login') {
        loginForm.classList.add('active');
    } else {
        registerForm.classList.add('active');
    }
}

// 로그인
async function login() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value.trim();
    
    if (!username || !password) {
        loginError.textContent = '사용자 이름과 비밀번호를 모두 입력해주세요.';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            isLoggedIn = true;
            currentUser = {
                id: data.user_id,
                username: data.username
            };
            updateAuthUI(true);
            closeAuthModal();
            loadPlaylists();
        } else {
            loginError.textContent = data.error || '로그인에 실패했습니다.';
        }
    } catch (error) {
        console.error('로그인 중 오류 발생:', error);
        loginError.textContent = '로그인 중 오류가 발생했습니다.';
    }
}

// 회원가입
async function register() {
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value.trim();
    const passwordConfirm = document.getElementById('register-password-confirm').value.trim();
    
    if (!username || !password) {
        registerError.textContent = '사용자 이름과 비밀번호를 모두 입력해주세요.';
        return;
    }
    
    if (password !== passwordConfirm) {
        registerError.textContent = '비밀번호가 일치하지 않습니다.';
        return;
    }
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            isLoggedIn = true;
            currentUser = {
                id: data.user_id,
                username: data.username
            };
            updateAuthUI(true);
            closeAuthModal();
            loadPlaylists();
            alert('회원가입이 완료되었습니다.');
        } else {
            registerError.textContent = data.error || '회원가입에 실패했습니다.';
        }
    } catch (error) {
        console.error('회원가입 중 오류 발생:', error);
        registerError.textContent = '회원가입 중 오류가 발생했습니다.';
    }
}

// 로그아웃
async function logout() {
    try {
        const response = await fetch('/api/auth/logout', {
            method: 'POST'
        });
        
        if (response.ok) {
            isLoggedIn = false;
            currentUser = null;
            updateAuthUI(false);
        }
    } catch (error) {
        console.error('로그아웃 중 오류 발생:', error);
    }
}

// 플레이리스트 관련 함수들
// 플레이리스트 목록 로드
async function loadPlaylists() {
    if (!isLoggedIn) {
        return Promise.resolve([]);
    }
    
    try {
        const response = await fetch('/api/playlists');
        const data = await response.json();
        
        // 플레이리스트 선택 옵션 업데이트
        updatePlaylistOptions(data.playlists);
        return data.playlists;
    } catch (error) {
        if (error.message.includes('401')) {
            // 인증 오류인 경우 로그인 상태 업데이트
            isLoggedIn = false;
            currentUser = null;
            updateAuthUI(false);
        } else {
            console.error('플레이리스트 로드 중 오류 발생:', error);
        }
        return [];
    }
}

// 플레이리스트 선택 옵션 업데이트
function updatePlaylistOptions(playlists) {
    // 기존 옵션 제거 (첫 번째 기본 옵션 제외)
    while (playlistSelect.options.length > 1) {
        playlistSelect.remove(1);
    }
    
    // 새 옵션 추가
    playlists.forEach(playlist => {
        const option = document.createElement('option');
        option.value = playlist.id;
        option.textContent = `${playlist.name} (${playlist.count}곡)`;
        playlistSelect.appendChild(option);
    });
}

// 새 플레이리스트 생성
async function createPlaylist() {
    const name = playlistNameInput.value.trim();
    
    if (!name) {
        alert('플레이리스트 이름을 입력해주세요.');
        return;
    }
    
    try {
        const response = await fetch('/api/playlists', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            playlistNameInput.value = '';
            loadPlaylists();
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('플레이리스트 생성 중 오류 발생:', error);
        alert(`오류: ${error.message}`);
    }
}

// 플레이리스트 보기
async function viewPlaylist() {
    const playlistId = playlistSelect.value;
    
    if (!playlistId) {
        // 플레이리스트 선택 옵션이 있는지 확인
        if (playlistSelect.options.length <= 1) {
            myPlaylistContainer.innerHTML = '<p>플레이리스트가 없습니다. 새 플레이리스트를 생성해보세요.</p>';
        }
        return;
    }
    
    try {
        const response = await fetch(`/api/playlists/${playlistId}`);
        const data = await response.json();
        
        if (response.ok) {
            currentPlaylistId = playlistId;
            displayPlaylist(data);
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('플레이리스트 로드 중 오류 발생:', error);
        myPlaylistContainer.innerHTML = `<p>오류가 발생했습니다: ${error.message}</p>`;
    }
}

// 플레이리스트 표시
function displayPlaylist(playlistData) {
    myPlaylistContainer.innerHTML = '';
    
    const playlistHeader = document.createElement('div');
    playlistHeader.className = 'playlist-header';
    playlistHeader.innerHTML = `
        <div class="playlist-title-container">
            <h3>${playlistData.name}</h3>
            <button class="delete-playlist-btn" data-playlist-id="${playlistData.id}">
                플레이리스트 삭제
            </button>
        </div>
    `;
    myPlaylistContainer.appendChild(playlistHeader);
    
    // 플레이리스트 삭제 버튼에 이벤트 리스너 추가
    const deleteBtn = playlistHeader.querySelector('.delete-playlist-btn');
    deleteBtn.addEventListener('click', function() {
        const playlistId = this.getAttribute('data-playlist-id');
        if (confirm(`정말로 "${playlistData.name}" 플레이리스트를 삭제하시겠습니까?`)) {
            deletePlaylist(playlistId);
        }
    });
    
    if (playlistData.videos.length === 0) {
        myPlaylistContainer.innerHTML += '<p>플레이리스트가 비어 있습니다.</p>';
        return;
    }
    
    playlistData.videos.forEach(video => {
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
                <p class="channel-name">${video.channelTitle}</p>
                <p class="view-count">조회수: ${video.formattedViewCount}회</p>
                <div class="video-actions">
                    <button class="remove-from-playlist-btn" data-video-id="${video.id}">
                        제거
                    </button>
                </div>
            </div>
        `;
        
        myPlaylistContainer.appendChild(videoElement);
    });
    
    // 제거 버튼에 이벤트 리스너 추가
    document.querySelectorAll('.remove-from-playlist-btn').forEach(button => {
        button.addEventListener('click', function() {
            const videoId = this.getAttribute('data-video-id');
            removeFromPlaylist(currentPlaylistId, videoId);
        });
    });
}

// 플레이리스트 선택 모달 생성
function createPlaylistSelectorModal() {
    // 이미 존재하는 모달이 있으면 제거
    const existingModal = document.getElementById('playlist-selector-modal');
    if (existingModal) {
        document.body.removeChild(existingModal);
    }
    
    // 새 모달 생성
    const modal = document.createElement('div');
    modal.id = 'playlist-selector-modal';
    modal.className = 'modal';
    
    modal.innerHTML = `
        <div class="modal-content playlist-selector-content">
            <span class="close">&times;</span>
            <h3>플레이리스트 선택</h3>
            <p>음악을 추가할 플레이리스트를 선택하세요:</p>
            <div class="playlist-selector-list" id="playlist-selector-list">
                <p>로딩 중...</p>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 닫기 버튼 이벤트
    const closeBtn = modal.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    return modal;
}

// 플레이리스트 선택기 표시
function showPlaylistSelector(video) {
    if (!isLoggedIn) {
        alert('플레이리스트 기능을 사용하려면 로그인이 필요합니다.');
        toggleAuthModal();
        return;
    }
    
    // 플레이리스트 목록 가져오기
    fetch('/api/playlists')
        .then(response => response.json())
        .then(data => {
            if (data.playlists.length === 0) {
                alert('먼저 플레이리스트를 생성해주세요.');
                return;
            }
            
            // 플레이리스트 선택 모달 생성
            const modal = createPlaylistSelectorModal();
            const listContainer = document.getElementById('playlist-selector-list');
            
            // 플레이리스트 목록 표시
            listContainer.innerHTML = '';
            data.playlists.forEach(playlist => {
                const item = document.createElement('div');
                item.className = 'playlist-selector-item';
                item.innerHTML = `
                    <div class="playlist-info">
                        <span class="playlist-name">${playlist.name}</span>
                        <span class="playlist-count">(${playlist.count}곡)</span>
                    </div>
                    <button class="select-playlist-btn">선택</button>
                `;
                
                // 선택 버튼 이벤트
                const selectBtn = item.querySelector('.select-playlist-btn');
                selectBtn.addEventListener('click', () => {
                    addToPlaylist(playlist.id, video);
                    modal.style.display = 'none';
                });
                
                listContainer.appendChild(item);
            });
            
            // 모달 표시
            modal.style.display = 'block';
        })
        .catch(error => {
            console.error('플레이리스트 목록 로드 중 오류 발생:', error);
            alert('플레이리스트 목록을 불러오는 중 오류가 발생했습니다.');
        });
}

// 플레이리스트에 비디오 추가
async function addToPlaylist(playlistId, video) {
    try {
        const response = await fetch(`/api/playlists/${playlistId}/videos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(`"${video.title}"이(가) 플레이리스트에 추가되었습니다.`);
            loadPlaylists();
            
            // 현재 보고 있는 플레이리스트가 업데이트된 플레이리스트라면 새로고침
            if (currentPlaylistId === playlistId) {
                viewPlaylist();
            }
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('플레이리스트에 추가 중 오류 발생:', error);
        alert(`오류: ${error.message}`);
    }
}

// 플레이리스트 삭제
async function deletePlaylist(playlistId) {
    try {
        const response = await fetch(`/api/playlists/${playlistId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            currentPlaylistId = null;
            loadPlaylists();
            myPlaylistContainer.innerHTML = '';
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('플레이리스트 삭제 중 오류 발생:', error);
        alert(`오류: ${error.message}`);
    }
}

// 플레이리스트에서 비디오 제거
async function removeFromPlaylist(playlistId, videoId) {
    try {
        const response = await fetch(`/api/playlists/${playlistId}/videos/${videoId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            alert(data.message);
            loadPlaylists();
            viewPlaylist();
        } else {
            throw new Error(data.error || '알 수 없는 오류가 발생했습니다.');
        }
    } catch (error) {
        console.error('플레이리스트에서 제거 중 오류 발생:', error);
        alert(`오류: ${error.message}`);
    }
}