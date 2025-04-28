// API service for object detection

const API_URL = "http://localhost:5000";

/**
 * Sends an image to the object detection API
 * @param image The image file to process
 * @returns A Promise with the blob response
 */
export async function detectObjects(image: File): Promise<Blob> {
  const formData = new FormData();
  formData.append("image", image);

  const response = await fetch(`${API_URL}/detect`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `Detection failed with status: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || JSON.stringify(errorData);
    } catch {
      errorMessage = (await response.text()) || errorMessage;
    }
    throw new Error(errorMessage);
  }

  return await response.blob();
}

/**
 * Check the health status of the API
 * @returns A Promise with the health check response
 */
export async function checkApiHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_URL}/health`);

  if (!response.ok) {
    throw new Error("API health check failed");
  }

  return await response.json();
}
