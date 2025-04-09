import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SignupPage from './pages/auth/Signup';
import LoginPage from './pages/auth/Login';
import CreateGroupPage from './pages/groups/CreateGroup';
import CreateCommunityPage from './pages/communities/CreateCommunity';
import Dashboard from './pages/dashboard/Dashboard';
import GroupPage from './pages/groups/GroupPage';
import CommunityPage from './pages/communities/CommunityPage';
import Layout from './pages/layout/Layout';
import ProtectedRoute from './pages/auth/ProtectedRoute';

const App = () => {
  return (
    <Router>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        
        {/* Protected routes */}
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="groups/create" element={<CreateGroupPage />} />
          <Route path="groups/:groupId" element={<GroupPage />} />
          <Route path="communities/create" element={<CreateCommunityPage />} />
          <Route path="communities/:communityId" element={<CommunityPage />} />
        </Route>
        
        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
};

export default App;