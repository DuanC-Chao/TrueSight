import React, { useState, useEffect } from 'react';
import { 
  Form, Input, Button, Card, Typography, message, 
  Select, Switch, Radio, Tabs, Space,
  Upload, Alert, Spin, InputNumber, Row, Col,
  Table, Modal, Collapse
} from 'antd';
import { 
  SaveOutlined, 
  SettingOutlined,
  CloudUploadOutlined,
  UploadOutlined,
  LinkOutlined,
  EditOutlined,
  FileTextOutlined,
  UndoOutlined,
  SyncOutlined
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
  updateFileTypeChunkMapping,
  getRepositoryPromptConfig,
  updateRepositoryPromptConfig,
  resetRepositoryPromptConfig,
  syncRepositoryPromptConfigFromGlobal,
  getPartialSyncConfig,
  setPartialSyncConfig
} from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { Panel } = Collapse;

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
  const [promptConfig, setPromptConfig] = useState({});
  const [promptForm] = Form.useForm();
  const [promptLoading, setPromptLoading] = useState(false);
  const [partialSyncConfig, setPartialSyncConfigState] = useState({});
  const [partialSyncForm] = Form.useForm();

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

  // 获取Prompt配置
  const fetchPromptConfig = async () => {
    try {
      const response = await getRepositoryPromptConfig(id);
      if (response.success) {
        setPromptConfig(response.prompt_config || {});
        promptForm.setFieldsValue(response.prompt_config || {});
      }
    } catch (error) {
      console.error('获取Prompt配置失败:', error);
    }
  };

  // 获取部分同步配置
  const fetchPartialSyncConfig = async () => {
    try {
      const response = await getPartialSyncConfig(id);
      if (response.success) {
        setPartialSyncConfigState(response.config || {});
        partialSyncForm.setFieldsValue(response.config || {});
      }
    } catch (error) {
      console.error('获取部分同步配置失败:', error);
    }
  };

  useEffect(() => {
    fetchRepository();
    fetchFileTypeMapping();
    fetchPromptConfig();
    fetchPartialSyncConfig();
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

    console.log('准备上传的文件列表:', fileList);

    setUploading(true);
    try {
      const formData = new FormData();
      let validFileCount = 0;
      
      fileList.forEach((file, index) => {
        console.log(`处理文件 ${index}:`, file.name);
        
        // 获取实际文件对象，处理不同浏览器的差异
        let actualFile = file;
        
        // 处理Antd Upload组件的文件对象
        if (file.originFileObj) {
          actualFile = file.originFileObj;
        } else if (file.file) {
          actualFile = file.file;
        }
        
        // 确保文件对象有效
        if (actualFile instanceof File || actualFile instanceof Blob) {
          // 处理文件名，确保跨平台兼容性
          let fileName = actualFile.name || file.name || `file_${index}`;
          
          // 清理文件名中的危险字符（Windows特别敏感）
          fileName = fileName.replace(/[\\/:*?"<>|]/g, '_');
          
          // 确保文件有扩展名
          if (!fileName.includes('.')) {
            // 根据MIME类型推断扩展名
            const mimeType = actualFile.type || file.type || '';
            if (mimeType === 'text/plain') {
              fileName += '.txt';
            } else if (mimeType === 'application/pdf') {
              fileName += '.pdf';
            } else if (mimeType === 'text/html') {
              fileName += '.html';
            } else {
              // 尝试从原始文件名推断
              const originalExt = (file.name || '').split('.').pop();
              if (originalExt && ['txt', 'pdf', 'html'].includes(originalExt.toLowerCase())) {
                fileName += '.' + originalExt.toLowerCase();
              } else {
                fileName += '.txt'; // 默认扩展名
              }
            }
          }
          
          // 创建新的File对象以确保一致性（解决某些浏览器的兼容性问题）
          const fileToAppend = new File([actualFile], fileName, {
            type: actualFile.type || 'application/octet-stream',
            lastModified: actualFile.lastModified || Date.now()
          });
          
          formData.append('files', fileToAppend);
          validFileCount++;
          console.log(`添加文件 ${index}: ${fileName} (${fileToAppend.size} bytes, ${fileToAppend.type})`);
        } else {
          console.error(`文件 ${index} 不是有效的File对象:`, actualFile);
          message.error(`文件 ${file.name || index} 格式无效，跳过上传`);
        }
      });

      // 验证是否有有效文件
      if (validFileCount === 0) {
        message.error('没有有效的文件可上传');
        setUploading(false);
        return;
      }

      // 调试：打印FormData内容
      console.log('FormData内容:');
      for (let [key, value] of formData.entries()) {
        if (value instanceof File) {
          console.log(key, `File: ${value.name} (${value.size} bytes, ${value.type})`);
        } else {
          console.log(key, value);
        }
      }

      const response = await uploadFiles(id, formData);
      if (response.success) {
        message.success(`成功上传 ${validFileCount} 个文件`);
        setFileList([]);
        // 刷新页面数据
        fetchRepository();
      } else {
        message.error(`上传文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('上传文件失败:', error);
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

  // 增强的文件上传属性
  const uploadProps = {
    onRemove: file => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: file => {
      console.log('设置页面 beforeUpload 被调用，文件:', file.name, '大小:', file.size, '类型:', file.type);
      console.log('文件对象详情:', file);
      
      // 更严格的文件类型检查，考虑Windows/macOS差异
      const fileName = file.name.toLowerCase();
      const fileType = file.type || '';
      
      // 多重验证文件类型
      const isValidType = (
        // 通过扩展名验证
        fileName.endsWith('.txt') || 
        fileName.endsWith('.pdf') || 
        fileName.endsWith('.html') ||
        // 通过MIME类型验证
        fileType === 'text/plain' ||
        fileType === 'application/pdf' ||
        fileType === 'text/html' ||
        // Windows可能的MIME类型变体
        fileType === 'application/x-pdf' ||
        fileType === 'text/htm'
      );
      
      if (!isValidType) {
        message.error(`文件 ${file.name} 格式不支持，只支持 .txt, .pdf, .html 格式`);
        return Upload.LIST_IGNORE;
      }
      
      // 文件大小检查（考虑不同系统的精度差异）
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > 10) {
        message.error(`文件 ${file.name} 大小超过10MB限制 (当前: ${fileSizeMB.toFixed(2)}MB)`);
        return Upload.LIST_IGNORE;
      }
      
      // 检查文件是否已存在（增强比较逻辑）
      const fileExists = fileList.some(existingFile => {
        const existingName = existingFile.name || existingFile.originFileObj?.name || '';
        const existingSize = existingFile.size || existingFile.originFileObj?.size || 0;
        return existingName === file.name && Math.abs(existingSize - file.size) < 100; // 允许小的尺寸差异
      });
      
      if (fileExists) {
        message.warning(`文件 ${file.name} 已存在，跳过重复文件`);
        return Upload.LIST_IGNORE;
      }
      
      // 验证文件对象的有效性
      if (!(file instanceof File) && !(file instanceof Blob)) {
        console.error('无效的文件对象:', file);
        message.error(`文件 ${file.name} 对象无效`);
        return Upload.LIST_IGNORE;
      }
      
      // 使用函数式更新确保正确添加文件
      setFileList(prevFileList => {
        const newFileList = [...prevFileList, file];
        console.log('设置页面添加文件后的列表长度:', newFileList.length);
        console.log('设置页面新文件列表:', newFileList.map(f => f.name));
        return newFileList;
      });
      
      return false; // 阻止自动上传
    },
    fileList,
    multiple: true,
    // 修复Windows文件选择器问题：简化accept属性，只使用扩展名
    accept: '.txt,.pdf,.html,.htm',
    showUploadList: {
      showRemoveIcon: true,
      showPreviewIcon: false,
      showDownloadIcon: false
    },
    // 增强的onChange处理
    onChange: (info) => {
      console.log('设置页面 Upload onChange:', info.fileList.length, '个文件');
      console.log('文件状态变化:', info.file.status);
      
      // 处理文件状态变化，确保跨平台一致性
      if (info.file.status === 'error') {
        message.error(`文件 ${info.file.name} 处理失败`);
      }
    },
    // 添加自定义文件列表渲染来处理显示问题
    itemRender: (originNode, file, fileList, actions) => {
      // 确保文件名正确显示，特别是在Windows上
      const displayName = file.name || file.originFileObj?.name || '未知文件';
      return React.cloneElement(originNode, {
        ...originNode.props,
        children: React.cloneElement(originNode.props.children, {
          ...originNode.props.children.props,
          title: displayName
        })
      });
    }
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

  // 保存Prompt配置
  const handleSavePromptConfig = async (values) => {
    setPromptLoading(true);
    try {
      const response = await updateRepositoryPromptConfig(id, values);
      if (response.success) {
        message.success('Prompt配置已保存');
        setPromptConfig(values);
      } else {
        message.error(`保存Prompt配置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`保存Prompt配置失败: ${error.error || '未知错误'}`);
    } finally {
      setPromptLoading(false);
    }
  };

  // 重置Prompt配置
  const handleResetPromptConfig = async () => {
    setPromptLoading(true);
    try {
      const response = await resetRepositoryPromptConfig(id);
      if (response.success) {
        message.success('Prompt配置已重置为默认值');
        setPromptConfig(response.prompt_config);
        promptForm.setFieldsValue(response.prompt_config);
      } else {
        message.error(`重置Prompt配置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`重置Prompt配置失败: ${error.error || '未知错误'}`);
    } finally {
      setPromptLoading(false);
    }
  };

  // 从全局配置同步
  const handleSyncFromGlobal = async () => {
    setPromptLoading(true);
    try {
      const response = await syncRepositoryPromptConfigFromGlobal(id);
      if (response.success) {
        message.success('已同步全局配置');
        setPromptConfig(response.prompt_config || {});
        promptForm.setFieldsValue(response.prompt_config || {});
      } else {
        message.error(`同步全局配置失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`同步全局配置失败: ${error.error || '未知错误'}`);
    } finally {
      setPromptLoading(false);
    }
  };

  // 设置部分同步配置
  const handleSetPartialSyncConfig = async (values) => {
    console.log('handleSetPartialSyncConfig 被调用，传入参数:', values);
    console.log('当前信息库ID:', id);
    console.log('当前信息库信息:', repository);
    
    setSaving(true);
    try {
      console.log('准备调用API，数据:', values);
      const response = await setPartialSyncConfig(id, values);
      console.log('API响应:', response);
      
      if (response && response.success) {
        message.success('部分同步配置已保存');
        setRepository(response.repository);
        setPartialSyncConfigState(values);
        console.log('配置保存成功');
      } else {
        console.error('API返回失败:', response);
        message.error(`保存部分同步配置失败: ${response?.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('请求失败，完整错误对象:', error);
      console.error('错误类型:', typeof error);
      console.error('错误属性:', Object.keys(error));
      
      let errorMessage = '未知错误';
      if (error && error.error) {
        // 处理axios拦截器包装的错误
        errorMessage = error.error;
      } else if (error && error.response && error.response.data) {
        // 处理原始HTTP错误
        errorMessage = error.response.data.error || `HTTP ${error.response.status} 错误`;
      } else if (error && error.message) {
        // 处理标准JavaScript错误
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        // 处理字符串错误
        errorMessage = error;
      }
      
      console.error('最终错误信息:', errorMessage);
      message.error(`保存部分同步配置失败: ${errorMessage}`);
    } finally {
      setSaving(false);
    }
  };

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
                <Paragraph>支持 .txt, .pdf, .html 格式文件，可选择多个文件</Paragraph>
                
                <Upload {...uploadProps}>
                  <Button icon={<UploadOutlined />}>
                    {fileList.length > 0 ? `已选择 ${fileList.length} 个文件，继续选择` : '选择文件'}
                  </Button>
                </Upload>
                
                {fileList.length > 0 && (
                  <div style={{ marginTop: 8, marginBottom: 16, color: '#666' }}>
                    <Text type="secondary">
                      文件列表：{fileList.map(f => f.name).join(', ')}
                    </Text>
                  </div>
                )}
                
                <div style={{ marginTop: 16 }}>
                  <Button
                    type="primary"
                    onClick={handleUploadFiles}
                    disabled={fileList.length === 0}
                    loading={uploading}
                  >
                    {uploading ? '上传中...' : `开始上传${fileList.length > 0 ? ` (${fileList.length}个文件)` : ''}`}
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

        <TabPane tab={<span><SettingOutlined />Prompt配置</span>} key="6">
          <Card className="flat-card">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <Title level={5}>Prompt配置</Title>
                <Text type="secondary">
                  配置此信息库专用的Prompt设置，将覆盖全局配置。留空则使用全局配置。
                </Text>
              </div>
              <Space>
                <Button
                  icon={<SyncOutlined />}
                  onClick={handleSyncFromGlobal}
                  loading={promptLoading}
                >
                  同步全局配置
                </Button>
                <Button
                  icon={<UndoOutlined />}
                  onClick={handleResetPromptConfig}
                  loading={promptLoading}
                >
                  重置为默认值
                </Button>
              </Space>
            </div>

            <Form
              form={promptForm}
              layout="vertical"
              onFinish={handleSavePromptConfig}
              initialValues={promptConfig}
            >
              <Collapse defaultActiveKey={['summary']}>
                <Panel header="总结配置" key="summary">
                  <Form.Item
                    label="总结提示词"
                    name="summary_prompt"
                    tooltip="用于生成内容总结的提示词"
                  >
                    <TextArea rows={3} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="总结系统提示词"
                    name="summary_system_prompt"
                    tooltip="总结任务的系统角色设定"
                  >
                    <TextArea rows={3} placeholder="留空使用全局配置" />
                  </Form.Item>
                </Panel>

                <Panel header="问答生成 - 分块阶段" key="chunk">
                  <Form.Item
                    label="分块大小"
                    name={['qa_stages', 'chunk', 'chunk_size']}
                    tooltip="每个文本块的Token数量"
                  >
                    <InputNumber min={100} max={10000} style={{ width: 200 }} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="分块重叠"
                    name={['qa_stages', 'chunk', 'chunk_overlap']}
                    tooltip="相邻文本块之间的重叠Token数量"
                  >
                    <InputNumber min={0} max={1000} style={{ width: 200 }} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="提示词"
                    name={['qa_stages', 'chunk', 'prompt']}
                    tooltip="用于生成问答对的提示词"
                  >
                    <TextArea rows={4} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="系统提示词"
                    name={['qa_stages', 'chunk', 'system_prompt']}
                    tooltip="问答对生成任务的系统角色设定"
                  >
                    <TextArea rows={3} placeholder="留空使用全局配置" />
                  </Form.Item>
                </Panel>

                <Panel header="问答生成 - 去重与筛选阶段" key="reduce">
                  <Form.Item
                    label="提示词"
                    name={['qa_stages', 'reduce', 'prompt']}
                    tooltip="用于去重和筛选问答对的提示词"
                  >
                    <TextArea rows={4} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="系统提示词"
                    name={['qa_stages', 'reduce', 'system_prompt']}
                    tooltip="去重筛选任务的系统角色设定"
                  >
                    <TextArea rows={3} placeholder="留空使用全局配置" />
                  </Form.Item>
                </Panel>

                <Panel header="问答生成 - 质量评估阶段" key="evaluate">
                  <Form.Item
                    label="提示词"
                    name={['qa_stages', 'evaluate', 'prompt']}
                    tooltip="用于评估问答对质量的提示词"
                  >
                    <TextArea rows={4} placeholder="留空使用全局配置" />
                  </Form.Item>

                  <Form.Item
                    label="系统提示词"
                    name={['qa_stages', 'evaluate', 'system_prompt']}
                    tooltip="质量评估任务的系统角色设定"
                  >
                    <TextArea rows={3} placeholder="留空使用全局配置" />
                  </Form.Item>
                </Panel>
              </Collapse>

              <div style={{ textAlign: 'right', marginTop: 16 }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  icon={<SaveOutlined />}
                  loading={promptLoading}
                >
                  保存Prompt配置
                </Button>
              </div>
            </Form>
          </Card>
        </TabPane>

        <TabPane tab={<span><SyncOutlined />部分同步</span>} key="7">
          <Card className="flat-card">
            <div style={{ marginBottom: 16 }}>
              <Title level={5}>部分同步模式</Title>
              <Text type="secondary">
                启用部分同步模式后，系统会在总结生成完成时自动检查并删除包含失败标识的总结文件，
                同时保留content_hashes条目以实现增量跳过。在此模式下，基于原始文件的问答对生成功能将被禁用。
              </Text>
            </div>

            <Form
              form={partialSyncForm}
              layout="vertical"
              onFinish={handleSetPartialSyncConfig}
              initialValues={{
                partial_sync_enabled: partialSyncConfig?.partial_sync_enabled ?? repository?.partial_sync_enabled ?? false,
                failure_marker: partialSyncConfig?.failure_marker ?? repository?.failure_marker ?? '对不起，文件内容异常，我无法完成总结任务'
              }}
            >
              <Form.Item
                name="partial_sync_enabled"
                valuePropName="checked"
                label="启用部分同步模式"
              >
                <Switch />
              </Form.Item>

              <Form.Item
                shouldUpdate={(prevValues, currentValues) => prevValues.partial_sync_enabled !== currentValues.partial_sync_enabled}
                noStyle
              >
                {({ getFieldValue }) => (
                  <Form.Item
                    name="failure_marker"
                    label="失败标识文本"
                    rules={[
                      {
                        required: getFieldValue('partial_sync_enabled'),
                        message: '请输入失败标识文本'
                      }
                    ]}
                    tooltip="系统将检查总结文件中是否包含此文本（区分大小写），如果包含则删除该文件"
                  >
                    <TextArea 
                      rows={3} 
                      disabled={!getFieldValue('partial_sync_enabled')}
                      placeholder="请输入用于识别失败总结的标识文本"
                    />
                  </Form.Item>
                )}
              </Form.Item>

              <Alert
                message="部分同步模式说明"
                description={
                  <div>
                    <p><strong>功能说明：</strong></p>
                    <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
                      <li>在总结生成任务完成后，系统会统一检查所有总结文件</li>
                      <li>删除包含失败标识的总结文件，但保留content_hashes条目</li>
                      <li>下次处理时会跳过已有哈希记录的文件，实现增量处理</li>
                      <li>禁用"基于原始文件生成问答对"功能</li>
                      <li>爬虫来源的信息库默认开启，上传来源的信息库默认关闭</li>
                    </ul>
                  </div>
                }
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
