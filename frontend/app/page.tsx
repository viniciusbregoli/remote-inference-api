"use client";

import { useState } from "react";
import Image from "next/image";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; // Get the file from the input
    if (file) {
      setSelectedImage(file);
      setResultImage(null); // Clear previous results

      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedImage) return;

    setIsLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("image", selectedImage);

    try {
      // Directly call the detect endpoint since the model is loaded at startup
      const response = await fetch("http://localhost:5000/detect", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const blob = await response.blob();
        const imageUrl = URL.createObjectURL(blob);
        setResultImage(imageUrl);
      } else {
        let errorText;
        try {
          const errorData = await response.json();
          errorText = errorData.detail || "Unknown error";
        } catch {
          errorText = await response.text();
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

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-2 text-center text-blue-600">
          Object Detection
        </h1>
        <p className="text-center text-gray-600 mb-8">
          Upload an image to detect objects using YOLOv8
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors bg-white shadow-sm">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="hidden"
                  id="image-upload"
                />
                <label htmlFor="image-upload" className="cursor-pointer block">
                  {preview ? (
                    <div className="space-y-4">
                      <div className="relative w-full h-64">
                        <Image
                          src={preview}
                          alt="Preview"
                          fill
                          className="object-contain rounded-lg"
                        />
                      </div>
                      <p className="text-sm text-gray-500">
                        Click to change image
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="text-6xl text-gray-300">📸</div>
                      <div className="text-gray-500">
                        Click to select an image
                      </div>
                    </div>
                  )}
                </label>
              </div>

              <button
                type="submit"
                disabled={!selectedImage || isLoading}
                className="w-full bg-blue-500 text-white py-3 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
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
                  </span>
                ) : (
                  "Detect Objects"
                )}
              </button>
            </form>

            {error && (
              <div className="p-4 bg-red-100 text-red-700 rounded-lg border border-red-200">
                <p className="font-medium">Error</p>
                <p>{error}</p>
              </div>
            )}
          </div>

          <div
            className={`bg-white p-6 rounded-lg shadow-sm ${
              resultImage ? "" : "flex items-center justify-center"
            }`}
          >
            {resultImage ? (
              <div>
                <h2 className="text-xl font-semibold mb-4 text-gray-800">
                  Detection Result
                </h2>
                <div className="relative w-full h-64 md:h-80 border border-gray-200 rounded-lg overflow-hidden">
                  <Image
                    src={resultImage}
                    alt="Detection Result"
                    className="object-contain w-full h-full"
                    fill
                    style={{ objectFit: "contain" }}
                  />
                </div>
                <p className="mt-3 text-sm text-gray-500">
                  Objects detected and highlighted with bounding boxes
                </p>
              </div>
            ) : (
              <div className="text-center text-gray-400">
                <p>Detection results will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
