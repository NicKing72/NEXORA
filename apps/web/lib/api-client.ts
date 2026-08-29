import { translateApiError } from "@/lib/i18n";

const API_ORIGIN = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ErrorPayload = { error?: { code?: string; message?: string }; detail?: string };

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ORIGIN}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ErrorPayload;
    throw new Error(translateApiError(payload.error?.code));
  }
  return response.json() as Promise<T>;
}
