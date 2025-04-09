import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const ChatInterface = ({ currentUser, recipient, recipientType }) => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [queryMode, setQueryMode] = useState(false);
  const messagesEndRef = useRef(null);
  
  // Fetch messages on component mount and when recipient changes
  useEffect(() => {
    if (recipient && recipientType) {
      fetchMessages();
    }
  }, [recipient, recipientType]);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  const fetchMessages = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/messages', {
        params: {
          recipient_id: recipient.id,
          recipient_type: recipientType
        },
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      // Sort messages by timestamp
      const sortedMessages = response.data.sort((a, b) => 
        new Date(a.timestamp) - new Date(b.timestamp)
      );
      
      setMessages(sortedMessages);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching messages:', error);
      setLoading(false);
    }
  };
  
  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!newMessage.trim()) return;
    
    try {
      setLoading(true);
      
      if (queryMode) {
        // RAG query mode
        const response = await axios.post('/api/rag/query', {
          query: newMessage
        }, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        // Add user query to messages
        const userQuery = {
          id: `temp-${Date.now()}`,
          content: newMessage,
          sender_id: currentUser.id,
          recipient_id: recipient.id,
          timestamp: new Date().toISOString()
        };
        
        // Add RAG response to messages
        const ragResponse = {
          id: `rag-${Date.now()}`,
          content: response.data.answer,
          sender_id: 'rag-assistant',
          recipient_id: recipient.id,
          timestamp: new Date().toISOString(),
          sources: response.data.sources
        };
        
        setMessages([...messages, userQuery, ragResponse]);
      } else {
        // Regular message mode
        const response = await axios.post('/api/messages', {
          content: newMessage,
          recipient_id: recipient.id,
          recipient_type: recipientType
        }, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        // Add new message to the list
        setMessages([...messages, response.data]);
      }
      
      // Clear input
      setNewMessage('');
      setLoading(false);
    } catch (error) {
      console.error('Error sending message:', error);
      setLoading(false);
    }
  };
  
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  return (
    <div className="flex flex-col h-full">
      <div className="header">
        <h1>PXNG</h1>
      </div>
      <div className="bg-gray-100 p-4 border-b">
        <div className="flex items-center">
          <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
            {recipientType === 'user' ? recipient?.name?.charAt(0)?.toUpperCase() : '#'}
          </div>
          <div className="ml-3">
            <h2 className="text-lg font-semibold">{recipient?.name}</h2>
            <p className="text-sm text-gray-500">{recipientType}</p>
          </div>
          <div className="ml-auto">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={queryMode}
                onChange={() => setQueryMode(!queryMode)}
                className="mr-2"
              />
              RAG Query Mode
            </label>
          </div>
        </div>
      </div>
      
      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto">
        {loading && messages.length === 0 ? (
          <div className="flex justify-center items-center h-full">
            <p>Loading messages...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender_id === currentUser.id ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md p-3 rounded-lg ${
                    message.sender_id === currentUser.id
                      ? 'bg-blue-500 text-white'
                      : message.sender_id === 'rag-assistant'
                      ? 'bg-green-100 border border-green-300'
                      : 'bg-gray-100'
                  }`}
                >
                  {message.sender_id !== currentUser.id && message.sender_id !== 'rag-assistant' && (
                    <p className="text-xs font-semibold mb-1">
                      {message.sender_name || 'User'}
                    </p>
                  )}
                  <p>{message.content}</p>
                  <p className="text-xs mt-1 text-right">
                    {formatTimestamp(message.timestamp)}
                  </p>
                  
                  {/* Display sources for RAG responses */}
                  {message.sender_id === 'rag-assistant' && message.sources && (
                    <div className="mt-2 pt-2 border-t border-green-200">
                      <p className="text-xs font-semibold">Sources:</p>
                      <ul className="text-xs mt-1 list-disc pl-4">
                        {message.sources.slice(0, 3).map((source, idx) => (
                          <li key={idx} className="truncate">
                            {source.type === 'message' ? (
                              <>Message from {source.sender_id}</>
                            ) : source.type === 'document_chunk' ? (
                              <>{source.document_name} (chunk {source.chunk_index})</>
                            ) : (
                              <>Unknown source</>
                            )}
                          </li>
                        ))}
                        {message.sources.length > 3 && (
                          <li>+{message.sources.length - 3} more sources</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>
      
      {/* Input */}
      <div className="border-t p-4">
        <form onSubmit={sendMessage} className="flex">
          <input
            type="text"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            placeholder={queryMode ? "Ask a question..." : "Type a message..."}
            className="flex-1 border rounded-l-lg px-4 py-2 focus:outline-none"
            disabled={loading}
          />
          <button
            type="submit"
            className="bg-blue-500 text-white px-4 py-2 rounded-r-lg hover:bg-blue-600 focus:outline-none"
            disabled={loading}
          >
            {queryMode ? "Ask" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;