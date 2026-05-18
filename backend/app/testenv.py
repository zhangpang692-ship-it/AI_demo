# check_env.py
import os
from pathlib import Path

print("=" * 60)
print("环境变量诊断")
print("=" * 60)

# 1. 查找 .env 文件
current_dir = Path.cwd()
print(f"\n1. 当前工作目录: {current_dir}")

# 查找可能的 .env 文件位置
possible_locations = [
    current_dir / ".env",
    current_dir.parent / ".env",
    Path(__file__).parent / ".env",
]

for loc in possible_locations:
    exists = "✅" if loc.exists() else "❌"
    print(f"   {exists} {loc}")

# 2. 检查当前环境变量
print(f"\n2. 当前环境变量中的值:")
for key in ['POSTGRES_HOST', 'POSTGRES_USER', 'POSTGRES_DB']:
    val = os.getenv(key)
    print(f"   {key} = {val if val else '未设置'}")

# 3. 尝试手动加载 .env
print(f"\n3. 尝试手动加载 .env:")
from dotenv import load_dotenv

# 在常见位置查找
for loc in [".env", "../.env", "app/.env"]:
    if Path(loc).exists():
        print(f"   找到: {loc}")
        load_dotenv(loc, override=True)
        print(f"   加载后 POSTGRES_HOST = {os.getenv('POSTGRES_HOST')}")
        break
else:
    print("   未找到 .env 文件")

# 4. 测试 Settings
print(f"\n4. 测试 Settings 类:")
from app.config.settings import settings
print(f"   postgres_host = {settings.postgres_host}")
print(f"   postgres_user = {settings.postgres_user}")
print(f"   postgres_db = {settings.postgres_db}")
print(f"   postgres_port = {settings.postgres_port}")