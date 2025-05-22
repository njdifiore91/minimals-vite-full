import axios from 'axios';
import { API_ENDPOINTS } from 'src/config/api';

/**
 * Retrieves a secure, time-limited URL for accessing a document from S3-compatible storage
 * with AES-256 encryption for data at rest and SSL/TLS for data in transit.
 * 
 * @param storagePath - The S3 storage path of the document
 * @param documentId - The unique identifier of the document
 * @returns A Promise that resolves to a secure, time-limited URL
 */
export async function getSecureDocumentUrl(storagePath: string, documentId: string): Promise<string> {
  try {
    // Request a secure, signed URL from the backend
    const response = await axios.post(API_ENDPOINTS.documents.getSecureUrl, {
      storagePath,
      documentId,
    });
    
    // The backend should return a time-limited, signed URL with proper encryption
    if (response.data && response.data.url) {
      return response.data.url;
    }
    
    throw new Error('Invalid response from server');
  } catch (error) {
    console.error('Error fetching secure document URL:', error);
    throw new Error('Failed to retrieve secure document URL');
  }
}

/**
 * Uploads a document to S3-compatible storage with AES-256 encryption
 * 
 * @param file - The file to upload
 * @param applicationId - The ID of the associated application
 * @param metadata - Optional metadata for the document
 * @returns A Promise that resolves to the uploaded document information
 */
export async function uploadDocument(
  file: File,
  applicationId: string,
  metadata?: Record<string, any>
) {
  try {
    // First, request a secure upload URL from the backend
    const urlResponse = await axios.post(API_ENDPOINTS.documents.getUploadUrl, {
      fileName: file.name,
      fileType: file.type,
      fileSize: file.size,
      applicationId,
      metadata,
    });
    
    if (!urlResponse.data || !urlResponse.data.uploadUrl || !urlResponse.data.documentId) {
      throw new Error('Invalid upload URL response');
    }
    
    const { uploadUrl, documentId, fields } = urlResponse.data;
    
    // Create form data for the upload
    const formData = new FormData();
    
    // Add the fields required by S3 (provided by the backend)
    if (fields) {
      Object.entries(fields).forEach(([key, value]) => {
        formData.append(key, value as string);
      });
    }
    
    // Add the file as the last field
    formData.append('file', file);
    
    // Upload directly to S3 using the pre-signed URL
    await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    // Return the document information
    return {
      id: documentId,
      name: file.name,
      size: file.size,
      type: file.type,
      applicationId,
    };
  } catch (error) {
    console.error('Error uploading document:', error);
    throw new Error('Failed to upload document');
  }
}

/**
 * Retrieves document classification and metadata
 * 
 * @param documentId - The unique identifier of the document
 * @returns A Promise that resolves to the document classification and metadata
 */
export async function getDocumentClassification(documentId: string) {
  try {
    const response = await axios.get(`${API_ENDPOINTS.documents.getClassification}/${documentId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching document classification:', error);
    throw new Error('Failed to retrieve document classification');
  }
}

/**
 * Deletes a document from S3-compatible storage
 * 
 * @param documentId - The unique identifier of the document
 * @returns A Promise that resolves when the document is deleted
 */
export async function deleteDocument(documentId: string) {
  try {
    await axios.delete(`${API_ENDPOINTS.documents.delete}/${documentId}`);
    return true;
  } catch (error) {
    console.error('Error deleting document:', error);
    throw new Error('Failed to delete document');
  }
}