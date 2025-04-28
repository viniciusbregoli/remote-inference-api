import { AlertCircle } from "lucide-react";

interface ErrorMessageProps {
  title?: string;
  message: string;
}

export default function ErrorMessage({
  title = "Error Occurred",
  message,
}: ErrorMessageProps) {
  if (!message) return null;

  return (
    <div className="flex items-start p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 space-x-3">
      <AlertCircle
        className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5"
        aria-hidden="true"
      />
      <div>
        <p className="font-medium text-red-800">{title}</p>
        <p className="text-sm break-words">{message}</p>
      </div>
    </div>
  );
}
