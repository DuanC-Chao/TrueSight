import React from 'react';
import { ConfigProvider, Layout, Menu, theme } from 'antd';
import { Routes, Route, Link } from 'react-router-dom';
import {
  HomeOutlined,
  DatabaseOutlined,
  SettingOutlined,
  BugOutlined,
  PlusOutlined,
  AppstoreOutlined
} from '@ant-design/icons';

// 导入页面组件
import HomePage from './pages/HomePage';
import RepositoryListPage from './pages/RepositoryListPage';
import RepositoryDetailPage from './pages/RepositoryDetailPage';
import RepositorySettingsPage from './pages/RepositorySettingsPage';
import CreateRepositoryPage from './pages/CreateRepositoryPage';
import GlobalSettingsPage from './pages/GlobalSettingsPage';
import BatchOperationPage from './pages/BatchOperationPage';
import ErrorLogPage from './pages/ErrorLogPage';

// 导入全局样式
import './styles/global.css';

const { Header, Content, Footer } = Layout;

const App = () => {
  // 状态和配置
  const [collapsed, setCollapsed] = React.useState(false);
  const [config, setConfig] = React.useState({});
  const [loading, setLoading] = React.useState(false);

  // 菜单项
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link to="/">首页</Link>,
    },
    {
      key: '/repositories',
      icon: <DatabaseOutlined />,
      label: <Link to="/repositories">信息库</Link>,
    },
    {
      key: '/repositories/create',
      icon: <PlusOutlined />,
      label: <Link to="/repositories/create">创建信息库</Link>,
    },
    {
      key: '/batch',
      icon: <AppstoreOutlined />,
      label: <Link to="/batch">批量操作</Link>,
    },
    {
      key: '/global-settings',
      icon: <SettingOutlined />,
      label: <Link to="/global-settings">全局设置</Link>,
    },
    {
      key: '/error-logs',
      icon: <BugOutlined />,
      label: <Link to="/error-logs">错误日志</Link>,
    },
  ];

  return (
    <Layout className="main-layout">
      <Header className="site-header">
        <div className="logo">
          <h1 style={{ margin: 0, color: '#1890ff' }}>TrueSight</h1>
        </div>
        <Menu
          theme="light"
          mode="horizontal"
          defaultSelectedKeys={['/']}
          items={menuItems}
          style={{ lineHeight: '64px' }}
        />
      </Header>
      <Content className="site-content">
        <div style={{ padding: '0 50px', maxWidth: 1200, margin: '0 auto' }}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/repositories" element={<RepositoryListPage />} />
            <Route path="/repositories/create" element={<CreateRepositoryPage />} />
            <Route path="/repositories/:id" element={<RepositoryDetailPage />} />
            <Route path="/repositories/:id/settings" element={<RepositorySettingsPage />} />
            <Route path="/batch" element={<BatchOperationPage />} />
            <Route path="/global-settings" element={<GlobalSettingsPage />} />
            <Route path="/error-logs" element={<ErrorLogPage />} />
          </Routes>
        </div>
      </Content>
      <Footer className="site-footer">
        TrueSight ©{new Date().getFullYear()} - 网页爬取、预处理与RAGFlow集成服务
      </Footer>
    </Layout>
  );
};

export default App;
