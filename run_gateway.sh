#!/bin/bash
# LLM Guard Gateway 启动脚本

# 设置默认配置
HOST=${GATEWAY_HOST:-0.0.0.0}
PORT=${GATEWAY_PORT:-8080}
CONFIG=${GATEWAY_CONFIG:-./configs/gateway.yaml}

# 显示帮助
show_help() {
    echo "LLM Guard Gateway 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help      显示帮助信息"
    echo "  -d, --dev       开发模式（自动重载）"
    echo "  -p, --prod      生产模式（多进程）"
    echo "  -c, --config    指定配置文件"
    echo "  --host          绑定主机 (默认: 0.0.0.0)"
    echo "  --port          绑定端口 (默认: 8080)"
    echo ""
    echo "环境变量:"
    echo "  GATEWAY_HOST    绑定主机"
    echo "  GATEWAY_PORT    绑定端口"
    echo "  GATEWAY_CONFIG  配置文件路径"
    echo ""
    echo "示例:"
    echo "  $0 -d                    # 开发模式启动"
    echo "  $0 -p                    # 生产模式启动"
    echo "  $0 -c ./my_config.yaml   # 使用指定配置"
    echo "  $0 --host 127.0.0.1 --port 3000"
}

# 解析参数
MODE="dev"
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dev)
            MODE="dev"
            shift
            ;;
        -p|--prod)
            MODE="prod"
            shift
            ;;
        -c|--config)
            CONFIG="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查配置文件
if [ ! -f "$CONFIG" ]; then
    echo "警告: 配置文件不存在: $CONFIG"
    echo "将使用默认配置"
    CONFIG=""
fi

echo "======================================"
echo "LLM Guard Gateway"
echo "======================================"
echo "模式: $MODE"
echo "主机: $HOST"
echo "端口: $PORT"
if [ -n "$CONFIG" ]; then
    echo "配置: $CONFIG"
fi
echo "======================================"
echo ""

# 启动服务
if [ "$MODE" == "dev" ]; then
    # 开发模式 - 自动重载
    echo "启动开发服务器..."
    if [ -n "$CONFIG" ]; then
        uvicorn gateway.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --log-level info
    else
        uvicorn gateway.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --reload \
            --log-level info
    fi
else
    # 生产模式 - 多进程
    echo "启动生产服务器..."
    WORKERS=${GATEWAY_WORKERS:-4}
    if [ -n "$CONFIG" ]; then
        uvicorn gateway.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level warning
    else
        uvicorn gateway.main:app \
            --host "$HOST" \
            --port "$PORT" \
            --workers "$WORKERS" \
            --log-level warning
    fi
fi
