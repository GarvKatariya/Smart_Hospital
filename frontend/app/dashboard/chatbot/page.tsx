'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { chatAPI } from '@/lib/api';
import { Send, Bot, User } from 'lucide-react';
import axios from 'axios';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'assistant', content: 'Hello! I am the SmartHospital AI assistant. How can I help you today? You can ask me about symptoms, hospital policies, or general medical information.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [initializing, setInitializing] = useState(true);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    const initialize = async () => {
      let stage = 'your saved chats';
      try {
        const sessions = await chatAPI.listSessions();
        const existing = Array.isArray(sessions.data) ? sessions.data[0] : undefined;
        stage = existing ? 'messages in your latest chat' : 'a new chat';
        const activeSession = existing || (await chatAPI.createSession()).data;
        if (!activeSession?.id) throw new Error('The chat service did not return a session ID');
        if (!mounted) return;
        setSessionId(activeSession.id);
        if (existing) {
          const history = await chatAPI.getMessages(activeSession.id);
          if (mounted && Array.isArray(history.data) && history.data.length) {
            setMessages(history.data);
          }
        }
      } catch (cause: unknown) {
        if (mounted) {
          const status = axios.isAxiosError(cause) ? cause.response?.status : undefined;
          const statusText = status ? ` (HTTP ${status})` : '';
          setError(`Could not load ${stage}${statusText}. Please refresh and try again.`);
        }
      } finally {
        if (mounted) setInitializing(false);
      }
    };
    void initialize();
    return () => { mounted = false; };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !sessionId || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const res = await chatAPI.sendMessage(sessionId, userMsg.content);
      const aiMsg: Message = { id: Date.now().toString() + 'ai', role: 'assistant', content: res.data.response };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      setMessages(prev => prev.filter(message => message.id !== userMsg.id));
      setInput(userMsg.content);
      setError(axios.isAxiosError(err) ? err.response?.data?.detail || 'The assistant could not respond. Please try again.' : 'The assistant could not respond. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] max-w-4xl mx-auto flex flex-col">
      <div className="mb-4">
        <h2 className="text-2xl font-bold tracking-tight">Hospital Chatbot</h2>
        <p className="text-muted-foreground">Ask medical questions or inquire about hospital services.</p>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden border-gray-200">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {initializing && <p className="text-sm text-gray-500 text-center">Opening your chat…</p>}
          {error && <p role="alert" className="text-sm text-red-700 bg-red-50 rounded-md p-3">{error}</p>}
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-blue-600 ml-3' : 'bg-gray-200 mr-3'}`}>
                  {msg.role === 'user' ? <User size={16} className="text-white" /> : <Bot size={16} className="text-gray-700" />}
                </div>
                <div className={`px-4 py-2 rounded-2xl ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-gray-100 text-gray-800 rounded-tl-none border'}`}>
                  <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="flex">
                <div className="flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center bg-gray-200 mr-3">
                  <Bot size={16} className="text-gray-700" />
                </div>
                <div className="px-4 py-3 rounded-2xl bg-gray-100 rounded-tl-none border flex items-center space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="p-4 bg-white border-t">
          <form onSubmit={handleSend} className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 h-10 px-4 py-2 bg-gray-50 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
              aria-label="Message the hospital assistant"
            />
            <Button type="submit" disabled={initializing || loading || !sessionId || !input.trim()} className="rounded-full px-4 h-10" aria-label="Send message">
              <Send size={18} />
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}
