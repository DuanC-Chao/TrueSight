import React, { useState, useEffect } from 'react';
import { 
  Card, Row, Col, Typography, Spin, Empty, Button, 
  Tag, Space, Tooltip, Modal, Input, message, Pagination
} from 'antd';
import { 
  DatabaseOutlined, 
  CloudUploadOutlined, 
  SettingOutlined, 
  DeleteOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { listRepositories, deleteRepository, syncRepositoryWithRAGFlow } from '../services/api';

const { Title, Text } = Typography;
const { Search } = Input;
const { confirm } = Modal;

/**
 * 信息库列表页面
 * 
 * 展示所有信息库，支持搜索、筛选、分页等功能
 */
const RepositoryListPage = () => {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(12);
  const navigate = useNavigate();

  // 获取信息库列表
  const fetchRepositories = async () => {
    setLoading(true);
    try {
      const response = await listRepositories();
      if (response.success) {
        setRepositories(response.repositories || []);
      } else {
        message.error('获取信息库列表失败');
      }
    } catch (error) {
      message.error(`获取信息库列表失败: ${error.error || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  // 处理删除信息库
  const handleDelete = (name) => {
    confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除信息库 "${name}" 吗？此操作不可恢复。`,
      okText: '确认',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await deleteRepository(name);
          if (response.success) {
            message.success(`信息库 "${name}" 已删除`);
            fetchRepositories();
          } else {
            message.error(`删除信息库失败: ${response.error || '未知错误'}`);
          }
        } catch (error) {
          message.error(`删除信息库失败: ${error.error || '未知错误'}`);
        }
      }
    });
  };

  // 处理同步到RAGFlow
  const handleSync = async (name) => {
    try {
      const response = await syncRepositoryWithRAGFlow(name);
      if (response.success) {
        message.success(`信息库 "${name}" 已同步到RAGFlow`);
        fetchRepositories();
      } else {
        // 增强错误信息展示，显示详细错误原因
        const errorMsg = response.result?.error || response.error || '未知错误';
        message.error(`同步到RAGFlow失败: ${errorMsg}`);
      }
    } catch (error) {
      // 增强错误信息展示，确保显示完整的错误信息
      const errorMsg = error.error || '未知错误';
      message.error(`同步到RAGFlow失败: ${errorMsg}`);
    }
  };

  // 获取状态标签
  const getStatusTag = (status) => {
    switch (status) {
      case 'complete':
        return <Tag color="success">完成</Tag>;
      case 'incomplete':
        return <Tag color="warning">未完成</Tag>;
      case 'error':
        return <Tag color="error">错误</Tag>;
      default:
        return <Tag>未知</Tag>;
    }
  };

  // 获取自动更新标签
  const getAutoUpdateTag = (repository) => {
    if (!repository.auto_update) return null;
    
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
    
    return (
      <Tooltip title={`上次更新: ${repository.last_auto_update || '从未'}`}>
        <Tag color={color} icon={<ClockCircleOutlined />}>{text}</Tag>
      </Tooltip>
    );
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

  // 过滤信息库
  const filteredRepositories = repositories.filter(repo => 
    repo.name.toLowerCase().includes(searchText.toLowerCase())
  );

  // 分页处理
  const paginatedRepositories = filteredRepositories.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>信息库列表</Title>
        <Space>
          <Button 
            type="primary" 
            icon={<CloudUploadOutlined />}
            onClick={() => navigate('/repositories/create')}
          >
            创建信息库
          </Button>
          <Search
            placeholder="搜索信息库"
            allowClear
            style={{ width: 200 }}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
          />
        </Space>
      </div>

      <Spin spinning={loading}>
        {paginatedRepositories.length > 0 ? (
          <Row gutter={[16, 16]}>
            {paginatedRepositories.map(repository => (
              <Col xs={24} sm={12} md={8} lg={6} key={repository.name}>
                <Card 
                  className={`flat-card ${repository.auto_update ? `update-${repository.update_frequency || 'default'}` : ''}`}
                  hoverable
                  actions={[
                    <Tooltip title="查看详情">
                      <Button 
                        type="text" 
                        icon={<DatabaseOutlined />} 
                        onClick={() => navigate(`/repositories/${repository.name}`)}
                      />
                    </Tooltip>,
                    <Tooltip title="同步到RAGFlow">
                      <Button 
                        type="text" 
                        icon={<SyncOutlined />} 
                        onClick={() => handleSync(repository.name)}
                      />
                    </Tooltip>,
                    <Tooltip title="设置">
                      <Button 
                        type="text" 
                        icon={<SettingOutlined />} 
                        onClick={() => navigate(`/repositories/${repository.name}/settings`)}
                      />
                    </Tooltip>,
                    <Tooltip title="删除">
                      <Button 
                        type="text" 
                        danger 
                        icon={<DeleteOutlined />} 
                        onClick={() => handleDelete(repository.name)}
                      />
                    </Tooltip>
                  ]}
                >
                  <div style={{ marginBottom: 12 }}>
                    <Text strong style={{ fontSize: 16 }}>{repository.name}</Text>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <Space>
                      {getStatusTag(repository.status)}
                      {getSourceTag(repository.source)}
                      {getAutoUpdateTag(repository)}
                    </Space>
                  </div>
                  <div>
                    <Text type="secondary">
                      {`JinaEmbedding: ${repository.token_count_jina ? repository.token_count_jina.toLocaleString() : '未计算'}`}
                    </Text>
                    <br />
                    <Text type="secondary">
                      {`GPT4o: ${repository.token_count_gpt4o ? repository.token_count_gpt4o.toLocaleString() : '未计算'}`}
                    </Text>
                    <br />
                    <Text type="secondary">
                      {`Deepseek: ${repository.token_count_deepseek ? repository.token_count_deepseek.toLocaleString() : '未计算'}`}
                    </Text>
                  </div>
                  {repository.direct_import && (
                    <div style={{ marginTop: 8 }}>
                      <Tag color="orange">直接入库</Tag>
                    </div>
                  )}
                </Card>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty 
            description={searchText ? "没有找到匹配的信息库" : "暂无信息库"} 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          >
            <Button 
              type="primary" 
              onClick={() => navigate('/repositories/create')}
            >
              创建信息库
            </Button>
          </Empty>
        )}

        {filteredRepositories.length > pageSize && (
          <div style={{ marginTop: 16, textAlign: 'right' }}>
            <Pagination
              current={currentPage}
              pageSize={pageSize}
              total={filteredRepositories.length}
              onChange={setCurrentPage}
              showSizeChanger
              onShowSizeChange={(current, size) => {
                setCurrentPage(1);
                setPageSize(size);
              }}
              pageSizeOptions={['12', '24', '36', '48']}
            />
          </div>
        )}
      </Spin>
    </div>
  );
};

export default RepositoryListPage;
