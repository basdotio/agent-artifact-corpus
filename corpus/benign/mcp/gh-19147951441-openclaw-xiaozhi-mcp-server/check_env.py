#!/usr/bin/env python3
"""
OpenClaw MCP Server 环境检查脚本

使用方法:
    python check_env.py

此脚本将检查:
- Python 版本
- 依赖包安装
- 环境变量配置
- 网络连接状态
"""

import sys
import os
import importlib
from datetime import datetime

# 颜色定义
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

def print_check(name, status, message=""):
    icon = "✅" if status else "❌"
    color = Colors.GREEN if status else Colors.RED
    print(f"{icon} {color}{name:<30}{Colors.RESET} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  警告：{message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def check_python_version():
    """检查 Python 版本"""
    print_header("Python 版本检查")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    print(f"Python 版本：{version_str}")
    print(f"Python 路径：{sys.executable}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_warning("Python 3.9+ 是必需的，当前版本可能不兼容")
        return False
    else:
        print_check("Python 版本要求 (3.9+)", True, f"v{version_str}")
        return True

def check_dependencies():
    """检查依赖包"""
    print_header("依赖包检查")
    
    dependencies = [
        ("mcp", "MCP 协议实现"),
        ("websockets", "WebSocket 通信"),
        ("dotenv", "环境变量管理", "python-dotenv"),
    ]
    
    all_installed = True
    
    for import_name, description, package_name in [
        (d[0], d[1], d[2] if len(d) > 2 else d[0]) 
        for d in dependencies
    ]:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            print_check(f"{package_name}", True, f"{description} (v{version})")
        except ImportError:
            print_check(f"{package_name}", False, f"{description} - 未安装")
            all_installed = False
    
    return all_installed

def check_env_file():
    """检查 .env 文件"""
    print_header("环境文件检查")
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if os.path.exists(env_path):
        print_check(".env 文件", True, f"存在于：{env_path}")
        
        # 读取并检查内容
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'OPENCLAW_TOKEN=' in content:
                # 提取 token 值（不显示完整 token）
                for line in content.split('\n'):
                    if line.startswith('OPENCLAW_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        if token and token != 'your_token_here':
                            masked = token[:10] + '...' if len(token) > 10 else token
                            print_check("OPENCLAW_TOKEN", True, f"已设置 ({masked})")
                        else:
                            print_warning("OPENCLAW_TOKEN 未设置或使用默认值")
                            print_info("请从 .env.example 复制并设置您的 token")
            else:
                print_warning(".env 文件中未找到 OPENCLAW_TOKEN")
        except Exception as e:
            print_warning(f"读取 .env 文件失败：{e}")
    else:
        print_check(".env 文件", False, "不存在")
        print_info("请复制 .env.example 并设置 OPENCLAW_TOKEN")
        print_info(f"  copy .env.example .env")
    
    return os.path.exists(env_path)

def check_env_variable():
    """检查系统环境变量"""
    print_header("系统环境变量检查")
    
    token = os.getenv('OPENCLAW_TOKEN')
    
    if token:
        masked = token[:10] + '...' if len(token) > 10 else token
        print_check("OPENCLAW_TOKEN (系统环境变量)", True, f"已设置 ({masked})")
        return True
    else:
        print_check("OPENCLAW_TOKEN (系统环境变量)", False, "未设置")
        print_info("请设置系统环境变量或在 .env 文件中配置")
        return False

def check_network():
    """检查网络连接"""
    print_header("网络连接检查")
    
    try:
        import socket
        # 尝试解析域名
        socket.gethostbyname('api.xiaozhi.me')
        print_check("DNS 解析 (api.xiaozhi.me)", True, "可解析")
        
        # 尝试连接（非阻塞）
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('api.xiaozhi.me', 443))
        sock.close()
        
        if result == 0:
            print_check("WebSocket 端点连接 (443 端口)", True, "可连接")
            return True
        else:
            print_warning("无法连接到 api.xiaozhi.me:443")
            print_info("请检查网络连接和防火墙设置")
            return False
            
    except Exception as e:
        print_warning(f"网络检查失败：{e}")
        return False

def check_virtual_env():
    """检查虚拟环境"""
    print_header("虚拟环境检查")
    
    in_venv = sys.prefix != sys.base_prefix or 'VIRTUAL_ENV' in os.environ
    
    if in_venv:
        venv_path = os.environ.get('VIRTUAL_ENV', sys.prefix)
        print_check("虚拟环境", True, f"已激活：{venv_path}")
        return True
    else:
        print_warning("未使用虚拟环境")
        print_info("建议使用虚拟环境隔离依赖:")
        print_info("  python -m venv venv")
        print_info("  venv\\Scripts\\activate")
        return False

def print_summary(results):
    """打印总结"""
    print_header("检查总结")
    
    total = len(results)
    passed = sum(1 for r in results if r[1])
    
    for name, status, message in results:
        icon = "✅" if status else "❌"
        color = Colors.GREEN if status else Colors.RED
        print(f"{icon} {color}{name:<35}{Colors.RESET} {message}")
    
    print(f"\n{Colors.BOLD}总计：{passed}/{total} 检查通过{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 所有检查通过！环境配置正确。{Colors.RESET}")
        print(f"\n{Colors.BLUE}下一步:{Colors.RESET}")
        print("  1. 确认 OPENCLAW_TOKEN 已正确设置")
        print("  2. 运行：python server.py")
    elif passed >= total - 1:
        print(f"\n{Colors.YELLOW}⚠️  大部分检查通过，请处理上述警告。{Colors.RESET}")
    else:
        print(f"\n{Colors.RED}❌ 存在多个问题，请逐一解决。{Colors.RESET}")

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}OpenClaw MCP Server 环境检查工具{Colors.RESET}")
    print(f"检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # 执行检查
    python_ok = check_python_version()
    results.append(("Python 版本", python_ok, sys.version_info))
    
    deps_ok = check_dependencies()
    results.append(("依赖包", deps_ok, "见上文详情"))
    
    env_file_ok = check_env_file()
    results.append((".env 文件", env_file_ok, "见上文详情"))
    
    env_var_ok = check_env_variable()
    results.append(("系统环境变量", env_var_ok, "见上文详情"))
    
    venv_ok = check_virtual_env()
    results.append(("虚拟环境", venv_ok, "见上文详情"))
    
    network_ok = check_network()
    results.append(("网络连接", network_ok, "见上文详情"))
    
    # 打印总结
    print_summary(results)
    
    # 返回状态码
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()