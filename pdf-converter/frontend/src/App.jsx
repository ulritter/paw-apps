import React, { useState, useEffect } from 'react';
import { Upload, Download, Sparkles, FileText, AlertCircle, CheckCircle, Loader } from 'lucide-react';

const API_URL = process.env.REACT_APP_API_URL || '/api/converter';

export default function AIPdfToExcel() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState('');
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [userEmail, setUserEmail] = useState('');

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/crawler/auth/check', {
          credentials: 'include'
        });
        const data = await response.json();
        
        if (!data.authenticated) {
          window.location.href = '/login.html';
          return;
        }
        
        setIsAuthenticated(true);
        setUserEmail(data.email || '');
        setIsCheckingAuth(false);
      } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
      }
    };
    
    checkAuth();
  }, []);

  // Show loading while checking auth
  if (isCheckingAuth) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Loader className="animate-spin" size={48} />
      </div>
    );
  }

  const analyzeWithBackend = async (file) => {
    const formData = new FormData();
    formData.append('pdf', file);
    const response = await fetch(`${API_URL}/convert`, {
      method: 'POST',
      body: formData
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    return await response.json();
  };

  const processFile = async (uploadedFile) => {
    if (!uploadedFile) return;
    if (uploadedFile.type !== 'application/pdf') {
      setError('Bitte laden Sie eine PDF-Datei hoch.');
      return;
    }
    setFile(uploadedFile);
    setError(null);
    setStatus('processing');
    setProgress('PDF wird gelesen...');
    try {
      setProgress('KI analysiert die Dokumentstruktur...');
      const result = await analyzeWithBackend(uploadedFile);
      setExtractedData(result);
      setStatus('complete');
      setProgress('Fertig! Daten wurden extrahiert.');
    } catch (err) {
      console.error('Error:', err);
      setError(`Fehler bei der Verarbeitung: ${err.message}`);
      setStatus('error');
    }
  };

  const handleFileUpload = async (e) => {
    const uploadedFile = e.target.files[0];
    await processFile(uploadedFile);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const droppedFiles = e.dataTransfer?.files;
    if (!droppedFiles || droppedFiles.length === 0) return;
    const uploadedFile = droppedFiles[0];
    await processFile(uploadedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragOver) setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };

  const downloadExcel = () => {
    if (!extractedData) return;
    let csvContent = '\ufeff';
    if (extractedData.metadata) {
      csvContent += `Dokumenttyp:;${extractedData.documentType}\n`;
      if (extractedData.metadata.date) csvContent += `Datum:;${extractedData.metadata.date}\n`;
      if (extractedData.metadata.reference) csvContent += `Referenz:;${extractedData.metadata.reference}\n`;
      csvContent += '\n';
    }
    extractedData.tables.forEach((table) => {
      if (table.title) csvContent += `${table.title}\n`;
      csvContent += table.headers.join(';') + '\n';
      table.rows.forEach(row => {
        csvContent += row.map(cell => {
          const cellStr = String(cell || '');
          if (cellStr.includes(';') || cellStr.includes('"') || cellStr.includes('\n')) {
            return `"${cellStr.replace(/"/g, '""')}"`;
          }
          return cellStr;
        }).join(';') + '\n';
      });
      csvContent += '\n';
    });
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${file.name.replace('.pdf', '')}_extracted.csv`;
    link.click();
  };

  const copyToClipboard = () => {
    let text = '';
    extractedData.tables.forEach((table, i) => {
      text += `Tabelle ${i + 1}:\n`;
      table.rows.forEach(row => { text += row.join('\t') + '\n'; });
      text += '\n';
    });
    navigator.clipboard.writeText(text);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/crawler/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });
      window.location.href = '/login.html';
    } catch (error) {
      console.error('Logout failed:', error);
      window.location.href = '/login.html';
    }
  };

  const handleHome = () => {
    window.location.href = window.location.protocol + '//' + window.location.host + '/';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <div className="mb-4 flex justify-between items-center">
            <button
              onClick={handleHome}
              className="px-4 py-2 rounded-full transition-all"
              style={{
                background: 'rgba(139, 92, 246, 0.1)',
                color: '#8b5cf6',
                border: 'none',
                fontSize: '0.85rem',
                fontWeight: '500'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(139, 92, 246, 0.2)';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(139, 92, 246, 0.1)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              ← Home
            </button>
            <img src="/pws-logo.png" alt="People Work Systems" className="h-10 md:h-12 object-contain" />
            <div 
              className="flex items-center gap-3 px-6 py-3 rounded-full"
              style={{
                background: 'rgba(139, 92, 246, 0.1)',
                backdropFilter: 'blur(10px)'
              }}
            >
              <span style={{ color: '#8b5cf6', fontSize: '0.9rem', fontWeight: '500' }}>
                {userEmail}
              </span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 rounded-full transition-all"
                style={{
                  background: 'rgba(139, 92, 246, 0.2)',
                  color: '#8b5cf6',
                  border: 'none',
                  fontSize: '0.85rem',
                  fontWeight: '500'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(139, 92, 246, 0.3)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(139, 92, 246, 0.2)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                Logout
              </button>
            </div>
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-gradient-to-br from-purple-500 to-indigo-600 p-3 rounded-lg">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-800">KI-gestützte PDF → Excel Konvertierung</h1>
              <p className="text-gray-600 mt-1">Claude AI analysiert automatisch jede PDF-Struktur und extrahiert Daten intelligent</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-purple-50 rounded-lg p-4">
              <h3 className="font-semibold text-purple-900 mb-2">🎯 Automatische Erkennung</h3>
              <p className="text-sm text-purple-700">Erkennt Tabellen, Listen und Strukturen automatisch</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">🧠 KI-Analyse</h3>
              <p className="text-sm text-blue-700">Claude Sonnet 4-5 analysiert und versteht den Dokumentinhalt</p>
            </div>
            <div className="bg-indigo-50 rounded-lg p-4">
              <h3 className="font-semibold text-indigo-900 mb-2">📊 Excel-Export</h3>
              <p className="text-sm text-indigo-700">Strukturierte Daten direkt als CSV exportieren</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-lg p-8 mb-6">
          <h2 className="text-xl font-bold text-gray-800 mb-4">PDF hochladen</h2>
          <div
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-all ${
              isDragOver
                ? 'border-indigo-600 bg-indigo-100'
                : 'border-indigo-300 bg-gradient-to-br from-indigo-50 to-purple-50 hover:from-indigo-100 hover:to-purple-100'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input type="file" accept=".pdf" onChange={handleFileUpload} className="hidden" id="file-upload" disabled={status === 'processing'} />
            <label htmlFor="file-upload" className="cursor-pointer">
              <Upload className="w-16 h-16 text-indigo-600 mx-auto mb-4" />
              <p className="text-xl font-medium text-gray-700 mb-2">{file ? file.name : 'PDF-Datei auswählen'}</p>
              <p className="text-sm text-gray-500">Beliebige PDF mit Tabellen oder strukturierten Daten</p>
              <p className="text-xs text-gray-400 mt-2">oder Datei hierher ziehen und ablegen</p>
            </label>
          </div>
          {status === 'processing' && (
            <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <Loader className="w-6 h-6 text-blue-600 animate-spin" />
                <div>
                  <p className="font-semibold text-blue-900">Verarbeitung läuft...</p>
                  <p className="text-sm text-blue-700">{progress}</p>
                </div>
              </div>
            </div>
          )}
          {error && (
            <div className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <AlertCircle className="w-6 h-6 text-red-600" />
                <div>
                  <p className="font-semibold text-red-900">Fehler</p>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}
          {status === 'complete' && (
            <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-6 h-6 text-green-600" />
                <div>
                  <p className="font-semibold text-green-900">Erfolgreich extrahiert!</p>
                  <p className="text-sm text-green-700">{progress}</p>
                </div>
              </div>
            </div>
          )}
        </div>
        {extractedData && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-gray-800">Extrahierte Daten</h2>
                <p className="text-gray-600 mt-1">{extractedData.documentType}</p>
              </div>
              <div className="flex gap-3">
                <button onClick={copyToClipboard} className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors">
                  <FileText className="w-5 h-5" />In Zwischenablage
                </button>
                <button onClick={downloadExcel} className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                  <Download className="w-5 h-5" />Als CSV speichern
                </button>
              </div>
            </div>
            {extractedData.tables.map((table, idx) => (
              <div key={idx} className="mb-8">
                {table.title && <h3 className="text-lg font-semibold text-gray-800 mb-3">{table.title}</h3>}
                <div className="overflow-x-auto rounded-lg border border-gray-200">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gradient-to-r from-indigo-100 to-purple-100">
                        {table.headers.map((header, hIdx) => (
                          <th key={hIdx} className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold text-gray-800">{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className={rIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="border border-gray-200 px-4 py-2 text-sm text-gray-700">{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="text-sm text-gray-600 mt-2">{table.rows.length} Zeilen extrahiert</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
