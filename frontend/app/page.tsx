"use client";

import { useState, useEffect } from "react"; // Import useEffect
import Image from "next/image";
import {
  UploadCloud,
  Image as ImageIcon,
  AlertCircle,
  CheckCircle,
} from "lucide-react";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clean up object URLs when component unmounts or when dependencies change
  // FIX: Changed useState to useEffect
  useEffect(() => {
    // This is the cleanup function that runs when the component unmounts
    // or before the effect runs again due to dependency changes.
    return () => {
      if (preview?.startsWith("blob:")) {
        console.log("Revoking preview URL:", preview);
        URL.revokeObjectURL(preview);
      }
      if (resultImage?.startsWith("blob:")) {
        console.log("Revoking result URL:", resultImage);
        URL.revokeObjectURL(resultImage);
      }
    };
  }, [preview, resultImage]); // Dependencies: effect runs cleanup when these change

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // It's generally better to revoke URLs *before* setting the new state
      // to ensure the old blob isn't held onto unnecessarily.
      // The useEffect cleanup handles the final cleanup or changes.
      if (preview?.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }
      if (resultImage?.startsWith("blob:")) {
        URL.revokeObjectURL(resultImage);
      }

      setSelectedImage(file);
      setResultImage(null);
      setError(null);

      // Create a new blob URL for the preview
      const objectUrl = URL.createObjectURL(file);
      setPreview(objectUrl); // Use object URL directly for preview state for consistency

      // Note: Using FileReader (reader.readAsDataURL) is also valid for previews,
      // but since the result will be a blob URL, using blob URLs for both preview
      // and result makes cleanup logic slightly more consistent via useEffect.
      // If you stick with readAsDataURL, the useEffect cleanup for `preview`
      // would not be strictly necessary as Data URLs don't need revoking.
      // Let's stick with createObjectURL for consistency here.
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedImage) return;

    setIsLoading(true);
    setError(null);
    // Clean up previous result blob URL before fetching new one
    if (resultImage?.startsWith("blob:")) {
      URL.revokeObjectURL(resultImage);
    }
    setResultImage(null);

    const formData = new FormData();
    formData.append("image", selectedImage);

    try {
      const response = await fetch("http://localhost:5000/detect", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        setResultImage(imageUrl);
      } else {
        let errorText = "Detection failed with status: " + response.status;
        try {
          const errorData = await response.json();
          errorText = errorData.detail || JSON.stringify(errorData);
        } catch {
          errorText = (await response.text()) || errorText;
        }
        setError(`Detection failed: ${errorText}`);
        console.error("Detection failed", errorText);
      }
    } catch (error) {
      setError(
        `Error processing image: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
      console.error("Error processing image:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Rest of the component remains the same until the error line...

  return (
    <main className="min-h-screen py-12 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-sky-50 to-indigo-100">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-12">
          <h1 className="text-4xl sm:text-5xl font-bold text-gray-800 tracking-tight mb-3">
            Object Detection AI
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Upload an image and let our YOLOv8 model detect the objects within
            it. See the results instantly!
          </p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-start">
          {/* Left Column: Upload Form */}
          <div className="bg-white rounded-xl shadow-lg p-6 sm:p-8 space-y-6">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">
              Upload Your Image
            </h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Input Area */}
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 transition-colors duration-200 bg-gray-50">
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/webp"
                  onChange={handleImageChange}
                  className="hidden"
                  id="image-upload"
                  disabled={isLoading}
                />
                <label
                  htmlFor="image-upload"
                  className={`cursor-pointer block ${
                    isLoading ? "cursor-not-allowed opacity-60" : ""
                  }`}
                >
                  {preview ? (
                    <div className="space-y-4">
                      <div className="relative w-full h-60 sm:h-72 border border-gray-200 rounded-lg overflow-hidden bg-white">
                        <Image
                          src={preview}
                          alt="Selected image preview"
                          fill
                          className="object-contain"
                        />
                      </div>
                      <p className="text-sm text-indigo-600 font-medium hover:underline">
                        Click to change image
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3 flex flex-col items-center justify-center h-60 sm:h-72">
                      <UploadCloud
                        className="h-12 w-12 text-gray-400"
                        strokeWidth={1.5}
                      />
                      <p className="text-gray-600 font-medium">
                        Click to upload or drag and drop
                      </p>
                      <p className="text-xs text-gray-500">
                        PNG, JPG, WEBP up to 10MB
                      </p>
                    </div>
                  )}
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!selectedImage || isLoading}
                className="w-full flex justify-center items-center bg-indigo-600 text-white py-3 px-4 rounded-lg font-semibold hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-all duration-200 shadow-md hover:shadow-lg"
              >
                {isLoading ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Processing...
                  </>
                ) : (
                  "Detect Objects"
                )}
              </button>
            </form>

            {/* Error Display */}
            {error && (
              <div className="flex items-start p-4 bg-red-50 text-red-700 rounded-lg border border-red-200 space-x-3">
                <AlertCircle
                  className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5"
                  aria-hidden="true"
                />
                <div>
                  <p className="font-medium text-red-800">Error Occurred</p>
                  <p className="text-sm break-words">{error}</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Results */}
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
                  {/* FIX: Escaped double quotes */}
                  <p className="text-sm">
                    Upload an image and click &quot;Detect Objects&quot;.
                  </p>
                </div>
              )}
            </div>
            {resultImage && !isLoading && (
              <div className="mt-4 flex items-center p-3 bg-green-50 text-green-700 rounded-md border border-green-200 space-x-2">
                <CheckCircle
                  className="h-5 w-5 text-green-500 flex-shrink-0"
                  aria-hidden="true"
                />
                <p className="text-sm font-medium text-green-800">
                  Detection complete. Objects highlighted above.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
