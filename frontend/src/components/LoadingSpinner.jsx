import React from 'react';

const LoadingSpinner = () => {
  return (
    <div className="flex flex-col items-center justify-center">
      <div className="spinner"></div>
      <p className="mt-4 text-gray-600 animate-pulse">Loading...</p>
    </div>
  );
};

export default LoadingSpinner;
