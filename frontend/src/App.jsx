import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

// Pages - Before Module
import Home from './pages/Home';
import Destinations from './pages/Destinations';
import DestinationDetail from './pages/DestinationDetail';
import AIRecommendations from './pages/AIRecommendations';
import Favorites from './pages/Favorites';

// Pages - During Module
import VisualSearch from './pages/VisualSearch';
import DetectionHistory from './pages/DetectionHistory';

// Pages - After Module
import AlbumCreator from './pages/AlbumCreator';
import MyAlbums from './pages/MyAlbums';
import TripSummary from './pages/TripSummary';
import SharedAlbum from './pages/SharedAlbum';

// Pages - Auth
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import Profile from './pages/Profile';

import './App.css';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <div className="app">
            <Navbar />
            <main className="app-main">
              <Routes>
                {/* Public Routes - Before Module */}
                <Route path="/" element={<Home />} />
                <Route path="/destinations" element={<Destinations />} />
                <Route path="/destination/:id" element={<DestinationDetail />} />
                <Route path="/recommendations" element={<AIRecommendations />} />

                {/* Public Routes - During Module */}
                <Route path="/visual-search" element={<VisualSearch />} />

                {/* Public Routes - After Module (Shared Albums) */}
                <Route path="/shared/:shareToken" element={<SharedAlbum />} />

                {/* Auth Routes */}
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/forgot-password" element={<ForgotPassword />} />
                <Route path="/reset-password" element={<ResetPassword />} />

                {/* Protected Routes - Profile & Favorites */}
                <Route path="/profile" element={
                  <ProtectedRoute>
                    <Profile />
                  </ProtectedRoute>
                } />
                <Route path="/favorites" element={
                  <ProtectedRoute>
                    <Favorites />
                  </ProtectedRoute>
                } />

                <Route path="/detection-history" element={
                  <ProtectedRoute>
                    <DetectionHistory />
                  </ProtectedRoute>
                } />

                {/* Protected Routes - After Module */}
                <Route path="/album-creator" element={
                  <ProtectedRoute>
                    <AlbumCreator />
                  </ProtectedRoute>
                } />
                <Route path="/my-albums" element={
                  <ProtectedRoute>
                    <MyAlbums />
                  </ProtectedRoute>
                } />
                <Route path="/trip-summary" element={
                  <ProtectedRoute>
                    <TripSummary />
                  </ProtectedRoute>
                } />
              </Routes>
            </main>
            <footer className="app-footer">
              <div className="container">
                <p>© 2024 Smart Sightseeing</p>
              </div>
            </footer>
          </div>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
