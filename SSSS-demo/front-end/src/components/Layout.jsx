import React from 'react';
import Navbar from './Navbar';
import Footer from './Footer';

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      <Navbar />
      <div className="main-content">{children}</div>
      <Footer />
    </div>
  );
};
export default Layout;