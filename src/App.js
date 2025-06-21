import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import ChatPage from './pages/ChatPage';
import UploadPage from './pages/UploadPage';
import './styles/App.css';

function App() {
  const [isNavCollapsed, setIsNavCollapsed] = useState(false);

  return (
    <Router>
      <div className={`app ${isNavCollapsed ? 'nav-collapsed' : ''}`}>
        <Navigation 
          isCollapsed={isNavCollapsed}
          onToggleCollapse={setIsNavCollapsed}
        />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/upload" element={<UploadPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App; 