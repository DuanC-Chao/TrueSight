import React, { useState, useEffect } from 'react';
import { 
  Card, Row, Col, Typography, Spin, Empty, Button, 
  Statistic, Space, Alert, Divider, Collapse, Tag
} from 'antd';
import { 
  DatabaseOutlined, 
  CloudUploadOutlined, 
  SettingOutlined,
  FileTextOutlined,
  BugOutlined,
  CloudSyncOutlined,
  ExclamationCircleOutlined,
  WarningOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { listRepositories, checkHealth, getErrorLogs } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

/**
 * 首页组件
 * 
 * 显示系统概览、统计信息和快速入口
 */
const HomePage = () => {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    total: 0,
    crawling: 0,
    notStarted: 0,
    error: 0,
    crawler: 0,
    upload: 0,
    autoUpdate: 0,
    ragflowSynced: 0
  });
  const [systemStatus, setSystemStatus] = useState({
    healthy: true,
    message: '系统正常运行',
    details: null, // 详细错误信息
    errorType: null, // 错误类型
    errorLogs: [] // 系统错误日志
  });
  const navigate = useNavigate();

  // 获取信息库统计
  const fetchStats = async () => {
    try {
      const response = await listRepositories();
      if (response.success) {
        const repositories = response.repositories || [];
        
        // 计算统计数据
        const newStats = {
          total: repositories.length,
          crawling: repositories.filter(repo => repo.status === 'incomplete').length,
          notStarted: repositories.filter(repo => repo.status === 'not_started').length,
          error: repositories.filter(repo => repo.status === 'error').length,
          crawler: repositories.filter(repo => repo.source === 'crawler').length,
          upload: repositories.filter(repo => repo.source === 'upload').length,
          autoUpdate: repositories.filter(repo => repo.auto_update).length,
          ragflowSynced: repositories.filter(repo => repo.dataset_id).length
        };
        
        setStats(newStats);
      }
    } catch (error) {
      console.error('获取信息库统计失败:', error);
    }
  };

  // 获取系统错误日志
  const fetchErrorLogs = async () => {
    try {
      const response = await getErrorLogs();
      if (response.success) {
        return response.logs || [];
      }
      return [];
    } catch (error) {
      console.error('获取错误日志失败:', error);
      return [];
    }
  };

  // 格式化错误对象为可读字符串
  const formatErrorDetails = (error) => {
    let details = '';
    
    // 处理错误对象
    if (error) {
      // 添加错误消息
      if (error.error) {
        details += `错误信息: ${error.error}\n\n`;
      }
      
      // 添加响应数据
      if (error.response) {
        details += `状态码: ${error.response.status}\n`;
        if (error.response.data) {
          try {
            details += `响应数据: ${JSON.stringify(error.response.data, null, 2)}\n\n`;
          } catch (e) {
            details += `响应数据: [无法序列化]\n\n`;
          }
        }
      }
      
      // 添加请求信息
      if (error.request) {
        details += `请求URL: ${error.request.responseURL || '未知'}\n`;
        details += `请求方法: ${error.config?.method?.toUpperCase() || '未知'}\n\n`;
      }
      
      // 添加错误堆栈
      if (error.stack) {
        details += `错误堆栈:\n${error.stack}\n`;
      }
      
      // 如果没有提取到任何详细信息，则显示整个错误对象
      if (!details) {
        try {
          details = `完整错误对象:\n${JSON.stringify(error, Object.getOwnPropertyNames(error), 2)}`;
        } catch (e) {
          details = `无法序列化错误对象: ${e.message}`;
        }
      }
    }
    
    return details || '无详细错误信息';
  };

  // 确定错误类型
  const determineErrorType = (error) => {
    if (!error) return 'unknown';
    
    if (error.error && error.error.includes('连接')) {
      return 'connection';
    }
    
    if (error.response) {
      const status = error.response.status;
      if (status >= 500) return 'server';
      if (status >= 400) return 'client';
      return 'http';
    }
    
    if (error.request) return 'network';
    
    return 'unknown';
  };

  // 获取错误类型标签
  const getErrorTypeTag = (errorType) => {
    switch (errorType) {
      case 'connection':
        return <Tag color="red">连接错误</Tag>;
      case 'server':
        return <Tag color="red">服务器错误</Tag>;
      case 'client':
        return <Tag color="orange">客户端错误</Tag>;
      case 'network':
        return <Tag color="volcano">网络错误</Tag>;
      case 'http':
        return <Tag color="gold">HTTP错误</Tag>;
      default:
        return <Tag color="purple">未知错误</Tag>;
    }
  };

  // 检查系统健康状态
  const checkSystemHealth = async () => {
    try {
      const response = await checkHealth();
      
      // 获取错误日志
      const errorLogs = await fetchErrorLogs();
      
      // 检查健康状态 - 兼容两种API返回格式
      // 1. 如果response.success为true，表示健康
      // 2. 如果response.status为'ok'，也表示健康
      const isHealthy = response.success === true || 
                        (response.status && response.status.toLowerCase() === 'ok');
      
      // 如果健康检查成功但有错误日志，仍然显示警告
      if (isHealthy && errorLogs.length > 0) {
        setSystemStatus({
          healthy: true,
          message: '系统运行中，但存在错误日志',
          details: `系统有 ${errorLogs.length} 条错误日志，请查看错误日志页面了解详情。`,
          errorType: 'warning',
          errorLogs: errorLogs
        });
      } else if (isHealthy) {
        setSystemStatus({
          healthy: true,
          message: '系统正常运行',
          details: null,
          errorType: null,
          errorLogs: []
        });
      } else {
        // 健康检查失败
        setSystemStatus({
          healthy: false,
          message: response.error || '系统异常',
          details: `健康检查失败: ${response.error || '未知错误'}\n\n完整响应: ${JSON.stringify(response, null, 2)}`,
          errorType: 'server',
          errorLogs: errorLogs
        });
      }
    } catch (error) {
      console.error('系统健康检查失败:', error);
      
      // 提取并格式化详细错误信息
      const errorDetails = formatErrorDetails(error);
      const errorType = determineErrorType(error);
      
      // 尝试获取错误日志
      let errorLogs = [];
      try {
        errorLogs = await fetchErrorLogs();
      } catch (e) {
        console.error('获取错误日志失败:', e);
      }
      
      setSystemStatus({
        healthy: false,
        message: error.error || '无法连接到服务器',
        details: errorDetails,
        errorType: errorType,
        errorLogs: errorLogs
      });
    }
  };

  // 加载数据
  const loadData = async () => {
    setLoading(true);
    await Promise.all([fetchStats(), checkSystemHealth()]);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
    
    // 设置定时刷新
    const intervalId = setInterval(() => {
      checkSystemHealth();
    }, 60000); // 每分钟检查一次
    
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 16 }}>
        <Title level={4}>系统概览</Title>
      </div>

      {/* 系统状态 */}
      <Card className="flat-card" style={{ marginBottom: 24 }}>
        <Alert
          message={
            <Space>
              {systemStatus.healthy ? "系统状态: 正常" : "系统状态: 异常"}
              {systemStatus.errorType && getErrorTypeTag(systemStatus.errorType)}
            </Space>
          }
          description={
            <>
              <div>{systemStatus.message}</div>
              
              {/* 显示错误日志摘要 */}
              {systemStatus.errorLogs && systemStatus.errorLogs.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Space>
                    <WarningOutlined style={{ color: '#faad14' }} />
                    <Text type="warning">
                      系统有 {systemStatus.errorLogs.length} 条错误日志
                      <Button 
                        type="link" 
                        size="small" 
                        onClick={() => navigate('/error-logs')}
                        style={{ padding: '0 4px' }}
                      >
                        查看详情
                      </Button>
                    </Text>
                  </Space>
                </div>
              )}
              
              {/* 显示详细错误信息 */}
              {!systemStatus.healthy && systemStatus.details && (
                <Collapse ghost style={{ marginTop: 12 }}>
                  <Panel 
                    header={
                      <Space>
                        <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                        <Text type="danger">查看详细错误信息</Text>
                      </Space>
                    } 
                    key="1"
                  >
                    <pre style={{ 
                      backgroundColor: '#f6f8fa', 
                      padding: 12, 
                      borderRadius: 4,
                      maxHeight: 300,
                      overflow: 'auto',
                      fontSize: '12px',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}>
                      {systemStatus.details}
                    </pre>
                  </Panel>
                </Collapse>
              )}
            </>
          }
          type={systemStatus.healthy ? (systemStatus.errorType === 'warning' ? "warning" : "success") : "error"}
          showIcon
          action={
            <Button size="small" onClick={loadData} loading={loading}>
              刷新
            </Button>
          }
        />
      </Card>

      {/* 统计信息 */}
      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card className="flat-card">
              <Statistic 
                title="信息库总数" 
                value={stats.total} 
                prefix={<DatabaseOutlined />} 
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="flat-card">
              <Statistic 
                title="RAGFlow同步" 
                value={stats.ragflowSynced} 
                suffix={`/ ${stats.total}`}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="flat-card">
              <Statistic 
                title="自动更新" 
                value={stats.autoUpdate} 
                suffix={`/ ${stats.total}`}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card className="flat-card">
              <Statistic 
                title="爬取中" 
                value={stats.crawling} 
                suffix={`/ ${stats.crawler}`}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      <Divider />

      {/* 快速入口 */}
      <div style={{ marginBottom: 16, marginTop: 24 }}>
        <Title level={4}>快速入口</Title>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => navigate('/repositories')}
          >
            <div style={{ textAlign: 'center' }}>
              <DatabaseOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
              <Title level={5}>信息库管理</Title>
              <Paragraph>查看和管理所有信息库</Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => navigate('/repositories/create')}
          >
            <div style={{ textAlign: 'center' }}>
              <CloudUploadOutlined style={{ fontSize: 48, color: '#52c41a', marginBottom: 16 }} />
              <Title level={5}>创建信息库</Title>
              <Paragraph>创建新的信息库，支持爬虫和上传</Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => navigate('/batch')}
          >
            <div style={{ textAlign: 'center' }}>
              <CloudSyncOutlined style={{ fontSize: 48, color: '#722ed1', marginBottom: 16 }} />
              <Title level={5}>批量操作</Title>
              <Paragraph>批量设置自动更新和同步到RAGFlow</Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => navigate('/global-settings')}
          >
            <div style={{ textAlign: 'center' }}>
              <SettingOutlined style={{ fontSize: 48, color: '#fa8c16', marginBottom: 16 }} />
              <Title level={5}>全局设置</Title>
              <Paragraph>配置爬虫、预处理和RAGFlow设置</Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => navigate('/error-logs')}
          >
            <div style={{ textAlign: 'center' }}>
              <BugOutlined style={{ fontSize: 48, color: '#f5222d', marginBottom: 16 }} />
              <Title level={5}>错误日志</Title>
              <Paragraph>查看系统错误日志</Paragraph>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card 
            className="flat-card repository-card"
            hoverable
            onClick={() => window.open('https://github.com/yourusername/truesight', '_blank')}
          >
            <div style={{ textAlign: 'center' }}>
              <FileTextOutlined style={{ fontSize: 48, color: '#13c2c2', marginBottom: 16 }} />
              <Title level={5}>帮助文档</Title>
              <Paragraph>查看TrueSight使用文档</Paragraph>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default HomePage;
