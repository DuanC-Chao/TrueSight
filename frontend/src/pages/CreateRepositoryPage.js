import React, { useState } from 'react';
import { 
  Card, Form, Input, Button, Upload, message, 
  Typography, InputNumber, Alert, Spin, Tabs 
} from 'antd';
import { 
  UploadOutlined, 
  LinkOutlined, 
  DatabaseOutlined,
  CloudUploadOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { createRepository } from '../services/api';

const { Title, Paragraph, Text } = Typography;
const { TextArea } = Input;

/**
 * 创建信息库页面
 * 
 * 支持两种创建方式：
 * 1. 爬虫方式：提供起始URL列表
 * 2. 上传方式：上传文件或文件夹
 */
const CreateRepositoryPage = () => {
  const [form] = Form.useForm();
  const [uploadForm] = Form.useForm();
  const [createType, setCreateType] = useState('crawler');
  const [loading, setLoading] = useState(false);
  const [fileList, setFileList] = useState([]);
  const navigate = useNavigate();

  // 处理表单提交
  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      // 处理URL列表
      const urls = values.urls.split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);
      
      if (urls.length === 0) {
        message.error('请至少提供一个有效的URL');
        setLoading(false);
        return;
      }

      const data = {
        name: values.name,
        description: values.description || '',
        source: 'crawler',
        urls: urls,
        max_depth: values.depth !== undefined ? values.depth : 1,
        max_threads: values.threads !== undefined ? values.threads : 5
      };

      // 创建信息库
      const response = await createRepository(data);
      if (response.success) {
        message.success('信息库创建成功');
        
        // 确保获取到正确的信息库名称
        const repositoryName = response.repository_name || values.name;
        
        // 使用信息库专用爬取接口启动爬取任务
        try {
          const crawlResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/crawler/repository/${repositoryName}/start`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
          });
          
          const crawlResult = await crawlResponse.json();
          
          if (crawlResult.success) {
            message.success('爬取任务已启动');
            // 导航到详情页，并传递爬取任务ID
            navigate(`/repositories/${repositoryName}`, { 
              state: { crawlTaskId: crawlResult.task_id } 
            });
          } else {
            message.warning(`爬取任务启动失败: ${crawlResult.error || '未知错误'}`);
            navigate(`/repositories/${repositoryName}`);
          }
        } catch (crawlError) {
          console.error('启动爬取任务失败:', crawlError);
          message.warning('爬取任务启动失败，请在详情页手动启动');
          navigate(`/repositories/${repositoryName}`);
        }
      } else {
        message.error(`创建失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('创建信息库失败:', error);
      message.error(`创建信息库失败: ${error.error || '未知错误'}`);
    }
    setLoading(false);
  };

  // 处理上传表单提交
  const handleUploadSubmit = async (values) => {
    setLoading(true);
    try {
      if (fileList.length === 0) {
        message.error('请至少上传一个文件');
        setLoading(false);
        return;
      }

      console.log('准备上传的文件列表:', fileList);
      
      // 使用增强的跨平台兼容FormData
      const formData = new FormData();
      formData.append('name', values.name);
      formData.append('description', values.description || '');
      formData.append('source', 'upload');
      
      // 添加文件
      fileList.forEach((file, index) => {
        // 获取实际文件对象
        let actualFile = file;
        if (file.originFileObj) {
          actualFile = file.originFileObj;
        }
        formData.append('files', actualFile);
      });

      // 验证FormData内容
      const files = formData.getAll('files');
      console.log('FormData诊断结果:', {
        fileEntries: files.length,
        fileNames: files.map(f => f.name)
      });
      
      if (files.length === 0) {
        message.error('FormData中没有有效的文件，请重试');
        setLoading(false);
        return;
      }

      const response = await createRepository(formData, true);
      if (response.success) {
        message.success(`信息库创建成功，已上传 ${files.length} 个文件`);
        
        // 确保获取到正确的信息库名称
        const repositoryName = response.repository_name || values.name;
        
        // 清空文件列表
        setFileList([]);
        
        // 使用正确的信息库名称进行导航
        navigate(`/repositories/${repositoryName}`);
      } else {
        message.error(`创建失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('创建信息库失败:', error);
      message.error(`创建信息库失败: ${error.error || '未知错误'}`);
      
      // 额外的错误诊断信息
      console.error('错误时的诊断信息:', {
        fileList: fileList.map(f => ({ name: f.name, size: f.size, type: f.type })),
        userAgent: navigator.userAgent,
        platform: navigator.platform
      });
    }
    setLoading(false);
  };

  // 增强的文件上传配置
  const uploadProps = {
    onRemove: file => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: file => {
      console.log('beforeUpload 被调用，文件:', file.name, '大小:', file.size, '类型:', file.type);
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
        console.log('添加文件后的列表长度:', newFileList.length);
        console.log('新文件列表:', newFileList.map(f => f.name));
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
      console.log('Upload onChange:', info.fileList.length, '个文件');
      console.log('文件状态变化:', info.file.status);
      
      // 处理文件状态变化，确保跨平台一致性
      if (info.file.status === 'error') {
        message.error(`文件 ${info.file.name} 处理失败`);
      }
    }
  };

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 16 }}>
        <Title level={4}>创建信息库</Title>
        <Paragraph>创建新的信息库，支持爬虫和上传两种方式</Paragraph>
      </div>

      <Tabs 
        defaultActiveKey="crawler" 
        onChange={setCreateType}
        tabBarStyle={{ marginBottom: 24 }}
        items={[
          {
            key: 'crawler',
            label: (
              <span>
                <LinkOutlined />
                爬虫方式
              </span>
            ),
            children: (
              <Card className="flat-card">
                <Spin spinning={loading && createType === 'crawler'}>
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                    initialValues={{
                      depth: 1,
                      threads: 5
                    }}
                  >
                    <Form.Item
                      name="name"
                      label="信息库名称"
                      rules={[{ required: true, message: '请输入信息库名称' }]}
                    >
                      <Input placeholder="例如: Harvard_University" />
                    </Form.Item>

                    <Form.Item
                      name="description"
                      label="描述"
                    >
                      <Input placeholder="可选描述" />
                    </Form.Item>

                    <Form.Item
                      name="urls"
                      label="起始URL列表"
                      rules={[{ required: true, message: '请输入至少一个URL' }]}
                      extra="每行一个URL，例如: https://www.harvard.edu"
                    >
                      <TextArea
                        placeholder="https://www.example.com"
                        autoSize={{ minRows: 3, maxRows: 10 }}
                      />
                    </Form.Item>

                    <Form.Item
                      name="depth"
                      label="爬取深度"
                      extra="从起始URL开始的链接跟踪深度，0表示只爬取入口URL"
                    >
                      <InputNumber min={0} max={10} />
                    </Form.Item>

                    <Form.Item
                      name="threads"
                      label="并发线程数"
                      extra="同时爬取的线程数，建议5-10"
                    >
                      <InputNumber min={1} max={20} />
                    </Form.Item>

                    <Form.Item>
                      <Button 
                        type="primary" 
                        htmlType="submit" 
                        loading={loading && createType === 'crawler'}
                        icon={<DatabaseOutlined />}
                      >
                        创建并开始爬取
                      </Button>
                    </Form.Item>
                  </Form>
                </Spin>
              </Card>
            )
          },
          {
            key: 'upload',
            label: (
              <span>
                <UploadOutlined />
                上传方式
              </span>
            ),
            children: (
              <Card className="flat-card">
                <Spin spinning={loading && createType === 'upload'}>
                  <Form
                    form={uploadForm}
                    layout="vertical"
                    onFinish={handleUploadSubmit}
                  >
                    <Form.Item
                      name="name"
                      label="信息库名称"
                      rules={[{ required: true, message: '请输入信息库名称' }]}
                    >
                      <Input placeholder="例如: Custom_Documents" />
                    </Form.Item>

                    <Form.Item
                      name="description"
                      label="描述"
                    >
                      <Input placeholder="可选描述" />
                    </Form.Item>

                    <Form.Item
                      label="上传文件"
                      extra={`支持 .txt, .pdf, .html 格式，可选择多个文件。已选择 ${fileList.length} 个文件`}
                    >
                      <Upload {...uploadProps}>
                        <Button icon={<UploadOutlined />}>
                          {fileList.length > 0 ? `已选择 ${fileList.length} 个文件，继续选择` : '选择文件'}
                        </Button>
                      </Upload>
                      {fileList.length > 0 && (
                        <div style={{ marginTop: 8, color: '#666' }}>
                          <Text type="secondary">
                            文件列表：{fileList.map(f => f.name).join(', ')}
                          </Text>
                        </div>
                      )}
                    </Form.Item>

                    <Form.Item>
                      <Button 
                        type="primary" 
                        htmlType="submit" 
                        loading={loading && createType === 'upload'}
                        icon={<CloudUploadOutlined />}
                        disabled={fileList.length === 0}
                      >
                        创建信息库
                      </Button>
                    </Form.Item>
                  </Form>
                </Spin>
              </Card>
            )
          }
        ]}
      />

      <Alert
        message="提示"
        description="创建信息库后，系统将自动开始爬取或处理上传的文件。爬取过程可能需要一些时间，您可以在信息库详情页查看进度。"
        type="info"
        showIcon
        style={{ marginTop: 24 }}
      />
    </div>
  );
};

export default CreateRepositoryPage;
