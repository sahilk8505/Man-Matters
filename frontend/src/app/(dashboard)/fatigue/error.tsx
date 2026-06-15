"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function FatigueError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error so it shows in the browser console for debugging
    console.error("[Fatigue page error]", error?.message, error?.stack);
  }, [error]);

  return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <div className="flex items-center justify-center w-14 h-14 bg-red-100 rounded-full">
        <AlertTriangle className="h-7 w-7 text-red-600" />
      </div>
      <div className="text-center max-w-md">
        <h2 className="text-lg font-semibold mb-2">Fatigue Monitor failed to load</h2>
        <p className="text-sm text-muted-foreground mb-1">
          {error?.message || "An unexpected error occurred."}
        </p>
        {error?.digest && (
          <p className="text-xs text-muted-foreground font-mono mt-1">
            Error ID: {error.digest}
          </p>
        )}
      </div>
      <button
        onClick={reset}
        className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
      >
        <RefreshCw className="h-4 w-4" />
        Try again
      </button>
    </div>
  );
}
