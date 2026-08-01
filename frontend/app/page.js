"use client";

import { useState, useEffect, useRef } from "react";

// Access matrix mapping (for frontend display)
const ROLE_COLLECTIONS = {
  doctor: ["general", "clinical", "nursing"],
  nurse: ["general", "nursing"],
  billing_executive: ["general", "billing"],
  technician: ["general", "equipment"],
  admin: ["general", "clinical", "nursing", "billing", "equipment"]
};

const ROLE_DISPLAY_NAMES = {
  doctor: "Medical Doctor",
  nurse: "Registered Nurse",
  billing_executive: "Billing & Insurance Executive",
  technician: "Equipment Technician",
  admin: "System Administrator"
};

// Colors for badges
const ROLE_BADGES = {
  doctor: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  nurse: "bg-sky-500/10 text-sky-400 border border-sky-500/20",
  billing_executive: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  technician: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
  admin: "bg-rose-500/10 text-rose-400 border border-rose-500/20"
};

const DEMO_USERS = [
  { username: "dr.mehta", role: "doctor", label: "Dr. Mehta (Doctor)" },
  { username: "nurse.priya", role: "nurse", label: "Nurse Priya (Nurse)" },
  { username: "billing.ravi", role: "billing_executive", label: "Billing Ravi (Billing Exec)" },
  { username: "tech.anand", role: "technician", label: "Tech Anand (Technician)" },
  { username: "admin.sys", role: "admin", label: "Admin Sys (Admin)" }
];

export default function Home() {
  // Session states
  const [user, setUser] = useState(null);
  const [token, setToken] = useState("");
  
  // Login form states
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("password123");
  const [loginError, setLoginError] = useState("");
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Chat states
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isSending, setIsSending] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Scroll chat to bottom on new messages
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle mock login
  const handleLogin = async (e, selectUsername = null) => {
    if (e) e.preventDefault();
    setIsLoggingIn(true);
    setLoginError("");

    const finalUsername = selectUsername || username;
    if (!finalUsername) {
      setLoginError("Please enter a username or select a demo account");
      setIsLoggingIn(false);
      return;
    }

    try {
      const res = await fetch("http://localhost:8000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: finalUsername, password })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Login failed");
      }

      const data = await res.json();
      setToken(data.token);
      setUser({
        username: data.username,
        role: data.role
      });
      // Clear fields
      setUsername("");
      
      // Seed welcome message
      setMessages([
        {
          id: "welcome",
          role: "assistant",
          content: `Welcome to MediBot, ${data.username}! You are logged in as **${ROLE_DISPLAY_NAMES[data.role]}**. You have permission to access: ${ROLE_COLLECTIONS[data.role].map(c => `\`${c}\``).join(", ")}. How can I assist you today?`,
          retrievalType: "system"
        }
      ]);
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setIsLoggingIn(false);
    }
  };

  // Logout handler
  const handleLogout = () => {
    setUser(null);
    setToken("");
    setMessages([]);
  };

  // Send message handler
  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputMessage.trim()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsSending(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: userMessage.content,
          role: user.role
        })
      });

      if (!res.ok) {
        throw new Error("Failed to contact the backend service.");
      }

      const data = await res.json();
      
      const botMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        retrievalType: data.retrieval_type, // 'hybrid_rag', 'sql_rag', or 'blocked'
        sources: data.sources || [],
        sqlQuery: data.sql_query
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (err) {
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${err.message}. Make sure the FastAPI backend is running at http://localhost:8000.`,
        retrievalType: "error"
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };

  if (!user) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        {/* Background mesh effects */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.15),rgba(255,255,255,0))] pointer-events-none" />
        
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative overflow-hidden backdrop-blur-md">
          {/* Top glow decoration */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-emerald-500 via-teal-500 to-sky-500" />
          
          <div className="text-center mb-8 relative">
            <div className="inline-flex p-3 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20 mb-3">
              <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">MediBot Assistant</h1>
            <p className="text-sm text-slate-400 mt-1">MediAssist Health Network - Internal Operations Portal</p>
          </div>

          <form onSubmit={(e) => handleLogin(e)} className="space-y-4">
            {loginError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm rounded-lg text-center font-medium">
                {loginError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Username</label>
              <input
                type="text"
                placeholder="e.g. dr.mehta"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:border-emerald-500 transition-colors text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={isLoggingIn}
              className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-50 text-white rounded-lg py-2.5 font-semibold text-sm transition-all shadow-lg shadow-emerald-950/20 flex items-center justify-center gap-2"
            >
              {isLoggingIn ? "Authenticating..." : "Login"}
            </button>
          </form>

          <div className="mt-8 border-t border-slate-800 pt-6">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 text-center">Demo Quick Logins</h2>
            <div className="grid grid-cols-1 gap-2">
              {DEMO_USERS.map((demo) => (
                <button
                  key={demo.username}
                  onClick={(e) => handleLogin(e, demo.username)}
                  disabled={isLoggingIn}
                  className="w-full text-left px-4 py-2.5 bg-slate-950/50 hover:bg-slate-950 border border-slate-850 hover:border-slate-700 text-xs text-slate-300 rounded-lg transition-all flex items-center justify-between"
                >
                  <span>{demo.label}</span>
                  <span className="text-slate-500 text-[10px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded uppercase font-semibold">
                    {demo.role.replace("_", " ")}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Active user chat dashboard
  return (
    <main className="h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row overflow-hidden font-sans">
      {/* Sidebar - Permissions & Info */}
      <section className="w-full md:w-80 bg-slate-900 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col justify-between shrink-0">
        <div>
          {/* Header */}
          <div className="p-6 border-b border-slate-800 flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <div>
              <h2 className="font-bold text-white tracking-wide">MediBot Console</h2>
              <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">MediAssist Network</p>
            </div>
          </div>

          {/* User Profile Card */}
          <div className="p-6 border-b border-slate-800 bg-slate-950/20">
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1.5">Authenticated User</p>
            <h3 className="font-semibold text-white text-base mb-2">{user.username}</h3>
            <span className={`inline-block text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${ROLE_BADGES[user.role]}`}>
              {ROLE_DISPLAY_NAMES[user.role]}
            </span>
          </div>

          {/* Accessible collections list */}
          <div className="p-6">
            <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Authorized Collections</h4>
            <div className="space-y-2">
              {ROLE_COLLECTIONS[user.role].map((col) => (
                <div key={col} className="flex items-center gap-2 text-xs font-medium text-slate-300 bg-slate-950/40 px-3 py-2 rounded-lg border border-slate-850">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span className="capitalize">{col} documents</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Action / Logout */}
        <div className="p-6 border-t border-slate-800">
          <button
            onClick={handleLogout}
            className="w-full bg-slate-950 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 text-xs font-semibold text-slate-400 hover:text-white rounded-lg py-2 transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </button>
        </div>
      </section>

      {/* Main Chat Panel */}
      <section className="flex-1 flex flex-col justify-between bg-slate-950 overflow-hidden relative">
        {/* Glow decoration */}
        <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full filter blur-[80px] pointer-events-none" />
        
        {/* Chat Header */}
        <header className="p-4 bg-slate-900/60 border-b border-slate-800/80 backdrop-blur flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-slate-300">MediBot Service Active</span>
          </div>
          <span className="text-[10px] text-slate-500 font-bold bg-slate-950 border border-slate-850 px-2 py-0.5 rounded uppercase">
            RBAC Enforced
          </span>
        </header>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-2xl rounded-2xl p-4 shadow-md ${
                msg.role === "user"
                  ? "bg-emerald-600 text-white rounded-tr-none"
                  : msg.retrievalType === "blocked"
                  ? "bg-rose-500/10 border border-rose-500/25 text-rose-200 rounded-tl-none"
                  : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none"
              }`}>
                {/* Message Header info for Bot */}
                {msg.role === "assistant" && msg.retrievalType && (
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${
                      msg.retrievalType === "blocked"
                        ? "bg-rose-500/20 text-rose-400 border-rose-500/30"
                        : msg.retrievalType === "sql_rag"
                        ? "bg-purple-500/10 text-purple-400 border-purple-500/20"
                        : msg.retrievalType === "hybrid_rag"
                        ? "bg-teal-500/10 text-teal-400 border-teal-500/20"
                        : "bg-slate-800 text-slate-400 border-slate-700"
                    }`}>
                      {msg.retrievalType.replace("_", " ")}
                    </span>
                  </div>
                )}

                {/* Message text */}
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>

                {/* SQL Query Debug Info */}
                {msg.sqlQuery && (
                  <div className="mt-3 bg-slate-950/90 border border-slate-850 rounded-lg p-2.5">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">Executed Query</p>
                    <code className="text-xs text-purple-300 block overflow-x-auto whitespace-pre font-mono">
                      {msg.sqlQuery}
                    </code>
                  </div>
                )}

                {/* Sources list */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-4 border-t border-slate-800/80 pt-3">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">Source Citations</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.sources.map((src, sIdx) => (
                        <div key={sIdx} className="bg-slate-950/50 border border-slate-850/80 rounded-lg p-2 text-xs">
                          <div className="flex justify-between items-center mb-1">
                            <span className="font-semibold text-slate-300 truncate mr-2">{src.source_document}</span>
                            <span className="text-[9px] uppercase font-bold px-1 rounded bg-slate-900 border border-slate-800 text-slate-500 shrink-0">
                              {src.collection}
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-400 truncate">{src.section_title}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {isSending && (
            <div className="flex justify-start">
              <div className="bg-slate-900 border border-slate-850 rounded-2xl rounded-tl-none p-4 flex items-center gap-2 text-slate-400 text-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" />
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce delay-150" />
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce delay-300" />
                </div>
                MediBot is searching and synthesizing...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <form onSubmit={handleSendMessage} className="p-4 bg-slate-900/40 border-t border-slate-800/60 backdrop-blur">
          <div className="flex gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              placeholder={`Ask MediBot as a ${user.role.replace("_", " ")} (e.g. standard procedures, drug details, or operations metrics)`}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-800 focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none transition-all"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isSending}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl px-5 py-3 transition-colors shadow-lg shadow-emerald-950/20"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
