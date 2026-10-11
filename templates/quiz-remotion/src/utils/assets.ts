import { staticFile } from "remotion";

/**
 * Resolves an asset path to a valid Remotion URL.
 * Handles remote URLs, relative paths via staticFile, and normalization.
 */
export function resolveAssetUrl(pathOrUrl: string | null | undefined): string {
  if (!pathOrUrl) return "";

  // Remote URLs or data URIs
  if (
    pathOrUrl.startsWith("http://") ||
    pathOrUrl.startsWith("https://") ||
    pathOrUrl.startsWith("data:") ||
    pathOrUrl.startsWith("blob:")
  ) {
    return pathOrUrl;
  }

  // Normalize Windows backslashes
  const normalized = pathOrUrl.replace(/\\/g, "/");

  // If path is already inside Remotion staticFile convention (starts with slash or relative)
  // Check if it looks like an absolute Windows path (e.g. C:/...) or absolute POSIX path (/Users/...)
  const isWindowsAbsolute = /^[a-zA-Z]:\//.test(normalized);
  const isPosixAbsolute = normalized.startsWith("/") && !normalized.startsWith("/public");

  if (isWindowsAbsolute || isPosixAbsolute) {
    // If orchestrator stages files in public dir, we extract relative path or filename
    // Or if disabled web security is used, browser might accept file:// protocol
    const basename = normalized.split("/").pop() || "";
    // If passed absolute path, fallback to staticFile of the basename
    try {
      return staticFile(basename);
    } catch {
      return `file:///${normalized.replace(/^file:\/\//, "")}`;
    }
  }

  // Remove leading slash if any before passing to staticFile
  const cleanPath = normalized.startsWith("/") ? normalized.slice(1) : normalized;
  try {
    return staticFile(cleanPath);
  } catch {
    return `/${cleanPath}`;
  }
}
