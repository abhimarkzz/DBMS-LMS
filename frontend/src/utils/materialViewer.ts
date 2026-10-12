// Shared Authenticated Material Viewer & Downloader Utility

import { getAuthToken, removeAuthToken, removeStoredUser, API_BASE } from '../api';

export interface MaterialFetchResult {
  blob: Blob;
  filename: string;
  contentType: string;
  format: 'PDF' | 'DOCX' | 'PPTX' | 'TXT' | 'MD' | 'OTHER';
}

/**
 * Parse standard Content-Disposition header to extract the actual filename
 */
export function extractFilenameFromHeader(header: string | null, fallback: string): string {
  if (!header) return fallback;

  // 1. Try RFC 5987 filename*=UTF-8''encoded_name
  const rfc5987Match = header.match(/filename\*=UTF-8''([^;]+)/i);
  if (rfc5987Match && rfc5987Match[1]) {
    try {
      return decodeURIComponent(rfc5987Match[1]);
    } catch {
      return rfc5987Match[1];
    }
  }

  // 2. Try quoted filename="..."
  const quotedMatch = header.match(/filename="([^"]+)"/i);
  if (quotedMatch && quotedMatch[1]) {
    return quotedMatch[1];
  }

  // 3. Try unquoted filename=...
  const unquotedMatch = header.match(/filename=([^;]+)/i);
  if (unquotedMatch && unquotedMatch[1]) {
    return unquotedMatch[1].trim();
  }

  return fallback;
}

/**
 * Detect file format from filename extension and MIME type
 */
export function detectFormat(filename: string, contentType: string): 'PDF' | 'DOCX' | 'PPTX' | 'TXT' | 'MD' | 'OTHER' {
  const lowerName = filename.toLowerCase();
  const lowerType = contentType.toLowerCase();

  if (lowerName.endsWith('.pdf') || lowerType.includes('application/pdf')) return 'PDF';
  if (lowerName.endsWith('.docx') || lowerType.includes('wordprocessingml')) return 'DOCX';
  if (lowerName.endsWith('.pptx') || lowerType.includes('presentationml')) return 'PPTX';
  if (lowerName.endsWith('.md') || lowerType.includes('markdown')) return 'MD';
  if (lowerName.endsWith('.txt') || lowerType.includes('text/plain')) return 'TXT';

  return 'OTHER';
}

/**
 * Authenticated fetch for study material file
 */
export async function fetchAuthenticatedMaterial(
  courseId: number,
  materialId: number,
  defaultFilename?: string
): Promise<MaterialFetchResult> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('Authentication required. Please sign in to access course materials.');
  }

  const endpoint = `${API_BASE}/courses/${courseId}/materials/${materialId}/download`;
  const res = await fetch(endpoint, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      removeAuthToken();
      removeStoredUser();
      throw new Error('Your session has expired. Please log in again to access materials.');
    }
    if (res.status === 403) {
      throw new Error('Access denied. You must be enrolled in this course to access this material.');
    }
    if (res.status === 404) {
      throw new Error('The requested study material or file could not be found.');
    }

    let errorDetail = `Failed to download file (HTTP ${res.status})`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      // not JSON
    }
    throw new Error(errorDetail);
  }

  const disposition = res.headers.get('content-disposition');
  const contentType = res.headers.get('content-type') || 'application/octet-stream';
  const fallback = defaultFilename || `material_${materialId}`;
  const filename = extractFilenameFromHeader(disposition, fallback);
  const format = detectFormat(filename, contentType);

  const rawBlob = await res.blob();

  // Ensure blob has appropriate explicit MIME type
  let mimeForBlob = contentType;
  if (format === 'PDF') mimeForBlob = 'application/pdf';
  else if (format === 'TXT') mimeForBlob = 'text/plain;charset=utf-8';
  else if (format === 'MD') mimeForBlob = 'text/markdown;charset=utf-8';
  else if (format === 'DOCX') mimeForBlob = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
  else if (format === 'PPTX') mimeForBlob = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';

  const blob = new Blob([rawBlob], { type: mimeForBlob });

  return { blob, filename, contentType: mimeForBlob, format };
}

/**
 * Handle opening or previewing a material depending on its format:
 * - PDF: opens in browser PDF viewer via secure Blob URL
 * - TXT / MD: previews via text callback if provided, or opens in new tab
 * - DOCX / PPTX: reliably downloads authenticated binary file
 */
export async function openProtectedMaterial(
  courseId: number,
  materialId: number,
  defaultFilename?: string,
  onPreviewText?: (text: string, filename: string) => void
): Promise<{ action: 'PREVIEW' | 'DOWNLOADED'; filename: string; format: string }> {
  const result = await fetchAuthenticatedMaterial(courseId, materialId, defaultFilename);
  const { blob, filename, format } = result;

  if (format === 'PDF') {
    const blobUrl = URL.createObjectURL(blob);
    const win = window.open(blobUrl, '_blank');
    if (!win) {
      // Pop-up blocked, fallback to download
      triggerBlobDownload(blob, filename);
      return { action: 'DOWNLOADED', filename, format };
    }
    // Clean up Blob URL after preview has loaded
    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
    }, 120000);
    return { action: 'PREVIEW', filename, format };
  }

  if ((format === 'TXT' || format === 'MD') && onPreviewText) {
    const text = await blob.text();
    onPreviewText(text, filename);
    return { action: 'PREVIEW', filename, format };
  }

  if (format === 'TXT' || format === 'MD') {
    const blobUrl = URL.createObjectURL(blob);
    const win = window.open(blobUrl, '_blank');
    if (!win) {
      triggerBlobDownload(blob, filename);
      return { action: 'DOWNLOADED', filename, format };
    }
    setTimeout(() => {
      URL.revokeObjectURL(blobUrl);
    }, 60000);
    return { action: 'PREVIEW', filename, format };
  }

  // DOCX, PPTX, or other binary files: download directly
  triggerBlobDownload(blob, filename);
  return { action: 'DOWNLOADED', filename, format };
}

/**
 * Directly trigger authenticated file download for any format
 */
export async function downloadProtectedMaterial(
  courseId: number,
  materialId: number,
  defaultFilename?: string
): Promise<{ filename: string; format: string }> {
  const result = await fetchAuthenticatedMaterial(courseId, materialId, defaultFilename);
  triggerBlobDownload(result.blob, result.filename);
  return { filename: result.filename, format: result.format };
}

/**
 * Helper to trigger browser download of a Blob
 */
function triggerBlobDownload(blob: Blob, filename: string): void {
  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => {
    URL.revokeObjectURL(blobUrl);
  }, 1000);
}
