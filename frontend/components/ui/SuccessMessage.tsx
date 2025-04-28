import { CheckCircle } from "lucide-react";

interface SuccessMessageProps {
  message: string;
}

export default function SuccessMessage({ message }: SuccessMessageProps) {
  if (!message) return null;

  return (
    <div className="flex items-center p-3 bg-green-50 text-green-700 rounded-md border border-green-200 space-x-2">
      <CheckCircle
        className="h-5 w-5 text-green-500 flex-shrink-0"
        aria-hidden="true"
      />
      <p className="text-sm font-medium text-green-800">{message}</p>
    </div>
  );
}
