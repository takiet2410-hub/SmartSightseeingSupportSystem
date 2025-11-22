import React from 'react';
import { Link, NavLink } from 'react-router-dom';

const Navbar = () => {
  return (
    <nav className="navbar">
      <Link to="/" className="logo">
        <span>✦</span> Smart Sightseeing Support System
      </Link>
      <div className="nav-links">
        <NavLink to="/recommend" className="nav-link">Before Trip</NavLink>
        <NavLink to="/identify" className="nav-link">During Trip</NavLink>
        <NavLink to="/curate" className="nav-link">After Trip</NavLink>
      </div>
    </nav>
  );
};
export default Navbar;