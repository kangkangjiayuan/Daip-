#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite数据库管理模块
用于存储聊天消息和用户会话数据
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    """SQLite数据库管理器"""
    
    def __init__(self, db_path: str = "chat_database.db"):
        """
        初始化数据库管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接
        
        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # 允许通过列名访问结果
        return conn
        
    def create_user(self, username: str, password: str) -> bool:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 生成密码哈希
            password_hash = generate_password_hash(password)
            
            # 插入用户数据
            cursor.execute('''
                INSERT INTO users (username, password_hash)
                VALUES (?, ?)
            ''', (username, password_hash))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # 用户名已存在
            return False
        except Exception as e:
            print(f"创建用户失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        根据用户名获取用户信息
        
        Args:
            username: 用户名
            
        Returns:
            Optional[Dict]: 用户信息字典，不存在返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, username, password_hash, created_at
                FROM users
                WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            if user:
                return dict(user)
            return None
            
        except Exception as e:
            print(f"获取用户失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def verify_user_password(self, username: str, password: str) -> Optional[int]:
        """
        验证用户密码
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            Optional[int]: 验证成功返回用户ID，失败返回None
        """
        user = self.get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return user['id']
        return None
    
    def init_database(self):
        """初始化数据库和表结构"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建用户会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    nickname TEXT NOT NULL,
                    user_id INTEGER,
                    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    status TEXT DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 创建聊天消息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    nickname TEXT NOT NULL,
                    message TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    is_ai_response BOOLEAN DEFAULT 0,
                    is_at_message BOOLEAN DEFAULT 0,
                    is_movie BOOLEAN DEFAULT 0,
                    movie_url TEXT,
                    movie_info TEXT,
                    is_music BOOLEAN DEFAULT 0,
                    music_data TEXT,
                    is_weather BOOLEAN DEFAULT 0,
                    weather_data TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    user_ip TEXT,
                    room TEXT DEFAULT 'chat_room',
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
                )
            ''')
            
            # 创建用户配置表（用于存储用户偏好）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    nickname TEXT NOT NULL,
                    settings_json TEXT DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES user_sessions(session_id)
                )
            ''')
            
            # 为现有数据库添加音乐和天气功能列
            try:
                cursor.execute('''
                    ALTER TABLE messages ADD COLUMN is_music BOOLEAN DEFAULT 0
                ''')
                cursor.execute('''
                    ALTER TABLE messages ADD COLUMN music_data TEXT
                ''')
                cursor.execute('''
                    ALTER TABLE messages ADD COLUMN is_weather BOOLEAN DEFAULT 0
                ''')
                cursor.execute('''
                    ALTER TABLE messages ADD COLUMN weather_data TEXT
                ''')
                print("成功为现有数据库添加音乐和天气功能列")
            except sqlite3.OperationalError as e:
                # 列已存在，忽略错误
                if "duplicate column name" not in str(e).lower():
                    print(f"警告：添加列时发生错误（可能列已存在）: {str(e)}")

            # 创建索引以提高查询性能
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_nickname 
                ON messages(nickname)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_timestamp 
                ON messages(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session_id 
                ON messages(session_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_room 
                ON messages(room)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_sessions_nickname 
                ON user_sessions(nickname)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_sessions_status 
                ON user_sessions(status)
            ''')
            
            conn.commit()
            print("数据库初始化成功！")
            
        except sqlite3.Error as e:
            print(f"数据库初始化失败: {str(e)}")
            raise
        finally:
            conn.close()
    
    def create_session(self, session_id: str, nickname: str, ip_address: str = None, user_agent: str = None) -> bool:
        """
        创建用户会话
        
        Args:
            session_id: 会话ID
            nickname: 用户昵称
            ip_address: IP地址
            user_agent: 用户代理
            
        Returns:
            bool: 创建成功返回True，否则返回False
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_sessions (session_id, nickname, ip_address, user_agent)
                VALUES (?, ?, ?, ?)
            ''', (session_id, nickname, ip_address, user_agent))
            
            conn.commit()
            return True
            
        except sqlite3.IntegrityError:
            # 会话已存在，更新最后活动时间
            return self.update_session_activity(session_id)
        except sqlite3.Error as e:
            print(f"创建会话失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        更新会话活动时间
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"更新会话活动时间失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def save_message(self, nickname: str, message: str, session_id: str = None, 
                    message_type: str = 'text', is_ai_response: bool = False,
                    is_at_message: bool = False, is_movie: bool = False,
                    movie_url: str = None, movie_info: str = None,
                    is_music: bool = False, music_data: str = None,
                    is_weather: bool = False, weather_data: str = None,
                    user_ip: str = None, room: str = 'chat_room') -> Optional[int]:
        """
        保存聊天消息
        
        Args:
            nickname: 用户昵称
            message: 消息内容
            session_id: 会话ID
            message_type: 消息类型 (text, ai, at, movie, music, weather等)
            is_ai_response: 是否为AI回复
            is_at_message: 是否为@消息
            is_movie: 是否为电影分享
            movie_url: 视频链接
            movie_info: 视频信息
            is_music: 是否为音乐分享
            music_data: 音乐数据（JSON格式）
            is_weather: 是否为天气信息
            weather_data: 天气数据（JSON格式）
            user_ip: 用户IP
            room: 聊天室名称
            
        Returns:
            int: 消息ID，失败返回None
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO messages (
                    session_id, nickname, message, message_type,
                    is_ai_response, is_at_message, is_movie,
                    movie_url, movie_info, is_music, music_data,
                    is_weather, weather_data, user_ip, room
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session_id, nickname, message, message_type,
                is_ai_response, is_at_message, is_movie,
                movie_url, movie_info, is_music, music_data,
                is_weather, weather_data, user_ip, room
            ))
            
            message_id = cursor.lastrowid
            conn.commit()
            return message_id
            
        except sqlite3.Error as e:
            print(f"保存消息失败: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_messages(self, limit: int = 50, offset: int = 0, 
                    nickname: str = None, room: str = 'chat_room',
                    message_type: str = None, start_time: str = None,
                    end_time: str = None) -> List[Dict]:
        """
        获取聊天消息历史
        
        Args:
            limit: 返回消息数量限制
            offset: 偏移量
            nickname: 按用户昵称过滤
            room: 按聊天室过滤
            message_type: 按消息类型过滤
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[Dict]: 消息列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            where_conditions = ["1=1"]
            params = []
            
            if nickname:
                where_conditions.append("nickname = ?")
                params.append(nickname)
            
            if room:
                where_conditions.append("room = ?")
                params.append(room)
            
            if message_type:
                where_conditions.append("message_type = ?")
                params.append(message_type)
            
            if start_time:
                where_conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                where_conditions.append("timestamp <= ?")
                params.append(end_time)
            
            where_clause = " AND ".join(where_conditions)
            
            cursor.execute(f'''
                SELECT id, session_id, nickname, message, message_type,
                       is_ai_response, is_at_message, is_movie, movie_url,
                       movie_info, is_music, music_data, is_weather, 
                       weather_data, timestamp, user_ip, room
                FROM messages 
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (*params, limit, offset))
            
            rows = cursor.fetchall()
            
            # 转换为字典列表
            messages = []
            for row in rows:
                message_dict = dict(row)
                messages.append(message_dict)
            
            # 返回正序（最新的消息在最后）
            return messages[::-1]
            
        except sqlite3.Error as e:
            print(f"获取消息历史失败: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_user_sessions(self, nickname: str = None) -> List[Dict]:
        """
        获取用户会话列表
        
        Args:
            nickname: 按用户昵称过滤
            
        Returns:
            List[Dict]: 会话列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if nickname:
                cursor.execute('''
                    SELECT session_id, nickname, start_time, last_activity, 
                           ip_address, status, created_at
                    FROM user_sessions 
                    WHERE nickname = ? 
                    ORDER BY last_activity DESC
                ''', (nickname,))
            else:
                cursor.execute('''
                    SELECT session_id, nickname, start_time, last_activity, 
                           ip_address, status, created_at
                    FROM user_sessions 
                    ORDER BY last_activity DESC
                ''')
            
            rows = cursor.fetchall()
            sessions = [dict(row) for row in rows]
            
            return sessions
            
        except sqlite3.Error as e:
            print(f"获取会话列表失败: {str(e)}")
            return []
        finally:
            conn.close()

    def get_message_history(self, nickname: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        获取消息历史（get_messages方法的别名）
        
        Args:
            nickname: 按用户昵称过滤
            limit: 返回消息数量限制
            offset: 偏移量
            
        Returns:
            List[Dict]: 消息列表
        """
        return self.get_messages(nickname=nickname, limit=limit, offset=offset)

    def get_user_stats(self, nickname: str = None, start_time: str = None, 
                      end_time: str = None) -> Dict:
        """
        获取用户统计信息
        
        Args:
            nickname: 用户昵称
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict: 统计信息
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            where_conditions = ["1=1"]
            params = []
            
            if nickname:
                where_conditions.append("nickname = ?")
                params.append(nickname)
            
            if start_time:
                where_conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time:
                where_conditions.append("timestamp <= ?")
                params.append(end_time)
            
            where_clause = " AND ".join(where_conditions)
            
            # 获取总消息数
            cursor.execute(f'''
                SELECT COUNT(*) as total_messages
                FROM messages 
                WHERE {where_clause}
            ''', params)
            total_messages = cursor.fetchone()['total_messages']
            
            # 获取AI回复数
            cursor.execute(f'''
                SELECT COUNT(*) as ai_messages
                FROM messages 
                WHERE {where_clause} AND is_ai_response = 1
            ''', params)
            ai_messages = cursor.fetchone()['ai_messages']
            
            # 获取@消息数
            cursor.execute(f'''
                SELECT COUNT(*) as at_messages
                FROM messages 
                WHERE {where_clause} AND is_at_message = 1
            ''', params)
            at_messages = cursor.fetchone()['at_messages']
            
            # 获取电影分享数
            cursor.execute(f'''
                SELECT COUNT(*) as movie_messages
                FROM messages 
                WHERE {where_clause} AND is_movie = 1
            ''', params)
            movie_messages = cursor.fetchone()['movie_messages']
            
            # 获取活跃用户列表
            cursor.execute(f'''
                SELECT nickname, COUNT(*) as message_count
                FROM messages 
                WHERE {where_clause}
                GROUP BY nickname
                ORDER BY message_count DESC
                LIMIT 10
            ''', params)
            active_users = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_messages': total_messages,
                'ai_messages': ai_messages,
                'at_messages': at_messages,
                'movie_messages': movie_messages,
                'active_users': active_users
            }
            
        except sqlite3.Error as e:
            print(f"获取用户统计失败: {str(e)}")
            return {}
        finally:
            conn.close()
    
    def close_session(self, session_id: str) -> bool:
        """
        关闭用户会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 成功返回True
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_sessions 
                SET status = 'closed', last_activity = CURRENT_TIMESTAMP 
                WHERE session_id = ?
            ''', (session_id,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"关闭会话失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def cleanup_old_messages(self, days: int = 30) -> bool:
        """
        清理过期的聊天消息
        
        Args:
            days: 保留天数
            
        Returns:
            bool: 成功返回True
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM messages 
                WHERE timestamp < datetime('now', '-{} days')
            '''.format(days))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"清理了 {deleted_count} 条过期消息")
            return True
            
        except sqlite3.Error as e:
            print(f"清理过期消息失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def export_messages(self, filename: str = None, format: str = 'json') -> bool:
        """
        导出聊天记录
        
        Args:
            filename: 导出文件名
            format: 导出格式 ('json' 或 'csv')
            
        Returns:
            bool: 成功返回True
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"chat_messages_{timestamp}.{format}"
            
            messages = self.get_messages(limit=10000)  # 最多导出1万条记录
            
            if format.lower() == 'json':
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(messages, f, ensure_ascii=False, indent=2, default=str)
            elif format.lower() == 'csv':
                import csv
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if messages:
                        writer = csv.DictWriter(f, fieldnames=messages[0].keys())
                        writer.writeheader()
                        writer.writerows(messages)
            
            print(f"聊天记录已导出到: {filename}")
            return True
            
        except Exception as e:
            print(f"导出记录失败: {str(e)}")
            return False
        finally:
            pass
    
    def check_data_integrity(self) -> Dict:
        """
        检查数据完整性
        
        Returns:
            Dict: 完整性检查结果
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            issues = []
            
            # 检查孤儿消息（没有对应会话的消息）
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM messages m
                LEFT JOIN user_sessions s ON m.session_id = s.session_id
                WHERE s.session_id IS NULL AND m.session_id IS NOT NULL
            ''')
            orphan_messages = cursor.fetchone()['count']
            if orphan_messages > 0:
                issues.append(f"发现 {orphan_messages} 条孤儿消息")
            
            # 检查重复会话
            cursor.execute('''
                SELECT COUNT(*) as count FROM (
                    SELECT session_id, COUNT(*) as cnt
                    FROM user_sessions
                    GROUP BY session_id
                    HAVING cnt > 1
                )
            ''')
            duplicate_sessions = cursor.fetchone()['count']
            if duplicate_sessions > 0:
                issues.append(f"发现 {duplicate_sessions} 个重复会话")
            
            # 检查消息长度
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM messages
                WHERE LENGTH(message) > 4000
            ''')
            long_messages = cursor.fetchone()['count']
            if long_messages > 0:
                issues.append(f"发现 {long_messages} 条过长的消息")
            
            # 检查会话活跃性
            cursor.execute('''
                SELECT COUNT(*) as count
                FROM user_sessions
                WHERE status = 'active' AND last_activity < datetime('now', '-24 hours')
            ''')
            stale_sessions = cursor.fetchone()['count']
            if stale_sessions > 0:
                issues.append(f"发现 {stale_sessions} 个超过24小时未活跃的会话")
            
            return {
                'status': 'healthy' if not issues else 'warning',
                'issues': issues,
                'check_time': datetime.now().isoformat()
            }
            
        except sqlite3.Error as e:
            print(f"数据完整性检查失败: {str(e)}")
            return {
                'status': 'error',
                'issues': [f"检查失败: {str(e)}"],
                'check_time': datetime.now().isoformat()
            }
        finally:
            conn.close()
    
    def backup_database(self, backup_dir: str = "backups") -> bool:
        """
        备份数据库
        
        Args:
            backup_dir: 备份目录
            
        Returns:
            bool: 成功返回True
        """
        try:
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # 使用SQLite的备份API
            source = sqlite3.connect(self.db_path)
            backup = sqlite3.connect(backup_path)
            
            with backup:
                source.backup(backup)
            
            source.close()
            backup.close()
            
            print(f"数据库备份成功: {backup_path}")
            return True
            
        except Exception as e:
            print(f"数据库备份失败: {str(e)}")
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        从备份恢复数据库
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 成功返回True
        """
        try:
            if not os.path.exists(backup_path):
                print(f"备份文件不存在: {backup_path}")
                return False
            
            # 创建当前数据库的备份
            if os.path.exists(self.db_path):
                backup_current = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.db_path, backup_current)
                print(f"当前数据库已备份到: {backup_current}")
            
            # 恢复备份
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            print(f"数据库恢复成功: {self.db_path}")
            return True
            
        except Exception as e:
            print(f"数据库恢复失败: {str(e)}")
            return False
    
    def migrate_data(self, target_version: str = "1.1") -> bool:
        """
        数据迁移（用于数据库结构升级）
        
        Args:
            target_version: 目标版本
            
        Returns:
            bool: 成功返回True
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查当前数据库版本
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 如果没有版本表，创建一个
            if 'database_version' not in tables:
                cursor.execute('''
                    CREATE TABLE database_version (
                        version TEXT PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
                current_version = "1.0"
            else:
                cursor.execute("SELECT version FROM database_version ORDER BY applied_at DESC LIMIT 1")
                result = cursor.fetchone()
                current_version = result[0] if result else "1.0"
            
            # 根据版本执行迁移
            migrations = []
            
            if current_version == "1.0" and target_version >= "1.1":
                migrations.append(("1.1", self._migrate_to_1_1))
            
            # 执行迁移
            for version, migration_func in migrations:
                print(f"执行数据迁移到版本 {version}...")
                if migration_func(cursor):
                    cursor.execute("INSERT OR REPLACE INTO database_version (version) VALUES (?)", (version,))
                    conn.commit()
                    print(f"迁移到版本 {version} 完成")
                else:
                    print(f"迁移到版本 {version} 失败")
                    return False
            
            return True
            
        except sqlite3.Error as e:
            print(f"数据迁移失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def _migrate_to_1_1(self, cursor) -> bool:
        """
        迁移到版本1.1的示例（添加一些新功能）
        
        Args:
            cursor: 数据库游标
            
        Returns:
            bool: 成功返回True
        """
        try:
            # 示例：添加消息优先级字段
            cursor.execute("ALTER TABLE messages ADD COLUMN priority INTEGER DEFAULT 0")
            
            # 示例：添加消息标签字段
            cursor.execute("ALTER TABLE messages ADD COLUMN tags TEXT DEFAULT '{}'")
            
            # 示例：创建消息搜索索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_message_search ON messages(message)")
            
            return True
            
        except sqlite3.Error as e:
            print(f"版本1.1迁移失败: {str(e)}")
            return False
    
    def optimize_database(self) -> bool:
        """
        优化数据库性能
        
        Returns:
            bool: 成功返回True
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 重建索引
            cursor.execute("REINDEX")
            
            # 清理数据库
            cursor.execute("VACUUM")
            
            # 分析表统计信息
            cursor.execute("ANALYZE")
            
            conn.commit()
            print("数据库优化完成")
            return True
            
        except sqlite3.Error as e:
            print(f"数据库优化失败: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_database_stats(self) -> Dict:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 表大小统计
            cursor.execute("""
                SELECT 
                    name,
                    (SELECT COUNT(*) FROM messages) as message_count,
                    (SELECT COUNT(*) FROM user_sessions) as session_count,
                    (SELECT COUNT(*) FROM user_settings) as settings_count
                FROM sqlite_master 
                WHERE type='table' AND name IN ('messages', 'user_sessions', 'user_settings')
            """)
            
            stats = {}
            for row in cursor.fetchall():
                stats[row[0]] = {
                    'table_name': row[0],
                    'message_count': row[1],
                    'session_count': row[2],
                    'settings_count': row[3]
                }
            
            # 数据库文件大小
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
            
            return {
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'tables': stats,
                'generated_at': datetime.now().isoformat()
            }
            
        except sqlite3.Error as e:
            print(f"获取数据库统计失败: {str(e)}")
            return {}
        finally:
            conn.close()

# 全局数据库管理器实例
db_manager = DatabaseManager()