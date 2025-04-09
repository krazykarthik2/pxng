// frontend/src/layout/Layout.jsx
import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Menu, X, LogOut, User, Users, Globe, MessageCircle, Search, Plus } from 'lucide-react';

const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };
  
  const isActive = (path) => {
    return location.pathname === path;
  };
  
  return (
    <div className="h-screen flex overflow-hidden bg-gray-100">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="md:hidden fixed inset-0 z-40 bg-gray-600 bg-opacity-75" 
          onClick={() => setSidebarOpen(false)}
        ></div>
      )}
      
      {/* Sidebar */}
      <div className={`
        md:flex md:flex-shrink-0 transform top-0 left-0 w-64 bg-white fixed h-full overflow-auto ease-in-out transition-all duration-300 z-50
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        <div className="flex flex-col w-full">
          {/* Logo and mobile close button */}
          <div className="flex items-center justify-between h-16 flex-shrink-0 px-4 bg-blue-600">
            <Link to="/dashboard" className="text-white font-bold text-xl">
              ChatGraph
            </Link>
            <button 
              className="md:hidden text-white"
              onClick={() => setSidebarOpen(false)}
            >
              <X size={24} />
            </button>
          </div>
          
          {/* Navigation */}
          <div className="flex-1 flex flex-col overflow-y-auto">
            <div className="px-2 space-y-1 py-4">
              {/* Search */}
              <div className="px-2 mb-4">
                <div className="relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search size={16} className="text-gray-400" />
                  </div>
                  <input
                    type="text"
                    className="form-input block w-full pl-10 sm:text-sm sm:leading-5 border-gray-300 rounded-md"
                    placeholder="Search..."
                  />
                </div>
              </div>
              
              {/* Nav Links */}
              <Link 
                to="/dashboard" 
                className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                  isActive('/dashboard') 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <MessageCircle 
                  size={20} 
                  className={`mr-3 ${
                    isActive('/dashboard') ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500'
                  }`} 
                />
                Chats
              </Link>
              
              <Link 
                to="/groups" 
                className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                  isActive('/groups') 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Users 
                  size={20} 
                  className={`mr-3 ${
                    isActive('/groups') ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500'
                  }`} 
                />
                Groups
              </Link>
              
              <Link 
                to="/communities" 
                className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                  isActive('/communities') 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Globe 
                  size={20} 
                  className={`mr-3 ${
                    isActive('/communities') ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500'
                  }`} 
                />
                Communities
              </Link>
              
              <Link 
                to="/profile" 
                className={`group flex items-center px-2 py-2 text-sm font-medium rounded-md ${
                  isActive('/profile') 
                    ? 'bg-gray-100 text-gray-900' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <User 
                  size={20} 
                  className={`mr-3 ${
                    isActive('/profile') ? 'text-gray-500' : 'text-gray-400 group-hover:text-gray-500'
                  }`} 
                />
                Profile
              </Link>
              
              {/* Create New Dropdown */}
              <div className="mt-4 border-t border-gray-200 pt-4">
                <div className="px-2 mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Create New
                </div>
                <Link 
                  to="/create/group" 
                  className="group flex items-center px-2 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <Plus size={20} className="mr-3 text-gray-400 group-hover:text-gray-500" />
                  New Group
                </Link>
                <Link 
                  to="/create/community" 
                  className="group flex items-center px-2 py-2 text-sm font-medium rounded-md text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                >
                  <Plus size={20} className="mr-3 text-gray-400 group-hover:text-gray-500" />
                  New Community
                </Link>
                <button 
                  onClick={handleLogout}
                  className="w-full group flex items-center px-2 py-2 text-sm font-medium rounded-md text-red-600 hover:bg-red-50"
                >
                  <LogOut size={20} className="mr-3 text-red-400 group-hover:text-red-500" />
                  Logout
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        {/* Top header */}
        <div className="relative z-10 flex-shrink-0 flex h-16 bg-white shadow md:hidden">
          <button
            className="px-4 text-gray-500 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 md:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={24} />
          </button>
          <div className="flex-1 flex justify-center px-4">
            <div className="flex-1 flex">
              <div className="w-full flex items-center justify-center">
                <div className="text-lg font-bold text-gray-900">ChatGraph</div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Page content */}
        <main className="flex-1 relative overflow-y-auto focus:outline-none">
          <div className="py-6 px-4 sm:px-6 md:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;