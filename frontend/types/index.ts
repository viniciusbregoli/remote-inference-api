
export interface DetectionState {
    selectedImage: File | null;
    preview: string | null;
    resultImage: string | null;
    isLoading: boolean;
    error: string | null;
  }