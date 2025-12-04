from flask import Flask, render_template, request, jsonify, redirect, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
from datetime import datetime
import openai
import threading
import time
import uuid
# 导入川小农助手类
from scau_assistant import SCAUAssistant
# 导入腾讯视频爬虫模块
from tencent_video_crawler import TencentVideoCrawler
# 导入数据库管理器
from database import db_manager
# 导入音乐天气API
from music_weather_api import MusicWeatherAPI
# 导入新闻API
import news_api

# 初始化视频爬虫
video_crawler = TencentVideoCrawler(
    output_format='json',
    max_retries=3,
    max_workers=5
)

# 创建川小农助手实例
assistant = SCAUAssistant()

# 创建音乐天气API实例
music_weather_api = MusicWeatherAPI()

# AI模型配置
AI_CONFIG = {
    'api_key': 'sk-jnmakzcrkwfvgbymzrcwurcltdcyxojmsgqrgnvnkqjrdhwh',
    'model_name': 'Qwen/Qwen2.5-7B-Instruct',
    'api_url': 'https://api.siliconflow.cn/v1/',
    'base_url': 'https://api.siliconflow.cn/v1/'
}

# 初始化OpenAI客户端
openai_client = openai.OpenAI(
    api_key=AI_CONFIG['api_key'],
    base_url=AI_CONFIG['base_url']
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'daipp_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 存储在线用户信息
online_users = {}
# 存储用户会话信息
user_sessions = {}  # session_id -> nickname
# 默认房间名
DEFAULT_ROOM = 'chat_room'

# 读取配置文件
def load_config():
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'servers': []}

# 主页路由（登录页）
@app.route('/')
def login():
    config = load_config()
    return render_template('login.html', servers=config['servers'])

# 注册页面路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证密码一致性
        if password != confirm_password:
            return jsonify({'success': False, 'message': '两次输入的密码不一致'})
        
        # 验证用户名和密码长度
        if len(username) < 3 or len(password) < 6:
            return jsonify({'success': False, 'message': '用户名至少3个字符，密码至少6个字符'})
        
        # 创建用户
        if db_manager.create_user(username, password):
            return jsonify({'success': True, 'message': '注册成功，请登录'})
        else:
            return jsonify({'success': False, 'message': '用户名已存在'})
    
    config = load_config()
    return render_template('login.html', servers=config['servers'], is_register=True)

# 聊天室路由
@app.route('/chat')
def chat():
    nickname = request.args.get('nickname')
    if not nickname:
        return redirect('/')
    return render_template('chat.html', nickname=nickname)

# 检查昵称是否可用
@app.route('/check_nickname', methods=['POST'])
def check_nickname():
    nickname = request.json.get('nickname')
    return jsonify({'available': nickname not in online_users})

# 登录验证路由
@app.route('/login_validate', methods=['POST'])
def login_validate():
    username = request.form.get('username')
    password = request.form.get('password')
    server = request.form.get('server')
    
    # 验证用户名和密码
    user_id = db_manager.verify_user_password(username, password)
    if user_id:
        # 用户名和密码验证成功
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        # 验证失败
        return jsonify({'success': False, 'message': '用户名或密码错误'})

# 用户上线下线功能路由
@app.route('/api/user/status', methods=['POST'])
def update_user_status():
    """
    更新用户状态（上线/下线）
    """
    try:
        data = request.get_json()
        nickname = data.get('nickname')
        status = data.get('status')  # 'online' 或 'offline'
        
        if not nickname or status not in ['online', 'offline']:
            return jsonify({'success': False, 'message': '参数错误'})
        
        # 更新用户在线状态
        if status == 'online':
            # 用户上线，将其添加到在线用户列表
            # 由于无法直接获取socket_id，我们使用一个虚拟的session_id来跟踪
            # 在实际使用中，应该通过socket连接来管理
            if nickname not in online_users.values():
                # 为离线用户创建一个虚拟session_id
                virtual_session_id = f"virtual_{nickname}_{int(time.time())}"
                online_users[virtual_session_id] = nickname
                print(f"用户 {nickname} 上线，虚拟session_id: {virtual_session_id}")
        else:
            # 用户下线，从在线用户列表中移除
            removed = False
            for sid, user_nickname in list(online_users.items()):
                if user_nickname == nickname:
                    del online_users[sid]
                    removed = True
                    print(f"用户 {nickname} 下线，移除session_id: {sid}")
                    break
            
            # 如果没有找到对应的session_id，可能是虚拟用户，需要清理所有匹配的
            if not removed:
                for sid in list(online_users.keys()):
                    if sid.startswith(f"virtual_{nickname}_"):
                        del online_users[sid]
                        print(f"清理虚拟用户 {nickname}，session_id: {sid}")
        
        # 广播用户状态变化
        socketio.emit('user_status_change', {
            'nickname': nickname,
            'status': status,
            'online_users': list(online_users.values())
        }, room=DEFAULT_ROOM, broadcast=True)
        
        print(f"广播用户状态变化: {nickname} -> {status}, 当前在线用户: {list(online_users.values())}")
        
        return jsonify({'success': True, 'message': '状态更新成功'})
    
    except Exception as e:
        print(f"更新用户状态失败: {str(e)}")
        return jsonify({'success': False, 'message': '状态更新失败'})

# Socket.IO 事件处理
# 历史记录相关路由
@app.route('/api/history', methods=['GET'])
def get_history():
    """获取聊天历史记录"""
    try:
        # 获取查询参数
        nickname = request.args.get('nickname')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        session_id = request.args.get('session_id')
        
        # 计算偏移量
        offset = (page - 1) * page_size
        
        # 获取历史记录
        messages = db_manager.get_message_history(
            nickname=nickname,
            limit=page_size,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'data': messages,
            'page': page,
            'page_size': page_size
        })
    except Exception as e:
        print(f"获取历史记录失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/history/sessions', methods=['GET'])
def get_user_sessions():
    """获取用户会话列表"""
    try:
        nickname = request.args.get('nickname')
        if not nickname:
            return jsonify({
                'success': False,
                'error': '缺少nickname参数'
            }), 400
        
        sessions = db_manager.get_user_sessions(nickname)
        
        return jsonify({
            'success': True,
            'data': sessions
        })
    except Exception as e:
        print(f"获取会话列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/music/random', methods=['GET'])
def get_random_music():
    """获取随机音乐API"""
    try:
        music_data = music_weather_api.get_random_music()
        if music_data:
            return jsonify({
                'success': True,
                'data': music_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '获取随机音乐失败'
            }), 500
    except Exception as e:
        print(f"获取随机音乐API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/news/latest', methods=['GET'])
def get_latest_news():
    """获取最新新闻API"""
    try:
        # 导入新闻API模块
        import news_api
        
        # 获取最近3天的新闻
        news_data = news_api.get_recent_cctv_news(3)
        
        if news_data:
            return jsonify({
                'success': True,
                'data': news_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '获取最新新闻失败'
            }), 500
    except Exception as e:
        print(f"获取最新新闻API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/weather/info', methods=['GET'])
def get_weather_info():
    """获取天气信息API"""
    try:
        city = request.args.get('city', '成都')  # 默认为成都
        weather_data = music_weather_api.get_weather_info(city)
        if weather_data:
            return jsonify({
                'success': True,
                'data': weather_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '获取天气信息失败'
            }), 500
    except Exception as e:
        print(f"获取天气信息API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/weather/current-location', methods=['GET'])
def get_current_location_weather():
    """获取当前位置天气信息API"""
    try:
        weather_data = music_weather_api.get_current_location_weather()
        if weather_data:
            return jsonify({
                'success': True,
                'data': weather_data
            })
        else:
            return jsonify({
                'success': False,
                'error': '获取当前位置天气信息失败'
            }), 500
    except Exception as e:
        print(f"获取当前位置天气API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news/list', methods=['GET'])
def get_news_list():
    """获取新闻列表API"""
    try:
        category = request.args.get('category', '全部')
        limit = int(request.args.get('limit', 10))
        news_list = news_api.get_news_list(category=category, limit=limit)
        return jsonify({
            'success': True,
            'data': news_list
        })
    except Exception as e:
        print(f"获取新闻列表API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news/categories', methods=['GET'])
def get_news_categories():
    """获取新闻分类API"""
    try:
        categories = news_api.get_categories()
        return jsonify({
            'success': True,
            'data': categories
        })
    except Exception as e:
        print(f"获取新闻分类API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news/trending', methods=['GET'])
def get_trending_news():
    """获取热门新闻API"""
    try:
        limit = int(request.args.get('limit', 5))
        trending_news = news_api.get_trending_news(limit=limit)
        return jsonify({
            'success': True,
            'data': trending_news
        })
    except Exception as e:
        print(f"获取热门新闻API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/news/detail', methods=['GET'])
def get_news_detail():
    """获取新闻详情API"""
    try:
        news_id = request.args.get('news_id')
        if not news_id:
            return jsonify({
                'success': False,
                'error': '缺少news_id参数'
            }), 400
        
        news_detail = news_api.get_news_detail(news_id)
        if news_detail:
            return jsonify({
                'success': True,
                'data': news_detail
            })
        else:
            return jsonify({
                'success': False,
                'error': '新闻不存在'
            }), 404
    except Exception as e:
        print(f"获取新闻详情API失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Socket.IO事件处理
@socketio.on('connect', namespace='/')
def handle_connect():
    """处理用户连接"""
    try:
        from flask import g
        # 生成会话ID
        session_id = str(uuid.uuid4())
        g.session_id = session_id
        
        # 获取客户端IP
        client_ip = request.remote_addr
        g.client_ip = client_ip
        
        print(f"用户连接 - Session ID: {session_id}, IP: {client_ip}")
    except Exception as e:
        print(f"连接处理出错: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    # 查找断开连接的用户
    disconnected_user = None
    for nickname, sid in online_users.items():
        if sid == request.sid:
            disconnected_user = nickname
            break
    
    if disconnected_user:
        del online_users[disconnected_user]
        # 关闭用户会话
        for session_id, user_nickname in user_sessions.items():
            if user_nickname == disconnected_user:
                db_manager.close_session(session_id)
                del user_sessions[session_id]
                break
        
        # 通知房间内其他用户
        emit('user_left', {
            'nickname': disconnected_user,
            'online_users': list(online_users.keys())
        }, room=DEFAULT_ROOM, broadcast=True)
        leave_room(DEFAULT_ROOM)

@socketio.on('join_room')
def handle_join_room(data):
    nickname = data['nickname']
    online_users[nickname] = request.sid
    
    # 获取会话ID和客户端IP
    from flask import g
    session_id = getattr(g, 'session_id', str(uuid.uuid4()))
    client_ip = getattr(g, 'client_ip', request.remote_addr)
    
    # 创建用户会话
    user_agent = request.headers.get('User-Agent', '')
    db_manager.create_session(session_id, nickname, client_ip, user_agent)
    user_sessions[session_id] = nickname
    
    join_room(DEFAULT_ROOM)
    
    # 发送欢迎消息
    emit('welcome', {
        'message': f'{nickname} 加入了聊天室！',
        'online_users': list(online_users.keys())
    }, room=DEFAULT_ROOM, broadcast=True)

@socketio.on('send_message')
def handle_send_message(data):
    nickname = data['nickname']
    message = data['message']
    
    # 获取会话ID
    from flask import g
    session_id = getattr(g, 'session_id', None)
    client_ip = getattr(g, 'client_ip', request.remote_addr)
    
    # 获取消息类型和特性
    is_at = message.startswith('@')
    is_ai = False
    is_movie = False
    message_type = 'text'
    movie_url = None
    movie_info = None
    
    # 检查是否为@命令
    if message.startswith('@'):
        message_type = 'at'
        
        # 简单处理@命令
        if '@川小农' in message:
            # 提取用户问题
            question = message.split('@川小农', 1)[1].strip() if len(message.split('@川小农', 1)) > 1 else ''
            
            # 保存用户消息到数据库
            db_manager.save_message(
                nickname=nickname,
                message=message,
                session_id=session_id,
                message_type='at',
                is_at_message=True,
                is_ai_response=False,
                user_ip=client_ip,
                room=DEFAULT_ROOM
            )
            
            # 先发送用户的原始消息，让提问显示出来
            emit('new_message', {
                'nickname': nickname,
                'message': message,
                'is_at': True
            }, room=DEFAULT_ROOM, broadcast=True)
            
            # 开始AI流式回复
            if question.strip():  # 如果有具体问题
                # 直接使用AI模型生成回复（不进行流式回复，因为SocketIO在线程中有上下文问题）
                try:
                    ai_message = generate_ai_response(question, use_ai_model=True)
                    
                    # 保存AI回复到数据库
                    db_manager.save_message(
                        nickname='川小农',
                        message=ai_message,
                        session_id=session_id,
                        message_type='ai',
                        is_ai_response=True,
                        is_at_message=True,
                        user_ip=client_ip,
                        room=DEFAULT_ROOM
                    )
                    
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': ai_message,
                        'is_ai': True,
                        'is_at': True
                    }, room=DEFAULT_ROOM, broadcast=True)
                except Exception as e:
                    print(f"AI回复出错: {str(e)}")
                    # 回退到川小农知识库
                    ai_message = generate_ai_response(question, use_ai_model=False)
                    
                    # 保存AI回复到数据库
                    db_manager.save_message(
                        nickname='川小农',
                        message=ai_message,
                        session_id=session_id,
                        message_type='ai',
                        is_ai_response=True,
                        is_at_message=True,
                        user_ip=client_ip,
                        room=DEFAULT_ROOM
                    )
                    
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': ai_message,
                        'is_ai': True,
                        'is_at': True
                    }, room=DEFAULT_ROOM, broadcast=True)
            else:
                # 如果没有具体问题，直接生成一个简单的回复
                ai_message = generate_ai_response(question, use_ai_model=False)  # 不使用AI模型
                
                # 保存AI回复到数据库
                db_manager.save_message(
                    nickname='川小农',
                    message=ai_message,
                    session_id=session_id,
                    message_type='ai',
                    is_ai_response=True,
                    is_at_message=True,
                    user_ip=client_ip,
                    room=DEFAULT_ROOM
                )
                
                emit('new_message', {
                    'nickname': '川小农',
                    'message': ai_message,
                    'is_ai': True,
                    'is_at': True
                }, room=DEFAULT_ROOM, broadcast=True)
        elif '@电影' in message:
            message_type = 'movie'
            is_movie = True
            # 提取消息内容
            message_content = message.split('@电影', 1)[1].strip()
            
            # 检查是否有URL参数
            import re
            url_match = re.search(r'https?://[\w\-\._~:/?#[\]@!\$&\'\(\)\*\+,;=.]+', message_content)
            
            if url_match:
                url = url_match.group(0)
                # 判断是否是腾讯视频链接
                if 'v.qq.com' in url or 'video.qq.com' in url:
                    # 从腾讯视频URL中提取视频ID
                    video_id_match = re.search(r'/([a-zA-Z0-9]+)\.html', url)
                    if video_id_match:
                        video_id = video_id_match.group(1)
                        # 清理video_id，移除可能的特殊字符
                        clean_video_id = re.sub(r'[^a-zA-Z0-9]', '', video_id)
                        # 构建腾讯视频原始URL
                        original_url = f"https://v.qq.com/x/cover/{clean_video_id}.html"
                        # 使用指定的解析服务URL
                        movie_url = f"https://jx.m3u8.tv/jiexi/?url={original_url}"
                        
                        # 保存用户消息到数据库
                        db_manager.save_message(
                            nickname=nickname,
                            message='分享了一个腾讯视频：',
                            session_id=session_id,
                            message_type='movie',
                            is_at_message=True,
                            is_movie=True,
                            movie_url=movie_url,
                            user_ip=client_ip,
                            room=DEFAULT_ROOM
                        )
                        
                        emit('new_message', {
                            'nickname': nickname,
                            'message': '分享了一个腾讯视频：',
                            'is_movie': True,
                            'movie_url': movie_url
                        }, room=DEFAULT_ROOM, broadcast=True)
                    else:
                        # 无法提取视频ID
                        # 保存用户消息到数据库
                        db_manager.save_message(
                            nickname=nickname,
                            message=message,
                            session_id=session_id,
                            message_type='at',
                            is_at_message=True,
                            user_ip=client_ip,
                            room=DEFAULT_ROOM
                        )
                        
                        emit('new_message', {
                            'nickname': nickname,
                            'message': '无法从链接中提取视频ID',
                            'is_movie': False
                        }, room=DEFAULT_ROOM, broadcast=True)
                else:
                    # 非腾讯视频URL，使用解析服务URL
                    movie_url = f"https://jx.m3u8.tv/jiexi/?url={url}"
                    
                    # 保存用户消息到数据库
                    db_manager.save_message(
                        nickname=nickname,
                        message=f'分享了一个视频链接：{url}',
                        session_id=session_id,
                        message_type='movie',
                        is_at_message=True,
                        is_movie=True,
                        movie_url=movie_url,
                        user_ip=client_ip,
                        room=DEFAULT_ROOM
                    )
                    
                    emit('new_message', {
                        'nickname': nickname,
                        'message': f'分享了一个视频链接：{url}',
                        'is_movie': True,
                        'movie_url': movie_url
                    }, room=DEFAULT_ROOM, broadcast=True)
            else:
                # 用户没有提供URL，自动获取一个随机免费电影
                # 保存用户消息到数据库
                db_manager.save_message(
                    nickname=nickname,
                    message=message,
                    session_id=session_id,
                    message_type='at',
                    is_at_message=True,
                    user_ip=client_ip,
                    room=DEFAULT_ROOM
                )
                
                emit('new_message', {
                    'nickname': nickname,
                    'message': '正在为您查找免费电影...',
                    'is_movie': False
                }, room=DEFAULT_ROOM, broadcast=True)
                
                # 获取随机免费电影
                try:
                    random_video = video_crawler.get_random_free_video()
                    if random_video:
                        # 获取视频ID，兼容新旧格式
                        video_id = random_video.get('video_id', random_video.get('id', ''))
                        movie_url = video_crawler.get_iframe_url(video_id)
                        video_info = f"为您找到免费电影《{random_video['title']}》\n"
                        if random_video.get('duration') and random_video['duration'] != '未知时长':
                            video_info += f"时长：{random_video['duration']}\n"
                        if random_video.get('description') and random_video['description'] != '暂无简介':
                            video_info += f"简介：{random_video['description'][:200]}..."
                        
                        # 如果有播放链接，添加到消息中
                        play_url = random_video.get('url', random_video.get('play_url', ''))
                        if play_url:
                            video_info += f"\n播放链接：{play_url}"
                        
                        # 保存AI回复到数据库
                        db_manager.save_message(
                            nickname='川小农',
                            message=video_info,
                            session_id=session_id,
                            message_type='movie',
                            is_ai_response=True,
                            is_movie=True,
                            movie_url=movie_url,
                            movie_info=video_info,
                            user_ip=client_ip,
                            room=DEFAULT_ROOM
                        )
                        
                        emit('new_message', {
                            'nickname': '川小农',
                            'message': video_info,
                            'is_movie': True,
                            'movie_url': movie_url,
                            'is_ai': True
                        }, room=DEFAULT_ROOM, broadcast=True)
                    else:
                        emit('new_message', {
                            'nickname': '川小农',
                            'message': '暂时无法获取免费电影资源，请稍后再试',
                            'is_ai': True
                        }, room=DEFAULT_ROOM, broadcast=True)
                except Exception as e:
                    print(f"获取随机电影失败: {str(e)}")
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': '获取电影信息时出错，请稍后重试',
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
        elif '@音乐' in message:
            message_type = 'music'
            
            # 保存用户消息到数据库
            db_manager.save_message(
                nickname=nickname,
                message=message,
                session_id=session_id,
                message_type='music',
                is_at_message=True,
                user_ip=client_ip,
                room=DEFAULT_ROOM
            )
            
            emit('new_message', {
                'nickname': nickname,
                'message': message,
                'is_at': True
            }, room=DEFAULT_ROOM, broadcast=True)
            
            # 提取用户输入的音乐名称
            music_name = message.split('@音乐', 1)[1].strip() if len(message.split('@音乐', 1)) > 1 else None
            
            # 获取音乐并发送音乐卡片
            if music_name:
                emit('new_message', {
                    'nickname': '川小农',
                    'message': f'正在为您搜索音乐《{music_name}》...',
                    'is_ai': True
                }, room=DEFAULT_ROOM, broadcast=True)
                
                try:
                    music_data = music_weather_api.search_music(music_name)
                    if not music_data:
                        # 如果搜索不到，使用随机音乐作为备选
                        music_data = music_weather_api.get_random_music()
                        emit('new_message', {
                            'nickname': '川小农',
                            'message': f'未找到《{music_name}》，为您推荐一首相似音乐...',
                            'is_ai': True
                        }, room=DEFAULT_ROOM, broadcast=True)
                except Exception as e:
                    print(f"搜索音乐失败: {str(e)}")
                    music_data = music_weather_api.get_random_music()
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': f'搜索《{music_name}》失败，为您推荐一首随机音乐...',
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
            else:
                emit('new_message', {
                    'nickname': '川小农',
                    'message': '正在为您推荐一首好听的音乐...',
                    'is_ai': True
                }, room=DEFAULT_ROOM, broadcast=True)
                
                try:
                    music_data = music_weather_api.get_random_music()
                except Exception as e:
                    print(f"获取随机音乐失败: {str(e)}")
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': '获取音乐失败，请稍后再试...',
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
                    return
                if music_data:
                    # 发送音乐卡片给所有用户
                    emit('music_card', {
                        'nickname': '川小农',
                        'music_data': music_data,
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
                    
                    # 保存音乐信息到数据库
                    music_info = f"🎵 音乐推荐：《{music_data.get('name', '未知')}》 - {music_data.get('singer', '未知歌手')}"
                    db_manager.save_message(
                        nickname='川小农',
                        message=music_info,
                        session_id=session_id,
                        message_type='music',
                        is_ai_response=True,
                        user_ip=client_ip,
                        room=DEFAULT_ROOM
                    )
                else:
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': '抱歉，暂时无法获取音乐推荐，请稍后再试！',
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)

        elif '@天气' in message:
            message_type = 'weather'
            
            # 保存用户消息到数据库
            db_manager.save_message(
                nickname=nickname,
                message=message,
                session_id=session_id,
                message_type='weather',
                is_at_message=True,
                user_ip=client_ip,
                room=DEFAULT_ROOM
            )
            
            emit('new_message', {
                'nickname': nickname,
                'message': message,
                'is_at': True
            }, room=DEFAULT_ROOM, broadcast=True)
            
            # 提取城市名称（支持多种格式）
            if '@天气' in message:
                city_part = message.split('@天气', 1)[1].strip()
                # 清理常见的前缀词
                city_part = city_part.replace('查询', '').replace('查看', '').replace('一下', '')
                city_part = city_part.replace('的', '').replace('天', '').replace('气', '')
                city = city_part.strip() if city_part else "位置"  # 默认获取当前位置
            else:
                city = "位置"
            
            # 发送天气查询中提示
            if city == "位置":
                query_message = '正在获取你的当前位置天气信息...'
            else:
                query_message = f'正在查询{city}的天气信息...'
            
            emit('new_message', {
                'nickname': '川小农',
                'message': query_message,
                'is_ai': True
            }, room=DEFAULT_ROOM, broadcast=True)
            
            try:
                # 根据城市名称选择天气获取方法
                if city == "位置" or city == "当前位置":
                    weather_data = music_weather_api.get_current_location_weather()
                else:
                    weather_data = music_weather_api.get_weather_info(city)
                
                if weather_data:
                    # 生成天气报告消息
                    weather_report = f"""🌤️ {weather_data['city']}天气预报
{weather_data['icon']} {weather_data['condition']} {weather_data['temperature']}
💨 风力: {weather_data['wind']}
💧 湿度: {weather_data['humidity']}%
🕐 更新时间: {weather_data['update_time']}"""
                    
                    # 发送天气卡片给所有用户
                    emit('weather_card', {
                        'nickname': '川小农',
                        'weather_data': weather_data,
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
                    
                    # 保存天气信息到数据库
                    db_manager.save_message(
                        nickname='川小农',
                        message=weather_report,
                        session_id=session_id,
                        message_type='weather',
                        is_ai_response=True,
                        user_ip=client_ip,
                        room=DEFAULT_ROOM
                    )
                else:
                    error_msg = f'抱歉，无法获取{city}的天气信息，请稍后重试！'
                    emit('new_message', {
                        'nickname': '川小农',
                        'message': error_msg,
                        'is_ai': True
                    }, room=DEFAULT_ROOM, broadcast=True)
            except Exception as e:
                print(f"获取天气失败: {str(e)}")
                error_msg = f'获取{city}天气信息时出错，请稍后重试！'
                emit('new_message', {
                    'nickname': '川小农',
                    'message': error_msg,
                    'is_ai': True
                }, room=DEFAULT_ROOM, broadcast=True)
        else:
            # 普通@提醒
            # 保存用户消息到数据库
            db_manager.save_message(
                nickname=nickname,
                message=message,
                session_id=session_id,
                message_type='at',
                is_at_message=True,
                user_ip=client_ip,
                room=DEFAULT_ROOM
            )
            
            emit('new_message', {
                'nickname': nickname,
                'message': message,
                'is_at': True
            }, room=DEFAULT_ROOM, broadcast=True)
    else:
        # 普通消息
        # 保存用户消息到数据库
        db_manager.save_message(
            nickname=nickname,
            message=message,
            session_id=session_id,
            message_type='text',
            user_ip=client_ip,
            room=DEFAULT_ROOM
        )
        
        emit('new_message', {
            'nickname': nickname,
            'message': message
        }, room=DEFAULT_ROOM, broadcast=True)

# AI流式回复生成器
def generate_ai_stream_response(question):
    """
    使用AI大模型生成流式回复
    参数:
        question: 用户问题
    生成器:
        流式输出AI回复文本
    """
    try:
        # 确保问题不为None
        if question is None:
            question = ""
        
        # 去除首尾空格
        question = question.strip()
        
        # 如果问题为空，返回引导用户提问的消息
        if not question:
            welcome_message = "你好！我是川小农，四川农业大学的AI百科助手。请问你想了解关于川农的哪些信息呢？比如：学校历史、校区、专业设置、宿舍环境等。"
            # 模拟流式输出
            for char in welcome_message:
                yield f"data: {json.dumps({'content': char, 'type': 'token'})}\n\n"
                time.sleep(0.03)  # 模拟打字延迟
            yield f"data: {json.dumps({'content': '', 'type': 'end'})}\n\n"
            return
        
        # 构建川小农的角色提示词
        system_prompt = """你是川小农，四川农业大学的智能百科助手。你的使命是回答关于四川农业大学的各类问题，为学生、家长和关心川农的人士提供准确、及时、友好的信息。

请始终以川小农的身份回答，保持友好、专业的语气，并确保信息的准确性。如果遇到不确定的信息，请诚实地表示不知道，并建议用户查询官方渠道获取最新信息。"""
        
        try:
            # 调用AI大模型流式接口
            stream = openai_client.chat.completions.create(
                model=AI_CONFIG['model_name'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                stream=True,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9
            )
            
            # 流式输出AI回复
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    yield f"data: {json.dumps({'content': content, 'type': 'token'})}\n\n"
                    time.sleep(0.02)  # 控制输出速度
            
            yield f"data: {json.dumps({'content': '', 'type': 'end'})}\n\n"
            
        except Exception as ai_error:
            print(f"AI流式模型调用失败: {str(ai_error)}")
            print("回退到川小农知识库...")
            
            # AI调用失败时回退到川小农知识库
            fallback_response, _ = assistant.generate_response(question)
            
            # 模拟流式输出fallback回复
            for char in fallback_response:
                yield f"data: {json.dumps({'content': char, 'type': 'token'})}\n\n"
                time.sleep(0.03)
            yield f"data: {json.dumps({'content': '', 'type': 'end'})}\n\n"
            
    except Exception as e:
        print(f"生成AI流式回复时出错: {str(e)}")
        error_message = f"很抱歉，在处理你的问题'{question}'时遇到了一些困难。请稍后再试，或者尝试使用不同的关键词提问。"
        
        # 模拟流式输出错误消息
        for char in error_message:
            yield f"data: {json.dumps({'content': char, 'type': 'token'})}\n\n"
            time.sleep(0.03)
        yield f"data: {json.dumps({'content': '', 'type': 'end'})}\n\n"

# AI流式回复路由
@app.route('/api/ai/stream')
def ai_stream():
    """
    AI流式回复API端点
    使用SSE (Server-Sent Events) 协议返回流式响应
    """
    question = request.args.get('question', '')
    
    def generate():
        yield from generate_ai_stream_response(question)
    
    return Response(generate(), mimetype='text/event-stream', 
                   headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

# 退出聊天室
@socketio.on('leave_room')
def handle_leave_room(data):
    nickname = data['nickname']
    if nickname in online_users:
        del online_users[nickname]
        leave_room(DEFAULT_ROOM)
        emit('user_left', {
            'nickname': nickname,
            'online_users': list(online_users.keys())
        }, room=DEFAULT_ROOM, broadcast=True)

# AI回复生成函数 - 使用川小农助手类提供完整的关键词匹配功能
def generate_ai_response(question, use_ai_model=True):
    """
    使用AI大模型生成更智能的回复
    参数:
        question: 用户问题
        use_ai_model: 是否使用AI大模型（True则调用AI接口，False则使用川小农知识库）
    返回:
        生成的回复文本
    """
    try:
        # 确保问题不为None
        if question is None:
            question = ""
        
        # 去除首尾空格
        question = question.strip()
        
        # 如果问题为空，返回引导用户提问的消息
        if not question:
            return "你好！我是川小农，四川农业大学的AI百科助手。请问你想了解关于川农的哪些信息呢？比如：学校历史、校区、专业设置、宿舍环境等。"
        
        # 如果不使用AI模型，直接使用川小农知识库
        if not use_ai_model:
            response, _ = assistant.generate_response(question)
            if not response or response.strip() == "":
                return f"感谢你的提问：'{question}'。请尝试使用更具体的关键词，如'校区'、'专业'、'宿舍'、'招生'等，我会为你提供详细解答！"
            return response
        
        # 使用AI大模型生成回复
        try:
            # 构建川小农的角色提示词
            system_prompt = """你是川小农，四川农业大学的智能百科助手。你的使命是回答关于四川农业大学的各类问题，为学生、家长和关心川农的人士提供准确、及时、友好的信息。

请始终以川小农的身份回答，保持友好、专业的语气，并确保信息的准确性。如果遇到不确定的信息，请诚实地表示不知道，并建议用户查询官方渠道获取最新信息。"""
            
            # 调用AI大模型
            response = openai_client.chat.completions.create(
                model=AI_CONFIG['model_name'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                stream=False,
                max_tokens=1000,
                temperature=0.7,
                top_p=0.9
            )
            
            # 提取AI回复内容
            ai_response = response.choices[0].message.content
            
            # 如果AI回复为空或太短，回退到川小农知识库
            if not ai_response or len(ai_response.strip()) < 10:
                fallback_response, _ = assistant.generate_response(question)
                return fallback_response
            
            return ai_response
            
        except Exception as ai_error:
            print(f"AI模型调用失败: {str(ai_error)}")
            print("回退到川小农知识库...")
            # AI调用失败时回退到川小农知识库
            fallback_response, _ = assistant.generate_response(question)
            return fallback_response
            
    except Exception as e:
        print(f"生成AI回复时出错: {str(e)}")
        return f"很抱歉，在处理你的问题'{question}'时遇到了一些困难。请稍后再试，或者尝试使用不同的关键词提问。"


if __name__ == '__main__':
    # 设置调试模式
    app.config['DEBUG'] = True
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)