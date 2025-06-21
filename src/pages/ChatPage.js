import React, { useState, useRef, useEffect } from 'react';
import { FaPaperPlane, FaRobot, FaSpinner, FaChevronDown, FaChevronUp, FaHistory, FaTrash, FaPlus, FaCog, FaBars, FaTimes } from 'react-icons/fa';
import api, { 
  saveChatSession, 
  loadCurrentChatSession, 
  getChatSessions, 
  setCurrentChatSession, 
  deleteChatSession, 
  createNewChatSession,

} from '../utils/api';
import './ChatPage.css';

const ChatPage = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      content: '您好！我是您的AI助手。我可以幫您回答關於已上傳文檔的問題。請問有什麼我可以協助您的嗎？',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});
  const [showHistory, setShowHistory] = useState(false);
  const [chatSessions, setChatSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [showRagToggle, setShowRagToggle] = useState(false); // 控制 RAG 切換的顯示
  const [showSidebar, setShowSidebar] = useState(false); // 控制左側邊欄的顯示
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 載入當前會話
  useEffect(() => {
    loadCurrentSession();
  }, []);

  // 自動保存聊天記錄
  useEffect(() => {
    if (messages.length > 1) { // 排除初始歡迎消息
      saveCurrentSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const loadCurrentSession = async () => {
    try {
      const response = await loadCurrentChatSession();
      if (response.success && response.session && response.session.messages.length > 0) {
        // 轉換時間戳格式
        const loadedMessages = response.session.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        setMessages(loadedMessages);
        setCurrentSessionId(response.session.session_id);
      }
    } catch (error) {
      console.error('載入當前會話失敗:', error);
    }
  };

  const saveCurrentSession = async () => {
    try {
      // 轉換消息格式以便保存
      const messagesToSave = messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp.toISOString()
      }));
      
      const response = await saveChatSession(messagesToSave);
      if (response.success) {
        setCurrentSessionId(response.session_id);
      }
    } catch (error) {
      console.error('保存會話失敗:', error);
    }
  };

  const loadChatSessions = async () => {
    setIsLoadingHistory(true);
    try {
      const response = await getChatSessions();
      if (response.success) {
        setChatSessions(response.sessions);
      }
    } catch (error) {
      console.error('載入聊天記錄失敗:', error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleLoadSession = async (sessionId) => {
    try {
      const response = await setCurrentChatSession(sessionId);
      if (response.success) {
        await loadCurrentSession();
        setShowHistory(false);
      }
    } catch (error) {
      console.error('載入會話失敗:', error);
    }
  };

  const handleDeleteSession = async (sessionId, event) => {
    event.stopPropagation();
    if (window.confirm('確定要刪除這個會話嗎？')) {
      try {
        const response = await deleteChatSession(sessionId);
        if (response.success) {
          // 如果刪除的是當前會話，重置為初始狀態
          if (sessionId === currentSessionId) {
            setMessages([{
              id: 1,
              type: 'bot',
              content: '您好！我是您的AI助手。我可以幫您回答關於已上傳文檔的問題。請問有什麼我可以協助您的嗎？',
              timestamp: new Date()
            }]);
            setCurrentSessionId(null);
          }
          // 重新載入會話列表
          await loadChatSessions();
        }
      } catch (error) {
        console.error('刪除會話失敗:', error);
      }
    }
  };

  const handleNewSession = async () => {
    try {
      const response = await createNewChatSession();
      if (response.success) {
        setMessages([{
          id: 1,
          type: 'bot',
          content: '您好！我是您的AI助手。我可以幫您回答關於已上傳文檔的問題。請問有什麼我可以協助您的嗎？',
          timestamp: new Date()
        }]);
        setCurrentSessionId(response.session_id);
        setShowHistory(false);
      }
    } catch (error) {
      console.error('創建新會話失敗:', error);
    }
  };

  const toggleHistory = () => {
    console.log('Toggle history clicked, current state:', showHistory); // 調試信息
    if (!showHistory) {
      // 每次打開歷史面板時都重新載入會話列表
      loadChatSessions();
    }
    setShowHistory(!showHistory);
    console.log('New state will be:', !showHistory); // 調試信息
  };

  const toggleSources = (messageId) => {
    setExpandedSources(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputValue.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await api.post('/api/query', {
        question: userMessage.content,
        use_rag: useRag
      });

      const botMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: response.data.answer || '抱歉，我無法回答這個問題。',
        sources: response.data.sources || [],
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        content: '抱歉，發生了錯誤。請確保後端服務正在運行。',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('zh-TW', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatSessionTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="chat-page">
      {/* 左側邊欄 */}
      <div className={`chat-sidebar ${showSidebar ? 'sidebar-open' : ''}`}>
        <div className="sidebar-header">
            <button 
              className="new-chat-button"
              onClick={handleNewSession}
              title="新對話"
            >
              <FaPlus />
            <span>新對話</span>
            </button>
              <button 
            className="close-sidebar"
            onClick={() => setShowSidebar(false)}
            title="關閉側邊欄"
              >
            <FaTimes />
              </button>
            </div>
        <div className="sidebar-content">
          <div className="sidebar-section">
            <h3>聊天記錄</h3>
              {isLoadingHistory ? (
                <div className="history-loading">
                  <FaSpinner className="loading-spinner" />
                  <span>載入中...</span>
                </div>
              ) : chatSessions.length === 0 ? (
                <div className="no-history">
                  <p>暫無聊天記錄</p>
                </div>
              ) : (
                <div className="history-list">
                  {chatSessions.map((session) => (
                    <div 
                      key={session.session_id}
                      className={`history-item ${session.session_id === currentSessionId ? 'active' : ''}`}
                      onClick={() => handleLoadSession(session.session_id)}
                    >
                      <div className="history-item-content">
                        <div className="history-title">{session.title}</div>
                        <div className="history-meta">
                          <span className="history-time">
                            {formatSessionTime(session.last_updated)}
                          </span>
                          <span className="history-count">
                            {session.message_count} 條消息
                          </span>
                        </div>
                      </div>
                      <button 
                        className="delete-session"
                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                        title="刪除會話"
                      >
                        <FaTrash />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
      </div>

      {/* 固定的側邊欄切換按鈕 */}
      <button 
        className={`sidebar-toggle-fixed ${showSidebar ? 'sidebar-open' : ''}`}
        onClick={() => {
          setShowSidebar(!showSidebar);
          if (!showSidebar) {
            loadChatSessions();
          }
        }}
        title="切換側邊欄"
      >
        <FaBars />
      </button>

      {/* 主要聊天區域 */}
      <div className={`chat-container ${showSidebar ? 'sidebar-open' : ''}`}>
        <div className="chat-header">
          <div className="chat-title">
            <FaRobot className="chat-title-icon" />
            <h1>AI 助手對話</h1>
          </div>
          <div className="chat-subtitle">
            基於您的文檔知識庫進行智能問答
          </div>
        </div>
  

        <div className="chat-messages">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.type === 'user' ? 'message-user' : 'message-bot'}`}
            >
              <div className="message-avatar">
                {message.type === 'user' ? (
                  <img 
                    src="/avatar.png" 
                    alt="User Avatar" 
                    className="user-avatar-img"
                  />
                ) : (
                  <FaRobot size={20} />
                )}
              </div>
              <div className="message-content">
                <div className="message-text">
                  {message.content}
                </div>
                {message.sources && message.sources.length > 0 && (
                  <div className="message-sources">
                    <div 
                      className="sources-header"
                      onClick={() => toggleSources(message.id)}
                    >
                      <span className="sources-title">參考來源 ({message.sources.length})</span>
                      {expandedSources[message.id] ? (
                        <FaChevronUp className="sources-toggle" />
                      ) : (
                        <FaChevronDown className="sources-toggle" />
                      )}
                    </div>
                    {expandedSources[message.id] && (
                      <div className="sources-content">
                        {message.sources.map((source, index) => (
                          <div key={index} className="source-item">
                            <span className="source-name">{source.source_file}</span>
                            <span className="source-score">相似度: {((source.similarity || 0) * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <div className="message-time">
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message message-bot">
              <div className="message-avatar">
                <FaRobot size={20} />
              </div>
              <div className="message-content">
                <div className="message-loading">
                  <FaSpinner className="loading-spinner" size={16} />
                  <span>正在思考中...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        <div className={`chat-input-container ${showSidebar ? 'sidebar-open' : ''}`}>
          {/* 可折疊的 RAG 切換 */}
          {showRagToggle && (
          <div className="rag-toggle-container">
            <label className="rag-toggle-label">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => setUseRag(e.target.checked)}
                className="rag-toggle-checkbox"
              />
              <span className="rag-toggle-slider"></span>
              <span className="rag-toggle-text">
                {useRag ? '文檔檢索模式' : '直接對話模式'}
              </span>
            </label>
            <div className="rag-toggle-description">
              {useRag 
                ? '將從上傳的文檔中檢索相關資料來回答問題' 
                : '僅回答簡單交互問題（如打招呼、語言設定等）'
              }
            </div>
          </div>
          )}
          
          <div className="chat-input-wrapper">
            <button
              className="settings-button"
              onClick={() => setShowRagToggle(!showRagToggle)}
              title="切換設定"
            >
              <FaCog />
            </button>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="輸入您的問題..."
              className="chat-input"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="chat-send-button"
            >
              <FaPaperPlane size={18} />
            </button>
          </div>
          <div className="chat-input-hint">
            按 Enter 發送，Shift + Enter 換行
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage; 