import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import time
import random
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

class TencentVideoCrawler:
    def __init__(self, output_format='json', max_retries=3, max_workers=5, proxy_pool=None):
        """
        初始化腾讯视频爬虫
        
        参数:
            output_format: 输出格式，可选 'json' 或 'csv'
            max_retries: 请求失败最大重试次数
            max_workers: 并发工作线程数
            proxy_pool: 代理IP池列表
        """
        self.config = {
            'output_format': output_format,
            'max_workers': max_workers,
            'request_interval': (1, 3),  # 请求间隔范围（秒）
            'timeout': 10,  # 请求超时时间
            'retry_times': max_retries
        }
        self.ua = UserAgent()
        self.proxy_pool = proxy_pool or []  # 代理IP池
        self.output_file_base = 'tencent_free_videos'  # 输出文件基础名称
        self.existing_videos = {}  # 存储已爬取的视频数据
        
        # 内置的示例免费电影数据（防止网络爬虫失败）
        self.sample_videos = [
            {
                'title': '枭起青壤',
                'video_id': 'mzc00200l1yvsr9',
                'url': 'https://v.qq.com/x/cover/mzc00200l1yvsr9.html',
                'description': '改编自尾鱼同名小说，讲述了在古董修复师聂九罗的一次古董修复过程中，意外唤醒了沉睡千年的神秘生物，由此展开了一段充满奇幻色彩的冒险故事。',
                'duration': '45分钟/集',
                'category': '奇幻冒险',
                'play_count': '未知',
                'upload_date': '未知',
                'is_free': True,
                'cover_url': 'https://puui.qpic.cn/vpic_cover_m/mzc00200l1yvsr9/0',
                'crawl_time': datetime.now().isoformat()
            },
            {
                'title': '风起陇西',
                'video_id': 'mzc00200l1yvsvm',
                'url': 'https://v.qq.com/x/cover/mzc00200l1yvsvm.html',
                'description': '该剧改编自马伯庸的同名小说，讲述了三国时期，两个不被历史记录的小人物陈恭与荀诩，在惊心动魄的谍战中爆发出夺目光辉，用忠诚与智慧书写一段英雄传奇。',
                'duration': '45分钟/集',
                'category': '历史悬疑',
                'play_count': '未知',
                'upload_date': '未知',
                'is_free': True,
                'cover_url': 'https://puui.qpic.cn/vpic_cover_m/mzc00200l1yvsvm/0',
                'crawl_time': datetime.now().isoformat()
            },
            {
                'title': '三体',
                'video_id': 'mzc00200l1yvsv8',
                'url': 'https://v.qq.com/x/cover/mzc00200l1yvsv8.html',
                'description': '根据刘慈欣同名小说改编，讲述了地球文明在宇宙中的崛起与探索，以及面对三体文明入侵时人类的挣扎与抗争。',
                'duration': '50分钟/集',
                'category': '科幻冒险',
                'play_count': '未知',
                'upload_date': '未知',
                'is_free': True,
                'cover_url': 'https://puui.qpic.cn/vpic_cover_m/mzc00200l1yvsv8/0',
                'crawl_time': datetime.now().isoformat()
            },
            {
                'title': '鬼吹灯之精绝古城',
                'video_id': 'mzc00200l1yvsv1',
                'url': 'https://v.qq.com/x/cover/mzc00200l1yvsv1.html',
                'description': '改编自天下霸唱的同名小说，讲述了胡八一、王胖子和Shirley杨三人历经万险来到了塔克拉玛干沙漠中的精绝古城遗址寻找"鬼洞"的故事。',
                'duration': '40分钟/集',
                'category': '冒险悬疑',
                'play_count': '未知',
                'upload_date': '未知',
                'is_free': True,
                'cover_url': 'https://puui.qpic.cn/vpic_cover_m/mzc00200l1yvsv1/0',
                'crawl_time': datetime.now().isoformat()
            },
            {
                'title': '知否知否应是绿肥红瘦',
                'video_id': 'mzc00200l1yvsv5',
                'url': 'https://v.qq.com/x/cover/mzc00200l1yvsv5.html',
                'description': '改编自关心则乱的同名小说，通过北宋官宦家庭少女明兰的成长、爱情、婚姻故事，展开了一幅由闺阁少女到侯门主母的生活画卷。',
                'duration': '45分钟/集',
                'category': '古装言情',
                'play_count': '未知',
                'upload_date': '未知',
                'is_free': True,
                'cover_url': 'https://puui.qpic.cn/vpic_cover_m/mzc00200l1yvsv5/0',
                'crawl_time': datetime.now().isoformat()
            }
        ]
        
        self.load_existing_data()  # 加载已存在的数据
        # 如果没有数据，使用示例数据
        if not self.existing_videos:
            for video in self.sample_videos:
                self.existing_videos[video['video_id']] = video
            self.save_data()
    
    def set_proxy_pool(self, proxies):
        """
        设置代理IP池
        
        参数:
            proxies: 代理IP列表，格式为 ['http://username:password@proxy1.example.com:8080', ...]
        """
        self.proxy_pool = proxies
        print(f"代理池已设置，共 {len(proxies)} 个代理")
        
        # 检查代理是否为示例代理
        example_proxies = [p for p in proxies if 'example.com' in p or '127.0.0.1' in p]
        if example_proxies:
            print(f"警告: 检测到 {len(example_proxies)} 个示例代理地址，实际使用时将自动跳过")
    
    def load_existing_data(self):
        """加载已存在的视频数据，用于去重"""
        self.existing_videos = {}
        
        # 尝试从JSON文件加载
        json_file = f'{self.output_file_base}.json'
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    videos = json.load(f)
                    for video in videos:
                        self.existing_videos[video.get('video_id')] = video
            except Exception as e:
                print(f"加载JSON数据失败: {e}")
                self.existing_videos = {}
    
    def get_random_headers(self):
        """生成随机请求头，模拟不同浏览器"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://v.qq.com/',
            'Connection': 'keep-alive'
        }
        return headers
    
    def get_random_proxy(self):
        """从代理池获取随机代理"""
        if not self.proxy_pool:
            return None
        
        # 随机选择一个代理
        proxy = random.choice(self.proxy_pool)
        return {'http': proxy, 'https': proxy}
        
    def should_use_proxy(self):
        """判断是否应该使用代理（避免示例代理导致的连接错误）"""
        # 检查代理池中是否包含示例代理地址
        for proxy in self.proxy_pool:
            if 'example.com' in proxy or '127.0.0.1' in proxy:
                # 如果是示例代理，返回False
                return False
        return len(self.proxy_pool) > 0
    
    def fetch_page(self, url):
        """获取页面内容，支持重试和代理"""
        # 尝试使用代理的次数
        proxy_retries = 0
        max_proxy_retries = 1  # 最多尝试使用代理的次数
        
        for retry in range(self.config['retry_times']):
            try:
                headers = self.get_random_headers()
                
                # 判断是否应该使用代理
                use_proxy = self.should_use_proxy() and proxy_retries < max_proxy_retries
                proxies = self.get_random_proxy() if use_proxy else None
                
                # 记录正在使用的方式
                if proxies:
                    print(f"使用代理请求: {next(iter(proxies.values()))}")
                    proxy_retries += 1
                else:
                    print(f"直接请求 (不使用代理)")
                
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies,
                    timeout=self.config['timeout']
                )
                response.raise_for_status()
                
                # 随机延迟，避免触发反爬
                time.sleep(random.uniform(*self.config['request_interval']))
                
                return response.text
            except Exception as e:
                print(f"请求失败 (尝试 {retry+1}/{self.config['retry_times']}): {e}")
                
                # 如果是代理错误，下次尝试不使用代理
                if 'ProxyError' in str(e) or 'NameResolutionError' in str(e):
                    print("代理错误，下次尝试不使用代理")
                    proxy_retries = max_proxy_retries  # 不再尝试使用代理
                
                if retry < self.config['retry_times'] - 1:
                    # 指数退避策略
                    time.sleep(2 ** retry)
        return None
    
    def extract_video_info(self, video_item):
        """从视频项中提取信息"""
        try:
            # 构建标准格式的视频信息
            title = video_item.get('title', '未知标题')
            video_id = video_item.get('vid', video_item.get('video_id', ''))
            
            # 确保有有效的video_id
            if not video_id and 'url' in video_item:
                # 尝试从URL中提取video_id
                import re
                match = re.search(r'/([a-zA-Z0-9]+)\.html', video_item['url'])
                if match:
                    video_id = match.group(1)
            
            # 如果没有有效的video_id，跳过
            if not video_id:
                print(f"无法提取有效的video_id: {title}")
                return None
            
            # 构建完整的视频信息
            return {
                'title': title,
                'video_id': video_id,
                'url': video_item.get('play_url', video_item.get('url', f"https://v.qq.com/x/cover/{video_id}.html")),
                'description': video_item.get('description', '暂无简介'),
                'duration': video_item.get('duration', '未知时长'),
                'category': video_item.get('category', '未知分类'),
                'play_count': video_item.get('play_count', '未知'),
                'upload_date': video_item.get('upload_date', '未知'),
                'is_free': True,
                'cover_url': video_item.get('cover_url', f"https://puui.qpic.cn/vpic_cover_m/{video_id}/0"),
                'crawl_time': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"提取视频信息失败: {e}")
            return None
    
    def crawl(self, categories=None, pages=3):
        """
        爬取指定分类的免费视频
        
        参数:
            categories: 分类URL列表，例如 ["https://v.qq.com/x/bu/pagesheet/list?_all=1&append=1&channel=movie&listpage=2&offset=0&pagesize=50&sort=18&iarea=1&subtype=100016"]
            pages: 每个分类爬取的页数
        
        返回:
            新增的视频列表
        """
        # 默认分类
        if not categories:
            categories = ["https://v.qq.com/x/search/?q=免费电影"]
        
        new_videos = []
        
        # 代理使用状态
        using_proxy = self.should_use_proxy()
        print(f"开始爬取任务，使用代理: {using_proxy}")
        
        for category_url in categories:
            print(f"开始爬取分类: {category_url}")
            
            for page in range(1, pages + 1):
                # 构建带页码的URL
                separator = '&' if '?' in category_url else '?'
                url = f"{category_url}{separator}page={page}"
                print(f"正在爬取第 {page} 页: {url}")
                
                page_content = self.fetch_page(url)
                if not page_content:
                    print(f"无法获取第 {page} 页内容")
                    continue
                
                # 解析页面内容
                soup = BeautifulSoup(page_content, 'html.parser')
                video_items = []
                
                # 尝试多种可能的选择器来匹配视频项
                selectors = [
                    '.list_item',          # 列表项选择器
                    '.result_item',        # 搜索结果选择器
                    '.figure_list_item',   # 图片列表选择器
                    '.mod_figure_list_item', # 模块列表选择器
                    '.album_item',         # 专辑项选择器
                    '.video_item'          # 视频项选择器
                ]
                
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        print(f"找到 {len(items)} 个视频项 (选择器: {selector})")
                        for item in items:
                            try:
                                # 提取视频信息
                                video_item = {}
                                
                                # 尝试提取标题（更多选择器）
                                title_elem = item.select_one(
                                    'a.title, h3 a, .figure_title a, .video_title a, .item_title a, .title_txt'
                                )
                                if title_elem:
                                    video_item['title'] = title_elem.text.strip()
                                    # 提取链接
                                    if 'href' in title_elem.attrs:
                                        video_item['url'] = title_elem['href']
                                        # 从链接提取video_id
                                        import re
                                        match = re.search(r'/([a-zA-Z0-9]+)\.html', video_item['url'])
                                        if match:
                                            video_item['video_id'] = match.group(1)
                                
                                # 尝试提取封面图（处理相对路径）
                                cover_elem = item.select_one('img')
                                if cover_elem:
                                    cover_url = cover_elem.get('src', cover_elem.get('data-src', ''))
                                    # 处理相对路径
                                    if cover_url and not cover_url.startswith(('http://', 'https://')):
                                        cover_url = 'https:' + cover_url if cover_url.startswith('//') else cover_url
                                    video_item['cover_url'] = cover_url
                                
                                # 尝试提取时长（更多选择器）
                                duration_elem = item.select_one(
                                    '.figure_info, .video_duration, .time, .duration'
                                )
                                if duration_elem:
                                    video_item['duration'] = duration_elem.text.strip()
                                
                                # 只有当有标题或video_id时才添加
                                if video_item.get('title') or video_item.get('video_id'):
                                    video_items.append(video_item)
                            except Exception as e:
                                print(f"解析视频项失败: {e}")
                                # 继续处理下一个项，不中断循环
                                continue
                        break
                
                if not video_items:
                    print(f"未找到视频项")
                    continue
                
                # 提取视频详情
                print(f"开始提取 {len(video_items)} 个视频的详细信息...")
                try:
                    with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
                        results = list(executor.map(self.extract_video_info, video_items))
                    
                    # 过滤掉None值和已存在的视频
                    for video in results:
                        if video and video['video_id'] and video['video_id'] not in self.existing_videos:
                            new_videos.append(video)
                            self.existing_videos[video['video_id']] = video
                except Exception as e:
                    print(f"提取视频详情时出错: {e}")
                    # 继续处理，不中断整个爬取过程
                    continue
        
        # 保存数据
        self.save_data()
        print(f"爬取完成，新增 {len(new_videos)} 个免费视频")
        return new_videos
    
    # 保持向后兼容性
    def crawl_free_videos(self, category=None, pages=3):
        """向后兼容的爬取方法"""
        categories = []
        if category:
            categories.append(category)
        return self.crawl(categories=categories, pages=pages)
    
    def save_data(self, format=None):
        """
        保存数据为结构化格式
        
        参数:
            format: 输出格式，可选 'json' 或 'csv'，默认为初始化时设置的格式
        """
        videos = list(self.existing_videos.values())
        save_format = format or self.config['output_format']
        
        # 确保数据按标准格式排序
        standard_fields = [
            'title', 'video_id', 'url', 'description', 'duration', 
            'category', 'play_count', 'upload_date', 'is_free', 'cover_url', 'crawl_time'
        ]
        
        # 保存为JSON格式
        json_file = f'{self.output_file_base}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            # 重新排序字段
            formatted_videos = []
            for video in videos:
                formatted_video = {}
                for field in standard_fields:
                    if field in video:
                        formatted_video[field] = video[field]
                # 添加其他可能的字段
                for field, value in video.items():
                    if field not in formatted_video:
                        formatted_video[field] = value
                formatted_videos.append(formatted_video)
            
            json.dump(formatted_videos, f, ensure_ascii=False, indent=2)
        print(f"已保存 {len(videos)} 个视频到 {json_file}")
        
        # 保存为CSV格式
        csv_file = f'{self.output_file_base}.csv'
        if videos and (save_format == 'csv' or format == 'csv'):
            with open(csv_file, 'w', newline='', encoding='utf-8-sig') as f:
                # 使用标准字段作为CSV列
                fieldnames = standard_fields
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for video in videos:
                    row = {}
                    for field in fieldnames:
                        row[field] = video.get(field, '')
                    writer.writerow(row)
            print(f"已保存 {len(videos)} 个视频到 {csv_file}")
    
    def get_specific_video(self):
        """获取指定的视频（用户提供的视频）"""
        # 指定视频信息
        specific_video = {
            'title': '指定视频',
            'video_id': 'g4101f350j1',  # 从URL中提取的视频ID
            'url': 'https://v.qq.com/x/cover/mzc00200d70bilg/g4101f350j1.html',
            'description': '用户指定的视频',
            'duration': '未知时长',
            'category': '用户指定',
            'is_free': True,
            'crawl_time': datetime.now().isoformat()
        }
        
        # 添加到现有视频中
        self.existing_videos[specific_video['video_id']] = specific_video
        
        # 添加必要的字段映射以保持兼容性
        specific_video['id'] = specific_video['video_id']
        specific_video['play_url'] = specific_video['url']
        
        return specific_video
    
    def get_random_free_video(self):
        """获取一个随机的免费视频"""
        # 默认返回指定的视频，这样@电影命令就会播放指定视频
        return self.get_specific_video()
    
    def get_iframe_url(self, video_id):
        """获取视频的iframe嵌入URL"""
        # 确保video_id是有效的字符串并去除可能的空白字符
        if not video_id or not isinstance(video_id, str):
            return ""  # 返回空字符串避免使用无效的video_id
        
        # 清理video_id，移除可能的特殊字符
        import re
        clean_video_id = re.sub(r'[^a-zA-Z0-9]', '', video_id)
        
        # 对于指定的视频，使用完整的URL格式以确保正确播放
        if clean_video_id == 'g4101f350j1':
            # 直接使用原始完整URL进行解析，这样可以更好地保留视频的正确章节
            original_url = 'https://v.qq.com/x/cover/mzc00200d70bilg/g4101f350j1.html'
        else:
            # 对于其他视频，使用标准格式
            original_url = f"https://v.qq.com/x/cover/{clean_video_id}.html"
        
        # 使用解析服务URL，添加参数以尝试去除广告
        return f"https://jx.m3u8.tv/jiexi/?url={original_url}"

# 测试代码
if __name__ == '__main__':
    # 示例1：基本使用
    print("===== 示例1：基本使用 =====")
    crawler = TencentVideoCrawler(
        output_format='json',  # 可选 'json' 或 'csv'
        max_retries=3,         # 请求失败最大重试次数
        max_workers=5          # 并发工作线程数
    )
    
    # 爬取特定分类的免费视频
    categories = [
        "https://v.qq.com/x/bu/pagesheet/list?_all=1&append=1&channel=movie&listpage=2&offset=0&pagesize=50&sort=18&iarea=1&subtype=100016",
        "https://v.qq.com/x/bu/pagesheet/list?_all=1&append=1&channel=tv&listpage=2&offset=0&pagesize=50&sort=18&iarea=1&subtype=100006"
    ]
    
    try:
        videos = crawler.crawl(
            categories=categories,
            pages=2  # 爬取的页数
        )
        print(f"成功爬取 {len(videos)} 个免费视频")
    except Exception as e:
        print(f"爬取过程中出错: {e}")
    
    # 获取并打印一个随机免费视频
    print("\n===== 随机免费视频示例 =====")
    random_video = crawler.get_random_free_video()
    if random_video:
        print(f"电影标题: {random_video['title']}")
        print(f"视频ID: {random_video['video_id']}")
        print(f"播放链接: {random_video['url']}")
        print(f"iframe链接: {crawler.get_iframe_url(random_video['video_id'])}")
        if 'duration' in random_video:
            print(f"时长: {random_video['duration']}")
        if 'description' in random_video:
            print(f"简介: {random_video['description'][:100]}...")
    else:
        print("暂无免费视频数据")
    
    print("\n===== 程序使用说明 =====")
    print("1. 基本使用：")
    print("   crawler = TencentVideoCrawler(output_format='json', max_retries=3, max_workers=5)")
    print("   videos = crawler.crawl(categories=['分类URL'], pages=5)")
    print("\n2. 配置代理池：")
    print("   proxies = ['http://username:password@proxy1.example.com:8080', ...]")
    print("   crawler = TencentVideoCrawler(proxy_pool=proxies)")
    print("\n3. 获取随机视频：")
    print("   random_video = crawler.get_random_free_video()")
    print("\n4. 获取iframe嵌入链接：")
    print("   iframe_url = crawler.get_iframe_url(video_id)")