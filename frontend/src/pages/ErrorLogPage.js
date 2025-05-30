import React, { useState, useEffect } from 'react';
import { 
  Card, Table, Typography, Button, Tag, Space, 
  Tooltip, Modal, Input, DatePicker, Spin, Empty, Alert, Divider
} from 'antd';
import { 
  BugOutlined, 
  ReloadOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { getErrorLogs, clearErrorLog } from '../services/api';
import moment from 'moment';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { Search } = Input;

/**
 * 错误日志页面
 * 
 * 显示系统错误日志，支持筛选、搜索和清除
 */
const ErrorLogPage = () => {
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [dateRange, setDateRange] = useState(null);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  // 获取错误日志
  const fetchErrorLogs = async () => {
    setLoading(true);
    try {
      const response = await getErrorLogs();
      if (response.success) {
        const logsWithKeys = response.logs.map((log, index) => ({
          ...log,
          key: index.toString()
        }));
        setLogs(logsWithKeys);
        setFilteredLogs(logsWithKeys);
      } else {
        console.error('获取错误日志失败:', response.error);
      }
    } catch (error) {
      console.error('获取错误日志失败:', error);
    }
    setLoading(false);
  };

  // 清除错误日志
  const handleClearLog = async (logId) => {
    try {
      const response = await clearErrorLog(logId);
      if (response.success) {
        fetchErrorLogs();
        setDeleteModalVisible(false);
      } else {
        console.error('清除错误日志失败:', response.error);
      }
    } catch (error) {
      console.error('清除错误日志失败:', error);
    }
  };

  // 筛选日志
  const filterLogs = () => {
    let filtered = [...logs];
    
    // 按搜索文本筛选
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      filtered = filtered.filter(log => 
        (log.task_type && log.task_type.toLowerCase().includes(searchLower)) ||
        (log.error_message && log.error_message.toLowerCase().includes(searchLower)) ||
        (log.repository_name && log.repository_name.toLowerCase().includes(searchLower))
      );
    }
    
    // 按日期范围筛选
    if (dateRange && dateRange[0] && dateRange[1]) {
      const startDate = dateRange[0].startOf('day');
      const endDate = dateRange[1].endOf('day');
      
      filtered = filtered.filter(log => {
        const logDate = moment(log.timestamp);
        return logDate.isBetween(startDate, endDate, null, '[]');
      });
    }
    
    setFilteredLogs(filtered);
  };

  // 初始加载
  useEffect(() => {
    fetchErrorLogs();
  }, []);

  // 筛选变化时更新
  useEffect(() => {
    filterLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText, dateRange, logs]);

  // 表格列定义
  const columns = [
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: text => moment(text).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a, b) => moment(a.timestamp).unix() - moment(b.timestamp).unix(),
      defaultSortOrder: 'descend'
    },
    {
      title: '任务类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: text => (
        <Tag color={
          text === 'crawler' ? 'blue' : 
          text === 'processor' ? 'green' :
          text === 'ragflow' ? 'purple' :
          text === 'scheduler' ? 'orange' : 'default'
        }>
          {text || '未知'}
        </Tag>
      ),
      filters: [
        { text: '爬虫', value: 'crawler' },
        { text: '预处理', value: 'processor' },
        { text: 'RAGFlow', value: 'ragflow' },
        { text: '调度器', value: 'scheduler' },
        { text: '其他', value: 'other' }
      ],
      onFilter: (value, record) => {
        if (value === 'other') {
          return !record.task_type || !['crawler', 'processor', 'ragflow', 'scheduler'].includes(record.task_type);
        }
        return record.task_type === value;
      }
    },
    {
      title: '信息库',
      dataIndex: 'repository_name',
      key: 'repository_name',
      render: text => text || '-'
    },
    {
      title: '错误信息',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: text => (
        <Tooltip title="点击查看完整错误信息">
          <Text 
            style={{ cursor: 'pointer' }} 
            ellipsis={{ tooltip: false }}
            onClick={() => {
              setSelectedLog(logs.find(log => log.error_message === text));
              setDetailModalVisible(true);
            }}
          >
            {text || '无错误信息'}
          </Text>
        </Tooltip>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button 
            type="text" 
            icon={<DeleteOutlined />} 
            onClick={() => {
              setSelectedLog(record);
              setDeleteModalVisible(true);
            }}
            danger
          />
        </Space>
      )
    }
  ];

  return (
    <div className="fade-in">
      <div style={{ marginBottom: 16 }}>
        <Title level={4}>
          <BugOutlined /> 错误日志
        </Title>
        <Paragraph>查看和管理系统错误日志</Paragraph>
      </div>

      <Card className="flat-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
          <Space>
            <Search
              placeholder="搜索错误信息或任务类型"
              allowClear
              onSearch={value => setSearchText(value)}
              style={{ width: 250 }}
            />
            <RangePicker 
              onChange={value => setDateRange(value)}
              placeholder={['开始日期', '结束日期']}
            />
          </Space>
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchErrorLogs}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        </div>

        <Spin spinning={loading}>
          {filteredLogs.length > 0 ? (
            <Table 
              columns={columns} 
              dataSource={filteredLogs}
              pagination={{ 
                pageSize: 10,
                showSizeChanger: true,
                showTotal: total => `共 ${total} 条记录`
              }}
            />
          ) : (
            <Empty 
              description="暂无错误日志" 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          )}
        </Spin>
      </Card>

      <Alert
        message="提示"
        description="错误日志会自动记录系统运行过程中遇到的错误，包括爬虫、预处理、RAGFlow集成和调度任务等。您可以通过查看错误日志来诊断和解决问题。"
        type="info"
        showIcon
      />

      {/* 删除确认对话框 */}
      <Modal
        title="确认删除"
        open={deleteModalVisible}
        onOk={() => handleClearLog(selectedLog?.id)}
        onCancel={() => setDeleteModalVisible(false)}
        okText="删除"
        cancelText="取消"
      >
        <p>确定要删除这条错误日志吗？此操作不可恢复。</p>
      </Modal>

      {/* 错误详情对话框 */}
      <Modal
        title="错误详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {selectedLog && (
          <div>
            <p><strong>时间：</strong> {moment(selectedLog.timestamp).format('YYYY-MM-DD HH:mm:ss')}</p>
            <p><strong>任务类型：</strong> {selectedLog.task_type || '未知'}</p>
            <p><strong>信息库：</strong> {selectedLog.repository_name || '-'}</p>
            <Divider />
            <p><strong>错误信息：</strong></p>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: 16, 
              borderRadius: 4,
              maxHeight: 300,
              overflow: 'auto'
            }}>
              {selectedLog.error_message || '无错误信息'}
            </pre>
            {selectedLog.stack_trace && (
              <>
                <p><strong>堆栈跟踪：</strong></p>
                <pre style={{ 
                  backgroundColor: '#f5f5f5', 
                  padding: 16, 
                  borderRadius: 4,
                  maxHeight: 300,
                  overflow: 'auto'
                }}>
                  {selectedLog.stack_trace}
                </pre>
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default ErrorLogPage;
