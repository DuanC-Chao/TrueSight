import React, { useState, useEffect } from 'react';
import { 
  Card, Form, Input, Button, Radio, Upload, message, 
  Typography, Divider, InputNumber, Alert, Spin, Tabs 
} from 'antd';
import { 
  UploadOutlined, 
  LinkOutlined, 
  DatabaseOutlined,
  CloudUploadOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { createRepository } from '../services/api';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;
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

      // 构建FormData
      const formData = new FormData();
      formData.append('name', values.name);
      formData.append('description', values.description || '');
      formData.append('source', 'upload');
      
      // 添加文件
      fileList.forEach(file => {
        formData.append('files', file.originFileObj);
      });

      const response = await createRepository(formData, true);
      if (response.success) {
        message.success('信息库创建成功');
        
        // 确保获取到正确的信息库名称
        const repositoryName = response.repository_name || values.name;
        
        // 使用正确的信息库名称进行导航
        navigate(`/repositories/${repositoryName}`);
      } else {
        message.error(`创建失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('创建信息库失败:', error);
      message.error(`创建信息库失败: ${error.error || '未知错误'}`);
    }
    setLoading(false);
  };

  // 文件上传配置
  const uploadProps = {
    onRemove: file => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: file => {
      // 检查文件类型
      const isValidType = file.type === 'text/plain' || 
                          file.type === 'application/pdf' || 
                          file.type === 'text/html' ||
                          file.name.endsWith('.txt') ||
                          file.name.endsWith('.pdf') ||
                          file.name.endsWith('.html');
      
      if (!isValidType) {
        message.error('只支持 .txt, .pdf, .html 格式的文件');
        return Upload.LIST_IGNORE;
      }
      
      setFileList([...fileList, file]);
      return false;
    },
    fileList,
    multiple: true,
    directory: true
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
      >
        <TabPane 
          tab={
            <span>
              <LinkOutlined />
              爬虫方式
            </span>
          } 
          key="crawler"
        >
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
        </TabPane>

        <TabPane 
          tab={
            <span>
              <UploadOutlined />
              上传方式
            </span>
          } 
          key="upload"
        >
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
                  extra="支持 .txt, .pdf, .html 格式，可上传文件夹"
                >
                  <Upload {...uploadProps}>
                    <Button icon={<UploadOutlined />}>选择文件或文件夹</Button>
                  </Upload>
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
        </TabPane>
      </Tabs>

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
