'use client';

import { useEffect, useState } from 'react';

interface ConnectionStatusProps {
  isConnected: boolean;
  message?: string;
}

export function ConnectionStatus({
  isConnected,
  message = 'Connecting to Agora...',
}: ConnectionStatusProps) {
  const [isVisible, setIsVisible] = useState(!isConnected);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (isConnected) {
        setIsVisible(false);
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [isConnected]);

  if (!isVisible) return null;

  return (
    <div
      className={`fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg animate-slide-in-right z-50
        ${
          isConnected
            ? 'bg-green-50 border border-green-200'
            : 'bg-yellow-50 border border-yellow-200'
        }
      `}
    >
      <p
        className={`text-sm font-medium ${
          isConnected ? 'text-green-700' : 'text-yellow-700'
        }`}
      >
        {isConnected ? 'Connected to Agora' : message}
      </p>
    </div>
  );
}
