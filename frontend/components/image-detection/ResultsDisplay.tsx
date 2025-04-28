import Image from "next/image";
import { ImageIcon } from "lucide-react";
import SuccessMessage from "../ui/SuccessMessage";

interface ResultsDisplayProps {
  resultImage: string | null;
  isLoading: boolean;
}

export default function ResultsDisplay({
  resultImage,
  isLoading,
}: ResultsDisplayProps) {
  return (
    <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8 sticky top-8">
      <h2 className="text-2xl font-semibold text-gray-700 mb-4">
        Detection Result
      </h2>
      <div
        className={`relative w-full h-80 sm:h-96 border border-gray-200 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center ${
          resultImage ? "bg-white" : ""
        }`}
      >
        {isLoading && !resultImage && (
          <div className="flex flex-col items-center text-gray-400 animate-pulse">
            <ImageIcon className="h-16 w-16 mb-2" strokeWidth={1} />
            <p>Loading result...</p>
          </div>
        )}
        {!isLoading && resultImage && (
          <Image
            src={resultImage}
            alt="Object detection result"
            fill
            className="object-contain"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        )}
        {!isLoading && !resultImage && (
          <div className="text-center text-gray-400 px-4">
            <ImageIcon
              className="h-16 w-16 mx-auto mb-3 text-gray-300"
              strokeWidth={1}
            />
            <p className="font-medium">Results will appear here</p>
            <p className="text-sm">
              Upload an image and click &quot;Detect Objects&quot;.
            </p>
          </div>
        )}
      </div>
      {resultImage && !isLoading && (
        <div className="mt-4">
          <SuccessMessage message="Detection complete. Objects highlighted above." />
        </div>
      )}
    </div>
  );
}
