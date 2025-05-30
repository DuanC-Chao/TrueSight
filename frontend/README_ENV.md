# 前端环境变量配置说明

## API基础URL配置

前端默认连接到 `http://localhost:5001` 的后端服务。

如果您的后端运行在不同的地址或端口，可以通过以下方式配置：

### 方法一：创建 .env 文件（推荐）

在 `frontend/` 目录下创建 `.env` 文件：

```bash
# 后端API基础URL
REACT_APP_API_BASE_URL=http://localhost:5001

# 如果后端运行在不同地址，请修改为实际地址
# 例如：
# REACT_APP_API_BASE_URL=http://192.168.1.100:5001
# REACT_APP_API_BASE_URL=https://api.example.com
```

### 方法二：设置环境变量

在启动前端服务前设置环境变量：

```bash
# Linux/macOS
export REACT_APP_API_BASE_URL=http://localhost:5001
npm start

# Windows
set REACT_APP_API_BASE_URL=http://localhost:5001
npm start
```

### 默认配置

如果没有设置 `REACT_APP_API_BASE_URL` 环境变量，前端将使用默认值：
- `http://localhost:5001`

这与后端的默认配置匹配。

## 注意事项

1. 环境变量必须以 `REACT_APP_` 开头才能在React应用中使用
2. 修改环境变量后需要重启前端开发服务器
3. 确保后端服务正在运行并且可以访问指定的地址和端口 