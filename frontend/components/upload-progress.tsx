'use client';

interface UploadingFile {
  filename: string;
  progress: number;
}

interface UploadProgressProps {
  uploadingFiles: Map<string, UploadingFile>;
  error: string | null;
}

export function UploadProgress({ uploadingFiles, error }: UploadProgressProps) {
  const hasUploads = uploadingFiles.size > 0;

  if (!hasUploads && !error) {
    return null;
  }

  return (
    <>
      {/* Uploading files */}
      {hasUploads && (
        <div className="flex-shrink-0 px-4 pt-4">
          {Array.from(uploadingFiles.entries()).map(([id, file]) => (
            <div key={id} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-zinc-400 truncate">
                  {file.filename}
                </span>
                <span className="text-xs text-zinc-500">
                  {Math.round(file.progress)}%
                </span>
              </div>
              <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${file.progress}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="mx-4 mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}
    </>
  );
}
