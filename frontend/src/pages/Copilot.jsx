/**
 * pages/Copilot.jsx
 * =================
 * AI Copilot RAG & Automation Assistant View
 * Exposes persistent session logs, collapsible ReAct reasoning trails, and streaming text replies.
 */

import React, { useEffect, useState, useRef } from 'react';
import Sidebar from '../components/Sidebar';
import { copilotService } from '../services/copilot';
import { useAuth } from '../context/AuthContext';
import { 
  MessageSquareCode, 
  Send, 
  Plus, 
  Trash2, 
  Bot, 
  Terminal, 
  RefreshCw, 
  Info,
  BookOpen
} from 'lucide-react';
import { Toast } from '../components/Toast';

export const Copilot = () => {
  const { user } = useAuth();
  
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [toast, setToast] = useState(null);

  const messagesEndRef = useRef(null);

  const showToast = (type, message) => {
    setToast({ type, message });
  };

  // 1. Fetch User Sessions
  const fetchSessions = async (selectFirst = false) => {
    setLoadingSessions(true);
    try {
      const data = await copilotService.listSessions();
      setSessions(data || []);
      
      if (selectFirst && data && data.length > 0) {
        setCurrentSessionId(data[0].id);
      } else if (data && data.length > 0 && !currentSessionId) {
        setCurrentSessionId(data[0].id);
      }
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to retrieve chat sessions.');
    } finally {
      setLoadingSessions(false);
    }
  };

  // 2. Fetch Session History
  const fetchHistory = async (sessionId) => {
    if (!sessionId) return;
    setLoadingHistory(true);
    try {
      const data = await copilotService.getSessionHistory(sessionId);
      setMessages(data || []);
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to load conversation history.');
    } finally {
      setLoadingHistory(false);
    }
  };

  // 3. Create Session
  const handleCreateSession = async () => {
    try {
      const newSess = await copilotService.createSession(`Chat Session ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
      setSessions(prev => [newSess, ...prev]);
      setCurrentSessionId(newSess.id);
      setMessages([]);
      showToast('success', 'New chat session initialized.');
    } catch (err) {
      console.error(err);
      showToast('error', 'Could not create new session.');
    }
  };

  // 4. Delete Session
  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (!window.confirm('Delete this chat session and all messages?')) return;
    
    try {
      await copilotService.deleteSession(sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        setCurrentSessionId('');
        setMessages([]);
      }
      showToast('success', 'Chat session deleted.');
    } catch (err) {
      console.error(err);
      showToast('error', 'Failed to delete chat session.');
    }
  };

  // 5. Submit Message
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || isStreaming || !currentSessionId) return;

    const userQuery = input.trim();
    setInput('');
    setIsStreaming(true);
    setStreamingMessage('');

    // Optimistically append user message to local state
    const optimisticUserMsg = {
      id: Date.now(),
      session_id: currentSessionId,
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, optimisticUserMsg]);

    try {
      await copilotService.streamChat(
        currentSessionId,
        userQuery,
        // onChunk callback
        (chunk) => {
          setStreamingMessage(prev => prev + chunk);
        },
        // onError callback
        (errMsg) => {
          showToast('error', errMsg);
          setIsStreaming(false);
        },
        // onDone callback
        () => {
          setIsStreaming(false);
          // Refresh session list to update timestamps/titles and history to align IDs
          fetchHistory(currentSessionId);
          fetchSessions();
        }
      );
    } catch (err) {
      console.error(err);
      setIsStreaming(false);
    }
  };

  // Scroll to bottom on messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  // Load sessions on mount
  useEffect(() => {
    fetchSessions();
  }, []);

  // Fetch history when active session changes
  useEffect(() => {
    if (currentSessionId) {
      fetchHistory(currentSessionId);
    } else {
      setMessages([]);
    }
  }, [currentSessionId]);

  // Markdown reasoning logger format parser
  const renderMessageContent = (content) => {
    const lines = content.split('\n');
    const thoughts = [];
    const answerLines = [];
    let inThoughts = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('🤖') || trimmed.startsWith('>') || trimmed.startsWith('Thought:') || trimmed.startsWith('Action:') || trimmed.startsWith('Observation:')) {
        thoughts.push(line);
        inThoughts = true;
      } else {
        if (trimmed === '' && inThoughts && thoughts.length > 0) {
          // ignore double spacing in thoughts
        } else {
          inThoughts = false;
          answerLines.push(line);
        }
      }
    }

    const answerText = answerLines.join('\n').trim();

    return (
      <div className="space-y-3">
        {thoughts.length > 0 && (
          <details className="bg-slate-950 border border-slate-800/80 rounded-xl p-3 text-xs font-mono text-violet-300" open>
            <summary className="cursor-pointer font-bold select-none text-slate-400 hover:text-violet-400 transition-colors flex items-center gap-2">
              <Terminal className="h-3.5 w-3.5 text-violet-400" />
              <span>NOC Agent ReAct Trace</span>
              <span className="text-[9px] bg-slate-900 text-slate-500 px-1.5 py-0.5 rounded border border-slate-800">
                {thoughts.length} logs
              </span>
            </summary>
            <div className="mt-2 space-y-1.5 opacity-90 border-t border-slate-900 pt-2 max-h-60 overflow-y-auto">
              {thoughts.map((th, i) => {
                let colorClass = "text-slate-300";
                if (th.includes("Observation:")) colorClass = "text-emerald-400";
                else if (th.includes("Action:")) colorClass = "text-amber-400";
                else if (th.includes("Thought:")) colorClass = "text-violet-400";
                return (
                  <div key={i} className={`whitespace-pre-wrap ${colorClass}`}>
                    {th}
                  </div>
                );
              })}
            </div>
          </details>
        )}
        
        {answerText && (
          <div className="markdown-content text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
            {answerText}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      <Sidebar />
      
      <main className="flex-1 flex overflow-hidden">
        {toast && (
          <Toast
            type={toast.type}
            message={toast.message}
            onClose={() => setToast(null)}
          />
        )}

        {/* Sessions Sidebar Panel */}
        <section className="w-80 border-r border-slate-800 bg-slate-900/10 flex flex-col shrink-0">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/20">
            <h2 className="text-sm font-bold text-slate-200 flex items-center gap-2">
              <MessageSquareCode className="h-5 w-5 text-violet-400" />
              <span>Copilot Sessions</span>
            </h2>
            <button
              onClick={handleCreateSession}
              title="Start New Chat"
              className="bg-violet-600/10 hover:bg-violet-600/20 border border-violet-500/20 text-violet-400 p-2 rounded-xl transition-all cursor-pointer"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {loadingSessions ? (
              <div className="text-center text-slate-500 text-xs py-8">
                Loading sessions...
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center text-slate-600 text-xs py-8 px-4 leading-normal">
                No active conversations. Start a new session.
              </div>
            ) : (
              sessions.map(sess => (
                <div
                  key={sess.id}
                  onClick={() => setCurrentSessionId(sess.id)}
                  className={`p-3 rounded-2xl border transition-all cursor-pointer flex justify-between items-center group ${
                    currentSessionId === sess.id
                      ? 'bg-slate-900/90 border-slate-700 shadow-md ring-1 ring-violet-500/30'
                      : 'bg-slate-900/30 border-slate-800/60 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="truncate flex-1 pr-2">
                    <p className="text-xs font-semibold text-slate-200 truncate">{sess.title}</p>
                    <span className="text-[10px] text-slate-500 block mt-0.5">
                      {new Date(sess.updated_at).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <button
                    onClick={(e) => handleDeleteSession(e, sess.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 rounded-lg hover:bg-slate-800/80 transition-all cursor-pointer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        {/* Chat Workspace */}
        <section className="flex-1 flex flex-col bg-slate-950/40 relative overflow-hidden">
          
          {/* Header */}
          <div className="p-4 border-b border-slate-800 bg-slate-900/20 flex justify-between items-center">
            <div>
              <h1 className="text-base font-bold text-slate-200">
                {currentSessionId 
                  ? sessions.find(s => s.id === currentSessionId)?.title || "Active Conversation"
                  : "NOC Intelligence Assistant"
                }
              </h1>
              <p className="text-xs text-slate-400">Ask operations questions, query alerts, check telemetry, or search runbooks.</p>
            </div>
            
            <div className="flex items-center gap-2 text-xs bg-slate-900/80 border border-slate-800/60 px-3 py-1.5 rounded-full text-violet-400">
              <Bot className="h-4 w-4 animate-pulse text-violet-400" />
              <span className="font-semibold">AETHER AI Copilot</span>
            </div>
          </div>

          {/* Messages List */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6">
            {!currentSessionId ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto">
                <div className="h-16 w-16 rounded-2xl bg-violet-600/10 border border-violet-500/20 flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(124,58,237,0.1)]">
                  <Bot className="h-8 w-8 text-violet-400" />
                </div>
                <h3 className="text-lg font-bold text-slate-200">NOC Operations Assistant</h3>
                <p className="text-slate-400 text-sm mt-2 leading-relaxed">
                  Welcome to the AI Copilot dashboard. This assistant runs a LangChain agent linked to physical system configurations and local operations tools.
                </p>
                <div className="grid grid-cols-2 gap-4 mt-8 w-full">
                  <div className="p-4 bg-slate-900/40 border border-slate-800/60 rounded-2xl text-left">
                    <BookOpen className="h-5 w-5 text-indigo-400 mb-2" />
                    <h4 className="text-xs font-bold text-slate-200">RAG Runbooks</h4>
                    <p className="text-[11px] text-slate-500 mt-1">Queries semantic vector stores indexing system guides and recovery procedures.</p>
                  </div>
                  <div className="p-4 bg-slate-900/40 border border-slate-800/60 rounded-2xl text-left">
                    <Terminal className="h-5 w-5 text-amber-400 mb-2" />
                    <h4 className="text-xs font-bold text-slate-200">NOC Toolsets</h4>
                    <p className="text-[11px] text-slate-500 mt-1">Executes real-time device ping queries, syslog audits, and updates tickets.</p>
                  </div>
                </div>
                <button
                  onClick={handleCreateSession}
                  className="mt-8 bg-violet-600 hover:bg-violet-500 text-white font-semibold py-2.5 px-6 rounded-xl transition-all shadow-[0_0_15px_rgba(124,58,237,0.2)] text-sm flex items-center gap-2 cursor-pointer"
                >
                  <Plus className="h-4 w-4" />
                  <span>Start First Chat Session</span>
                </button>
              </div>
            ) : loadingHistory ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                <RefreshCw className="h-5 w-5 animate-spin text-violet-400 mr-2" />
                <span>Loading session logs...</span>
              </div>
            ) : messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 max-w-md mx-auto text-slate-500">
                <Info className="h-8 w-8 text-slate-600 mb-3" />
                <p className="text-sm">Conversation started. Type a query below to prompt the Copilot agent.</p>
                <div className="mt-4 text-xs bg-slate-900/40 border border-slate-800/60 p-3 rounded-xl space-y-1 text-slate-400 max-w-sm text-left">
                  <p className="font-bold text-slate-300">Try asking:</p>
                  <p>• "What are the critical alerts today?"</p>
                  <p>• "Analyze router anomalies"</p>
                  <p>• "Show me the CPU spike runbook"</p>
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`p-4 rounded-2xl max-w-[80%] shadow-md border ${
                        msg.role === 'user'
                          ? 'bg-violet-600 border-violet-500 text-white rounded-tr-none'
                          : 'bg-slate-900/60 border-slate-800/80 text-slate-200 rounded-tl-none'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                      ) : (
                        renderMessageContent(msg.content)
                      )}
                      <span className={`text-[9px] block mt-2 text-right ${msg.role === 'user' ? 'text-violet-200' : 'text-slate-500'}`}>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
                
                {/* Streaming Response placeholder */}
                {isStreaming && streamingMessage && (
                  <div className="flex justify-start">
                    <div className="p-4 rounded-2xl max-w-[80%] bg-slate-900/60 border border-slate-800/80 text-slate-200 rounded-tl-none shadow-md">
                      {renderMessageContent(streamingMessage)}
                      <div className="flex items-center gap-1.5 mt-3 text-[10px] text-violet-400 font-semibold">
                        <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                        <span className="ml-1">Copilot is typing...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Form Input */}
          {currentSessionId && (
            <div className="p-4 border-t border-slate-800 bg-slate-900/20">
              <form onSubmit={handleSendMessage} className="flex gap-3">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={isStreaming ? "Copilot is answering..." : "Ask Copilot... (e.g. 'how to resolve high CPU', 'status of core-router')"}
                  disabled={isStreaming}
                  className="flex-1 bg-slate-900 border border-slate-800 hover:border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-all disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={isStreaming || !input.trim()}
                  className="bg-violet-600 hover:bg-violet-500 text-white font-semibold px-5 py-3 rounded-xl transition-all shadow-[0_0_15px_rgba(124,58,237,0.2)] hover:shadow-[0_0_20px_rgba(124,58,237,0.3)] disabled:opacity-50 flex items-center justify-center cursor-pointer shrink-0"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default Copilot;
