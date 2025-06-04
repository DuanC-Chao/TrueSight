import React, { useState } from 'react';
import { Upload, Button, Card, Space, Alert, Typography, Divider } from 'antd';
import { UploadOutlined } from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

/**
 * 文件上传测试组件
 * 用于测试不同的accept属性设置，诊断Windows文件选择器问题
 */
const FileUploadTest = () => {
  const [testResults, setTestResults] = useState([]);

  const testConfigs = [
    {
      name: '只使用扩展名',
      accept: '.txt,.pdf,.html,.htm',
      description: '推荐的Windows兼容设置'
    },
    {
      name: '只使用MIME类型',
      accept: 'text/plain,application/pdf,text/html',
      description: '标准MIME类型设置'
    },
    {
      name: '混合设置（原始）',
      accept: '.txt,.pdf,.html,text/plain,application/pdf,text/html',
      description: '扩展名和MIME类型混合'
    },
    {
      name: '无限制',
      accept: '',
      description: '接受所有文件类型'
    },
    {
      name: 'PDF专用',
      accept: '.pdf',
      description: '只接受PDF文件'
    },
    {
      name: '文本文件专用',
      accept: '.txt,text/plain',
      description: '只接受文本文件'
    }
  ];

  const handleTestUpload = (configIndex, file) => {
    const config = testConfigs[configIndex];
    const result = {
      configName: config.name,
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      timestamp: new Date().toLocaleTimeString(),
      success: true
    };

    setTestResults(prev => [result, ...prev.slice(0, 9)]); // 保留最近10条记录
    
    console.log('测试结果:', result);
    return false; // 阻止实际上传
  };

  const clearResults = () => {
    setTestResults([]);
  };

  return (
    <div style={{ padding: '20px' }}>
      <Title level={3}>文件上传兼容性测试</Title>
      <Paragraph>
        此工具用于测试不同的 accept 属性设置在您的系统上的表现。
        <br />
        <strong>使用方法：</strong>点击下方不同配置的上传按钮，查看文件选择器是否正确显示文件。
      </Paragraph>

      <Alert 
        message="Windows系统特别说明" 
        description="如果您在Windows上遇到文件选择器只显示文件夹不显示文件的问题，请重点测试'只使用扩展名'配置。" 
        type="warning" 
        showIcon 
        style={{ marginBottom: '20px' }}
      />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        {testConfigs.map((config, index) => (
          <Card 
            key={index} 
            size="small" 
            title={config.name}
            style={{ 
              border: config.name === '只使用扩展名' ? '2px solid #52c41a' : '1px solid #d9d9d9'
            }}
          >
            <Text type="secondary" style={{ display: 'block', marginBottom: '8px' }}>
              {config.description}
            </Text>
            <Text code style={{ display: 'block', marginBottom: '12px', fontSize: '11px' }}>
              accept="{config.accept}"
            </Text>
            <Upload
              accept={config.accept}
              beforeUpload={(file) => handleTestUpload(index, file)}
              showUploadList={false}
            >
              <Button icon={<UploadOutlined />} size="small">
                测试选择文件
              </Button>
            </Upload>
          </Card>
        ))}
      </div>

      <Divider />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <Title level={4} style={{ margin: 0 }}>测试结果</Title>
        <Button onClick={clearResults} size="small">清空结果</Button>
      </div>

      {testResults.length === 0 ? (
        <Alert message="暂无测试结果" description="请点击上方按钮进行测试" type="info" />
      ) : (
        <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
          {testResults.map((result, index) => (
            <Card 
              key={index} 
              size="small" 
              style={{ marginBottom: '8px' }}
              bodyStyle={{ padding: '12px' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Space direction="vertical" size="small">
                  <Text strong>{result.configName}</Text>
                  <Text>文件: {result.fileName}</Text>
                  <Text type="secondary">
                    大小: {(result.fileSize / 1024).toFixed(1)} KB | 
                    类型: {result.fileType || '未知'} | 
                    时间: {result.timestamp}
                  </Text>
                </Space>
                <div style={{ 
                  width: '12px', 
                  height: '12px', 
                  borderRadius: '50%', 
                  backgroundColor: result.success ? '#52c41a' : '#ff4d4f' 
                }} />
              </div>
            </Card>
          ))}
        </div>
      )}

      <Divider />

      <Alert
        message="诊断建议"
        description={
          <div>
            <p><strong>如果文件选择器无法显示文件：</strong></p>
            <ul>
              <li>首先测试"无限制"配置，如果可以看到文件，说明是accept属性问题</li>
              <li>然后测试"只使用扩展名"配置，这通常是Windows系统的最佳选择</li>
              <li>避免使用混合的扩展名+MIME类型设置</li>
              <li>如果所有配置都无法显示文件，可能是浏览器或系统级别的问题</li>
            </ul>
            <p><strong>如果测试成功：</strong></p>
            <ul>
              <li>记住哪个配置在您的系统上工作最好</li>
              <li>我们已经将主要上传组件更新为使用"只使用扩展名"配置</li>
            </ul>
          </div>
        }
        type="info"
      />
    </div>
  );
};

export default FileUploadTest; 