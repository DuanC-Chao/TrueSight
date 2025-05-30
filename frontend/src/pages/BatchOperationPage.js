import React, { useState, useEffect } from 'react';
import { 
  Table, Typography, Button, Space, Checkbox, 
  message, Modal, Form, Select, Spin, Tag,
  Tooltip, Alert, Card, Divider
} from 'antd';
import { 
  SyncOutlined, 
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons';
import { 
  listRepositories, 
  batchSetAutoUpdate, 
  batchSetDirectImport,
  batchSyncRepositoriesWithRAGFlow
} from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;
const { confirm } = Modal;

/**
 * 批量操作页面
 * 
 * 支持对多个信息库进行批量操作，如设置自动更新、直接入库、同步到RAGFlow等
 */
const BatchOperationPage = () => {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [autoUpdateModalVisible, setAutoUpdateModalVisible] = useState(false);
  const [directImportModalVisible, setDirectImportModalVisible] = useState(false);
  const [autoUpdateForm] = Form.useForm();
  const [directImportForm] = Form.useForm();
  const [processing, setProcessing] = useState(false);

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

  // 表格列定义
  const columns = [
    {
      title: '信息库名称',
      dataIndex: 'name',
      key: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
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
      },
      filters: [
        { text: '完成', value: 'complete' },
        { text: '未完成', value: 'incomplete' },
        { text: '错误', value: 'error' },
      ],
      onFilter: (value, record) => record.status === value,
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      render: (source) => {
        switch (source) {
          case 'crawler':
            return <Tag color="blue">爬虫</Tag>;
          case 'upload':
            return <Tag color="cyan">上传</Tag>;
          default:
            return <Tag>未知</Tag>;
        }
      },
      filters: [
        { text: '爬虫', value: 'crawler' },
        { text: '上传', value: 'upload' },
      ],
      onFilter: (value, record) => record.source === value,
    },
    {
      title: '自动更新',
      dataIndex: 'auto_update',
      key: 'auto_update',
      render: (auto_update, record) => {
        if (!auto_update) return <Tag>手动</Tag>;
        
        let color, text;
        switch (record.update_frequency) {
          case 'daily':
            color = 'blue';
            text = '每日';
            break;
          case 'weekly':
            color = 'green';
            text = '每周';
            break;
          case 'monthly':
            color = 'purple';
            text = '每月';
            break;
          case 'yearly':
            color = 'magenta';
            text = '每年';
            break;
          default:
            color = 'default';
            text = '自动';
        }
        
        return <Tag color={color}>{text}</Tag>;
      },
      filters: [
        { text: '手动', value: false },
        { text: '自动', value: true },
      ],
      onFilter: (value, record) => record.auto_update === value,
    },
    {
      title: '直接入库',
      dataIndex: 'direct_import',
      key: 'direct_import',
      render: (direct_import) => (
        direct_import ? 
          <Tag color="orange">是</Tag> : 
          <Tag>否</Tag>
      ),
      filters: [
        { text: '是', value: true },
        { text: '否', value: false },
      ],
      onFilter: (value, record) => record.direct_import === value,
    },
    {
      title: 'RAGFlow同步',
      dataIndex: 'ragflow_synced',
      key: 'ragflow_synced',
      render: (synced) => (
        synced ? 
          <Tag color="success" icon={<CheckCircleOutlined />}>已同步</Tag> : 
          <Tag color="warning" icon={<SyncOutlined />}>未同步</Tag>
      ),
      filters: [
        { text: '已同步', value: true },
        { text: '未同步', value: false },
      ],
      onFilter: (value, record) => record.ragflow_synced === value,
    },
  ];

  // 表格行选择配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (selectedKeys) => {
      setSelectedRowKeys(selectedKeys);
    },
  };

  // 处理批量设置自动更新
  const handleBatchAutoUpdate = async (values) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个信息库');
      return;
    }

    setProcessing(true);
    try {
      const response = await batchSetAutoUpdate({
        repository_names: selectedRowKeys,
        auto_update: values.auto_update,
        update_frequency: values.auto_update ? values.update_frequency : null
      });

      if (response.success) {
        message.success(`已成功设置 ${selectedRowKeys.length} 个信息库的自动更新`);
        setAutoUpdateModalVisible(false);
        fetchRepositories();
      } else {
        message.error(`设置自动更新失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`设置自动更新失败: ${error.error || '未知错误'}`);
    } finally {
      setProcessing(false);
    }
  };

  // 处理批量设置直接入库
  const handleBatchDirectImport = async (values) => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个信息库');
      return;
    }

    setProcessing(true);
    try {
      const response = await batchSetDirectImport({
        repository_names: selectedRowKeys,
        direct_import: values.direct_import
      });

      if (response.success) {
        message.success(`已成功设置 ${selectedRowKeys.length} 个信息库的直接入库`);
        setDirectImportModalVisible(false);
        fetchRepositories();
      } else {
        message.error(`设置直接入库失败: ${response.error || '未知错误'}`);
      }
    } catch (error) {
      message.error(`设置直接入库失败: ${error.error || '未知错误'}`);
    } finally {
      setProcessing(false);
    }
  };

  // 处理批量同步到RAGFlow
  const handleBatchSync = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请至少选择一个信息库');
      return;
    }

    confirm({
      title: '确认同步',
      icon: <ExclamationCircleOutlined />,
      content: `确定要将选中的 ${selectedRowKeys.length} 个信息库同步到RAGFlow吗？`,
      onOk: async () => {
        setProcessing(true);
        try {
          const response = await batchSyncRepositoriesWithRAGFlow({
            repository_names: selectedRowKeys
          });

          if (response.success) {
            message.success(`已成功同步 ${selectedRowKeys.length} 个信息库到RAGFlow`);
            fetchRepositories();
          } else {
            message.error(`同步到RAGFlow失败: ${response.error || '未知错误'}`);
          }
        } catch (error) {
          message.error(`同步到RAGFlow失败: ${error.error || '未知错误'}`);
        } finally {
          setProcessing(false);
        }
      }
    });
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4}>批量操作</Title>
        <Space>
          <Button 
            icon={<SyncOutlined />} 
            onClick={fetchRepositories}
            disabled={loading || processing}
          >
            刷新
          </Button>
        </Space>
      </div>

      <Card className="flat-card" style={{ marginBottom: 16 }}>
        <Alert
          message="批量操作说明"
          description="在下方表格中选择需要批量操作的信息库，然后点击相应的操作按钮。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button 
              type="primary" 
              icon={<ClockCircleOutlined />}
              onClick={() => setAutoUpdateModalVisible(true)}
              disabled={selectedRowKeys.length === 0 || loading || processing}
            >
              设置自动更新
            </Button>
            <Button 
              icon={<CheckCircleOutlined />}
              onClick={() => setDirectImportModalVisible(true)}
              disabled={selectedRowKeys.length === 0 || loading || processing}
            >
              设置直接入库
            </Button>
            <Button 
              type="primary" 
              icon={<SyncOutlined />}
              onClick={handleBatchSync}
              disabled={selectedRowKeys.length === 0 || loading || processing}
              danger
            >
              同步到RAGFlow
            </Button>
          </Space>
        </div>

        <Divider />

        <div style={{ marginBottom: 8 }}>
          <Text>已选择 {selectedRowKeys.length} 个信息库</Text>
        </div>
      </Card>

      <Spin spinning={loading || processing}>
        <Table 
          rowSelection={rowSelection}
          columns={columns}
          dataSource={repositories}
          rowKey="name"
          pagination={{ pageSize: 10 }}
        />
      </Spin>

      {/* 自动更新设置模态框 */}
      <Modal
        title="设置自动更新"
        visible={autoUpdateModalVisible}
        onCancel={() => setAutoUpdateModalVisible(false)}
        footer={null}
        destroyOnClose
      >
        <Form
          form={autoUpdateForm}
          layout="vertical"
          onFinish={handleBatchAutoUpdate}
          initialValues={{ auto_update: true, update_frequency: 'weekly' }}
        >
          <Form.Item
            name="auto_update"
            valuePropName="checked"
            label="启用自动更新"
          >
            <Checkbox>启用自动更新</Checkbox>
          </Form.Item>

          <Form.Item
            name="update_frequency"
            label="更新频率"
            dependencies={['auto_update']}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!getFieldValue('auto_update') || value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('请选择更新频率'));
                },
              }),
            ]}
          >
            <Select disabled={!autoUpdateForm.getFieldValue('auto_update')}>
              <Option value="daily">每日 (每天 00:01)</Option>
              <Option value="weekly">每周 (每周一 00:01)</Option>
              <Option value="monthly">每月 (每月1日 00:01)</Option>
              <Option value="yearly">每年 (每年1月1日 00:01)</Option>
            </Select>
          </Form.Item>

          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setAutoUpdateModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={processing}>
                确认
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>

      {/* 直接入库设置模态框 */}
      <Modal
        title="设置直接入库"
        visible={directImportModalVisible}
        onCancel={() => setDirectImportModalVisible(false)}
        footer={null}
        destroyOnClose
      >
        <Alert
          message="直接入库说明"
          description="启用直接入库后，文件将跳过预处理（总结和问答对生成）直接同步到RAGFlow。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form
          form={directImportForm}
          layout="vertical"
          onFinish={handleBatchDirectImport}
          initialValues={{ direct_import: false }}
        >
          <Form.Item
            name="direct_import"
            valuePropName="checked"
            label="启用直接入库"
          >
            <Checkbox>启用直接入库</Checkbox>
          </Form.Item>

          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setDirectImportModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit" loading={processing}>
                确认
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default BatchOperationPage;
