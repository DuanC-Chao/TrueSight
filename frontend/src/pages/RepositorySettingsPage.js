import React, { useState, useEffect } from 'react';
import { 
  Form, Input, Button, Card, Typography, message, 
  Select, Switch, Radio, Divider, Tabs, Space,
  Upload, Alert, Spin, InputNumber, Row, Col,
  Table, Modal
} from 'antd';
import { 
  SaveOutlined, 
  SettingOutlined,
  CloudUploadOutlined,
  UploadOutlined,
  LinkOutlined,
  EditOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getRepository, 
  updateRepository, 
  setAutoUpdate,
  setDirectImport,
  uploadFiles,
  uploadUrlFile,
  getFileTypeChunkMapping,
  updateFileTypeChunkMapping
} from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

/**
 * 信息库设置页面
 * 
 * 管理单个信息库的设置，包括基本信息、自动更新、直接入库等
 */
const RepositorySettingsPage = () => {
  // 修改参数名，与路由定义保持一致
  const { id } = useParams();
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [repository, setRepository] = useState(null);
  const [activeTab, setActiveTab] = useState('1');
  const [fileList, setFileList] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [fileTypeMapping, setFileTypeMapping] = useState({});
  const [editingFileType, setEditingFileType] = useState(null);
  const [editForm] = Form.useForm();
  const [editModalVisible, setEditModalVisible] = useState(false);

  // 获取信息库信息
  const fetchRepository = async () => {
    if (!id) {
      message.error('信息库ID未定义');
      setLoading(false);
      return;
    }
    
    setLoading(true);
    try {
      const response = await getRepository(id);
      if (response.success) {
        setRepository(response.repository);
        // 设置表单值，包括 max_depth 和 max_threads
        form.setFieldsValue({
          name: response.repository.name,
          description: response.repository.description,
          urls: response.repository.urls ? response.repository.urls.join('\n') : '',
          max_depth: response.repository.max_depth,
          max_threads: response.repository.max_threads,
          embedding_model: response.repository.embedding_model
        });
      } else {
        message.error(`获取信息库信息失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`获取信息库信息失败: ${error.error || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  // 获取文件类型映射
  const fetchFileTypeMapping = async () => {
    try {
      const response = await getFileTypeChunkMapping(id);
      if (response.success) {
        setFileTypeMapping(response.mapping || {});
      }
    } catch (error) {
      console.error('获取文件类型映射失败:', error);
    }
  };

  useEffect(() => {
    fetchRepository();
    fetchFileTypeMapping();
  }, [id]);

  // 保存基本设置
  const handleSaveBasic = async (values) => {
    setSaving(true);
    try {
      // 处理URLs
      const urls = values.urls ? values.urls.split('\n').filter(url => url.trim()) : [];
      
      const response = await updateRepository(id, {
        ...values,
        urls
      });

      if (response.success) {
        message.success('基本设置已保存');
        setRepository(response.repository);
      } else {
        message.error(`保存基本设置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`保存基本设置失败: ${error.error || '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  // 设置自动更新
  const handleSetAutoUpdate = async (values) => {
    setSaving(true);
    try {
      const response = await setAutoUpdate(id, {
        auto_update: values.auto_update,
        update_frequency: values.auto_update ? values.update_frequency : null
      });

      if (response.success) {
        message.success('自动更新设置已保存');
        setRepository(response.repository);
      } else {
        message.error(`保存自动更新设置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`保存自动更新设置失败: ${error.error || '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  // 设置直接入库
  const handleSetDirectImport = async (values) => {
    setSaving(true);
    try {
      const response = await setDirectImport(id, {
        direct_import: values.direct_import
      });

      if (response.success) {
        message.success('直接入库设置已保存');
        setRepository(response.repository);
      } else {
        message.error(`保存直接入库设置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`保存直接入库设置失败: ${error.error || '未知错误'}`);
    } finally {
      setSaving(false);
    }
  };

  // 上传文件
  const handleUploadFiles = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      fileList.forEach(file => {
        formData.append('files[]', file);
      });

      const response = await uploadFiles(id, formData);
      if (response.success) {
        message.success(`成功上传 ${response.uploaded_files.length} 个文件`);
        setFileList([]);
      } else {
        message.error(`上传文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`上传文件失败: ${error.error || '未知错误'}`);
    } finally {
      setUploading(false);
    }
  };

  // 上传URL文件
  const handleUploadUrlFile = async (values) => {
    if (!values.urls || !values.urls.trim()) {
      message.warning('请输入URL');
      return;
    }

    setUploading(true);
    try {
      const urls = values.urls.split('\n').filter(url => url.trim());
      
      const response = await uploadUrlFile(id, { urls });
      if (response.success) {
        message.success('URL文件已上传');
      } else {
        message.error(`上传URL文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`上传URL文件失败: ${error.error || '未知错误'}`);
    } finally {
      setUploading(false);
    }
  };

  // 文件上传属性
  const uploadProps = {
    onRemove: file => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: file => {
      setFileList([...fileList, file]);
      return false;
    },
    fileList,
    multiple: true,
    accept: '.txt,.pdf,.html'
  };

  // 处理编辑文件类型映射
  const handleEditFileType = (fileType) => {
    const mapping = fileTypeMapping[fileType] || {};
    setEditingFileType(fileType);
    editForm.setFieldsValue({
      chunk_method: mapping.chunk_method || 'naive',
      chunk_token_num: mapping.parser_config?.chunk_token_num || 128,
      delimiter: mapping.parser_config?.delimiter || '\\n!?;。；！？',
      layout_recognize: mapping.parser_config?.layout_recognize !== false,
      html4excel: mapping.parser_config?.html4excel || false,
      task_page_size: mapping.parser_config?.task_page_size || 12,
      use_raptor: mapping.parser_config?.raptor?.use_raptor || false
    });
    setEditModalVisible(true);
  };

  // 保存文件类型映射
  const handleSaveFileTypeMapping = async (values) => {
    try {
      const parser_config = {};
      
      // 只有 naive 方法才需要这些配置
      if (values.chunk_method === 'naive') {
        parser_config.chunk_token_num = values.chunk_token_num;
        parser_config.delimiter = values.delimiter;
        parser_config.layout_recognize = values.layout_recognize;
        parser_config.html4excel = values.html4excel;
        
        // PDF 特有的配置
        if (editingFileType === '.pdf') {
          parser_config.task_page_size = values.task_page_size;
        }
        
        parser_config.raptor = {
          use_raptor: values.use_raptor || false
        };
      } else if (['qa', 'manual', 'paper', 'book', 'laws', 'presentation'].includes(values.chunk_method)) {
        // 这些方法只需要 raptor 配置
        parser_config.raptor = {
          use_raptor: values.use_raptor || false
        };
      }
      // picture, table, one, email 等方法不需要任何配置

      const response = await updateFileTypeChunkMapping(id, {
        file_type: editingFileType,
        chunk_method: values.chunk_method,
        parser_config: parser_config
      });

      if (response.success) {
        message.success('文件类型映射已更新');
        setEditModalVisible(false);
        fetchFileTypeMapping();
      } else {
        message.error(`更新失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`更新失败: ${error.error || '未知错误'}`);
    }
  };

  // 文件类型映射表格列定义
  const fileTypeMappingColumns = [
    {
      title: '文件类型',
      dataIndex: 'fileType',
      key: 'fileType',
      render: (text) => <strong>{text}</strong>
    },
    {
      title: 'Chunk Method',
      dataIndex: 'chunkMethod',
      key: 'chunkMethod',
      render: (text) => {
        const methodMap = {
          'naive': 'General',
          'qa': 'Q&A',
          'table': 'Table',
          'paper': 'Paper',
          'book': 'Book',
          'laws': 'Laws',
          'presentation': 'Presentation',
          'picture': 'Picture',
          'one': 'One',
          'email': 'Email',
          'manual': 'Manual'
        };
        return methodMap[text] || text;
      }
    },
    {
      title: 'Token数量',
      dataIndex: 'tokenNum',
      key: 'tokenNum',
      render: (text, record) => {
        if (record.chunkMethod === 'naive') {
          return text || '-';
        }
        return '-';
      }
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button 
          type="link" 
          icon={<EditOutlined />}
          onClick={() => handleEditFileType(record.fileType)}
        >
          编辑
        </Button>
      )
    }
  ];

  // 准备表格数据
  const fileTypeMappingData = Object.entries(fileTypeMapping).map(([fileType, config]) => ({
    key: fileType,
    fileType: fileType,
    chunkMethod: config.chunk_method || 'naive',
    tokenNum: config.parser_config?.chunk_token_num
  }));

  if (!repository && loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Spin tip="加载中..." />
      </div>
    );
  }

  if (!repository && !loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Alert
          message="信息库不存在"
          description={`无法找到ID为 "${id}" 的信息库，请检查URL是否正确。`}
          type="error"
          showIcon
          action={
            <Button type="primary" onClick={() => navigate('/repositories')}>
              返回信息库列表
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>{repository.name} - 设置</Title>
        <Space>
          <Button 
            onClick={() => navigate(`/repositories/${id}`)}
          >
            返回详情
          </Button>
        </Space>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={<span><SettingOutlined />基本设置</span>} key="1">
          <Card className="flat-card">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSaveBasic}
            >
              <Form.Item
                label="信息库名称"
                name="name"
                rules={[{ required: true, message: '请输入信息库名称' }]}
              >
                <Input disabled style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                label="信息库描述"
                name="description"
              >
                <Input.TextArea rows={3} style={{ width: '100%' }} />
              </Form.Item>

              {repository.source === 'crawler' && (
                <>
                  <Form.Item
                    label="爬取URL列表"
                    name="urls"
                    help="每行一个URL"
                  >
                    <Input.TextArea rows={5} style={{ width: '100%' }} />
                  </Form.Item>

                  <Form.Item
                    label="爬取深度"
                    name="max_depth"
                    help="从起始URL开始的链接跟踪深度，0表示只爬取入口URL"
                  >
                    <InputNumber min={0} max={10} style={{ width: 200 }} />
                  </Form.Item>

                  <Form.Item
                    label="并发线程数"
                    name="max_threads"
                    help="同时爬取的线程数，建议5-10"
                  >
                    <InputNumber min={1} max={20} style={{ width: 200 }} />
                  </Form.Item>
                </>
              )}

              <Form.Item
                label="Embedding模型"
                name="embedding_model"
                help="留空则使用全局默认设置"
              >
                <Input style={{ width: '100%' }} placeholder="jina-embeddings-v3" />
              </Form.Item>

              <div style={{ textAlign: 'right' }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  icon={<SaveOutlined />}
                  loading={saving}
                >
                  保存设置
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab={<span><CloudUploadOutlined />自动更新</span>} key="2">
          <Card className="flat-card">
            {repository.source !== 'crawler' ? (
              <Alert
                message="不支持自动更新"
                description="只有爬虫来源的信息库才支持自动更新功能。"
                type="warning"
                showIcon
              />
            ) : (
              <Form
                layout="vertical"
                onFinish={handleSetAutoUpdate}
                initialValues={{
                  auto_update: repository.auto_update || false,
                  update_frequency: repository.update_frequency || 'weekly'
                }}
              >
                <Form.Item
                  name="auto_update"
                  valuePropName="checked"
                  label="启用自动更新"
                >
                  <Switch />
                </Form.Item>

                <Form.Item
                  shouldUpdate={(prevValues, currentValues) => prevValues.auto_update !== currentValues.auto_update}
                  noStyle
                >
                  {({ getFieldValue }) => (
                    <Form.Item
                      name="update_frequency"
                      label="更新频率"
                      rules={[
                        {
                          required: getFieldValue('auto_update'),
                          message: '请选择更新频率'
                        }
                      ]}
                    >
                      <Radio.Group disabled={!getFieldValue('auto_update')}>
                        <Radio.Button value="daily">每日 (00:01)</Radio.Button>
                        <Radio.Button value="weekly">每周 (周一 00:01)</Radio.Button>
                        <Radio.Button value="monthly">每月 (1日 00:01)</Radio.Button>
                        <Radio.Button value="yearly">每年 (1月1日 00:01)</Radio.Button>
                      </Radio.Group>
                    </Form.Item>
                  )}
                </Form.Item>

                <Alert
                  message="自动更新说明"
                  description="自动更新将在指定时间自动爬取信息库URL，并根据设置进行预处理和同步到RAGFlow。"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <div style={{ textAlign: 'right' }}>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    icon={<SaveOutlined />}
                    loading={saving}
                  >
                    保存设置
                  </Button>
                </div>
              </Form>
            )}
          </Card>
        </TabPane>

        <TabPane tab={<span><LinkOutlined />直接入库</span>} key="3">
          <Card className="flat-card">
            <Form
              layout="vertical"
              onFinish={handleSetDirectImport}
              initialValues={{
                direct_import: repository.direct_import || false
              }}
            >
              <Form.Item
                name="direct_import"
                valuePropName="checked"
                label="启用直接入库"
              >
                <Switch />
              </Form.Item>

              <Alert
                message="直接入库说明"
                description="启用直接入库后，文件将跳过预处理（总结和问答对生成）直接同步到RAGFlow。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <div style={{ textAlign: 'right' }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  icon={<SaveOutlined />}
                  loading={saving}
                >
                  保存设置
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab={<span><UploadOutlined />上传文件</span>} key="4">
          <Card className="flat-card">
            <Row gutter={24}>
              <Col span={12}>
                <Title level={5}>上传本地文件</Title>
                <Paragraph>支持 .txt, .pdf, .html 格式文件</Paragraph>
                
                <Upload {...uploadProps}>
                  <Button icon={<UploadOutlined />}>选择文件</Button>
                </Upload>
                
                <div style={{ marginTop: 16 }}>
                  <Button
                    type="primary"
                    onClick={handleUploadFiles}
                    disabled={fileList.length === 0}
                    loading={uploading}
                  >
                    {uploading ? '上传中...' : '开始上传'}
                  </Button>
                </div>
              </Col>
              
              <Col span={12}>
                <Title level={5}>上传URL列表</Title>
                <Paragraph>每行输入一个URL</Paragraph>
                
                <Form
                  layout="vertical"
                  onFinish={handleUploadUrlFile}
                >
                  <Form.Item
                    name="urls"
                    rules={[{ required: true, message: '请输入URL' }]}
                  >
                    <TextArea rows={5} placeholder="http://example.com&#10;http://another-example.com" />
                  </Form.Item>
                  
                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={uploading}
                    >
                      {uploading ? '上传中...' : '上传URL'}
                    </Button>
                  </Form.Item>
                </Form>
              </Col>
            </Row>
          </Card>
        </TabPane>

        <TabPane tab={<span><FileTextOutlined />文件类型映射</span>} key="5">
          <Card className="flat-card">
            <Table
              columns={fileTypeMappingColumns}
              dataSource={fileTypeMappingData}
              rowKey="key"
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 编辑文件类型映射模态框 */}
      <Modal
        title={`编辑文件类型映射 - ${editingFileType}`}
        visible={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleSaveFileTypeMapping}
        >
          <Form.Item
            name="chunk_method"
            label="Chunk Method"
            rules={[{ required: true, message: '请选择 Chunk Method' }]}
          >
            <Select>
              <Option value="naive">General</Option>
              <Option value="qa">Q&A</Option>
              <Option value="table">Table</Option>
              <Option value="paper">Paper</Option>
              <Option value="book">Book</Option>
              <Option value="laws">Laws</Option>
              <Option value="presentation">Presentation</Option>
              <Option value="picture">Picture</Option>
              <Option value="one">One</Option>
              <Option value="email">Email</Option>
              <Option value="manual">Manual</Option>
            </Select>
          </Form.Item>

          <Form.Item
            shouldUpdate={(prevValues, currentValues) => prevValues.chunk_method !== currentValues.chunk_method}
            noStyle
          >
            {({ getFieldValue }) => {
              const chunkMethod = getFieldValue('chunk_method');
              
              if (chunkMethod === 'naive') {
                return (
                  <>
                    <Form.Item
                      name="chunk_token_num"
                      label="Chunk Token 数量"
                      rules={[{ required: true, message: '请输入 Token 数量' }]}
                    >
                      <InputNumber min={1} max={2048} style={{ width: '100%' }} />
                    </Form.Item>

                    <Form.Item
                      name="delimiter"
                      label="分隔符"
                    >
                      <Input placeholder="\\n!?;。；！？" />
                    </Form.Item>

                    <Form.Item
                      name="layout_recognize"
                      label="布局识别"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item
                      name="html4excel"
                      label="Excel转HTML"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>

                    {editingFileType === '.pdf' && (
                      <Form.Item
                        name="task_page_size"
                        label="任务页面大小"
                      >
                        <InputNumber min={1} max={100} style={{ width: '100%' }} />
                      </Form.Item>
                    )}

                    <Form.Item
                      name="use_raptor"
                      label="使用 RAPTOR"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </>
                );
              } else if (['qa', 'manual', 'paper', 'book', 'laws', 'presentation'].includes(chunkMethod)) {
                return (
                  <Form.Item
                    name="use_raptor"
                    label="使用 RAPTOR"
                    valuePropName="checked"
                  >
                    <Switch />
                  </Form.Item>
                );
              }
              
              return null;
            }}
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                保存
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RepositorySettingsPage;
