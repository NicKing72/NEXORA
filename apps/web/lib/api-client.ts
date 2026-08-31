import { translateApiError } from "@/lib/i18n";

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ErrorPayload = { error?: { code?: string; message?: string }; detail?: string };

type ApiRequestOptions = { fallbackMessage?: string };

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  options?: ApiRequestOptions,
): Promise<T> {
  const response = await fetch(`${API_ORIGIN}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ErrorPayload;
    const message = payload.error?.code
      ? translateApiError(payload.error.code)
      : options?.fallbackMessage ?? payload.error?.message ?? payload.detail;
    throw new Error(message || translateApiError());
  }
  return response.json() as Promise<T>;
}
