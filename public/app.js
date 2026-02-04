/**
 * VGame Horizon - 前端应用
 */

// 状态管理
const state = {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    games: [],
    filteredGames: [],
    selectedGenre: 'all',
    allGenres: [],
    loading: false
};

// DOM 元素（在 init 中初始化，确保 DOM 已加载）
let elements = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    init();
});

function init() {
    // 初始化 DOM 元素引用
    elements = {
        currentMonth: document.getElementById('currentMonth'),
        prevMonth: document.getElementById('prevMonth'),
        nextMonth: document.getElementById('nextMonth'),
        loading: document.getElementById('loading'),
        gameList: document.getElementById('gameList'),
        emptyState: document.getElementById('emptyState'),
        filterBar: document.getElementById('filterBar'),
        filterScroll: document.getElementById('filterScroll'),
        modalOverlay: document.getElementById('modalOverlay'),
        modal: document.getElementById('modal'),
        modalTitle: document.getElementById('modalTitle'),
        modalBody: document.getElementById('modalBody'),
        modalClose: document.getElementById('modalClose')
    };
    
    // 绑定事件
    elements.prevMonth.addEventListener('click', () => changeMonth(-1));
    elements.nextMonth.addEventListener('click', () => changeMonth(1));
    elements.modalClose.addEventListener('click', closeModal);
    elements.modalOverlay.addEventListener('click', (e) => {
        if (e.target === elements.modalOverlay) {
            closeModal();
        }
    });

    // 加载数据
    updateMonthDisplay();
    loadGames();
}

// 更新月份显示
function updateMonthDisplay() {
    elements.currentMonth.textContent = `${state.year}年${state.month}月`;
}

// 切换月份
function changeMonth(delta) {
    state.month += delta;
    
    if (state.month > 12) {
        state.month = 1;
        state.year++;
    } else if (state.month < 1) {
        state.month = 12;
        state.year--;
    }
    
    updateMonthDisplay();
    loadGames();
}

// 加载游戏数据（两阶段：先快速显示，再加载中文名）
async function loadGames() {
    if (state.loading) return;
    
    state.loading = true;
    showLoading(true);
    
    try {
        console.log(`正在加载 ${state.year}年${state.month}月 的游戏数据...`);
        
        // 第一阶段：快速加载（不翻译中文名）
        const response = await fetch(`/api/games?year=${state.year}&month=${state.month}&translate=false`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API 返回错误:', response.status, errorText);
            throw new Error(`加载失败: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API 返回数据:', data);
        state.games = data.games || [];
        state.filteredGames = state.games;
        state.selectedGenre = 'all';
        
        // 提取所有类型并渲染筛选按钮
        extractGenres();
        renderFilterChips();
        renderGames();
        
        // 隐藏加载状态
        state.loading = false;
        showLoading(false);
        
        // 第二阶段：异步加载中文名（不阻塞界面）
        loadChineseNames();
        
    } catch (error) {
        console.error('加载游戏失败:', error);
        showError(`加载失败: ${error.message}`);
        state.loading = false;
        showLoading(false);
    }
}

// 异步加载中文名
async function loadChineseNames() {
    if (state.games.length === 0) return;
    
    console.log('开始异步加载中文名...');
    
    try {
        const response = await fetch(`/api/games?year=${state.year}&month=${state.month}&translate=true`);
        
        if (!response.ok) {
            console.error('加载中文名失败');
            return;
        }
        
        const data = await response.json();
        
        // 检查是否还是同一个月份的数据（用户可能已经切换）
        if (data.year !== state.year || data.month !== state.month) {
            console.log('月份已切换，忽略中文名数据');
            return;
        }
        
        // 更新游戏数据中的中文名
        const cnNameMap = {};
        for (const game of data.games) {
            if (game.name_cn) {
                cnNameMap[game.name] = game.name_cn;
            }
        }
        
        // 更新 state.games
        let hasUpdate = false;
        for (const game of state.games) {
            if (cnNameMap[game.name] && !game.name_cn) {
                game.name_cn = cnNameMap[game.name];
                hasUpdate = true;
            }
        }
        
        // 如果有更新，重新渲染
        if (hasUpdate) {
            console.log('中文名加载完成，更新界面');
            renderGames();
        }
        
    } catch (error) {
        console.error('加载中文名出错:', error);
    }
}

// 显示/隐藏加载状态
function showLoading(show) {
    console.log('showLoading:', show);
    if (show) {
        elements.loading.classList.remove('hidden');
        elements.loading.style.display = 'flex';
        elements.gameList.style.display = 'none';
        elements.emptyState.style.display = 'none';
    } else {
        elements.loading.classList.add('hidden');
        elements.loading.style.display = 'none';
        // 不在这里设置 gameList 的显示，由 renderGames 或 showError 处理
    }
}

// 显示错误
function showError(message) {
    elements.emptyState.innerHTML = `<p>${message}</p>`;
    elements.emptyState.style.display = 'flex';
    elements.gameList.style.display = 'none';
}

// 提取所有游戏类型
function extractGenres() {
    const genreSet = new Set();
    
    for (const game of state.games) {
        if (game.genres && Array.isArray(game.genres)) {
            for (const genre of game.genres) {
                if (genre) genreSet.add(genre);
            }
        }
    }
    
    // 按字母排序
    state.allGenres = Array.from(genreSet).sort();
    console.log('提取到的游戏类型:', state.allGenres);
}

// 渲染筛选按钮
function renderFilterChips() {
    if (!elements.filterScroll) {
        console.error('filterScroll 元素不存在');
        return;
    }
    
    // 如果没有类型，隐藏筛选栏
    if (state.allGenres.length === 0) {
        elements.filterBar.style.display = 'none';
        return;
    }
    
    let html = `<button class="filter-chip ${state.selectedGenre === 'all' ? 'active' : ''}" data-genre="all">全部</button>`;
    
    for (const genre of state.allGenres) {
        const isActive = state.selectedGenre === genre;
        html += `<button class="filter-chip ${isActive ? 'active' : ''}" data-genre="${escapeHtml(genre)}">${escapeHtml(genre)}</button>`;
    }
    
    elements.filterScroll.innerHTML = html;
    
    // 显示筛选栏
    elements.filterBar.style.display = 'block';
    
    // 绑定点击事件
    elements.filterScroll.querySelectorAll('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const genre = chip.dataset.genre;
            selectGenre(genre);
        });
    });
}

// 选择类型筛选
function selectGenre(genre) {
    state.selectedGenre = genre;
    
    // 更新按钮状态
    elements.filterScroll.querySelectorAll('.filter-chip').forEach(chip => {
        chip.classList.toggle('active', chip.dataset.genre === genre);
    });
    
    // 筛选游戏
    if (genre === 'all') {
        state.filteredGames = state.games;
    } else {
        state.filteredGames = state.games.filter(game => 
            game.genres && game.genres.includes(genre)
        );
    }
    
    // 重新渲染
    renderGames();
}

// 渲染游戏列表
function renderGames() {
    const gamesToRender = state.filteredGames || state.games;
    console.log('渲染游戏列表, 数量:', gamesToRender.length);
    
    if (!gamesToRender || gamesToRender.length === 0) {
        elements.gameList.innerHTML = '';
        elements.gameList.style.display = 'none';
        const message = state.selectedGenre === 'all' ? '本月暂无新游数据' : `本月暂无「${state.selectedGenre}」类型游戏`;
        elements.emptyState.innerHTML = `<p>${message}</p>`;
        elements.emptyState.style.display = 'flex';
        return;
    }
    
    elements.emptyState.style.display = 'none';
    elements.gameList.style.display = 'block';
    
    // 按日期分组
    const grouped = groupByDate(gamesToRender);
    
    // 生成 HTML
    let html = '';
    
    for (const [date, games] of Object.entries(grouped)) {
        html += `
            <div class="date-group">
                <div class="date-header">
                    <span class="date-badge">${formatDateBadge(date)}</span>
                    <div class="date-line"></div>
                </div>
                ${games.map(game => renderGameCard(game)).join('')}
            </div>
        `;
    }
    
    elements.gameList.innerHTML = html;
    
    // 绑定卡片点击事件（仅对可点击的卡片）
    document.querySelectorAll('.game-card.clickable').forEach(card => {
        card.addEventListener('click', () => {
            const searchName = card.dataset.searchName;
            const fallbackName = card.dataset.fallbackName;
            openGameDetail(searchName, fallbackName);
        });
    });
}

// 按日期分组
function groupByDate(games) {
    const groups = {};
    
    for (const game of games) {
        const date = game.release_date || 'TBA';
        if (!groups[date]) {
            groups[date] = [];
        }
        groups[date].push(game);
    }
    
    // 按日期排序
    const sorted = {};
    Object.keys(groups).sort().forEach(key => {
        sorted[key] = groups[key];
    });
    
    return sorted;
}

// 格式化日期徽章
function formatDateBadge(dateStr) {
    if (dateStr === 'TBA') return '待定';
    
    const date = new Date(dateStr);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    
    return `${month}月${day}日`;
}

// 渲染游戏卡片
function renderGameCard(game) {
    const title = game.name_cn || game.name;
    const showEnName = game.name_cn && game.name_cn !== game.name;
    
    const coverHtml = game.cover_url
        ? `<img src="${game.cover_url}" alt="${title}" loading="lazy">`
        : `<div class="game-cover-placeholder">暂无封面</div>`;
    
    const genresHtml = game.genres.slice(0, 3).map(g => 
        `<span class="game-tag">${g}</span>`
    ).join('');
    
    // 存储中文名和英文名，用于查询
    const searchName = game.name_cn || game.name;
    const fallbackName = game.name; // 英文名作为备用
    
    // 只有知名游戏才显示"明星团队"按钮
    const hintHtml = game.is_notable 
        ? `<div class="game-card-hint notable">
                <span class="notable-badge">⭐ 明星团队</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
            </div>`
        : '';
    
    // 只有知名游戏的卡片才可点击
    const cardClass = game.is_notable ? 'game-card clickable' : 'game-card';
    const dataAttrs = game.is_notable 
        ? `data-search-name="${escapeHtml(searchName)}" data-fallback-name="${escapeHtml(fallbackName)}"`
        : '';
    
    return `
        <div class="${cardClass}" ${dataAttrs}>
            <div class="game-card-inner">
                <div class="game-cover">
                    ${coverHtml}
                </div>
                <div class="game-info">
                    <div class="game-title">${escapeHtml(title)}</div>
                    ${showEnName ? `<div class="game-title-en">${escapeHtml(game.name)}</div>` : ''}
                    <div class="game-meta">${genresHtml}</div>
                    <div class="game-developer">${escapeHtml(game.developer || '未知开发商')}</div>
                    ${game.summary ? `<div class="game-summary">${escapeHtml(truncate(game.summary, 60))}</div>` : ''}
                </div>
            </div>
            ${hintHtml}
        </div>
    `;
}

// 打开游戏详情
async function openGameDetail(searchName, fallbackName) {
    elements.modalTitle.textContent = searchName;
    elements.modalBody.innerHTML = `
        <div class="detail-loading">
            <div class="spinner"></div>
            <p>正在获取制作团队信息...</p>
        </div>
    `;
    
    elements.modalOverlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    
    try {
        // 构建查询 URL，包含备用名
        let url = `/api/games/${encodeURIComponent(searchName)}/detail`;
        if (fallbackName && fallbackName !== searchName) {
            url += `?fallback_name=${encodeURIComponent(fallbackName)}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('获取详情失败');
        }
        
        const detail = await response.json();
        renderGameDetail(detail);
    } catch (error) {
        console.error('获取详情失败:', error);
        elements.modalBody.innerHTML = `
            <div class="detail-empty">
                <p>未能获取制作团队信息</p>
                <p style="margin-top: 8px; font-size: 12px;">该游戏可能是独立游戏或信息较少</p>
            </div>
        `;
    }
}

// 渲染游戏详情
function renderGameDetail(detail) {
    let html = '';
    
    // 监督/导演
    if (detail.directors && detail.directors.length > 0) {
        html += renderDetailSection('监督/导演', 'director', detail.directors);
    }
    
    // 编剧
    if (detail.writers && detail.writers.length > 0) {
        html += renderDetailSection('编剧/剧本', 'writer', detail.writers);
    }
    
    // 作曲
    if (detail.composers && detail.composers.length > 0) {
        html += renderDetailSection('作曲/音乐', 'composer', detail.composers);
    }
    
    // 制作人
    if (detail.producers && detail.producers.length > 0) {
        html += renderDetailSection('制作人', 'producer', detail.producers);
    }
    
    // 系列
    if (detail.series) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    </svg>
                    所属系列
                </div>
                <div class="detail-tag-list">
                    <span class="detail-tag">${escapeHtml(detail.series)}</span>
                </div>
            </div>
        `;
    }
    
    // 关联作品
    if (detail.related_games && detail.related_games.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="2" y1="12" x2="22" y2="12"></line>
                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                    </svg>
                    关联作品
                </div>
                <div class="detail-tag-list">
                    ${detail.related_games.map(g => `<span class="detail-tag">${escapeHtml(g)}</span>`).join('')}
                </div>
            </div>
        `;
    }
    
    // 亮点
    if (detail.highlights && detail.highlights.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                    值得关注
                </div>
                ${detail.highlights.map(h => `<div class="detail-highlight">${escapeHtml(h)}</div>`).join('')}
            </div>
        `;
    }
    
    // 如果没有任何信息
    if (!html) {
        html = `
            <div class="detail-empty">
                <p>暂未找到该游戏的详细制作信息</p>
                <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
                    可能是独立游戏、新作或小众作品
                </p>
            </div>
        `;
    }
    
    elements.modalBody.innerHTML = html;
}

// 渲染详情区块
function renderDetailSection(title, type, people) {
    const icons = {
        director: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"></path><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>',
        writer: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 19l7-7 3 3-7 7-3-3z"></path><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path></svg>',
        composer: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>',
        producer: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'
    };
    
    return `
        <div class="detail-section">
            <div class="detail-section-title">
                ${icons[type] || ''}
                ${title}
            </div>
            ${people.map(p => `
                <div class="detail-person">
                    <div class="detail-person-name">${escapeHtml(p.name)}</div>
                    ${p.known_for && p.known_for.length > 0 
                        ? `<div class="detail-person-works">代表作：${escapeHtml(p.known_for.join('、'))}</div>` 
                        : ''}
                </div>
            `).join('')}
        </div>
    `;
}

// 关闭弹窗
function closeModal() {
    elements.modalOverlay.classList.remove('active');
    document.body.style.overflow = '';
}

// 工具函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength) + '...';
}
