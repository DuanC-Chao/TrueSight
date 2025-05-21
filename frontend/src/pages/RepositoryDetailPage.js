import React, { useState, useEffect } from 'react';
import { 
  Tabs, Typography, Spin, Button, message, 
  Descriptions, Card, Table, Space, Tag, Empty,
  Tooltip, Modal, List, Divider
} from 'antd';
import { 
  FileTextOutlined, 
  QuestionCircleOutlined, 
  SyncOutlined,
  CalculatorOutlined,
  FileSearchOutlined,
  CloudUploadOutlined,
  ExclamationCircleOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  getRepository, 
  getRepositoryFiles, 
  getRepositorySummaryFiles,
  getRepositoryQAFiles,
  calculateTokens,
  generateSummary,
  generateQA,
  getProcessStatus,
  syncRepositoryWithRAGFlow
} from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;
const { confirm } = Modal;

/**
 * 信息库详情页面
 * 
 * 展示信息库的详细信息、文件列表、总结文件和问答文件
 */
const RepositoryDetailPage = () => {
  // 修改参数名，与路由定义保持一致
  const { id } = useParams();
  const navigate = useNavigate();
  const [repository, setRepository] = useState(null);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [summaryFiles, setSummaryFiles] = useState([]);
  const [qaFiles, setQAFiles] = useState([]);
  const [activeTab, setActiveTab] = useState('1');
  const [processingTask, setProcessingTask] = useState(null);
  const [processingType, setProcessingType] = useState(null);
  const [statusPolling, setStatusPolling] = useState(null);
  const [error, setError] = useState(null);
  
  // 添加分页状态
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    pageSizeOptions: ['10', '20', '50', '100'],
    showSizeChanger: true
  });

  // 获取信息库信息
  const fetchRepository = async () => {
    if (!id) {
      setError('信息库ID未定义');
      setLoading(false);
      return;
    }
    
    try {
      const response = await getRepository(id);
      if (response.success) {
        setRepository(response.repository);
        setError(null);
      } else {
        setError(`获取信息库信息失败: ${response.error || '未知错误'}`);
        message.error(`获取信息库信息失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      setError(`获取信息库信息失败: ${error.error || '未知错误'}`);
      message.error(`获取信息库信息失败: ${error.error || '未知错误'}`);
    }
  };

  // 获取信息库文件
  const fetchFiles = async () => {
    if (!id) return;
    
    try {
      const response = await getRepositoryFiles(id);
      if (response.success) {
        setFiles(response.files || []);
      } else {
        message.error(`获取信息库文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`获取信息库文件失败: ${error.error || '未知错误'}`);
    }
  };

  // 获取总结文件
  const fetchSummaryFiles = async () => {
    if (!id) return;
    
    try {
      const response = await getRepositorySummaryFiles(id);
      if (response.success) {
        setSummaryFiles(response.files || []);
      } else {
        message.error(`获取总结文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`获取总结文件失败: ${error.error || '未知错误'}`);
    }
  };

  // 获取问答文件
  const fetchQAFiles = async () => {
    if (!id) return;
    
    try {
      const response = await getRepositoryQAFiles(id);
      if (response.success) {
        setQAFiles(response.files || []);
      } else {
        message.error(`获取问答文件失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`获取问答文件失败: ${error.error || '未知错误'}`);
    }
  };

  // 加载所有数据
  const loadAllData = async () => {
    setLoading(true);
    await fetchRepository();
    await fetchFiles();
    await fetchSummaryFiles();
    await fetchQAFiles();
    setLoading(false);
  };

  useEffect(() => {
    loadAllData();
    
    // 清理函数
    return () => {
      if (statusPolling) {
        clearInterval(statusPolling);
      }
    };
  }, [id]); // 修改依赖项

  // 计算Token
  const handleCalculateTokens = async () => {
    try {
      const response = await calculateTokens(id);
      if (response.success) {
        message.success('Token计算已开始');
        setProcessingTask(response.task_id);
        setProcessingType('token');
        startStatusPolling(response.task_id);
      } else {
        message.error(`计算Token失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`计算Token失败: ${error.error || '未知错误'}`);
    }
  };

  // 生成总结
  const handleGenerateSummary = async () => {
    confirm({
      title: '确认生成总结',
      icon: <ExclamationCircleOutlined />,
      content: '生成总结将调用LLM API，可能需要一些时间。确定要继续吗？',
      onOk: async () => {
        try {
          const response = await generateSummary(id);
          if (response.success) {
            message.success('总结生成已开始');
            setProcessingTask(response.task_id);
            setProcessingType('summary');
            startStatusPolling(response.task_id);
          } else {
            message.error(`生成总结失败: ${response.error || '未知错误'}`);
          }
        } catch (error) {
          message.error(`生成总结失败: ${error.error || '未知错误'}`);
        }
      }
    });
  };

  // 生成问答对
  const handleGenerateQA = async () => {
    confirm({
      title: '确认生成问答对',
      icon: <ExclamationCircleOutlined />,
      content: '生成问答对将调用LLM API，可能需要一些时间。确定要继续吗？',
      onOk: async () => {
        try {
          const response = await generateQA(id);
          if (response.success) {
            message.success('问答对生成已开始');
            setProcessingTask(response.task_id);
            setProcessingType('qa');
            startStatusPolling(response.task_id);
          } else {
            message.error(`生成问答对失败: ${response.error || '未知错误'}`);
          }
        } catch (error) {
          message.error(`生成问答对失败: ${error.error || '未知错误'}`);
        }
      }
    });
  };

  // 同步到RAGFlow
  const handleSyncToRAGFlow = async () => {
    try {
      const response = await syncRepositoryWithRAGFlow(id);
      if (response.success) {
        message.success('已成功同步到RAGFlow');
        fetchRepository();
      } else {
        message.error(`同步到RAGFlow失败: ${response.result?.error || response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`同步到RAGFlow失败: ${error.error || '未知错误'}`);
    }
  };

  // 处理分页变化
  const handleTableChange = (newPagination) => {
    setPagination({
      ...pagination,
      current: newPagination.current,
      pageSize: newPagination.pageSize
    });
  };

  // 跳转到设置页面
  const goToSettings = () => {
    // 确保使用id参数而不是name
    navigate(`/repositories/${id}/settings`);
  };

  // 开始轮询任务状态
  const startStatusPolling = (taskId) => {
    // 清除现有的轮询
    if (statusPolling) {
      clearInterval(statusPolling);
    }

    // 设置新的轮询
    const interval = setInterval(async () => {
      try {
        const response = await getProcessStatus(taskId);
        if (response.success) {
          const status = response.status.status;
          
          if (status === 'completed') {
            message.success(`${getProcessingTypeText()}已完成`);
            clearInterval(interval);
            setStatusPolling(null);
            setProcessingTask(null);
            setProcessingType(null);
            
            // 刷新数据
            loadAllData();
          } else if (status === 'failed') {
            message.error(`${getProcessingTypeText()}失败: ${response.status.error || '未知错误'}`);
            clearInterval(interval);
            setStatusPolling(null);
            setProcessingTask(null);
            setProcessingType(null);
          }
        }
      } catch (error) {
        console.error('获取任务状态失败:', error);
      }
    }, 3000);

    setStatusPolling(interval);
  };

  // 获取处理类型文本
  const getProcessingTypeText = () => {
    switch (processingType) {
      case 'token':
        return 'Token计算';
      case 'summary':
        return '总结生成';
      case 'qa':
        return '问答对生成';
      default:
        return '处理';
    }
  };

  // 获取爬取状态标签
  const getCrawlStatusTag = (status) => {
    switch (status) {
      case 'complete':
        return <Tag color="success">爬取完成</Tag>;
      case 'incomplete':
        return <Tag color="processing">爬取中</Tag>;
      case 'not_started':
        return <Tag>爬取未开始</Tag>;
      case 'error':
        return <Tag color="error">错误</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  // 获取总结状态标签
  const getSummaryStatusTag = () => {
    if (!files || !summaryFiles) return <Tag>未知</Tag>;
    
    // 总结文件数量大于等于原始文件数量，则为"同步"
    const isSynced = summaryFiles.length >= files.length;
    
    return isSynced ? 
      <Tag color="success">同步</Tag> : 
      <Tag color="warning">未同步</Tag>;
  };

  // 获取问答对状态标签
  const getQAStatusTag = () => {
    if (!files || !qaFiles) return <Tag>未知</Tag>;
    
    // 问答文件数量大于等于原始文件数量，则为"同步"
    const isSynced = qaFiles.length >= files.length;
    
    return isSynced ? 
      <Tag color="success">同步</Tag> : 
      <Tag color="warning">未同步</Tag>;
  };

  // 获取来源标签
  const getSourceTag = (source) => {
    switch (source) {
      case 'crawler':
        return <Tag color="blue">爬虫</Tag>;
      case 'upload':
        return <Tag color="cyan">上传</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  // 获取自动更新标签
  const getAutoUpdateTag = (repository) => {
    if (!repository.auto_update) return <Tag>手动更新</Tag>;
    
    let color, text;
    switch (repository.update_frequency) {
      case 'daily':
        color = 'blue';
        text = '每日更新';
        break;
      case 'weekly':
        color = 'green';
        text = '每周更新';
        break;
      case 'monthly':
        color = 'purple';
        text = '每月更新';
        break;
      case 'yearly':
        color = 'magenta';
        text = '每年更新';
        break;
      default:
        color = 'default';
        text = '自动更新';
    }
    
    return <Tag color={color}>{text}</Tag>;
  };

  // 文件列表列定义
  const fileColumns = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <a href={`/api/repository/${id}/file?path=${encodeURIComponent(record.path)}`} target="_blank" rel="noopener noreferrer">
          {text}
        </a>
      )
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      render: (size) => `${(size / 1024).toFixed(2)} KB`
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type) => {
        let color;
        switch (type) {
          case 'txt':
            color = 'green';
            break;
          case 'pdf':
            color = 'red';
            break;
          case 'html':
            color = 'blue';
            break;
          default:
            color = 'default';
        }
        return <Tag color={color}>{type}</Tag>;
      }
    },
    {
      title: '修改时间',
      dataIndex: 'modified_time',
      key: 'modified_time'
    }
  ];

  // 显示错误信息
  if (error) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div>
              <Text type="danger" style={{ fontSize: 16 }}>{error}</Text>
              <div style={{ marginTop: 16 }}>
                <Button type="primary" onClick={() => navigate('/repositories')}>
                  返回信息库列表
                </Button>
              </div>
            </div>
          }
        />
      </div>
    );
  }

  // 显示加载状态
  if (loading && !repository) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Spin tip="加载中..." />
      </div>
    );
  }

  // 信息库不存在
  if (!repository) {
    return (
      <div style={{ textAlign: 'center', padding: '50px 0' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div>
              <Text type="danger" style={{ fontSize: 16 }}>信息库不存在或无法访问</Text>
              <div style={{ marginTop: 16 }}>
                <Button type="primary" onClick={() => navigate('/repositories')}>
                  返回信息库列表
                </Button>
              </div>
            </div>
          }
        />
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>{repository.name}</Title>
        <Space>
          <Button 
            icon={<CalculatorOutlined />} 
            onClick={handleCalculateTokens}
            loading={processingType === 'token'}
            disabled={!!processingTask}
          >
            计算Token
          </Button>
          <Button 
            icon={<FileSearchOutlined />} 
            onClick={handleGenerateSummary}
            loading={processingType === 'summary'}
            disabled={!!processingTask}
          >
            生成总结
          </Button>
          <Button 
            icon={<QuestionCircleOutlined />} 
            onClick={handleGenerateQA}
            loading={processingType === 'qa'}
            disabled={!!processingTask}
          >
            生成问答对
          </Button>
          <Button 
            type="primary" 
            icon={<CloudUploadOutlined />} 
            onClick={handleSyncToRAGFlow}
            disabled={!!processingTask}
          >
            同步到RAGFlow
          </Button>
          <Button 
            icon={<SettingOutlined />}
            onClick={goToSettings}
          >
            设置
          </Button>
          <Button 
            icon={<SyncOutlined />} 
            onClick={loadAllData}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Card className="flat-card" style={{ marginBottom: 16 }}>
        <Descriptions title="基本信息" bordered column={{ xxl: 4, xl: 3, lg: 3, md: 2, sm: 1, xs: 1 }}>
          <Descriptions.Item label="爬取状态">{getCrawlStatusTag(repository.status)}</Descriptions.Item>
          <Descriptions.Item label="总结状态">{getSummaryStatusTag()}</Descriptions.Item>
          <Descriptions.Item label="问答对状态">{getQAStatusTag()}</Descriptions.Item>
          <Descriptions.Item label="来源">{getSourceTag(repository.source)}</Descriptions.Item>
          <Descriptions.Item label="更新方式">{getAutoUpdateTag(repository)}</Descriptions.Item>
          <Descriptions.Item label="Token数量-JinaEmbedding">{repository.token_count_jina ? repository.token_count_jina.toLocaleString() : '未计算'}</Descriptions.Item>
          <Descriptions.Item label="Token数量-GPT4o">{repository.token_count_gpt4o ? repository.token_count_gpt4o.toLocaleString() : '未计算'}</Descriptions.Item>
          <Descriptions.Item label="Token数量-Deepseek">{repository.token_count_deepseek ? repository.token_count_deepseek.toLocaleString() : '未计算'}</Descriptions.Item>
          <Descriptions.Item label="直接入库">{repository.direct_import ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{repository.created_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="上次更新">{repository.updated_at || '-'}</Descriptions.Item>
          <Descriptions.Item label="RAGFlow状态">{repository.dataset_id ? <Tag color="success">已同步</Tag> : <Tag color="warning">未同步</Tag>}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={<span><FileTextOutlined />原始文件</span>} key="1">
          <Spin spinning={loading}>
            {files.length > 0 ? (
              <Table 
                dataSource={files} 
                columns={fileColumns} 
                rowKey="path"
                pagination={pagination}
                onChange={handleTableChange}
              />
            ) : (
              <Empty description="暂无文件" />
            )}
          </Spin>
        </TabPane>
        <TabPane tab={<span><FileSearchOutlined />总结文件</span>} key="2">
          <Spin spinning={loading}>
            {summaryFiles.length > 0 ? (
              <List
                itemLayout="vertical"
                dataSource={summaryFiles}
                pagination={{
                  pageSize: pagination.pageSize,
                  pageSizeOptions: pagination.pageSizeOptions,
                  showSizeChanger: true,
                  onChange: (page, pageSize) => {
                    setPagination({
                      ...pagination,
                      current: page,
                      pageSize: pageSize
                    });
                  }
                }}
                renderItem={file => (
                  <List.Item
                    key={file.path}
                    extra={
                      <Space>
                        <Tag color="blue">{file.type}</Tag>
                        <Text type="secondary">{`${(file.size / 1024).toFixed(2)} KB`}</Text>
                      </Space>
                    }
                  >
                    <List.Item.Meta
                      title={
                        <a href={`/api/repository/${id}/file?path=${encodeURIComponent(file.path)}`} target="_blank" rel="noopener noreferrer">
                          {file.name}
                        </a>
                      }
                      description={`修改时间: ${file.modified}`}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无总结文件" />
            )}
          </Spin>
        </TabPane>
        <TabPane tab={<span><QuestionCircleOutlined />问答文件</span>} key="3">
          <Spin spinning={loading}>
            {qaFiles.length > 0 ? (
              <List
                itemLayout="vertical"
                dataSource={qaFiles}
                pagination={{
                  pageSize: pagination.pageSize,
                  pageSizeOptions: pagination.pageSizeOptions,
                  showSizeChanger: true,
                  onChange: (page, pageSize) => {
                    setPagination({
                      ...pagination,
                      current: page,
                      pageSize: pageSize
                    });
                  }
                }}
                renderItem={file => (
                  <List.Item
                    key={file.path}
                    extra={
                      <Space>
                        <Tag color="green">{file.type}</Tag>
                        <Text type="secondary">{`${(file.size / 1024).toFixed(2)} KB`}</Text>
                      </Space>
                    }
                  >
                    <List.Item.Meta
                      title={
                        <a href={`/api/repository/${id}/file?path=${encodeURIComponent(file.path)}`} target="_blank" rel="noopener noreferrer">
                          {file.name}
                        </a>
                      }
                      description={`修改时间: ${file.modified}`}
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="暂无问答文件" />
            )}
          </Spin>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default RepositoryDetailPage;
