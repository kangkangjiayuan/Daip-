// 新闻展示功能实现
class NewsDisplay {
    constructor() {
        this.currentNews = [];
        this.currentPage = 1;
        this.newsPerPage = 10;
        this.isPlaying = false;
        this.audioPlayer = null;
        this.playStartTime = null;
    }

    // 初始化新闻展示功能
    init() {
        this.createNewsModal();
        this.bindEvents();
        console.log('新闻展示功能已初始化');
    }

    // 创建新闻模态框
    createNewsModal() {
        const modalHTML = `
            <div id="news-overlay" class="news-overlay">
                <div id="news-modal" class="news-modal">
                    <div class="news-header">
                <h2>📰 最新新闻</h2>
                <button id="close-news-modal" class="close-btn">&times;</button>
            </div>
                    <div class="news-controls">
                        <button id="refresh-news" class="control-btn">🔄 刷新</button>
                        <button id="play-news" class="control-btn">▶️ 播报</button>
                        <span id="play-timer" class="play-timer">00:00</span>
                    </div>
                    <div id="news-content" class="news-content">
                        <div id="news-loading" class="loading">正在加载新闻...</div>
                        <div id="news-list" class="news-list"></div>
                    </div>
                    <div class="news-footer">
                        <button id="prev-page" class="page-btn">⬅️ 上一页</button>
                        <span id="page-info" class="page-info">第 1 页</span>
                        <button id="next-page" class="page-btn">下一页 ➡️</button>
                    </div>
                </div>
            </div>
        `;

        // 添加样式
        const style = document.createElement('style');
        style.textContent = `
            .news-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.7);
                backdrop-filter: blur(5px);
                z-index: 9999;
                justify-content: center;
                align-items: center;
            }

            .news-modal {
                background: white;
                border-radius: 15px;
                width: 90%;
                max-width: 800px;
                min-height: 500px;
                max-height: 80vh;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                display: flex;
                flex-direction: column;
            }

            .news-header {
                background: linear-gradient(45deg, #4A90E2, #5E60CE);
                color: white;
                padding: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .news-header h2 {
                margin: 0;
                font-size: 1.5rem;
            }

            .close-btn {
                background: none;
                border: none;
                color: white;
                font-size: 2rem;
                cursor: pointer;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background 0.2s;
            }

            .close-btn:hover {
                background: rgba(255, 255, 255, 0.2);
            }

            .news-controls {
                padding: 15px 20px;
                background: #f8f9fa;
                display: flex;
                gap: 10px;
                align-items: center;
                border-bottom: 1px solid #eee;
                flex-wrap: wrap;
            }

            .control-btn {
                padding: 12px 20px;
                border: none;
                border-radius: 25px;
                background: linear-gradient(45deg, #4A90E2, #5E60CE);
                color: white;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 500;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 6px;
                min-width: 100px;
                justify-content: center;
                flex-shrink: 0;
            }

            .control-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
            }

            .play-timer {
                margin-left: auto;
                font-weight: bold;
                color: #4A90E2;
            }

            .news-content {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                min-height: 250px;
            }

            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
                font-style: italic;
            }

            .news-list {
                display: grid;
                gap: 15px;
            }

            .news-item {
                padding: 15px;
                border-radius: 10px;
                background: #f8f9fa;
                border: 1px solid #eee;
                transition: all 0.3s ease;
                cursor: pointer;
            }

            .news-item:hover {
                transform: translateY(-3px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
                border-color: #4A90E2;
            }

            .news-title {
                font-weight: bold;
                font-size: 1.1rem;
                margin-bottom: 8px;
                color: #333;
            }

            .news-date {
                font-size: 0.85rem;
                color: #666;
                margin-bottom: 10px;
            }

            .news-content-preview {
                font-size: 0.95rem;
                color: #555;
                line-height: 1.5;
            }

            .news-footer {
                padding: 15px 20px;
                background: #f8f9fa;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 15px;
                border-top: 1px solid #eee;
                flex-wrap: wrap;
            }

            .page-btn {
                padding: 10px 20px;
                border: 1px solid #ddd;
                background: white;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 1rem;
                font-weight: 500;
                display: flex;
                align-items: center;
                gap: 6px;
                min-width: 100px;
                justify-content: center;
                flex-shrink: 0;
            }

            .page-btn:hover:not(:disabled) {
                background: #4A90E2;
                color: white;
                border-color: #4A90E2;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(74, 144, 226, 0.2);
            }

            .page-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
                color: #999;
            }

            .page-info {
                font-weight: bold;
                color: #333;
                padding: 0 15px;
                white-space: nowrap;
            }

            @media (max-width: 768px) {
                .news-modal {
                    width: 95%;
                    height: 90vh;
                }
                
                .news-content {
                    padding: 15px;
                }
                
                .news-item {
                    padding: 12px;
                }
            }
        `;

        document.head.appendChild(style);
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    // 绑定事件
    bindEvents() {
        // 关闭模态框
        document.getElementById('close-news-modal').addEventListener('click', () => {
            this.hideNewsModal();
        });

        // 点击遮罩关闭模态框
        document.getElementById('news-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'news-overlay') {
                this.hideNewsModal();
            }
        });

        // 按ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && document.getElementById('news-overlay').style.display === 'flex') {
                this.hideNewsModal();
            }
        });

        // 刷新新闻
        document.getElementById('refresh-news').addEventListener('click', () => {
            this.loadNews();
        });

        // 播报新闻
        document.getElementById('play-news').addEventListener('click', () => {
            this.toggleNewsPlayback();
        });

        // 分页按钮
        document.getElementById('prev-page').addEventListener('click', () => {
            this.showPage(this.currentPage - 1);
        });

        document.getElementById('next-page').addEventListener('click', () => {
            this.showPage(this.currentPage + 1);
        });
    }

    // 显示新闻模态框
    showNewsModal() {
        document.getElementById('news-overlay').style.display = 'flex';
        // 如果还没有加载过新闻，则加载新闻
        if (this.currentNews.length === 0) {
            this.loadNews();
        }
    }

    // 隐藏新闻模态框
    hideNewsModal() {
        document.getElementById('news-overlay').style.display = 'none';
        // 停止播报
        this.stopNewsPlayback();
    }

    // 加载新闻
    async loadNews() {
        try {
            // 显示加载状态
            document.getElementById('news-loading').style.display = 'block';
            document.getElementById('news-list').innerHTML = '';

            // 调用API获取新闻
            const response = await fetch('/api/news/latest');
            const result = await response.json();

            if (result.success) {
                this.currentNews = result.data;
                this.currentPage = 1;
                this.showPage(1);
            } else {
                throw new Error(result.error || '获取新闻失败');
            }
        } catch (error) {
            console.error('加载新闻失败:', error);
            document.getElementById('news-list').innerHTML = `
                <div class="error-message">
                    加载新闻失败: ${error.message}
                    <button onclick="newsDisplay.loadNews()" class="retry-btn">重试</button>
                </div>
            `;
        } finally {
            document.getElementById('news-loading').style.display = 'none';
        }
    }

    // 显示指定页码的新闻
    showPage(page) {
        if (page < 1 || (page - 1) * this.newsPerPage >= this.currentNews.length) return;

        this.currentPage = page;
        const startIndex = (page - 1) * this.newsPerPage;
        const endIndex = Math.min(startIndex + this.newsPerPage, this.currentNews.length);
        const pageNews = this.currentNews.slice(startIndex, endIndex);

        let newsHTML = '';
        pageNews.forEach((news, index) => {
            newsHTML += `
                <div class="news-item" data-index="${startIndex + index}">
                    <div class="news-title">${news.title || '无标题'}</div>
                    <div class="news-date">${news.date || '未知日期'}</div>
                    <div class="news-content-preview">${news.content || '暂无内容'}</div>
                </div>
            `;
        });

        document.getElementById('news-list').innerHTML = newsHTML;

        // 更新分页信息
        document.getElementById('page-info').textContent = `第 ${page} 页`;
        document.getElementById('prev-page').disabled = page === 1;
        document.getElementById('next-page').disabled = endIndex >= this.currentNews.length;

        // 绑定新闻项点击事件
        document.querySelectorAll('.news-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.getAttribute('data-index'));
                this.showNewsDetail(index);
            });
        });
    }

    // 显示新闻详情（暂时只在控制台打印）
    showNewsDetail(index) {
        const news = this.currentNews[index];
        console.log('查看新闻详情:', news);
        // 这里可以扩展为显示新闻详情模态框
        alert(`新闻标题: ${news.title}\n\n发布日期: ${news.date}\n\n内容: ${news.content}`);
    }

    // 切换新闻播报
    toggleNewsPlayback() {
        if (this.isPlaying) {
            this.stopNewsPlayback();
        } else {
            this.startNewsPlayback();
        }
    }

    // 开始新闻播报
    startNewsPlayback() {
        if (this.currentNews.length === 0) {
            alert('没有可播报的新闻');
            return;
        }

        this.isPlaying = true;
        document.getElementById('play-news').textContent = '⏹️ 停止';

        // 创建音频播放器（模拟播报）
        this.audioPlayer = new Audio();
        this.playStartTime = Date.now();

        // 开始播报计时
        this.updatePlayTimer();

        // 模拟播报过程（实际应用中可能需要TTS服务）
        this.simulateNewsBroadcast();
    }

    // 模拟新闻播报过程
    simulateNewsBroadcast() {
        // 播报时长至少60秒
        const broadcastDuration = 60 * 1000; // 60秒
        let elapsedTime = 0;
        const interval = 1000; // 每秒更新一次

        const timer = setInterval(() => {
            elapsedTime += interval;
            
            // 检查是否达到最小播报时长
            if (elapsedTime >= broadcastDuration && this.isPlaying) {
                this.stopNewsPlayback();
                clearInterval(timer);
                alert('新闻播报完成！');
            }
        }, interval);
    }

    // 更新播报计时器
    updatePlayTimer() {
        if (!this.isPlaying) return;

        const elapsed = Math.floor((Date.now() - this.playStartTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        document.getElementById('play-timer').textContent = `${minutes}:${seconds}`;

        if (this.isPlaying) {
            setTimeout(() => this.updatePlayTimer(), 1000);
        }
    }

    // 停止新闻播报
    stopNewsPlayback() {
        this.isPlaying = false;
        if (this.audioPlayer) {
            this.audioPlayer.pause();
            this.audioPlayer = null;
        }
        document.getElementById('play-news').textContent = '▶️ 播报';
        document.getElementById('play-timer').textContent = '00:00';
    }
}

// 初始化新闻展示功能
const newsDisplay = new NewsDisplay();
document.addEventListener('DOMContentLoaded', () => {
    newsDisplay.init();
});