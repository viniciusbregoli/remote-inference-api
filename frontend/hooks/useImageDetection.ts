import { useState, useEffect } from "react";
import { detectObjects } from "../services/api";

export function useImageDetection() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [resultImage, setResultImage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Clean up URLs when component unmounts or when they change
  useEffect(() => {
    return () => {
      if (preview && preview.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }
      if (resultImage && resultImage.startsWith("blob:")) {
        URL.revokeObjectURL(resultImage);
      }
    };
  }, [preview, resultImage]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Revoke previous URL if it exists
      if (preview && preview.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }

      setSelectedImage(file);
      setResultImage(null);
      setError(null);

      // Create a new object URL for preview
      const objectUrl = URL.createObjectURL(file);
      setPreview(objectUrl);
    }
  };

  const handleDetection = async () => {
    if (!selectedImage) return;

    setIsLoading(true);
    setError(null);

    // Clean up previous result URL
    if (resultImage && resultImage.startsWith("blob:")) {
      URL.revokeObjectURL(resultImage);
      setResultImage(null);
    }

    try {
      const blob = await detectObjects(selectedImage);
      const imageUrl = URL.createObjectURL(blob);
      setResultImage(imageUrl);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
      console.error("Error processing image:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const resetDetection = () => {
    if (selectedImage) {
      setSelectedImage(null);
    }

    if (preview && preview.startsWith("blob:")) {
      URL.revokeObjectURL(preview);
      setPreview(null);
    }

    if (resultImage && resultImage.startsWith("blob:")) {
      URL.revokeObjectURL(resultImage);
      setResultImage(null);
    }

    setError(null);
  };

  return {
    selectedImage,
    preview,
    resultImage,
    isLoading,
    error,
    handleImageChange,
    handleDetection,
    resetDetection,
    setError,
  };
}
