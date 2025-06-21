import React, { useState, useCallback, useEffect } from 'react';
import { FaUpload, FaFile, FaCheckCircle, FaTimesCircle, FaClock, FaTrash, FaFileAlt, FaExclamationTriangle, FaTools } from 'react-icons/fa';
import api, { 
  deleteDocument, 
  cleanupOrphanedData, 
  checkDataConsistency,
  createUploadState,
  getUploadState,
  updateUploadState,
  deleteUploadState
} from '../utils/api';
import ConfirmDialog from '../components/ConfirmDialog';
import './UploadPage.css';

const UploadPage = () => {
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [existingDocuments, setExistingDocuments] = useState([]);
  const [stateId, setStateId] = useState(null);
  const [stateError, setStateError] = useState(null);
  const [confirmDialog, setConfirmDialog] = useState({
    isOpen: false,
    title: '',
    message: '',
    details: [],
    type: 'warning',
    onConfirm: null,
    isLoading: false
  });
  const [maintenanceStatus, setMaintenanceStatus] = useState({
    isChecking: false,
    isCleaning: false,
    lastCheck: null,
    issues: []
  });

  // 初始化安全上傳狀態
  useEffect(() => {
    initializeSecureUploadState();
    loadExistingDocuments();
    
    // 移除組件卸載時的狀態清理，讓文件能在後台繼續處理
    // 只在用戶明確關閉瀏覽器或標籤頁時才清理
    const handleBeforeUnload = (e) => {
      // 如果有處理中的文件，提醒用戶
      const processingFiles = files.filter(f => f.status === 'processing' || f.status === 'pending');
      if (processingFiles.length > 0) {
        e.preventDefault();
        e.returnValue = '您有文件正在處理中，關閉頁面可能會中斷處理。';
        return '您有文件正在處理中，關閉頁面可能會中斷處理。';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      // 不再清理上傳狀態，讓文件能在後台繼續處理
    };
  }, [files]);

  // 定期保存上傳狀態
  useEffect(() => {
    if (stateId && files.length > 0) {
      const saveTimer = setTimeout(() => {
        saveUploadState();
      }, 1000); // 1秒後保存狀態

      return () => clearTimeout(saveTimer);
    }
  }, [files, stateId]);

  // 自動開始處理等待中的文件
  useEffect(() => {
    const pendingFiles = files.filter(f => f.status === 'pending' && f.file);
    if (pendingFiles.length > 0 && !isProcessing) {
      console.log(`發現 ${pendingFiles.length} 個等待處理的文件，自動開始處理`);
      processFiles();
    }
  }, [files, isProcessing]);

  const initializeSecureUploadState = async () => {
    try {
      // 先檢查是否有現有的狀態ID（使用一個簡單的內存存儲方案）
      const existingStateId = window.uploadStateId;
      
      if (existingStateId) {
        console.log('嘗試恢復現有上傳狀態:', existingStateId.substring(0, 8) + '...');
        
        // 嘗試獲取現有狀態
        try {
          const response = await getUploadState(existingStateId);
          if (response.success) {
            setStateId(existingStateId);
            setStateError(null);
            console.log('成功恢復現有上傳狀態');
            
            // 恢復文件狀態
            if (response.files && response.files.length > 0) {
              const activeFiles = response.files.filter(file => 
                file.status === 'pending' || file.status === 'processing' || file.status === 'error'
              ).map(file => ({
                ...file,
                // 恢復的文件沒有實際File對象，但保留所有其他信息
                file: null,
                // 確保有處理步驟信息
                processingSteps: file.processingSteps || [
                  { name: '文件驗證', status: 'pending' },
                  { name: '內容提取', status: 'pending' },
                  { name: '文本分塊', status: 'pending' },
                  { name: '向量化', status: 'pending' },
                  { name: '存儲完成', status: 'pending' }
                ],
                currentStep: file.currentStep || 0
              }));
              
              if (activeFiles.length > 0) {
                console.log(`恢復 ${activeFiles.length} 個處理中的文件`);
                setFiles(activeFiles);
                
                // 檢查是否有需要標記為錯誤的文件（沒有file對象的pending文件）
                const invalidFiles = activeFiles.filter(f => f.status === 'pending' && !f.file);
                if (invalidFiles.length > 0) {
                  console.log(`發現 ${invalidFiles.length} 個需要重新選擇的文件`);
                  setTimeout(() => {
                    setFiles(prev => prev.map(f => {
                      if (f.status === 'pending' && !f.file) {
                        return {
                          ...f,
                          status: 'error',
                          error: '文件對象已失效，頁面切換後需要重新選擇此文件才能處理。'
                        };
                      }
                      return f;
                    }));
                  }, 1000);
                }
              }
            }
            return; // 成功恢復，直接返回
          }
        } catch (error) {
          console.log('現有狀態無效，將創建新狀態');
        }
      }
      
      // 創建新的上傳狀態
      console.log('正在創建新的安全上傳狀態...');
      const response = await createUploadState();
      
      if (response.success) {
        setStateId(response.state_id);
        setStateError(null);
        
        // 保存狀態ID到內存中
        window.uploadStateId = response.state_id;
        
        console.log('安全上傳狀態創建成功:', response.state_id.substring(0, 8) + '...');
      } else {
        throw new Error(response.message || '創建上傳狀態失敗');
      }
    } catch (error) {
      console.error('初始化安全上傳狀態失敗:', error);
      setStateError('無法創建安全上傳狀態，某些功能可能不可用');
    }
  };

  const saveUploadState = async () => {
    if (!stateId) return;
    
    try {
      // 只保存待處理和處理中的文件，並確保包含所有必要信息
      const filesToSave = files.filter(file => 
        file.status === 'pending' || file.status === 'processing' || file.status === 'error'
      ).map(file => ({
        id: file.id,
        name: file.name,
        size: file.size,
        status: file.status,
        progress: file.progress || 0,
        error: file.error,
        result: file.result,
        currentStep: file.currentStep,
        processingSteps: file.processingSteps,
        // 不保存實際的File對象，只保存基本信息
        fileInfo: {
          name: file.name,
          size: file.size,
          type: file.file?.type || 'application/pdf',
          lastModified: file.file?.lastModified || Date.now()
        }
      }));

      if (filesToSave.length > 0) {
        await updateUploadState(stateId, filesToSave);
        console.log(`上傳狀態已保存: ${filesToSave.length} 個文件`);
      } else {
        // 如果沒有需要保存的文件，清空狀態
        await updateUploadState(stateId, []);
        console.log('上傳狀態已清空（無處理中文件）');
      }
    } catch (error) {
      console.error('保存上傳狀態失敗:', error);
      // 保存失敗不影響正常使用
    }
  };

  const loadExistingDocuments = async () => {
    try {
      const response = await api.get('/api/documents');
      if (response.data && response.data.documents) {
        const existingDocs = response.data.documents.map(doc => ({
          id: `existing_${doc.filename}`,
          name: doc.filename,
          size: doc.character_count || 0,
          status: 'completed',
          progress: 100,
          result: {
            processing_time: doc.processing_time || 0,
            chunks_created: doc.chunk_count || 0,
            characters_extracted: doc.character_count || 0,
            pages_processed: doc.page_count || 0,
            storage_status: 'permanent'
          },
          isExisting: true,
          processed_at: doc.processed_at
        }));
        setExistingDocuments(existingDocs);
      }
    } catch (error) {
      console.error('Failed to load existing documents:', error);
    }
  };

  const cleanupUploadState = async () => {
    if (!stateId) return;
    
    try {
      await deleteUploadState(stateId);
      
      // 清理內存中的狀態ID
      if (window.uploadStateId === stateId) {
        delete window.uploadStateId;
      }
      
      // 重置本地狀態
      setStateId(null);
      setFiles([]);
      
      console.log('安全上傳狀態已清理');
      
      // 重新初始化
      setTimeout(() => {
        initializeSecureUploadState();
      }, 500);
    } catch (error) {
      console.error('清理上傳狀態失敗:', error);
    }
  };

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdfFiles = droppedFiles.filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length !== droppedFiles.length) {
      alert('只支持PDF文件格式');
    }
    
    addFiles(pdfFiles);
  }, []);

  const handleFileInput = (e) => {
    const selectedFiles = Array.from(e.target.files);
    addFiles(selectedFiles);
  };

  const addFiles = (newFiles) => {
    const fileObjects = newFiles.map(file => ({
      id: Date.now() + Math.random(),
      file, // 保留實際的File對象用於上傳
      name: file.name,
      size: file.size,
      status: 'pending', // pending, processing, completed, error
      progress: 0,
      error: null,
      result: null,
      currentStep: 0,
      processingSteps: [
        { name: '文件驗證', status: 'pending' },
        { name: '內容提取', status: 'pending' },
        { name: '文本分塊', status: 'pending' },
        { name: '向量化', status: 'pending' },
        { name: '存儲完成', status: 'pending' }
      ],
      // 保存文件基本信息
      fileInfo: {
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified
      }
    }));
    
    setFiles(prev => [...prev, ...fileObjects]);
  };

  const removeFile = (fileId) => {
    // 如果是已存在的文檔，從服務器刪除
    if (fileId.startsWith('existing_')) {
      const filename = fileId.replace('existing_', '');
      const fileToDelete = existingDocuments.find(file => file.id === fileId);
      
      // 顯示確認對話框
      setConfirmDialog({
        isOpen: true,
        title: '刪除文檔',
        message: `確定要刪除文檔 "${fileToDelete?.name || filename}" 嗎？`,
        details: [
          '從向量數據庫中移除所有相關數據',
          '刪除原始PDF文件',
          '刪除processed處理文件',
          '刪除摘要文件（如果存在）',
          '清除系統記錄'
        ],
        type: 'danger',
        confirmText: '刪除',
        onConfirm: () => handleDeleteExistingDocument(fileId),
        isLoading: false
      });
    } else {
      // 新上傳的文件，顯示簡單確認對話框
      const fileToDelete = files.find(file => file.id === fileId);
      
      setConfirmDialog({
        isOpen: true,
        title: '移除文件',
        message: `確定要移除文件 "${fileToDelete?.name || '未知文件'}" 嗎？`,
        details: [],
        type: 'warning',
        confirmText: '移除',
        onConfirm: () => {
          setFiles(prev => prev.filter(file => file.id !== fileId));
          closeConfirmDialog();
        },
        isLoading: false
      });
    }
  };

  const handleDeleteExistingDocument = async (fileId, force = false) => {
    const filename = fileId.replace('existing_', '');
    
    // 設置加載狀態
    setConfirmDialog(prev => ({ ...prev, isLoading: true }));
    
    // 設置刪除狀態
    setExistingDocuments(prev => prev.map(file => 
      file.id === fileId ? { ...file, isDeleting: true } : file
    ));
    
    try {
      const response = await deleteDocument(filename, force);
      
      // 從列表中移除
      setExistingDocuments(prev => prev.filter(file => file.id !== fileId));
      
      // 關閉對話框
      closeConfirmDialog();
      
      // 顯示成功消息
      if (response.removed_items) {
        const removedItems = response.removed_items.join('、');
        setTimeout(() => {
          alert(`文檔刪除成功！\n已移除：${removedItems}`);
        }, 100);
      }
      
    } catch (error) {
      console.error('Failed to delete existing document:', error);
      
      // 移除刪除狀態
      setExistingDocuments(prev => prev.map(file => 
        file.id === fileId ? { ...file, isDeleting: false } : file
      ));
      
      // 檢查是否需要強制刪除
      const errorMessage = error.response?.data?.detail || error.message || '未知錯誤';
      
      if (!force && errorMessage.includes('not found in system records')) {
        // 提供強制刪除選項
        setConfirmDialog(prev => ({
          ...prev,
          isLoading: false,
          title: '文檔記錄不存在',
          message: `文檔 "${filename}" 在系統記錄中不存在，但可能仍有殘留數據。是否要強制刪除？`,
          details: [
            '強制刪除會嘗試清理所有相關數據',
            '包括向量數據庫中的孤立數據',
            '這個操作不可逆轉'
          ],
          type: 'warning',
          confirmText: '強制刪除',
          onConfirm: () => handleDeleteExistingDocument(fileId, true)
        }));
      } else {
        // 移除加載狀態並顯示錯誤
        setConfirmDialog(prev => ({ ...prev, isLoading: false }));
        setTimeout(() => {
          alert(`刪除文檔失敗：${errorMessage}\n\n請稍後重試或聯繫管理員。`);
        }, 100);
      }
    }
  };

  const closeConfirmDialog = () => {
    setConfirmDialog({
      isOpen: false,
      title: '',
      message: '',
      details: [],
      type: 'warning',
      onConfirm: null,
      isLoading: false
    });
  };

  // 維護功能
  const handleCheckConsistency = async () => {
    setMaintenanceStatus(prev => ({ ...prev, isChecking: true }));
    
    try {
      const response = await checkDataConsistency();
      
      setMaintenanceStatus(prev => ({
        ...prev,
        isChecking: false,
        lastCheck: new Date(),
        issues: response.issues || []
      }));
      
      if (response.consistent) {
        alert('數據一致性檢查完成：所有數據一致！');
      } else {
        const issueCount = response.issue_count || 0;
        const message = `發現 ${issueCount} 個數據一致性問題：\n\n` +
          response.issues.map(issue => `• ${issue.description}: ${issue.count} 個文件`).join('\n') +
          '\n\n建議運行清理功能來修復這些問題。';
        
        if (window.confirm(message + '\n\n是否立即運行清理功能？')) {
          handleCleanupOrphaned();
        }
      }
      
    } catch (error) {
      console.error('數據一致性檢查失敗:', error);
      setMaintenanceStatus(prev => ({ ...prev, isChecking: false }));
      alert('數據一致性檢查失敗：' + (error.message || '未知錯誤'));
    }
  };

  const handleCleanupOrphaned = async () => {
    setMaintenanceStatus(prev => ({ ...prev, isCleaning: true }));
    
    try {
      const response = await cleanupOrphanedData();
      
      setMaintenanceStatus(prev => ({ ...prev, isCleaning: false }));
      
      if (response.success) {
        const cleanedCount = response.cleaned_count || 0;
        const orphanedCount = response.orphaned_files?.length || 0;
        
        let message = `清理完成！\n\n`;
        message += `發現孤立文件：${orphanedCount} 個\n`;
        message += `成功清理：${cleanedCount} 個\n`;
        
        if (response.errors && response.errors.length > 0) {
          message += `清理失敗：${response.errors.length} 個\n\n`;
          message += '失敗詳情：\n' + response.errors.join('\n');
        }
        
        alert(message);
        
        // 重新載入文檔列表
        await loadExistingDocuments();
      } else {
        alert('清理失敗：' + (response.message || '未知錯誤'));
      }
      
    } catch (error) {
      console.error('清理孤立數據失敗:', error);
      setMaintenanceStatus(prev => ({ ...prev, isCleaning: false }));
      alert('清理孤立數據失敗：' + (error.message || '未知錯誤'));
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const processFiles = async () => {
    // 只處理有實際File對象且狀態為pending的文件
    const pendingFiles = files.filter(f => f.status === 'pending' && f.file);
    if (pendingFiles.length === 0) {
      setIsProcessing(false);
      return;
    }
    
    console.log(`開始處理 ${pendingFiles.length} 個等待中的文件`);
    setIsProcessing(true);
    
    for (let i = 0; i < pendingFiles.length; i++) {
      const file = pendingFiles[i];
      
      // 再次檢查文件狀態，防止在處理過程中狀態被改變
      const currentFile = files.find(f => f.id === file.id);
      if (!currentFile || currentFile.status !== 'pending' || !currentFile.file) {
        console.log(`跳過文件 ${file.name}，狀態已改變或文件對象無效`);
        continue;
      }
      
      // Initialize processing steps
      const processingSteps = [
        { name: '上傳文件', status: 'pending', progress: 0 },
        { name: 'PDF轉文字', status: 'pending', progress: 0 },
        { name: 'LLM精簡', status: 'pending', progress: 0 },
        { name: '生成嵌入', status: 'pending', progress: 0 },
        { name: '存入數據庫', status: 'pending', progress: 0 }
      ];
      
      setFiles(prev => prev.map(f => 
        f.id === file.id ? { 
          ...f, 
          status: 'processing', 
          progress: 0,
          currentStep: 0,
          processingSteps: [...processingSteps]
        } : f
      ));
      
      try {
        const formData = new FormData();
        formData.append('file', file.file);
        formData.append('auto_summarize', 'true');
        
        // Step 1: Upload file
        updateFileStep(file.id, 0, 'processing', 0);
        
        const response = await api.post('/api/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent) => {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            updateFileStep(file.id, 0, 'processing', progress);
            
            // Update overall progress (upload is 20% of total)
            const overallProgress = Math.round(progress * 0.2);
            setFiles(prev => prev.map(f => 
              f.id === file.id ? { ...f, progress: overallProgress } : f
            ));
          }
        });
        
        // Complete upload step
        updateFileStep(file.id, 0, 'completed', 100);
        
        // Simulate other steps based on response
        if (response.data) {
          // Step 2: PDF to text (simulate)
          updateFileStep(file.id, 1, 'processing', 0);
          await simulateProgress(file.id, 1, 20, 40); // 20-40% overall
          updateFileStep(file.id, 1, 'completed', 100);
          
          // Step 3: LLM summarization
          updateFileStep(file.id, 2, 'processing', 0);
          await simulateProgress(file.id, 2, 40, 60); // 40-60% overall
          updateFileStep(file.id, 2, 'completed', 100);
          
          // Step 4: Generate embeddings
          updateFileStep(file.id, 3, 'processing', 0);
          await simulateProgress(file.id, 3, 60, 80); // 60-80% overall
          updateFileStep(file.id, 3, 'completed', 100);
          
          // Step 5: Store in database
          updateFileStep(file.id, 4, 'processing', 0);
          await simulateProgress(file.id, 4, 80, 100); // 80-100% overall
          updateFileStep(file.id, 4, 'completed', 100);
        }
        
        // Update final status
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { 
            ...f, 
            status: 'completed', 
            progress: 100,
            currentStep: 4,
            result: response.data 
          } : f
        ));
        
        // 處理完成後，重新加載文檔列表以確保持久化
        setTimeout(() => {
          loadExistingDocuments();
        }, 1000);
        
      } catch (error) {
        console.error('Upload error:', error);
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { 
            ...f, 
            status: 'error', 
            error: error.response?.data?.message || '處理失敗'
          } : f
        ));
      }
      
      // Add delay between files
      if (i < pendingFiles.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
    
    setIsProcessing(false);
    console.log('文件處理完成');
    
    // 保存最新狀態
    setTimeout(() => {
      saveUploadState();
    }, 500);
  };
  
  const updateFileStep = (fileId, stepIndex, status, progress) => {
    setFiles(prev => prev.map(f => {
      if (f.id === fileId && f.processingSteps) {
        const newSteps = [...f.processingSteps];
        newSteps[stepIndex] = { ...newSteps[stepIndex], status, progress };
        return { ...f, processingSteps: newSteps, currentStep: stepIndex };
      }
      return f;
    }));
  };
  
  const simulateProgress = async (fileId, stepIndex, startPercent, endPercent) => {
    const duration = 2000; // 2 seconds
    const steps = 20;
    const stepDuration = duration / steps;
    const progressStep = (endPercent - startPercent) / steps;
    
    for (let i = 0; i <= steps; i++) {
      const stepProgress = Math.round((i / steps) * 100);
      const overallProgress = Math.round(startPercent + (i * progressStep));
      
      updateFileStep(fileId, stepIndex, 'processing', stepProgress);
      setFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, progress: overallProgress } : f
      ));
      
      if (i < steps) {
        await new Promise(resolve => setTimeout(resolve, stepDuration));
      }
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <FaClock size={16} className="status-icon status-pending" />;
      case 'processing':
        return <div className="spinner" />;
      case 'completed':
        return <FaCheckCircle size={16} className="status-icon status-completed" />;
      case 'error':
        return <FaTimesCircle size={16} className="status-icon status-error" />;
      default:
        return null;
    }
  };

  const getStatusText = (file) => {
    switch (file.status) {
      case 'pending':
        return '等待處理';
      case 'processing':
        return `處理中 ${file.progress}%`;
      case 'completed':
        return '處理完成';
      case 'error':
        return file.error || '處理失敗';
      default:
        return '';
    }
  };

  const allFiles = [...existingDocuments, ...files];
  const pendingCount = files.filter(f => f.status === 'pending').length;
  const completedCount = files.filter(f => f.status === 'completed').length + existingDocuments.length;
  const errorCount = files.filter(f => f.status === 'error').length;

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <div className="upload-title">
            <FaFileAlt className="upload-title-icon" />
            <h1>文檔上傳</h1>
          </div>
          <div className="upload-subtitle">
            上傳PDF文檔到知識庫，支持批量處理
          </div>
          {stateError && (
            <div className="session-error">
              ⚠️ {stateError}
            </div>
          )}
 
        </div>

        <div className="upload-stats">
          <div className="stat-item">
            <span className="stat-number">{allFiles.length}</span>
            <span className="stat-label">總文件</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{pendingCount}</span>
            <span className="stat-label">等待中</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{completedCount}</span>
            <span className="stat-label">已完成</span>
          </div>
          <div className="stat-item">
            <span className="stat-number">{errorCount}</span>
            <span className="stat-label">失敗</span>
          </div>
        </div>

        <div 
          className={`upload-dropzone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
                      <FaUpload className="upload-icon" size={48} />
          <div className="upload-text">
            <div className="upload-primary-text">
              拖拽PDF文件到此處，或點擊選擇文件
            </div>
            <div className="upload-secondary-text">
              支持批量上傳，僅支持PDF格式 • 文件安全處理，不會在瀏覽器中保存敏感信息
            </div>
          </div>
          <input
            type="file"
            multiple
            accept=".pdf"
            onChange={handleFileInput}
            className="upload-input"
          />
        </div>

        {files.length > 0 && (
          <div className="upload-actions">
            <button
              onClick={processFiles}
              disabled={isProcessing || pendingCount === 0}
              className="btn btn-primary"
            >
              {isProcessing ? '處理中...' : `處理 ${pendingCount} 個文件`}
            </button>
            <button
              onClick={() => setFiles([])}
              disabled={isProcessing}
              className="btn btn-secondary"
            >
              清空列表
            </button>
            {files.some(f => f.status === 'error' && f.error && f.error.includes('文件對象已失效')) && (
              <button
                onClick={() => setFiles(prev => prev.filter(f => !(f.status === 'error' && f.error && f.error.includes('文件對象已失效'))))}
                disabled={isProcessing}
                className="btn btn-warning"
              >
                清除失效文件
              </button>
            )}
          </div>
        )}

        {allFiles.length > 0 && (
          <div className="file-list">
            <div className="file-list-header">
              <h3>文件列表 ({existingDocuments.length > 0 ? `${existingDocuments.length} 個已存在，${files.length} 個新上傳` : `${files.length} 個文件`})</h3>
              <div className="maintenance-controls">
                <button
                  onClick={handleCheckConsistency}
                  disabled={maintenanceStatus.isChecking || maintenanceStatus.isCleaning}
                  className="btn btn-maintenance"
                  title="檢查數據一致性"
                >
                  {maintenanceStatus.isChecking ? (
                    <>
                      <div className="mini-spinner" />
                      檢查中...
                    </>
                  ) : (
                    <>
                      <FaExclamationTriangle />
                      檢查一致性
                    </>
                  )}
                </button>
                <button
                  onClick={handleCleanupOrphaned}
                  disabled={maintenanceStatus.isChecking || maintenanceStatus.isCleaning}
                  className="btn btn-maintenance"
                  title="清理孤立數據"
                >
                  {maintenanceStatus.isCleaning ? (
                    <>
                      <div className="mini-spinner" />
                      清理中...
                    </>
                  ) : (
                    <>
                      <FaTools />
                      清理數據
                    </>
                  )}
                </button>
                {(files.length > 0 || stateId) && (
                  <button
                    onClick={cleanupUploadState}
                    disabled={isProcessing || maintenanceStatus.isChecking || maintenanceStatus.isCleaning}
                    className="btn btn-maintenance btn-danger"
                    title="重置上傳狀態（清除所有待處理文件）"
                  >
                    <FaTrash />
                    重置狀態
                  </button>
                )}
              </div>
            </div>
            <div className="file-items">
              {allFiles.map((file) => (
                <div key={file.id} className={`file-item file-${file.status} ${file.isExisting ? 'existing-doc' : ''} ${file.isDeleting ? 'deleting' : ''}`}>
                  <div className="file-info">
                    <div className="file-icon">
                      <FaFile size={20} />
                    </div>
                    <div className="file-details">
                      <div className="file-name">
                        {file.name}
                        {file.isExisting && <span className="existing-badge">已存在</span>}
                      </div>
                      <div className="file-meta">
                        <span className="file-size">{formatFileSize(file.size)}</span>
                        <span className="file-status-text">{getStatusText(file)}</span>
                        {file.processed_at && (
                          <span className="file-date">處理時間: {file.processed_at}</span>
                        )}
                      </div>
                      {file.status === 'processing' && (
                        <div className="file-progress">
                          <div className="progress-header">
                            <span className="progress-text">總進度: {file.progress}%</span>
                          </div>
                          <div 
                            className="file-progress-bar"
                            style={{ width: `${file.progress}%` }}
                          />
                          
                          {file.processingSteps && (
                            <div className="processing-steps">
                              {file.processingSteps.map((step, index) => (
                                <div 
                                  key={index} 
                                  className={`processing-step step-${step.status} ${index === file.currentStep ? 'current-step' : ''}`}
                                >
                                  <div className="step-icon">
                                    {step.status === 'completed' && <FaCheckCircle size={14} />}
                                    {step.status === 'processing' && <div className="mini-spinner" />}
                                    {step.status === 'pending' && <FaClock size={14} />}
                                    {step.status === 'error' && <FaTimesCircle size={14} />}
                                  </div>
                                  <div className="step-info">
                                    <span className="step-name">{step.name}</span>
                                    {step.status === 'processing' && (
                                      <span className="step-progress">{step.progress}%</span>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      {file.result && (
                        <div className="file-result">
                          <div className="result-header">
                            <FaCheckCircle className="result-icon" />
                            <span className="result-title">處理完成</span>
                          </div>
                          <div className="result-details">
                            <div className="result-item">
                              <span className="result-label">處理時間:</span>
                              <span className="result-value">{file.result.processing_time}秒</span>
                            </div>
                            <div className="result-item">
                              <span className="result-label">提取字符:</span>
                              <span className="result-value">{file.result.characters_extracted?.toLocaleString() || 'N/A'}</span>
                            </div>
                            <div className="result-item">
                              <span className="result-label">文本塊數:</span>
                              <span className="result-value">{file.result.chunks_created}</span>
                            </div>
                            <div className="result-item">
                              <span className="result-label">存儲狀態:</span>
                              <span className="result-value success">已永久保存</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="file-actions">
                    <div className="file-status">
                      {getStatusIcon(file.status)}
                    </div>
                    <button
                      onClick={() => removeFile(file.id)}
                      disabled={(isProcessing && file.status === 'processing') || file.isDeleting}
                      className="btn-icon"
                      title={file.isDeleting ? "刪除中..." : "移除文件"}
                    >
                      {file.isDeleting ? (
                        <div className="mini-spinner" />
                      ) : (
                        <FaTrash size={16} />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={closeConfirmDialog}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        message={confirmDialog.message}
        details={confirmDialog.details}
        type={confirmDialog.type}
        confirmText={confirmDialog.confirmText}
        isLoading={confirmDialog.isLoading}
      />
    </div>
  );
};

export default UploadPage; 