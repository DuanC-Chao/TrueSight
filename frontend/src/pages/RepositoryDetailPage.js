import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Tabs, Typography, Spin, Button, message, 
  Descriptions, Card, Table, Space, Tag, Empty,
  Tooltip, Modal, List, Divider, Progress
} from 'antd';
import { 
  FileTextOutlined, 
  QuestionCircleOutlined, 
  SyncOutlined,
  CalculatorOutlined,
  FileSearchOutlined,
  CloudUploadOutlined,
  ExclamationCircleOutlined,
  SettingOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from '@ant-design/icons';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { 
  getRepository, 
  getRepositoryFiles, 
  getRepositorySummaryFiles,
  getRepositoryQAFiles,
  calculateTokens,
  getProcessStatus,
  syncRepositoryWithRAGFlow,
  checkRepositoryRAGFlowSync
} from '../services/api';

const { Title, Text } = Typography;
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
  const location = useLocation();
  const [repository, setRepository] = useState(null);
  const [loading, setLoading] = useState(true);
  const [files, setFiles] = useState([]);
  const [summaryFiles, setSummaryFiles] = useState([]);
  const [qaFiles, setQAFiles] = useState([]);
  const [activeTab, setActiveTab] = useState('1');
  const [error, setError] = useState(null);
  
  // 添加分页状态
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    pageSizeOptions: ['10', '20', '50', '100'],
    showSizeChanger: true
  });

  // 统一的任务状态管理
  const [summaryTaskId, setSummaryTaskId] = useState(null);
  const [qaTaskId, setQaTaskId] = useState(null);
  const [crawlTaskId, setCrawlTaskId] = useState(null);
  const [tokenTaskId, setTokenTaskId] = useState(null);
  const [summaryStatus, setSummaryStatus] = useState(null);
  const [qaStatus, setQaStatus] = useState(null);
  const [crawlStatus, setCrawlStatus] = useState(null);
  const [tokenStatus, setTokenStatus] = useState(null);
  
  // RAGFlow同步状态
  const [ragflowSyncStatus, setRagflowSyncStatus] = useState(null);
  const [ragflowSyncLoading, setRagflowSyncLoading] = useState(false);
  
  // 统一的轮询管理
  const pollingIntervalRef = useRef(null);

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

  // 检查RAGFlow同步状态
  const checkRAGFlowSyncStatus = async () => {
    if (!id) return;
    
    setRagflowSyncLoading(true);
    try {
      const response = await checkRepositoryRAGFlowSync(id);
      if (response.success) {
        setRagflowSyncStatus(response.sync_status);
        
        // 根据同步状态显示相应的消息
        const status = response.sync_status;
        if (status.sync_status === 'synced') {
          message.success(status.message);
        } else if (status.sync_status === 'connection_failed') {
          message.error(`RAGFlow连接失败: ${status.message}`);
        } else if (status.sync_status === 'dataset_missing') {
          message.warning(`Dataset缺失: ${status.message}`);
        } else if (status.sync_status === 'file_count_mismatch') {
          message.warning(`文件数量不匹配: ${status.message}`);
        } else {
          message.info(status.message);
        }
      } else {
        message.error(`检查同步状态失败: ${response.error || '未知错误'}`);
        setRagflowSyncStatus(null);
      }
    } catch (error) {
      console.error('检查RAGFlow同步状态失败:', error);
      message.error(`检查同步状态失败: ${error.error || error.message || '未知错误'}`);
      setRagflowSyncStatus(null);
    } finally {
      setRagflowSyncLoading(false);
    }
  };

  // 检查运行中的任务
  const checkRunningTasks = async (repositoryName) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/repository/${repositoryName}/running-tasks`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success) {
        const runningTasks = data.running_tasks;
        
        // 设置爬取任务状态
        if (runningTasks.crawl) {
          setCrawlTaskId(runningTasks.crawl.id);
          setCrawlStatus({ status: 'running' });
        }
        
        // 设置总结任务状态
        if (runningTasks.summary) {
          setSummaryTaskId(runningTasks.summary.id);
          setSummaryStatus({ status: 'running' });
        }
        
        // 设置问答任务状态
        if (runningTasks.qa) {
          setQaTaskId(runningTasks.qa.id);
          setQaStatus({ status: 'running' });
        }
        
        // 注意：这里不再启动轮询，轮询由useEffect统一管理
      }
    } catch (error) {
      console.error('检查运行中任务失败:', error);
    }
  };

  useEffect(() => {
    loadAllData();
    
    // 检查是否从创建页面传递了爬取任务ID
    if (location.state?.crawlTaskId) {
      setCrawlTaskId(location.state.crawlTaskId);
      setCrawlStatus({ status: 'running' });
    }
    
    // 清理函数
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [id]); // 修改依赖项

  // 当repository加载完成后，检查运行中的任务
  useEffect(() => {
    if (repository && repository.name) {
      checkRunningTasks(repository.name);
    }
  }, [repository]);

  // 计算Token
  const handleCalculateTokens = async () => {
    try {
      const response = await calculateTokens(id);
      if (response.success) {
        message.success('Token计算已开始');
        setTokenTaskId(response.task_id);
        setTokenStatus({ status: 'running' });
        // 轮询由useEffect统一管理，这里不再手动启动
      } else {
        message.error(`计算Token失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('计算Token失败:', error);
      // 改进错误信息显示
      let errorMessage = '计算Token失败';
      if (error.response && error.response.data && error.response.data.error) {
        errorMessage += `: ${error.response.data.error}`;
      } else if (error.message) {
        errorMessage += `: ${error.message}`;
      } else if (error.error) {
        errorMessage += `: ${error.error}`;
      } else {
        errorMessage += ': 未知错误';
      }
      message.error(errorMessage);
    }
  };

  // 统一的轮询函数
  const pollTaskStatus = useCallback(async (taskId, type) => {
    try {
      let response;
      if (type === 'crawl') {
        // 爬取任务使用不同的API
        response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/crawler/status/${taskId}`);
      } else {
        // 其他任务使用统一的API
        response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/status/${taskId}`);
      }
      
      if (!response.ok) {
        // 如果是404错误，说明任务已经不存在，清理状态
        if (response.status === 404) {
          console.warn(`任务 ${taskId} 不存在，清理状态`);
          if (type === 'crawl') {
            setCrawlTaskId(null);
            setCrawlStatus(null);
          } else if (type === 'summary') {
            setSummaryTaskId(null);
            setSummaryStatus(null);
          } else if (type === 'qa') {
            setQaTaskId(null);
            setQaStatus(null);
          } else if (type === 'token') {
            setTokenTaskId(null);
            setTokenStatus(null);
          }
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (type === 'crawl') {
        const status = data.status;
        setCrawlStatus(status);
        if (status.status === 'completed' || status.status === 'failed') {
          setCrawlTaskId(null);
          if (status.status === 'completed') {
            message.success('爬取已完成');
            // 刷新文件列表和信息库信息
            await fetchFiles();
            await fetchRepository();
          } else if (status.status === 'failed') {
            message.error('爬取失败: ' + (status.error || '未知错误'));
          }
        }
      } else if (type === 'summary') {
        setSummaryStatus(data.status);
        if (data.status.status === 'completed' || data.status.status === 'failed') {
          setSummaryTaskId(null);
          if (data.status.status === 'completed') {
            message.success('总结生成已完成');
            // 刷新总结文件列表
            await fetchSummaryFiles();
          } else if (data.status.status === 'failed') {
            message.error('总结生成失败: ' + (data.status.error || '未知错误'));
          }
        }
      } else if (type === 'qa') {
        setQaStatus(data.status);
        if (data.status.status === 'completed' || data.status.status === 'failed') {
          setQaTaskId(null);
          if (data.status.status === 'completed') {
            message.success('问答对生成已完成');
            // 刷新问答文件列表
            await fetchQAFiles();
          } else if (data.status.status === 'failed') {
            message.error('问答对生成失败: ' + (data.status.error || '未知错误'));
          }
        }
      } else if (type === 'token') {
        setTokenStatus(data.status);
        if (data.status.status === 'completed' || data.status.status === 'failed') {
          setTokenTaskId(null);
          if (data.status.status === 'completed') {
            message.success('Token计算已完成');
            // 刷新信息库信息以获取最新的token数量
            await fetchRepository();
          } else if (data.status.status === 'failed') {
            message.error('Token计算失败: ' + (data.status.error || '未知错误'));
          }
        }
      }
    } catch (error) {
      console.error('轮询任务状态失败:', error);
    }
  }, [fetchFiles, fetchSummaryFiles, fetchQAFiles, fetchRepository]);

  // 设置轮询
  useEffect(() => {
    // 清理之前的轮询
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    // 检查是否有活跃的任务
    const activeTasks = [];
    if (crawlTaskId) activeTasks.push({ id: crawlTaskId, type: 'crawl' });
    if (summaryTaskId) activeTasks.push({ id: summaryTaskId, type: 'summary' });
    if (qaTaskId) activeTasks.push({ id: qaTaskId, type: 'qa' });
    if (tokenTaskId) activeTasks.push({ id: tokenTaskId, type: 'token' });

    if (activeTasks.length > 0) {
      pollingIntervalRef.current = setInterval(() => {
        activeTasks.forEach(task => {
          pollTaskStatus(task.id, task.type);
        });
      }, 2000); // 每2秒轮询一次
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [crawlTaskId, summaryTaskId, qaTaskId, tokenTaskId, pollTaskStatus]);

  // 生成总结
  const handleGenerateSummary = async () => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/summary/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_name: repository.name
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.task_id) {
        setSummaryTaskId(data.task_id);
        setSummaryStatus({ status: 'running' });
        message.success('总结生成任务已启动');
        // 轮询由useEffect统一管理，这里不再手动启动
      } else {
        throw new Error(data.error || '生成总结失败');
      }
    } catch (error) {
      console.error('生成总结失败:', error);
      message.error(error.message || '生成总结失败');
    }
  };

  // 生成问答对
  const handleGenerateQA = async () => {
    try {
      // 首先检查是否已计算Token
      const hasTokens = repository.token_count_deepseek > 0 || 
                       repository.token_count_gpt4o > 0 || 
                       repository.token_count_jina > 0;
      
      if (!hasTokens) {
        // 提示用户先计算Token
        Modal.confirm({
          title: '需要先计算Token',
          content: '生成问答对需要基于Token数量进行分块处理，请先点击"计算Token"按钮计算文件的Token数量。',
          okText: '去计算Token',
          cancelText: '取消',
          onOk: () => {
            // 自动触发计算Token
            handleCalculateTokens();
          }
        });
        return;
      }
      
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/qa/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_name: repository.name
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.task_id) {
        setQaTaskId(data.task_id);
        setQaStatus({ status: 'running' });
        message.success('问答对生成任务已启动');
        // 轮询由useEffect统一管理，这里不再手动启动
      } else {
        throw new Error(data.error || '生成问答对失败');
      }
    } catch (error) {
      console.error('生成问答对失败:', error);
      message.error(error.message || '生成问答对失败');
    }
  };

  // 同步到RAGFlow
  const handleSyncToRAGFlow = async () => {
    try {
      const response = await syncRepositoryWithRAGFlow(id);
      if (response.success) {
        const result = response.result;
        
        // 检查是否发生了模式切换
        if (result.mode_switched) {
          message.warning({
            content: `检测到同步模式切换：${result.mode_switch_info}。已清理旧文档并重新同步。`,
            duration: 6
          });
        } else {
          message.success('已成功同步到RAGFlow');
        }
        
        // 显示同步统计信息
        if (result.files_uploaded > 0 || result.files_updated > 0 || result.files_skipped > 0) {
          const stats = [];
          if (result.files_uploaded > 0) stats.push(`上传 ${result.files_uploaded} 个文件`);
          if (result.files_updated > 0) stats.push(`更新 ${result.files_updated} 个文件`);
          if (result.files_skipped > 0) stats.push(`跳过 ${result.files_skipped} 个文件`);
          
          message.info(`同步完成 (${result.sync_mode})：${stats.join('，')}`);
        }
        
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

  // 获取处理类型文本
  const getProcessingTypeText = () => {
    if (tokenStatus?.status === 'running') return 'Token计算';
    if (summaryStatus?.status === 'running') return '总结生成';
    if (qaStatus?.status === 'running') return '问答对生成';
    if (crawlStatus?.status === 'running') return '爬取';
    return '处理';
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

  // 获取RAGFlow同步状态标签
  const getRAGFlowSyncStatusTag = () => {
    if (ragflowSyncLoading) {
      return <Tag icon={<SyncOutlined spin />} color="processing">检查中</Tag>;
    }
    
    if (!ragflowSyncStatus) {
      // 如果没有检查过同步状态，显示基本状态
      return repository.dataset_id ? 
        <Tag color="success">已同步</Tag> : 
        <Tag color="warning">未同步</Tag>;
    }
    
    const status = ragflowSyncStatus;
    
    switch (status.sync_status) {
      case 'synced':
        return (
          <Tooltip title={`连接正常，Dataset存在，文件数量匹配 (${status.ragflow_file_count}/${status.local_file_count})`}>
            <Tag color="success">完全同步</Tag>
          </Tooltip>
        );
      case 'connection_failed':
        return (
          <Tooltip title={`无法连接到RAGFlow: ${status.errors.join(', ')}`}>
            <Tag color="error">连接失败</Tag>
          </Tooltip>
        );
      case 'dataset_missing':
        return (
          <Tooltip title={`Dataset不存在或已被删除 (ID: ${status.dataset_id})`}>
            <Tag color="warning">Dataset缺失</Tag>
          </Tooltip>
        );
      case 'file_count_mismatch':
        return (
          <Tooltip title={`文件数量不匹配: RAGFlow(${status.ragflow_file_count}) vs 本地(${status.local_file_count}) - ${status.sync_mode}`}>
            <Tag color="orange">文件不匹配</Tag>
          </Tooltip>
        );
      case 'error':
        return (
          <Tooltip title={`检查失败: ${status.errors.join(', ')}`}>
            <Tag color="error">检查失败</Tag>
          </Tooltip>
        );
      default:
        return (
          <Tooltip title={status.message}>
            <Tag color="default">状态未知</Tag>
          </Tooltip>
        );
    }
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

  // 开始爬取
  const handleStartCrawl = async () => {
    if (repository.source !== 'crawler') {
      message.warning('只有爬虫来源的信息库才能进行爬取');
      return;
    }
    
    try {
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/crawler/repository/${repository.name}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.success && data.task_id) {
        setCrawlTaskId(data.task_id);
        setCrawlStatus({ status: 'running' });
        message.success('爬取任务已启动');
      } else {
        throw new Error(data.error || '开始爬取失败');
      }
    } catch (error) {
      console.error('开始爬取失败:', error);
      message.error(error.message || '开始爬取失败');
    }
  };

  // 停止爬取
  const handleStopCrawl = async () => {
    if (!crawlTaskId) {
      message.warning('没有正在运行的爬取任务');
      return;
    }
    
    confirm({
      title: '确认停止爬取？',
      icon: <ExclamationCircleOutlined />,
      content: '停止后将无法恢复，是否确认停止爬取任务？',
      onOk: async () => {
        try {
          const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/crawler/stop/${crawlTaskId}`, {
            method: 'POST'
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const data = await response.json();
          if (data.success) {
            setCrawlTaskId(null);
            setCrawlStatus(null);
            message.success('爬取任务已停止');
            // 刷新文件列表
            await fetchFiles();
          } else {
            throw new Error(data.error || '停止爬取失败');
          }
        } catch (error) {
          console.error('停止爬取失败:', error);
          message.error(error.message || '停止爬取失败');
        }
      }
    });
  };

  // 停止总结生成
  const handleStopSummary = async () => {
    if (!summaryTaskId) {
      message.warning('没有正在运行的总结生成任务');
      return;
    }
    
    confirm({
      title: '确认停止总结生成？',
      icon: <ExclamationCircleOutlined />,
      content: '停止后将无法恢复，是否确认停止总结生成任务？',
      onOk: async () => {
        try {
          const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/task/${summaryTaskId}/cancel`, {
            method: 'POST'
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const data = await response.json();
          if (data.success) {
            setSummaryTaskId(null);
            setSummaryStatus(null);
            message.success('总结生成任务已停止');
            // 刷新总结文件列表
            await fetchSummaryFiles();
          } else {
            throw new Error(data.error || '停止总结生成失败');
          }
        } catch (error) {
          console.error('停止总结生成失败:', error);
          message.error(error.message || '停止总结生成失败');
        }
      }
    });
  };

  // 停止问答对生成
  const handleStopQA = async () => {
    if (!qaTaskId) {
      message.warning('没有正在运行的问答对生成任务');
      return;
    }
    
    confirm({
      title: '确认停止问答对生成？',
      icon: <ExclamationCircleOutlined />,
      content: '停止后将无法恢复，是否确认停止问答对生成任务？',
      onOk: async () => {
        try {
          const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'http://localhost:5001'}/api/processor/task/${qaTaskId}/cancel`, {
            method: 'POST'
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const data = await response.json();
          if (data.success) {
            setQaTaskId(null);
            setQaStatus(null);
            message.success('问答对生成任务已停止');
            // 刷新问答文件列表
            await fetchQAFiles();
          } else {
            throw new Error(data.error || '停止问答对生成失败');
          }
        } catch (error) {
          console.error('停止问答对生成失败:', error);
          message.error(error.message || '停止问答对生成失败');
        }
      }
    });
  };

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
      {/* 信息库标题 */}
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>{repository.name}</Title>
      </div>
      
      {/* 操作按钮区域 */}
      <div style={{ marginBottom: 16 }}>
        <Space wrap size="small" style={{ width: '100%' }}>
          {/* 爬取相关按钮 */}
          {repository.source === 'crawler' && (
            <>
              <Button 
                icon={<PlayCircleOutlined />} 
                onClick={handleStartCrawl}
                loading={crawlTaskId !== null && crawlStatus?.status === 'running'}
                disabled={crawlTaskId !== null}
                type="primary"
              >
                开始爬取
              </Button>
              {crawlTaskId && (
                <>
                  <Button 
                    icon={<PauseCircleOutlined />} 
                    onClick={handleStopCrawl}
                    danger
                  >
                    停止爬取
                  </Button>
                  {crawlStatus && crawlStatus.status === 'running' && (
                    <Tooltip title={`已爬取: ${crawlStatus.crawled_urls || 0} / ${crawlStatus.total_urls || 0}`}>
                      <Progress 
                        type="circle" 
                        percent={crawlStatus.total_urls ? Math.round((crawlStatus.crawled_urls || 0) / crawlStatus.total_urls * 100) : 0} 
                        width={40}
                        format={() => `${crawlStatus.crawled_urls || 0}`}
                      />
                    </Tooltip>
                  )}
                </>
              )}
            </>
          )}
          
          {repository.source === 'crawler' && <Divider type="vertical" />}
          
          {/* 处理相关按钮 */}
          <Tooltip title={crawlTaskId !== null && crawlStatus?.status === 'running' ? '爬取进行中，请等待爬取完成' : ''}>
            <Button 
              icon={<CalculatorOutlined />} 
              onClick={handleCalculateTokens}
              loading={tokenStatus?.status === 'running'}
              disabled={tokenTaskId !== null || (crawlTaskId !== null && crawlStatus?.status === 'running')}
            >
              计算Token
            </Button>
          </Tooltip>
          
          <Tooltip title={crawlTaskId !== null && crawlStatus?.status === 'running' ? '爬取进行中，请等待爬取完成' : ''}>
            <Button 
              icon={<FileSearchOutlined />} 
              onClick={handleGenerateSummary}
              loading={summaryTaskId !== null && summaryStatus?.status === 'running'}
              disabled={summaryTaskId !== null || (crawlTaskId !== null && crawlStatus?.status === 'running')}
            >
              生成总结
            </Button>
          </Tooltip>
          {summaryTaskId && (
            <>
              <Button 
                icon={<PauseCircleOutlined />} 
                onClick={handleStopSummary}
                size="small"
                danger
              >
                停止
              </Button>
              {summaryStatus && summaryStatus.status === 'running' && summaryStatus.progress !== undefined && (
                <Progress 
                  type="circle" 
                  percent={summaryStatus.progress} 
                  width={40}
                />
              )}
            </>
          )}
          
          <Tooltip title={crawlTaskId !== null && crawlStatus?.status === 'running' ? '爬取进行中，请等待爬取完成' : ''}>
            <Button 
              icon={<QuestionCircleOutlined />} 
              onClick={handleGenerateQA}
              loading={qaTaskId !== null && qaStatus?.status === 'running'}
              disabled={qaTaskId !== null || (crawlTaskId !== null && crawlStatus?.status === 'running')}
            >
              生成问答对
            </Button>
          </Tooltip>
          {qaTaskId && (
            <>
              <Button 
                icon={<PauseCircleOutlined />} 
                onClick={handleStopQA}
                size="small"
                danger
              >
                停止
              </Button>
              {qaStatus && qaStatus.status === 'running' && qaStatus.progress !== undefined && (
                <Progress 
                  type="circle" 
                  percent={qaStatus.progress} 
                  width={40}
                />
              )}
            </>
          )}
          
          <Divider type="vertical" />
          
          {/* 其他操作按钮 */}
          <Tooltip title={crawlTaskId !== null && crawlStatus?.status === 'running' ? '爬取进行中，请等待爬取完成' : ''}>
            <Button 
              type="primary" 
              icon={<CloudUploadOutlined />} 
              onClick={handleSyncToRAGFlow}
              disabled={tokenTaskId !== null || (crawlTaskId !== null && crawlStatus?.status === 'running')}
            >
              同步到RAGFlow
            </Button>
          </Tooltip>
          <Button 
            icon={<SettingOutlined />}
            onClick={goToSettings}
          >
            设置
          </Button>
          <Button 
            icon={<SyncOutlined />} 
            onClick={async () => {
              await loadAllData();
              await checkRAGFlowSyncStatus();
            }}
            loading={loading || ragflowSyncLoading}
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
          <Descriptions.Item label="RAGFlow状态">{getRAGFlowSyncStatusTag()}</Descriptions.Item>
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