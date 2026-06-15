# 05 - 配置系统

## 概述

配置系统使用 YAML 文件和环境变量，支持多模型配置、认证模式、过滤选项和 Judge 参数。

## 配置文件结构

```yaml
# configs/gateway.yaml

# 服务器配置
server:
  host: "0.0.0.0"
  port: 8080
  workers: 1

# 日志配置
logging:
  level: "info"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 模型配置
models:
  gpt-4:
    name: "gpt-4"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    timeout: 60.0
    api_type: "openai"
  
  claude-3:
    name: "claude-3-sonnet"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"
    timeout: 60.0
    api_type: "claude"
    custom_headers:
      "anthropic-version": "2023-06-01"

# PII 过滤配置
filter:
  enabled: true
  min_score: 0.5
  action: "redact"
  filter_response: false

# 认证配置
auth:
  mode: "both"  # config | client | both

# Layer 2 Judge 配置（可选）
judge:
  enabled: false
  endpoint: "http://localhost:8001/v1/chat/completions"
  model: "Qwen3Guard-8B-Stream"
  timeout: 5.0
  timeout_action: "pass"
  stream_intercept:
    enabled: true
    check_interval: 5
    safety_threshold: 0.3
```

## 配置类

### ServerConfig

```python
class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"     # 监听地址
    port: int = 8080          # 监听端口
    workers: int = 1          # 工作进程数
```

### LoggingConfig

```python
class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "info"       # 日志级别
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### ModelConfig

```python
class ModelConfig(BaseModel):
    """模型配置"""
    name: str                 # 模型名称
    base_url: str             # API 基础 URL
    api_key: Optional[str]    # API Key（支持环境变量）
    timeout: float = 60.0     # 超时时间（秒）
    api_type: Literal["openai", "claude"] = "openai"  # API 类型
    api_path: Optional[str]   # 自定义 API 路径
    custom_headers: Optional[Dict[str, str]]  # 自定义请求头
```

### FilterConfig

```python
class FilterConfig(BaseModel):
    """PII 过滤配置"""
    enabled: bool = True          # 是否启用 PII 过滤
    min_score: float = 0.5        # 最小置信度阈值
    action: Literal["redact", "block", "log"] = "redact"  # 处理方式
    placeholders: Optional[Dict[str, str]]  # 自定义占位符
    whitelist_paths: List[str]    # 白名单路径
    filter_response: bool = False # 是否过滤响应（默认只过滤请求）
    
    @field_validator("min_score")
    @classmethod
    def validate_min_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("min_score must be between 0 and 1")
        return v
```

### AuthConfig

```python
class AuthConfig(BaseModel):
    """认证配置"""
    mode: Literal["config", "client", "both"] = "both"

# mode 说明:
# - config: 只用配置文件中的 api_key
# - client: 只用客户端提供的 Authorization
# - both: 优先用配置文件的，如果没有则用客户端的
```

### JudgeConfig

```python
class JudgeConfig(BaseModel):
    """LLM Judge 配置"""
    enabled: bool = False         # 是否启用 Judge
    endpoint: str                 # Judge 服务地址
    model: str                    # 模型名称
    timeout: float = 5.0          # 超时时间
    confidence_threshold: float = 0.7  # 置信度阈值
    timeout_action: Literal["pass", "block"] = "pass"  # 超时策略
    stream_intercept: StreamInterceptConfig  # 流式拦截配置
```

### StreamInterceptConfig

```python
class StreamInterceptConfig(BaseModel):
    """流式拦截配置"""
    enabled: bool = True           # 是否启用
    check_interval: int = 5        # 每 N 个 token 检测一次
    safety_threshold: float = 0.3  # 安全分数阈值（低于此值中断）
    min_tokens_before_check: int = 10  # 开始检测前的最小 token 数
```

### GatewayConfig

```python
class GatewayConfig(BaseModel):
    """网关主配置"""
    server: ServerConfig
    logging: LoggingConfig
    models: Dict[str, ModelConfig]
    filter: FilterConfig
    auth: AuthConfig
    judge: JudgeConfig
    
    @field_validator("models", mode="after")
    @classmethod
    def filter_incomplete_models(cls, v):
        """过滤掉配置不完整的模型"""
        filtered = {}
        for name, config in v.items():
            if "${" in config.base_url:  # 环境变量未设置
                continue
            filtered[name] = config
        return filtered
```

## 配置加载

### 加载优先级

```python
def load_config(config_path: Optional[str] = None) -> GatewayConfig:
    """
    加载配置
    
    优先级:
    1. 指定的配置文件路径
    2. 环境变量 GATEWAY_CONFIG
    3. 默认路径 ./configs/gateway.yaml
    4. 使用默认配置
    """
    # 1. 指定路径
    if config_path:
        return load_yaml_config(config_path)
    
    # 2. 环境变量
    env_config = os.getenv("GATEWAY_CONFIG")
    if env_config and os.path.exists(env_config):
        return load_yaml_config(env_config)
    
    # 3. 默认路径
    default_paths = [
        "./configs/gateway.yaml",
        "./gateway.yaml",
        "/etc/guardrails/gateway.yaml",
    ]
    for path in default_paths:
        if os.path.exists(path):
            return load_yaml_config(path)
    
    # 4. 默认配置
    return GatewayConfig()
```

### 环境变量展开

```python
def expand_env_vars(value):
    """
    递归展开环境变量
    
    支持:
    - ${VAR}: 直接引用
    - ${VAR:-default}: 带默认值
    """
    if isinstance(value, str):
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            default = None
            
            if ":-" in env_var:
                env_var, default = env_var.split(":-", 1)
            
            env_value = os.getenv(env_var)
            if env_value is not None:
                return env_value
            if default is not None:
                return default
            return value  # 未设置，保持原样
    
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [expand_env_vars(v) for v in value]
    
    return value
```

## 环境变量配置

### 创建 .env 文件

```bash
# .env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx-xxx
JUDGE_ENDPOINT=http://localhost:8001/v1/chat/completions
```

### 在配置中引用

```yaml
models:
  gpt-4:
    api_key: "${OPENAI_API_KEY}"
  
  claude-3:
    api_key: "${ANTHROPIC_API_KEY:-sk-default}"  # 带默认值

judge:
  endpoint: "${JUDGE_ENDPOINT:-http://localhost:8001/v1/chat/completions}"
```

## 启动参数

```bash
# 指定配置文件
python -m gateway.main --config ./configs/gateway.yaml

# 指定主机和端口
python -m gateway.main --host=0.0.0.0 --port=8080

# 通过环境变量
export GATEWAY_CONFIG=/path/to/config.yaml
python -m gateway.main
```

## 配置验证

### Pydantic 验证

```python
# 字段验证示例
@field_validator("min_score")
@classmethod
def validate_min_score(cls, v):
    if not 0 <= v <= 1:
        raise ValueError("min_score must be between 0 and 1")
    return v

@field_validator("safety_threshold")
@classmethod
def validate_safety_threshold(cls, v):
    if not 0 <= v <= 1:
        raise ValueError("safety_threshold must be between 0 and 1")
    return v
```

### 模型过滤验证

```python
@field_validator("models", mode="after")
@classmethod
def filter_incomplete_models(cls, v):
    """过滤掉配置不完整的模型"""
    filtered = {}
    for name, config in v.items():
        if "${" in config.base_url:
            # 环境变量未设置，跳过此模型
            continue
        filtered[name] = config
    return filtered
```

## 配置示例

### 最小配置

```yaml
server:
  port: 8080

models:
  gpt-4:
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
```

### 完整配置

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  workers: 4

logging:
  level: "debug"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

models:
  gpt-4:
    name: "gpt-4"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    timeout: 120.0
    api_type: "openai"
  
  gpt-3.5-turbo:
    name: "gpt-3.5-turbo"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    timeout: 60.0
  
  claude-3-opus:
    name: "claude-3-opus"
    base_url: "https://api.anthropic.com/v1"
    api_key: "${ANTHROPIC_API_KEY}"
    api_type: "claude"
    custom_headers:
      "anthropic-version": "2023-06-01"
  
  local-llm:
    name: "local-model"
    base_url: "http://localhost:11434/v1"
    api_key: "local"
    timeout: 300.0

filter:
  enabled: true
  min_score: 0.6
  action: "redact"
  filter_response: true
  placeholders:
    CN_PHONE_NUMBER: "[已脱敏]"
    CN_ID_CARD: "***"

auth:
  mode: "config"

judge:
  enabled: true
  endpoint: "http://localhost:8001/v1/chat/completions"
  model: "Qwen3Guard-8B-Stream"
  timeout: 3.0
  confidence_threshold: 0.8
  timeout_action: "block"
  stream_intercept:
    enabled: true
    check_interval: 3
    safety_threshold: 0.2
    min_tokens_before_check: 5
```

## 配置最佳实践

### 安全性

```yaml
# 不要在配置文件中硬编码 API Key
api_key: "${OPENAI_API_KEY}"  # ✓ 使用环境变量

# 不要这样写
api_key: "sk-xxx"  # ✗ 硬编码
```

### 生产环境

```yaml
server:
  workers: 4        # 多进程

logging:
  level: "info"     # 生产用 info，开发用 debug

filter:
  min_score: 0.6    # 更严格的阈值

judge:
  timeout_action: "pass"  # 高可用场景放行
```

### 开发环境

```yaml
server:
  workers: 1

logging:
  level: "debug"

filter:
  min_score: 0.4    # 更宽松的阈值

judge:
  enabled: false    # 开发时可禁用
```

## 配置热更新

当前版本不支持热更新，需要重启服务：

```bash
# 修改配置后重启
./run_gateway.sh -d
```

未来版本计划支持：
- 文件监听自动重载
- API 接口动态修改