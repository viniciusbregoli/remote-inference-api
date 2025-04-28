import { UploadCloud } from "lucide-react";
import Image from "next/image";

interface ImageUploadProps {
  preview: string | null;
  isLoading: boolean;
  onImageChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function ImageUpload({
  preview,
  isLoading,
  onImageChange,
}: ImageUploadProps) {
  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-400 transition-colors duration-200 bg-gray-50">
      <input
        type="file"
        accept="image/png, image/jpeg, image/webp"
        onChange={onImageChange}
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
            <p className="text-xs text-gray-500">PNG, JPG, WEBP up to 10MB</p>
          </div>
        )}
      </label>
    </div>
  );
}
