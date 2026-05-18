# diagnostic.py
import asyncio
import asyncpg
import sys
import socket
from urllib.parse import quote_plus


async def full_diagnostic():
    print("=" * 60)
    print("PostgreSQL 连接完整诊断")
    print("=" * 60)

    # 配置信息
    config = {
        'user': 'postgres',
        'password': 'Tran2142024',
        'host': 'localhost',
        'port': 5432,
        'database': 'ai_test_agent_system_db'
    }

    print(f"\n1. 配置信息:")
    print(f"   主机: {config['host']}")
    print(f"   端口: {config['port']}")
    print(f"   用户: {config['user']}")
    print(f"   密码长度: {len(config['password'])} 字符")
    print(f"   数据库: {config['database']}")

    # 2. 测试网络连接
    print(f"\n2. 测试网络连接:")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 5432))
        if result == 0:
            print(f"   ✅ 端口 5432 可以访问")
        else:
            print(f"   ❌ 端口 5432 无法访问，错误码: {result}")
        sock.close()
    except Exception as e:
        print(f"   ❌ 网络测试失败: {e}")

    # 3. 使用 asyncpg 直接连接（详细错误）
    print(f"\n3. 测试 asyncpg 直接连接:")
    try:
        conn = await asyncpg.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            database=config['database'],
            timeout=5,
            command_timeout=5
        )
        print(f"   ✅ 连接成功！")
        version = await conn.fetchval("SELECT version()")
        print(f"   版本: {version[:60]}")
        await conn.close()
    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"   ❌ 密码错误: {e}")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        print(f"   ❌ 连接不存在: {e}")
    except ConnectionRefusedError as e:
        print(f"   ❌ 连接被拒绝: {e}")
    except OSError as e:
        print(f"   ❌ 系统错误: {e}")
    except Exception as e:
        print(f"   ❌ 其他错误: {type(e).__name__}: {e}")

    # 4. 尝试连接 postgres 默认数据库
    print(f"\n4. 测试连接到默认 postgres 数据库:")
    try:
        conn = await asyncpg.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            database='postgres',
            timeout=5
        )
        print(f"   ✅ 连接到 postgres 数据库成功！")

        # 检查目标数据库是否存在
        dbs = await conn.fetch("SELECT datname FROM pg_database WHERE datname = $1", config['database'])
        if dbs:
            print(f"   ✅ 数据库 '{config['database']}' 存在")
        else:
            print(f"   ⚠️  数据库 '{config['database']}' 不存在")
            print(f"   🔧 正在创建数据库...")
            await conn.execute(f'CREATE DATABASE "{config["database"]}"')
            print(f"   ✅ 数据库已创建")

        # 检查表是否存在
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = 'user'
        """)
        print(f"   📊 现有表: {[t['tablename'] for t in tables]}")

        await conn.close()
    except Exception as e:
        print(f"   ❌ 失败: {e}")

    # 5. 测试 SQLAlchemy 引擎
    print(f"\n5. 测试 SQLAlchemy 异步引擎:")
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text

        # 构建 URL（密码已经不含特殊字符）
        url = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
        print(
            f"   URL (密码隐藏): postgresql+asyncpg://{config['user']}:***@{config['host']}:{config['port']}/{config['database']}")

        engine = create_async_engine(url, echo=False, pool_pre_ping=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            print(f"   ✅ SQLAlchemy 连接成功！SELECT 1 = {val}")
        await engine.dispose()
    except Exception as e:
        print(f"   ❌ SQLAlchemy 失败: {e}")

    # 6. 检查环境变量
    print(f"\n6. 检查环境变量:")
    import os
    env_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB']
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'PASSWORD' in var:
                print(f"   {var}=***")
            else:
                print(f"   {var}={value}")
        else:
            print(f"   {var}=未设置")

    print("\n" + "=" * 60)
    print("诊断完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(full_diagnostic())