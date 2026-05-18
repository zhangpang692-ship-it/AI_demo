"""
应用配置管理

使用 Pydantic Settings 管理应用配置，所有配置项强制从 app/.env 环境变量文件加载，
代码中不再保留任何硬编码默认值。
"""
"""
版权所有 (c) 2023-2026 北京慧测信息技术有限公司(但问智能) 保留所有权利。

本代码版权归北京慧测信息技术有限公司(但问智能)所有，仅用于学习交流目的，未经公司商业授权，
不得用于任何商业用途，包括但不限于商业环境部署、售卖或以任何形式进行商业获利。违者必究。

授权商业应用请联系微信：huice666
"""

# pylint: disable  MC80OmFIVnBZMlhsdktEbHVwNDZXbVJFZEE9PTozNTM5YTE1Mw==

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


# 确保 .env 文件始终从当前文件所在目录加载（backend/app/）
_ENV_FILE_PATH = Path(__file__).parent.parent / ".env"
_ENV_FILE_PATH_FALLBACK = Path(__file__).parent.parent.parent / ".env"


class Settings(BaseSettings):
    """应用配置类 —— 所有配置强制从 .env 加载，代码中无硬编码默认值"""

    model_config = SettingsConfigDict(
        env_file=[str(_ENV_FILE_PATH), str(_ENV_FILE_PATH_FALLBACK)],
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_parse_json=True,
    )

    # 应用基础配置
    app_name: str
    app_version: str
    debug: bool
    api_prefix: str

    # PostgreSQL 数据库配置
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    @property
    def postgres_url(self) -> str:
        """获取 PostgreSQL 连接 URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def postgres_sync_url(self) -> str:
        """获取 PostgreSQL 同步连接 URL（用于 Alembic）"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
# type: ignore  MS80OmFIVnBZMlhsdktEbHVwNDZXbVJFZEE9PTozNTM5YTE1Mw==

    # MongoDB 配置
    mongodb_host: str
    mongodb_port: int
    mongodb_user: Optional[str] = None
    mongodb_password: Optional[str] = None
    mongodb_db: str

    @property
    def mongodb_url(self) -> str:
        """获取 MongoDB 连接 URL"""
        if self.mongodb_user and self.mongodb_password:
            return (
                f"mongodb://{self.mongodb_user}:{self.mongodb_password}"
                f"@{self.mongodb_host}:{self.mongodb_port}"
            )
        return f"mongodb://{self.mongodb_host}:{self.mongodb_port}"

    # 速率限制配置
    rate_limit_requests: int
    rate_limit_window: int

    # 分页配置
    pagination_default_size: int
    pagination_max_size: int

    @property
    def default_page_size(self) -> int:
        """获取默认分页大小（别名）"""
        return self.pagination_default_size

    @property
    def max_page_size(self) -> int:
        """获取最大分页大小（别名）"""
        return self.pagination_max_size

    # CORS 配置
    cors_origins: list[str]

    # JWT 配置（用于认证）
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    # 默认测试用户配置（开发环境使用）
    default_user_id: str
    default_user_email: str
    default_user_name: str

    # MinIO 对象存储配置
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str
    minio_secure: bool
    minio_region: Optional[str] = None
    minio_public_url: Optional[str] = None

    # 附件配置
    attachment_max_size: int
    attachment_allowed_types: list[str]

    # PDF 解析配置
    enable_pdf_multimodal: bool

    # 大模型配置
    deepseek_api_key: Optional[str] = None
# pylint: disable  Mi80OmFIVnBZMlhsdktEbHVwNDZXbVJFZEE9PTozNTM5YTE1Mw==

    # 性能测试工作目录配置
    perf_workspace_root: str
    perf_mcp_root: str
    perf_yaml_tests: str
    perf_skills_root: str

    # 接口测试工作目录配置
    api_workspace_root: str
    api_mcp_root: str
    api_skills_root: str

    # UI 测试工作目录配置
    # ui_workspace_root: str
    # ui_mcp_root: str
    # ui_skills_root: str

    # Web 测试工作目录配置
    web_workspace_root: str
    web_mcp_root: str
    web_skills_root: str

    # Web Chrome 测试工作目录配置
    web_chrome_workspace_root: str
    web_chrome_mcp_root: str
    web_chrome_skills_root: str

    # 测试用例工作目录配置
    testcase_workspace_root: str
    testcase_skills_root: str


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()

# noqa  My80OmFIVnBZMlhsdktEbHVwNDZXbVJFZEE9PTozNTM5YTE1Mw==

settings = get_settings()
