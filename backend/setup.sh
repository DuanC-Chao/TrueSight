#!/bin/bash

# TrueSight 后端环境初始化脚本
# 适用于 MacOS 和 Linux 系统

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始初始化 TrueSight 后端环境...${NC}"

# 检查 Python 版本
echo -e "${YELLOW}检查 Python 版本...${NC}"
if command -v python3.9 &>/dev/null; then
    PYTHON_CMD=python3.9
elif command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$PYTHON_VERSION >= 3.9" | bc) -eq 1 ]]; then
        PYTHON_CMD=python3
    else
        echo -e "${RED}错误: 需要 Python 3.9 或更高版本，当前版本为 $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}错误: 未找到 Python 3.9 或更高版本${NC}"
    exit 1
fi

echo -e "${GREEN}使用 Python 命令: $PYTHON_CMD${NC}"

# 创建虚拟环境
echo -e "${YELLOW}创建虚拟环境...${NC}"
$PYTHON_CMD -m venv venv

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # MacOS
    source venv/bin/activate
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    source venv/bin/activate
else
    echo -e "${RED}错误: 不支持的操作系统${NC}"
    exit 1
fi

# 升级 pip
echo -e "${YELLOW}升级 pip...${NC}"
pip install --upgrade pip

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
pip install -r requirements.txt

# 创建配置文件
echo -e "${YELLOW}创建配置文件...${NC}"
mkdir -p config
if [ ! -f config/config.yaml ]; then
    echo "# TrueSight 全局配置" > config/config.yaml
    echo "debug: true" >> config/config.yaml
    echo "log_level: INFO" >> config/config.yaml
    echo "server:" >> config/config.yaml
    echo "  host: 0.0.0.0" >> config/config.yaml
    echo "  port: 5000" >> config/config.yaml
fi

if [ ! -f config/ragflow.yaml ]; then
    echo "# RAGFlow API 配置" > config/ragflow.yaml
    echo "base_url: http://192.168.0.130" >> config/ragflow.yaml
    echo "# api_key: 从环境变量获取" >> config/ragflow.yaml
fi

if [ ! -f config/crawler.yaml ]; then
    echo "# 爬虫配置" > config/crawler.yaml
    echo "max_depth: 3" >> config/crawler.yaml
    echo "max_threads: 10" >> config/crawler.yaml
    echo "timeout: 30" >> config/crawler.yaml
    echo "user_agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36" >> config/crawler.yaml
fi

echo -e "${GREEN}TrueSight 后端环境初始化完成!${NC}"
echo -e "${YELLOW}使用方法:${NC}"
echo -e "  1. 激活虚拟环境: ${GREEN}source venv/bin/activate${NC}"
echo -e "  2. 运行服务: ${GREEN}python src/main.py${NC}"
