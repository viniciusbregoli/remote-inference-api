import { useState, useEffect } from "react";
import ImageUpload from "./ImageUpload";
import Button from "../ui/Button";
import ErrorMessage from "../ui/ErrorMessage";
import { detectObjects } from "../../services/api";

interface DetectionFormProps {
  onDetectionResult: (resultUrl: string) => void;
  onLoadingChange: (isLoading: boolean) => void;
}

export default function DetectionForm({
  onDetectionResult,
  onLoadingChange,
}: DetectionFormProps) {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cleanup object URLs when component unmounts
  useEffect(() => {
    return () => {
      if (preview && preview.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Revoke previous object URL if it exists
      if (preview && preview.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }

      setSelectedImage(file);
      setError(null);

      // Create a new object URL for preview
      const objectUrl = URL.createObjectURL(file);
      setPreview(objectUrl);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedImage) return;

    setIsLoading(true);
    onLoadingChange(true);
    setError(null);

    try {
      const blob = await detectObjects(selectedImage);
      const imageUrl = URL.createObjectURL(blob);
      onDetectionResult(imageUrl);
    } catch (error) {
      setError(error instanceof Error ? error.message : String(error));
      console.error("Error processing image:", error);
    } finally {
      setIsLoading(false);
      onLoadingChange(false);
    }
  };

  return (
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
          disabled={!selectedImage || isLoading}
          isLoading={isLoading}
          fullWidth={true}
        >
          Detect Objects
        </Button>
      </form>

      {error && <ErrorMessage message={error} />}
    </div>
  );
}
