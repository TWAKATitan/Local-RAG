import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaComments, FaUpload, FaRobot, FaChevronUp, FaChevronDown } from 'react-icons/fa';
import './Navigation.css';

const Navigation = ({ isCollapsed, onToggleCollapse }) => {
  const location = useLocation();

  const navItems = [
    {
      path: '/',
      label: '聊天',
      icon: FaComments,
      description: '與AI助手對話'
    },
    {
      path: '/upload',
      label: '上傳文檔',
      icon: FaUpload,
      description: '管理知識庫'
    }
  ];

  const toggleCollapse = () => {
    onToggleCollapse(!isCollapsed);
  };

  return (
    <>
      <nav className={`navigation ${isCollapsed ? 'navigation-collapsed' : ''}`}>
        <div className="nav-container">
          <div className="nav-brand">
            <FaRobot className="nav-brand-icon" />
            <span className="nav-brand-text">RAG 助手</span>
          </div>
          
          <div className="nav-links">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`nav-link ${isActive ? 'nav-link-active' : ''}`}
                  title={item.description}
                >
                  <Icon size={18} />
                  <span className="nav-link-text">{item.label}</span>
                </Link>
              );
            })}
          </div>
          
          <div className="nav-status">
            <div className="status-indicator">
              <div className="status-dot status-online"></div>
              <span className="status-text">系統運行中</span>
            </div>
          </div>
        </div>
      </nav>
      
      <button 
        className="nav-collapse-toggle"
        onClick={toggleCollapse}
        title={isCollapsed ? '展開導航欄' : '收縮導航欄'}
      >
        {isCollapsed ? <FaChevronDown size={16} /> : <FaChevronUp size={16} />}
      </button>
    </>
  );
};

export default Navigation; 