'use client';

export function MessageSkeleton() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="max-w-xs px-4 py-3 rounded-lg rounded-bl-none bg-secondary-dark">
        <div className="space-y-2">
          <div className="h-4 bg-primary-light bg-opacity-20 rounded w-48 animate-shimmer" />
          <div className="h-4 bg-primary-light bg-opacity-20 rounded w-40 animate-shimmer" />
        </div>
      </div>
    </div>
  );
}

export function WhiteboardSkeleton() {
  return (
    <div className="w-full h-full bg-secondary-dark animate-pulse">
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="h-8 bg-primary-light bg-opacity-20 rounded w-32 mx-auto mb-4 animate-shimmer" />
          <div className="h-4 bg-primary-light bg-opacity-20 rounded w-48 mx-auto animate-shimmer" />
        </div>
      </div>
    </div>
  );
}
