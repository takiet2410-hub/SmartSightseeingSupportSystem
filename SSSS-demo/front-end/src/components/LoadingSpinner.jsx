import React from 'react';
const LoadingSpinner = ({ message }) => (
  <div style={{textAlign:'center', padding:'4rem'}}>
    <div className="loader"></div>
    <p style={{color:'#cbd5e1', marginTop:'1rem'}}>{message}</p>
  </div>
);
export default LoadingSpinner;