"use client";

import { useState } from "react";
import Image from "next/image";

export default function Home() {
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedImage(file);
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

    const formData = new FormData();
    formData.append("image", selectedImage);

    try {
      const response = await fetch("http://localhost:5000/detect", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Upload successful:", data);
        // Clear the form after successful upload
        setSelectedImage(null);
        setPreview(null);
      } else {
        console.error("Upload failed");
      }
    } catch (error) {
      console.error("Error uploading image:", error);
    }
  };

  return (
    <main className="min-h-screen p-8">
      <div className="max-w-md mx-auto">
        <h1 className="text-3xl font-bold mb-8 text-center">Image Upload</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-gray-400 transition-colors">
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
                  <p className="text-sm text-gray-500">Click to change image</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-6xl text-gray-300">📸</div>
                  <div className="text-gray-500">Click to select an image</div>
                </div>
              )}
            </label>
          </div>

          <button
            type="submit"
            disabled={!selectedImage}
            className="w-full bg-blue-500 text-white py-3 px-4 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Upload Image
          </button>
        </form>
      </div>
    </main>
  );
}
