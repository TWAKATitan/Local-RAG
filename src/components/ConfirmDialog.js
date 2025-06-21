import React from 'react';
import { FaExclamationTriangle, FaTimes, FaTrash, FaCheck } from 'react-icons/fa';
import './ConfirmDialog.css';

const ConfirmDialog = ({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  details = [], 
  type = 'warning',
  confirmText = '確認',
  cancelText = '取消',
  isLoading = false 
}) => {
  if (!isOpen) return null;

  const getIcon = () => {
    switch (type) {
      case 'danger':
        return <FaTrash className="dialog-icon danger" />;
      case 'warning':
        return <FaExclamationTriangle className="dialog-icon warning" />;
      default:
        return <FaExclamationTriangle className="dialog-icon warning" />;
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="confirm-dialog-overlay" onClick={handleBackdropClick}>
      <div className="confirm-dialog">
        <div className="dialog-header">
          <div className="dialog-title-section">
            {getIcon()}
            <h3 className="dialog-title">{title}</h3>
          </div>
          <button 
            className="dialog-close-btn"
            onClick={onClose}
            disabled={isLoading}
          >
            <FaTimes />
          </button>
        </div>
        
        <div className="dialog-content">
          <p className="dialog-message">{message}</p>
          
          {details.length > 0 && (
            <div className="dialog-details">
              <p className="details-title">此操作將會：</p>
              <ul className="details-list">
                {details.map((detail, index) => (
                  <li key={index} className="detail-item">
                    {detail}
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          <div className="dialog-warning">
            <FaExclamationTriangle className="warning-icon" />
            <span>此操作無法撤銷！</span>
          </div>
        </div>
        
        <div className="dialog-actions">
          <button 
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button 
            className={`btn btn-${type === 'danger' ? 'danger' : 'primary'}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <div className="btn-spinner" />
                處理中...
              </>
            ) : (
              <>
                <FaCheck />
                {confirmText}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog; 