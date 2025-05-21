#!/bin/bash

# TrueSight 前端环境初始化脚本
# 适用于 MacOS 和 Linux 系统

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始初始化 TrueSight 前端环境...${NC}"

# 检查 Node.js 版本
echo -e "${YELLOW}检查 Node.js 版本...${NC}"
if ! command -v node &>/dev/null; then
    echo -e "${RED}错误: 未找到 Node.js${NC}"
    echo -e "${YELLOW}请安装 Node.js 14.0 或更高版本${NC}"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d 'v' -f 2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d '.' -f 1)

if [[ $NODE_MAJOR -lt 14 ]]; then
    echo -e "${RED}错误: 需要 Node.js 14.0 或更高版本，当前版本为 $NODE_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}Node.js 版本: $NODE_VERSION${NC}"

# 检查 npm 版本
echo -e "${YELLOW}检查 npm 版本...${NC}"
if ! command -v npm &>/dev/null; then
    echo -e "${RED}错误: 未找到 npm${NC}"
    exit 1
fi

NPM_VERSION=$(npm -v)
echo -e "${GREEN}npm 版本: $NPM_VERSION${NC}"

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
npm install

# 创建基础目录结构
echo -e "${YELLOW}创建基础目录结构...${NC}"
mkdir -p src/{components,pages,utils,services,assets,styles}
mkdir -p public/images

# 创建基础文件
echo -e "${YELLOW}创建基础文件...${NC}"

# 创建 index.js
if [ ! -f src/index.js ]; then
    echo "// TrueSight 前端入口文件" > src/index.js
    echo "import React from 'react';" >> src/index.js
    echo "import ReactDOM from 'react-dom/client';" >> src/index.js
    echo "import App from './App';" >> src/index.js
    echo "import './styles/index.css';" >> src/index.js
    echo "" >> src/index.js
    echo "const root = ReactDOM.createRoot(document.getElementById('root'));" >> src/index.js
    echo "root.render(" >> src/index.js
    echo "  <React.StrictMode>" >> src/index.js
    echo "    <App />" >> src/index.js
    echo "  </React.StrictMode>" >> src/index.js
    echo ");" >> src/index.js
fi

# 创建 App.js
if [ ! -f src/App.js ]; then
    echo "// TrueSight 主应用组件" > src/App.js
    echo "import React from 'react';" >> src/App.js
    echo "import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';" >> src/App.js
    echo "import { ConfigProvider } from 'antd';" >> src/App.js
    echo "import zhCN from 'antd/lib/locale/zh_CN';" >> src/App.js
    echo "import 'antd/dist/antd.css';" >> src/App.js
    echo "import './styles/App.css';" >> src/App.js
    echo "" >> src/App.js
    echo "// 页面导入" >> src/App.js
    echo "import HomePage from './pages/HomePage';" >> src/App.js
    echo "" >> src/App.js
    echo "function App() {" >> src/App.js
    echo "  return (" >> src/App.js
    echo "    <ConfigProvider locale={zhCN}>" >> src/App.js
    echo "      <Router>" >> src/App.js
    echo "        <Routes>" >> src/App.js
    echo "          <Route path=\"/\" element={<HomePage />} />" >> src/App.js
    echo "        </Routes>" >> src/App.js
    echo "      </Router>" >> src/App.js
    echo "    </ConfigProvider>" >> src/App.js
    echo "  );" >> src/App.js
    echo "}" >> src/App.js
    echo "" >> src/App.js
    echo "export default App;" >> src/App.js
fi

# 创建 index.css
if [ ! -f src/styles/index.css ]; then
    echo "/* TrueSight 全局样式 */" > src/styles/index.css
    echo "body {" >> src/styles/index.css
    echo "  margin: 0;" >> src/styles/index.css
    echo "  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen'," >> src/styles/index.css
    echo "    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue'," >> src/styles/index.css
    echo "    sans-serif;" >> src/styles/index.css
    echo "  -webkit-font-smoothing: antialiased;" >> src/styles/index.css
    echo "  -moz-osx-font-smoothing: grayscale;" >> src/styles/index.css
    echo "}" >> src/styles/index.css
    echo "" >> src/styles/index.css
    echo "code {" >> src/styles/index.css
    echo "  font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New'," >> src/styles/index.css
    echo "    monospace;" >> src/styles/index.css
    echo "}" >> src/styles/index.css
fi

# 创建 App.css
if [ ! -f src/styles/App.css ]; then
    echo "/* TrueSight 应用样式 */" > src/styles/App.css
    echo ".app-container {" >> src/styles/App.css
    echo "  min-height: 100vh;" >> src/styles/App.css
    echo "}" >> src/styles/App.css
    echo "" >> src/styles/App.css
    echo ".app-header {" >> src/styles/App.css
    echo "  background: linear-gradient(135deg, #1890ff 0%, #722ed1 100%);" >> src/styles/App.css
    echo "  padding: 0 24px;" >> src/styles/App.css
    echo "  color: white;" >> src/styles/App.css
    echo "}" >> src/styles/App.css
    echo "" >> src/styles/App.css
    echo ".app-content {" >> src/styles/App.css
    echo "  padding: 24px;" >> src/styles/App.css
    echo "  background: #f0f2f5;" >> src/styles/App.css
    echo "}" >> src/styles/App.css
    echo "" >> src/styles/App.css
    echo ".app-footer {" >> src/styles/App.css
    echo "  text-align: center;" >> src/styles/App.css
    echo "  padding: 16px;" >> src/styles/App.css
    echo "  background: #f0f2f5;" >> src/styles/App.css
    echo "  border-top: 1px solid #e8e8e8;" >> src/styles/App.css
    echo "}" >> src/styles/App.css
fi

# 创建 HomePage.js
if [ ! -f src/pages/HomePage.js ]; then
    echo "// TrueSight 首页" > src/pages/HomePage.js
    echo "import React from 'react';" >> src/pages/HomePage.js
    echo "import { Layout, Typography } from 'antd';" >> src/pages/HomePage.js
    echo "" >> src/pages/HomePage.js
    echo "const { Header, Content, Footer } = Layout;" >> src/pages/HomePage.js
    echo "const { Title } = Typography;" >> src/pages/HomePage.js
    echo "" >> src/pages/HomePage.js
    echo "function HomePage() {" >> src/pages/HomePage.js
    echo "  return (" >> src/pages/HomePage.js
    echo "    <Layout className=\"app-container\">" >> src/pages/HomePage.js
    echo "      <Header className=\"app-header\">" >> src/pages/HomePage.js
    echo "        <Title level={3} style={{ color: 'white', margin: '16px 0' }}>TrueSight</Title>" >> src/pages/HomePage.js
    echo "      </Header>" >> src/pages/HomePage.js
    echo "      <Content className=\"app-content\">" >> src/pages/HomePage.js
    echo "        <Typography.Title level={2}>欢迎使用 TrueSight</Typography.Title>" >> src/pages/HomePage.js
    echo "        <Typography.Paragraph>" >> src/pages/HomePage.js
    echo "          TrueSight 是一个集成了网页爬取、内容预处理和 RAGFlow 知识库管理的服务化应用。" >> src/pages/HomePage.js
    echo "        </Typography.Paragraph>" >> src/pages/HomePage.js
    echo "      </Content>" >> src/pages/HomePage.js
    echo "      <Footer className=\"app-footer\">TrueSight ©2025</Footer>" >> src/pages/HomePage.js
    echo "    </Layout>" >> src/pages/HomePage.js
    echo "  );" >> src/pages/HomePage.js
    echo "}" >> src/pages/HomePage.js
    echo "" >> src/pages/HomePage.js
    echo "export default HomePage;" >> src/pages/HomePage.js
fi

# 创建 .env 文件
if [ ! -f .env ]; then
    echo "# TrueSight 前端环境变量" > .env
    echo "REACT_APP_API_URL=http://localhost:5001" >> .env
    echo "REACT_APP_WS_URL=ws://localhost:5001" >> .env
fi

echo -e "${GREEN}TrueSight 前端环境初始化完成!${NC}"
echo -e "${YELLOW}使用方法:${NC}"
echo -e "  1. 开发模式运行: ${GREEN}npm start${NC}"
echo -e "  2. 构建生产版本: ${GREEN}npm run build${NC}"
