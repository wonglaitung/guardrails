"""
网关配置管理

支持YAML配置文件和环境变量。
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    workers: int = 1


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "info"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ModelConfig(BaseModel):
    """模型配置"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 60.0
    api_type: Literal["openai", "claude"] = "openai"
    api_path: Optional[str] = None  # 自定义 API 路径
    custom_headers: Optional[Dict[str, str]] = None  # 自定义请求头（如 Host）


class FilterConfig(BaseModel):
    """过滤配置"""
    enabled: bool = True
    min_score: float = 0.5
    action: Literal["redact", "block", "log"] = "redact"
    placeholders: Optional[Dict[str, str]] = None
    whitelist_paths: List[str] = Field(default_factory=list)
    filter_response: bool = False  # 是否对LLM响应进行PII过滤（默认关闭，只保护用户输入）

    @field_validator("min_score")
    @classmethod
    def validate_min_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("min_score must be between 0 and 1")
        return v


class AuthConfig(BaseModel):
    """认证配置"""
    mode: Literal["config", "client", "both"] = "both"
    # config: 只用配置文件中的 api_key
    # client: 只用客户端提供的 Authorization
    # both: 优先用配置文件的，如果没有则用客户端的


class GatewayConfig(BaseModel):
    """网关主配置"""
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    models: Dict[str, ModelConfig] = Field(default_factory=dict)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)

    @field_validator("models", mode="after")
    @classmethod
    def filter_incomplete_models(cls, v):
        """过滤掉配置不完整的模型（base_url 包含 ${ 表示环境变量未设置）"""
        filtered = {}
        for name, config in v.items():
            if config.base_url and "${" in config.base_url:
                # 环境变量未设置，跳过此模型
                continue
            filtered[name] = config
        return filtered


def load_yaml_config(path: str) -> GatewayConfig:
    """从YAML文件加载配置，支持环境变量展开"""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # 递归展开环境变量
    data = expand_env_vars(data)
    return GatewayConfig(**data)


def load_config(config_path: Optional[str] = None) -> GatewayConfig:
    """
    加载配置

    优先级：
    1. 指定的配置文件路径
    2. 环境变量 GATEWAY_CONFIG
    3. 默认路径 ./configs/gateway.yaml
    4. 使用默认配置
    """
    # 1. 检查指定路径
    if config_path:
        return load_yaml_config(config_path)

    # 2. 检查环境变量
    env_config = os.getenv("GATEWAY_CONFIG")
    if env_config and os.path.exists(env_config):
        return load_yaml_config(env_config)

    # 3. 检查默认路径
    default_paths = [
        "./configs/gateway.yaml",
        "./gateway.yaml",
        "/etc/guardrails/gateway.yaml",
    ]
    for path in default_paths:
        if os.path.exists(path):
            return load_yaml_config(path)

    # 4. 返回默认配置
    return GatewayConfig()


def expand_env_vars(value):
    """递归展开环境变量，未设置的变量保持原样"""
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            default = None
            # 支持 ${VAR:-default} 语法
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            env_value = os.getenv(env_var)
            if env_value is not None:
                return env_value
            if default is not None:
                return default
            # 环境变量未设置且无默认值，保持原样
            return value
        return value
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(v) for v in value]
    return value
