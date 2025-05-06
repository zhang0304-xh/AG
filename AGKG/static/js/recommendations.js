document.addEventListener('DOMContentLoaded', function() {
    const filterChips = document.querySelectorAll('.filter-chip');
    const refreshBtn = document.getElementById('refreshBtn');
    const refreshIcon = refreshBtn.querySelector('i');
    let currentSource = 'all';
    
    // 获取登录用户信息
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}');
    const userId = userInfo.user_id;
    
    // 加载推荐内容
    loadRecommendations();
    
    // 筛选切换
    filterChips.forEach(chip => {
        chip.addEventListener('click', function() {
            if (this.classList.contains('active')) return;
            
            filterChips.forEach(c => c.classList.remove('active'));
            this.classList.add('active');
            currentSource = this.dataset.source;
            loadRecommendations();
        });
    });
    
    // 刷新按钮点击事件
    refreshBtn.addEventListener('click', function() {
        refreshIcon.classList.add('refresh-spin');
        loadRecommendations().finally(() => {
            setTimeout(() => {
                refreshIcon.classList.remove('refresh-spin');
            }, 500);
        });
    });
    
    // 加载推荐内容函数
    function loadRecommendations() {
        if (!userId) {
            document.getElementById('noRecommendations').style.display = 'block';
            document.getElementById('noRecommendations').innerHTML = `
                <div class="bg-light rounded p-4">
                    <i class="fas fa-user-lock fa-2x text-muted mb-3"></i>
                    <p class="mb-3">请先登录以获取个性化推荐</p>
                    <a href="/login" class="btn btn-primary btn-sm">
                        <i class="fas fa-sign-in-alt me-1"></i>登录
                    </a>
                </div>
            `;
            return Promise.resolve();
        }

        document.getElementById('loadingIndicator').style.display = 'block';
        document.getElementById('recommendationsContainer').innerHTML = '';
        document.getElementById('noRecommendations').style.display = 'none';
        
        const apiUrl = `/api/recommendations/user/${userId}${currentSource !== 'all' ? '?source=' + currentSource : ''}`;
        
        return fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                document.getElementById('loadingIndicator').style.display = 'none';
                
                if (data.status === 'success' && data.data.recommendations && data.data.recommendations.length > 0) {
                    renderRecommendations(data.data.recommendations);
                } else {
                    document.getElementById('noRecommendations').style.display = 'block';
                    document.getElementById('noRecommendations').innerHTML = `
                        <div class="bg-light rounded p-4">
                            <i class="fas fa-search fa-2x text-muted mb-3"></i>
                            <p class="mb-3">暂无推荐内容</p>
                            <a href="/crop_qa" class="btn btn-primary btn-sm">
                                <i class="fas fa-search me-1"></i>开始搜索
                            </a>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error fetching recommendations:', error);
                document.getElementById('loadingIndicator').style.display = 'none';
                document.getElementById('noRecommendations').style.display = 'block';
                document.getElementById('noRecommendations').innerHTML = `
                    <div class="bg-light rounded p-4">
                        <i class="fas fa-exclamation-triangle fa-2x text-warning mb-3"></i>
                        <p class="mb-3">获取推荐内容时出错</p>
                        <button class="btn btn-primary btn-sm" onclick="location.reload()">
                            <i class="fas fa-sync-alt me-1"></i>重试
                        </button>
                    </div>
                `;
            });
    }
    
    // 渲染推荐内容
    function renderRecommendations(recommendations) {
        const container = document.getElementById('recommendationsContainer');
        
        recommendations.forEach(rec => {
            const cardDiv = document.createElement('div');
            cardDiv.className = 'col-md-6 col-lg-4 mb-4';
            
            let badgeClass = 'bg-primary';
            let icon = 'fas fa-lightbulb';
            let sourceText = rec.source_text || '知识图谱推荐';
            
            if (rec.source === 'Popular') {
                badgeClass = 'bg-info';
                icon = 'fas fa-fire';
            }
            
            cardDiv.innerHTML = `
                <div class="card recommendation-card">
                    <div class="card-body">
                        <span class="badge ${badgeClass} source-badge">
                            <i class="${icon}"></i>${sourceText}
                        </span>
                        <h5 class="card-title">${rec.name}</h5>
                        ${rec.category ? `
                            <div class="mb-2">
                                <span class="badge bg-light text-dark">
                                    <i class="fas fa-tag me-1"></i>${rec.category}
                                </span>
                            </div>
                        ` : ''}
                        <div class="d-flex align-items-center mb-3">
                            ${rec.frequency ? `
                                <div class="visit-count">
                                    <i class="fas fa-chart-bar me-1"></i>${rec.frequency} 次浏览
                                </div>
                            ` : ''}
                            ${rec.score ? `
                                <div class="similarity-score">
                                    <i class="fas fa-chart-line me-1"></i>${(rec.score * 100).toFixed(1)}% 相关度
                                </div>
                            ` : ''}
                        </div>
                        <div class="card-actions">
                            <a href="/crop_qa?q=${encodeURIComponent(rec.name)}" class="btn btn-outline-primary btn-sm">
                                <i class="fas fa-search me-1"></i>查看详情
                            </a>
                        </div>
                    </div>
                </div>
            `;
            
            container.appendChild(cardDiv);
        });
    }
}); 