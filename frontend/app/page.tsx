"use client";

import { FormEvent } from "react";
import ImageUpload from "../components/image-detection/ImageUpload";
import ResultsDisplay from "../components/image-detection/ResultsDisplay";
import Button from "../components/ui/Button";
import ErrorMessage from "../components/ui/ErrorMessage";
import { useImageDetection } from "../hooks/useImageDetection";

export default function Home() {
  const {
    preview,
    resultImage,
    isLoading,
    error,
    handleImageChange,
    handleDetection,
  } = useImageDetection();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    handleDetection();
  };

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
              <ImageUpload
                preview={preview}
                isLoading={isLoading}
                onImageChange={handleImageChange}
              />

              <Button
                type="submit"
                disabled={!preview || isLoading}
                isLoading={isLoading}
                fullWidth={true}
              >
                Detect Objects
              </Button>
            </form>

            {error && <ErrorMessage message={error} />}
          </div>

          {/* Right Column: Results Display */}
          <ResultsDisplay resultImage={resultImage} isLoading={isLoading} />
        </div>
      </div>
    </main>
  );
}
