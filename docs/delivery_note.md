# TrueSight 交付说明

## 交付内容

1. **源代码**
   - `/backend` - 后端Python代码
   - `/frontend` - 前端React代码
   - `/docs` - 文档和说明

2. **文档**
   - `user_manual.md` - 用户手册
   - `test_report.md` - 测试报告
   - `architecture.md` - 架构设计文档
   - `api_reference.md` - API参考文档

3. **安装和部署脚本**
   - `backend/setup.sh` - 后端环境安装脚本
   - `frontend/setup.sh` - 前端环境安装脚本
   - `start.sh` - 一键启动脚本

## 系统要求

- **操作系统**: MacOS 或 Linux
- **Python**: 3.9 或更高版本
- **Node.js**: 16.0 或更高版本
- **存储空间**: 至少 2GB 可用空间
- **内存**: 至少 4GB RAM

## 快速开始

1. 克隆或解压代码到本地目录
2. 配置环境变量（参见用户手册）
3. 运行安装脚本:
   ```
   chmod +x backend/setup.sh frontend/setup.sh
   ./backend/setup.sh
   ./frontend/setup.sh
   ```
4. 启动服务:
   ```
   chmod +x start.sh
   ./start.sh
   ```
5. 访问 `http://localhost:3000` 开始使用

## 功能亮点

- **全面的爬虫功能**: 多线程并发爬取，树状深度探索，增量更新
- **智能预处理**: Token计算，LLM内容总结，问答对生成
- **RAGFlow无缝集成**: 自动创建Dataset，文档上传，解析触发，增删改查
- **灵活的信息库管理**: 创建，配置，自动更新，批量操作
- **美观的用户界面**: 扁平化设计，渐变效果，响应式布局

## 注意事项

1. 首次使用时，请先在全局设置中配置RAGFlow和LLM API密钥
2. 爬取大型网站时，建议适当控制爬取深度和并发线程数
3. 定期检查自动更新任务的执行状态
4. 对于特别重要的数据，建议定期手动备份

## 后续支持

如有任何问题或需要技术支持，请联系：
- 邮箱: support@truesight.com
- 问题追踪: https://github.com/yourusername/TrueSight/issues

## 版本信息

- 版本: 1.0.0
- 发布日期: 2025-05-18
- 许可证: MIT
