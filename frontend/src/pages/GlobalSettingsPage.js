import React, { useState, useEffect } from 'react';
import { 
  Form, Input, Button, Card, Typography, message, 
  Select, Switch, Radio, Divider, Tabs, Space,
  Collapse, Alert, Spin, InputNumber
} from 'antd';
import {
  SaveOutlined,
  ReloadOutlined,
  SettingOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  ApiOutlined,
  RobotOutlined,
  CodeOutlined,
  UndoOutlined
} from '@ant-design/icons';
import { getConfig, updateConfig } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { Panel } = Collapse;
const { TextArea } = Input;

/**
 * 全局设置页面
 *
 * 管理系统全局配置，包括爬虫设置、预处理设置、RAGFlow设置等
 */
const GlobalSettingsPage = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [config, setConfig] = useState({});
  const [activeTab, setActiveTab] = useState('1');
  const [activeProvider, setActiveProvider] = useState('openai');

  // 获取配置
  const fetchConfig = async () => {
    setLoading(true);
    try {
      const response = await getConfig();
      if (response.success) {
        setConfig(response.config);
        form.setFieldsValue(response.config);
        // 设置当前激活的模型提供商
        if (response.config.processor && response.config.processor.provider) {
          setActiveProvider(response.config.processor.provider);
        }
      } else {
        message.error(`获取配置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`获取配置失败: ${error.error || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  // 保存配置
  const handleSave = async (values) => {
    setSaving(true);
    try {
      // 确保设置了正确的provider
      values.processor = values.processor || {};
      values.processor.provider = activeProvider;

      const response = await updateConfig(values);
      if (response.success) {
        message.success('配置已保存');
        setConfig(response.config);
      } else {
        message.error(`保存配置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`保存配置失败: ${error.error || '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  // 重置Prompt配置
  const resetPrompts = () => {
    const defaultPrompts = {
      processor: {
        summary_prompt: "请对以下内容进行总结，突出关键信息：",
        summary_system_prompt: "你是一个专业的文档总结助手，擅长提取文本中的关键信息并生成简洁明了的总结。",
        qa_stages: {
          chunk: {
            prompt: "请根据以下内容生成5-10个高质量的问答对，每个问答对应包含一个问题和一个详细的回答。输出格式为每行一个JSON对象，包含q和a字段。",
            system_prompt: "你是一个专业的问答对生成助手，擅长从文本中提取关键信息并生成有价值的问答对。"
          },
          reduce: {
            prompt: "请对以下问答对进行去重和筛选，保留最有价值、最独特的问答对。输出格式为每行一个JSON对象，包含q和a字段。",
            system_prompt: "你是一个专业的内容审核助手，擅长识别重复或低质量的问答对，并保留最有价值的内容。"
          },
          evaluate: {
            prompt: "请对以下问答对进行质量评估，为每个问答对添加一个self_eval字段，评分范围1-5，5分为最高。评估标准包括问题的清晰度、答案的准确性和完整性。输出格式为每行一个JSON对象，包含q、a和self_eval字段。",
            system_prompt: "你是一个专业的内容评估助手，擅长评估问答对的质量和价值。"
          }
        }
      }
    };

    // 更新表单中的prompt字段
    const currentValues = form.getFieldsValue();
    const newValues = {
      ...currentValues,
      processor: {
        ...currentValues.processor,
        summary_prompt: defaultPrompts.processor.summary_prompt,
        summary_system_prompt: defaultPrompts.processor.summary_system_prompt,
        qa_stages: defaultPrompts.processor.qa_stages
      }
    };

    form.setFieldsValue(newValues);
    message.success('Prompt配置已重置为默认值');
  };

  // 处理模型提供商切换
  const handleProviderChange = (e) => {
    setActiveProvider(e.target.value);
  };

  // 检查提供商是否可用（有API Key和模型名称）
  const isProviderAvailable = (provider) => {
    const values = form.getFieldsValue();
    const providerConfig = values.processor?.[provider] || {};
    return providerConfig.api_key && providerConfig.model;
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>全局设置</Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchConfig}
            disabled={loading || saving}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={() => form.submit()}
            loading={saving}
            disabled={loading}
          >
            保存配置
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
          initialValues={config}
        >
          <Tabs activeKey={activeTab} onChange={setActiveTab}>
            <TabPane tab={<span><DatabaseOutlined />爬虫设置</span>} key="1">
              <Card className="flat-card">
                <Form.Item
                  label="最大爬取深度"
                  name={['crawler', 'max_depth']}
                  rules={[{ required: true, message: '请输入最大爬取深度' }]}
                >
                  <InputNumber min={1} max={10} style={{ width: 200 }} />
                </Form.Item>

                <Form.Item
                  label="最大并发线程数"
                  name={['crawler', 'max_threads']}
                  rules={[{ required: true, message: '请输入最大并发线程数' }]}
                >
                  <InputNumber min={1} max={50} style={{ width: 200 }} />
                </Form.Item>

                <Form.Item
                  label="请求超时时间（秒）"
                  name={['crawler', 'timeout']}
                  rules={[{ required: true, message: '请输入请求超时时间' }]}
                >
                  <InputNumber min={5} max={120} style={{ width: 200 }} />
                </Form.Item>

                <Form.Item
                  label="User Agent"
                  name={['crawler', 'user_agent']}
                  rules={[{ required: true, message: '请输入User Agent' }]}
                >
                  <Input style={{ width: '100%' }} />
                </Form.Item>

                <Divider />

                <Form.Item
                  label="URL屏蔽词列表（每行一个，支持正则表达式和通配符，区分大小写）"
                  name={['crawler', 'blocklist']}
                  tooltip="如果URL中包含这些词，将不保存内容，但会继续探索子链接"
                >
                  <TextArea
                    rows={6}
                    placeholder="例如：
video
mp4
download
login
/admin/"
                  />
                </Form.Item>
              </Card>
            </TabPane>

            <TabPane tab={<span><FileTextOutlined />预处理设置</span>} key="2">
              <Card className="flat-card" title="LLM提供商设置">
                <Alert
                  message="LLM提供商设置"
                  description="选择一个LLM提供商并配置API密钥和模型。未设置API密钥和模型名称的提供商无法被激活。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Radio.Group
                  onChange={handleProviderChange}
                  value={activeProvider}
                  style={{ marginBottom: 16 }}
                >
                  <Radio.Button
                    value="openai"
                    disabled={!isProviderAvailable('openai')}
                  >
                    OpenAI
                  </Radio.Button>
                  <Radio.Button
                    value="deepseek"
                    disabled={!isProviderAvailable('deepseek')}
                  >
                    DeepSeek
                  </Radio.Button>
                  <Radio.Button
                    value="qwen"
                    disabled={!isProviderAvailable('qwen')}
                  >
                    Qwen
                  </Radio.Button>
                </Radio.Group>

                <Collapse defaultActiveKey={['openai']}>
                  <Panel header="OpenAI设置" key="openai">
                    <Form.Item
                      label="API密钥"
                      name={['processor', 'openai', 'api_key']}
                      rules={[{ required: activeProvider === 'openai', message: '请输入API密钥' }]}
                    >
                      <Input.Password style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item
                      label="模型名称"
                      name={['processor', 'openai', 'model']}
                      rules={[{ required: activeProvider === 'openai', message: '请输入模型名称' }]}
                    >
                      <Input style={{ width: '100%' }} placeholder="例如：gpt-3.5-turbo, gpt-4" />
                    </Form.Item>
                  </Panel>

                  <Panel header="DeepSeek设置" key="deepseek">
                    <Form.Item
                      label="API密钥"
                      name={['processor', 'deepseek', 'api_key']}
                      rules={[{ required: activeProvider === 'deepseek', message: '请输入API密钥' }]}
                    >
                      <Input.Password style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item
                      label="模型名称"
                      name={['processor', 'deepseek', 'model']}
                      rules={[{ required: activeProvider === 'deepseek', message: '请输入模型名称' }]}
                    >
                      <Input style={{ width: '100%' }} placeholder="例如：deepseek-chat, deepseek-coder" />
                    </Form.Item>
                  </Panel>

                  <Panel header="Qwen设置" key="qwen">
                    <Form.Item
                      label="API密钥"
                      name={['processor', 'qwen', 'api_key']}
                      rules={[{ required: activeProvider === 'qwen', message: '请输入API密钥' }]}
                    >
                      <Input.Password style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item
                      label="模型名称"
                      name={['processor', 'qwen', 'model']}
                      rules={[{ required: activeProvider === 'qwen', message: '请输入模型名称' }]}
                    >
                      <Input style={{ width: '100%' }} placeholder="例如：qwen-turbo, qwen-plus, qwen1.5-7b-chat" />
                    </Form.Item>
                  </Panel>
                </Collapse>

                <Divider />

                <Form.Item
                  label="温度"
                  name={['processor', 'temperature']}
                  rules={[{ required: true, message: '请输入温度' }]}
                  tooltip="控制生成文本的随机性，值越高随机性越大"
                >
                  <InputNumber min={0} max={2} step={0.1} style={{ width: 200 }} />
                </Form.Item>

                <Form.Item
                  label="最大Token数"
                  name={['processor', 'max_tokens']}
                  rules={[{ required: true, message: '请输入最大Token数' }]}
                  tooltip="生成文本的最大长度"
                >
                  <InputNumber min={100} max={8000} step={100} style={{ width: 200 }} />
                </Form.Item>
              </Card>

              <Card className="flat-card" title="Prompt配置" style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 16, textAlign: 'right' }}>
                  <Button
                    icon={<UndoOutlined />}
                    onClick={resetPrompts}
                  >
                    重置为默认值
                  </Button>
                </div>

                <Collapse defaultActiveKey={['summary']}>
                  <Panel header="总结配置" key="summary">
                    <Form.Item
                      label="总结提示词"
                      name={['processor', 'summary_prompt']}
                      rules={[{ required: true, message: '请输入总结提示词' }]}
                    >
                      <TextArea rows={3} />
                    </Form.Item>

                    <Form.Item
                      label="总结系统提示词"
                      name={['processor', 'summary_system_prompt']}
                      rules={[{ required: true, message: '请输入总结系统提示词' }]}
                    >
                      <TextArea rows={3} />
                    </Form.Item>
                  </Panel>

                  <Panel header="问答生成 - 分块阶段" key="chunk">
                    <Form.Item
                      label="启用"
                      name={['processor', 'qa_stages', 'chunk', 'enabled']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      label="分块大小"
                      name={['processor', 'qa_stages', 'chunk', 'chunk_size']}
                      rules={[{ required: true, message: '请输入分块大小' }]}
                    >
                      <InputNumber min={100} max={10000} style={{ width: 200 }} />
                    </Form.Item>

                    <Form.Item
                      label="分块重叠"
                      name={['processor', 'qa_stages', 'chunk', 'chunk_overlap']}
                      rules={[{ required: true, message: '请输入分块重叠' }]}
                    >
                      <InputNumber min={0} max={1000} style={{ width: 200 }} />
                    </Form.Item>

                    <Form.Item
                      label="提示词"
                      name={['processor', 'qa_stages', 'chunk', 'prompt']}
                      rules={[{ required: true, message: '请输入提示词' }]}
                    >
                      <TextArea rows={4} />
                    </Form.Item>

                    <Form.Item
                      label="系统提示词"
                      name={['processor', 'qa_stages', 'chunk', 'system_prompt']}
                      rules={[{ required: true, message: '请输入系统提示词' }]}
                    >
                      <TextArea rows={3} />
                    </Form.Item>
                  </Panel>

                  <Panel header="问答生成 - 去重与筛选阶段" key="reduce">
                    <Form.Item
                      label="启用"
                      name={['processor', 'qa_stages', 'reduce', 'enabled']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      label="提示词"
                      name={['processor', 'qa_stages', 'reduce', 'prompt']}
                      rules={[{ required: true, message: '请输入提示词' }]}
                    >
                      <TextArea rows={4} />
                    </Form.Item>

                    <Form.Item
                      label="系统提示词"
                      name={['processor', 'qa_stages', 'reduce', 'system_prompt']}
                      rules={[{ required: true, message: '请输入系统提示词' }]}
                    >
                      <TextArea rows={3} />
                    </Form.Item>
                  </Panel>

                  <Panel header="问答生成 - 质量评估阶段" key="evaluate">
                    <Form.Item
                      label="启用"
                      name={['processor', 'qa_stages', 'evaluate', 'enabled']}
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      label="提示词"
                      name={['processor', 'qa_stages', 'evaluate', 'prompt']}
                      rules={[{ required: true, message: '请输入提示词' }]}
                    >
                      <TextArea rows={4} />
                    </Form.Item>

                    <Form.Item
                      label="系统提示词"
                      name={['processor', 'qa_stages', 'evaluate', 'system_prompt']}
                      rules={[{ required: true, message: '请输入系统提示词' }]}
                    >
                      <TextArea rows={3} />
                    </Form.Item>
                  </Panel>
                </Collapse>
              </Card>
            </TabPane>

            <TabPane tab={<span><ApiOutlined />RAGFlow设置</span>} key="3">
              <Card className="flat-card">
                <Form.Item
                  label="RAGFlow API密钥"
                  name={['ragflow', 'api_key']}
                >
                  <Input.Password style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item
                  label="RAGFlow API基础URL"
                  name={['ragflow', 'api_base_url']}
                >
                  <Input style={{ width: '100%' }} placeholder="例如：https://api.ragflow.ai" />
                </Form.Item>

                <Form.Item
                  label="自动同步"
                  name={['ragflow', 'auto_sync']}
                  valuePropName="checked"
                  tooltip="完成问答对生成后自动同步到RAGFlow"
                >
                  <Switch />
                </Form.Item>
              </Card>
            </TabPane>

            <TabPane tab={<span><SettingOutlined />系统设置</span>} key="4">
              <Card className="flat-card">
                <Form.Item
                  label="日志级别"
                  name={['system', 'log_level']}
                  rules={[{ required: true, message: '请选择日志级别' }]}
                >
                  <Select style={{ width: 200 }}>
                    <Option value="DEBUG">DEBUG</Option>
                    <Option value="INFO">INFO</Option>
                    <Option value="WARNING">WARNING</Option>
                    <Option value="ERROR">ERROR</Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  label="数据目录"
                  name={['system', 'data_dir']}
                  rules={[{ required: true, message: '请输入数据目录' }]}
                >
                  <Input style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item
                  label="增量处理"
                  name={['system', 'incremental_processing']}
                  valuePropName="checked"
                  tooltip="启用后，只处理新增或修改的文件"
                >
                  <Switch />
                </Form.Item>
              </Card>
            </TabPane>
          </Tabs>
        </Form>
      </Spin>
    </div>
  );
};

export default GlobalSettingsPage;
