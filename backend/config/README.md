# 配置说明

## 快速开始

1. 复制配置模板文件：
   ```bash
   cp config.yaml.template config.yaml
   ```

2. 编辑 `config.yaml` 文件，填入您的 API 密钥：
   - 将 `YOUR_OPENAI_API_KEY_HERE` 替换为您的 OpenAI API 密钥
   - 将 `YOUR_DEEPSEEK_API_KEY_HERE` 替换为您的 DeepSeek API 密钥
   - 将 `YOUR_QWEN_API_KEY_HERE` 替换为您的通义千问 API 密钥
   - 将 `YOUR_RAGFLOW_API_KEY_HERE` 替换为您的 RAGFlow API 密钥

## 配置项说明

### LLM 提供商配置

系统支持三种 LLM 提供商：
- **OpenAI**: 使用 GPT 系列模型
- **DeepSeek**: 使用 DeepSeek 模型
- **Qwen**: 使用通义千问模型

在 `processor.provider` 中选择您要使用的提供商，并在对应的配置部分填入 API 密钥和模型名称。

### RAGFlow 配置

如果您使用 RAGFlow 进行知识库管理，需要配置：
- `api_base_url`: RAGFlow API 的基础 URL
- `api_key`: RAGFlow 的 API 密钥
- `base_url`: RAGFlow 的 Web 界面 URL

## 注意事项

- `config.yaml` 文件包含敏感信息，已被添加到 `.gitignore` 中，不会被提交到版本控制系统
- 请妥善保管您的 API 密钥，不要分享给他人
- 如果您需要在团队中共享配置，建议使用环境变量或密钥管理服务 