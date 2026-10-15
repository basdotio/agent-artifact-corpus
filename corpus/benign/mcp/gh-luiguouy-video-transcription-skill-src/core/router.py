"""
平台认证级别与风控策略路由器模块
负责基于 URL 静态特征与运行时异常特征，精准区分“免登录平台 (Guest-Fresh)”与“强登录平台 (Account-Login)”
"""

import re
from enum import Enum
from typing import Optional, Dict, Any


class AuthRequirement(str, Enum):
    """
    平台凭据需求等级
    """
    ANONYMOUS = "anonymous"          # 开放平台：完全公开，免登录免签名直连（如 B站普通视频、开放播客）
    GUEST_FRESH = "guest_fresh"      # 免账号登录，但依赖真实浏览器即时 JS 签名防爬（如 抖音、快手、西瓜短视频、TikTok）
    ACCOUNT_LOGIN = "account_login"  # 强登录平台：依赖用户真实账号的登录会话（如 YouTube 防机器人、B站大会员、X私密推文）


class PlatformClassifier:
    """
    平台特征与认证策略路由器
    第一性原理：
    1. 抖音等短视频平台核心是反爬防盗链（通过 __ac_signature/JS混淆），本质只需即时'造鲜'，无需个人账号；
    2. YouTube/B站大会员核心是反代理黑名单与会员权限，本质必须绑定个人账号的登录 Session。
    """

    # 静态规则库：域名到默认凭据级别的映射
    _DOMAIN_RULES = [
        # 免登录但需要新鲜 JS 签名的平台 (Guest-Fresh)
        (r"(douyin\.com|iesdouyin\.com|kuaishou\.com|tiktok\.com|ixigua\.com)", AuthRequirement.GUEST_FRESH),
        # 必须依赖真实用户账号登录态的平台 (Account-Login)
        (r"(youtube\.com|youtu\.be)", AuthRequirement.ACCOUNT_LOGIN),
        # 默认开放，但高码率/特殊内容可动态升级的平台
        (r"(bilibili\.com|b23\.tv)", AuthRequirement.ANONYMOUS),
        (r"(x\.com|twitter\.com)", AuthRequirement.ANONYMOUS),
    ]

    # 动态异常诊断特征库
    _ERROR_PATTERNS = [
        (r"Fresh cookies \(not necessarily logged in\) are needed", AuthRequirement.GUEST_FRESH),
        (r"Sign in to confirm you[’']re not a bot", AuthRequirement.ACCOUNT_LOGIN),
        (r"(Please sign in|This video is private|requires authentication|login required)", AuthRequirement.ACCOUNT_LOGIN),
    ]

    @classmethod
    def classify_url(cls, url: str) -> AuthRequirement:
        """
        基于 URL 域名特征，静态判定平台所需的凭证级别
        """
        clean_url = (url or "").strip().lower()
        for pattern, req_level in cls._DOMAIN_RULES:
            if re.search(pattern, clean_url):
                return req_level
        return AuthRequirement.ANONYMOUS

    @classmethod
    def diagnose_error(cls, error_message: str) -> Optional[AuthRequirement]:
        """
        基于抓取过程中抛出的底层报错信息，动态识别是否需要升级认证策略
        """
        msg = (error_message or "").strip()
        for pattern, req_level in cls._ERROR_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                return req_level
        return None

    @classmethod
    def get_strategy_description(cls, requirement: AuthRequirement) -> Dict[str, str]:
        """
        获取对应凭据级别的底层解决策略说明
        """
        if requirement == AuthRequirement.GUEST_FRESH:
            return {
                "level": "免登录平台 (GUEST_FRESH)",
                "description": "平台不需要个人账号，仅需真实 Chromium 浏览器即时渲染执行混淆 JS，生成最新 __ac_signature 等访客防爬签名。",
                "solution": "后台无头浏览器 1 秒即时造鲜，或使用已解除文件锁的 Chrome/Edge/cookies.txt。"
            }
        elif requirement == AuthRequirement.ACCOUNT_LOGIN:
            return {
                "level": "强登录平台 (ACCOUNT_LOGIN)",
                "description": "平台严格校验个人用户账号会话（对抗机房代理 IP 黑名单或会员专享限制）。",
                "solution": "优先连接 Chrome CDP 远程调试端口 (9222) 直抽内存登录态，或读取本地已登录的浏览器 Cookies。"
            }
        else:
            return {
                "level": "开放直连平台 (ANONYMOUS)",
                "description": "公开免登录视频流，可直接匿名高速抓取，无需任何 Cookies。",
                "solution": "直接请求 CDN，受限时动态升级。"
            }
