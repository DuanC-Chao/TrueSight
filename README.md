# TrueSight

TrueSight是一个集成了网页爬取、内容预处理和RAGFlow知识库管理的服务化应用。它允许用户通过网页前端上传或输入URL，进行多线程并发爬取，计算Token数量，生成内容总结和问答对，并自动将处理后的内容入库到RAGFlow的Dataset中。

## 功能特点

- **爬虫功能服务化**：支持通过网页上传URL文件或直接输入URL列表，多线程并发爬取，实时显示状态和进度
- **Token计算与预处理**：自动计算爬取内容的Token数量，使用LLM生成内容总结和问答对
- **与RAGFlow集成**：自动将处理后的内容入库到RAGFlow的Dataset，支持自动调用Parse Document API
- **信息库管理**：将爬取内容封装为"信息库"，支持选择、重新爬取和自动更新
- **自动更新**：支持按照设定的频率（每天/每周/每月/每年）自动更新信息库内容
- **批量操作**：支持批量设置自动更新和更改配置

## 系统架构

TrueSight采用前后端分离的架构设计：

- **后端**：基于Python的服务，负责爬虫、预处理和RAGFlow集成
- **前端**：基于React的Web应用，提供用户界面和交互功能

## 目录结构

```
TrueSight/
├── backend/              # 后端代码
│   ├── src/              # 源代码
│   ├── tests/            # 测试代码
│   └── config/           # 配置文件
├── frontend/             # 前端代码
│   ├── src/              # 源代码
│   ├── public/           # 静态资源
│   └── build/            # 构建输出
└── docs/                 # 文档
    ├── design/           # 设计文档
    ├── api/              # API文档
    └── user/             # 用户手册
```

## 环境要求

- **操作系统**：MacOS或Linux
- **Python版本**：3.9+
- **Node.js版本**：14.0+
- **RAGFlow API**：需要有效的API密钥和访问权限

## 安装与运行

### 后端

```bash
# 创建并激活虚拟环境
cd backend
python -m venv venv
source venv/bin/activate  # MacOS/Linux

# 安装依赖
pip install -r requirements.txt

# 运行服务
python src/main.py
```

### 前端

```bash
# 安装依赖
cd frontend
npm install

# 开发模式运行
npm start

# 构建生产版本
npm run build
```

## 许可证

[MIT](LICENSE)
