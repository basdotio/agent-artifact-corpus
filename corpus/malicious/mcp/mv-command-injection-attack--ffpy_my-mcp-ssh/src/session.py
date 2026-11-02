import time
import paramiko
import threading
import random
import string
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple


@dataclass
class Session:
    """SSH会话数据类，用于存储SSH连接信息"""
    
    # SSH客户端对象
    ssh_client: paramiko.SSHClient
    
    # 会话ID
    id: str
    
    # SFTP客户端对象
    sftp_client: Optional[paramiko.SFTPClient] = None
    
    # 最后活动时间戳
    last_active: float = 0
    
    def __post_init__(self):
        if not self.last_active:
            self.last_active = time.time()
    
    def update_activity(self):
        """更新最后活动时间"""
        self.last_active = time.time()
    
    def get_idle_time(self) -> float:
        """获取会话空闲时间(秒)"""
        return time.time() - self.last_active
    
    def close(self):
        """关闭会话连接"""
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于API返回"""
        return {
            "session_id": self.id,
            "idle_time": f"{self.get_idle_time():.1f}s"
        }


class SessionManager:
    """SSH会话管理器，用于管理所有SSH会话"""
    
    def __init__(self, timeout_minutes: int = 30):
        """初始化会话管理器
        
        参数:
            timeout_minutes: 会话超时时间（分钟），默认30分钟
        """
        # 会话字典，格式: {session_id: SSHSession对象}
        self.sessions: Dict[str, Session] = {}
        # 会话超时时间（分钟）
        self.timeout_minutes = timeout_minutes
        # 会话操作锁
        self.lock = threading.Lock()
        # 启动清理线程
        self.cleanup_thread = threading.Thread(target=self._cleanup_inactive_sessions, daemon=True)
        self.cleanup_thread.start()
    
    def create_session(self, session: Session) -> str:
        """创建一个新会话，生成并返回会话ID
        
        参数:
            session: SSHSession对象
            
        返回:
            生成的会话ID
        """
        with self.lock:
            # 生成8位随机字符串作为session_id
            while True:
                session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                # 确保session_id不重复
                if session_id not in self.sessions:
                    break
            
            # 设置会话ID
            session.id = session_id
            self.sessions[session_id] = session
            return session_id
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取指定ID的会话
        
        参数:
            session_id: 会话ID
            
        返回:
            SSHSession对象，如果不存在则返回None
        """
        with self.lock:
            return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> bool:
        """移除指定ID的会话
        
        参数:
            session_id: 会话ID
            
        返回:
            是否成功移除会话
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def update_session_activity(self, session_id: str) -> bool:
        """更新会话活动时间
        
        参数:
            session_id: 会话ID
            
        返回:
            是否成功更新会话
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id].update_activity()
                return True
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话信息
        
        返回:
            包含所有会话信息的列表
        """
        sessions_info = []
        with self.lock:
            for _, session in self.sessions.items():
                sessions_info.append(session.to_dict())
        return sessions_info
    
    def close_all_sessions(self) -> None:
        """关闭所有会话"""
        with self.lock:
            for session_id, session in list(self.sessions.items()):
                try:
                    session.close()
                    del self.sessions[session_id]
                except Exception as e:
                    print(f"关闭会话 {session_id} 时出错: {str(e)}")
    
    def _cleanup_inactive_sessions(self) -> None:
        """清理不活跃的会话（内部方法）"""
        while True:
            time.sleep(60)  # 每分钟检查一次
            with self.lock:
                for session_id in list(self.sessions.keys()):
                    session = self.sessions[session_id]
                    if session.get_idle_time() > (self.timeout_minutes * 60):
                        try:
                            session.close()
                            del self.sessions[session_id]
                            print(f"会话 {session_id} 因不活跃已自动关闭")
                        except Exception as e:
                            print(f"关闭不活跃会话 {session_id} 时出错: {str(e)}") 