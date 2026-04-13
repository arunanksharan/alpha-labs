import { API_URL } from "@/lib/utils";

/**
 * Authenticated fetch wrapper.
 * Auto-attaches JWT from localStorage. On 401, attempts refresh.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = path.startsWith("http") ? path : `${API_URL}${path}`;

  let res = await fetch(url, { ...options, headers });

  // If 401 and we have a refresh token, try refreshing
  if (res.status === 401 && typeof window !== "undefined") {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        const refreshRes = await fetch(`${API_URL}/api/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshRes.ok) {
          const data = await refreshRes.json();
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);

          // Retry original request with new token
          headers["Authorization"] = `Bearer ${data.access_token}`;
          res = await fetch(url, { ...options, headers });
        } else {
          // Refresh failed — clear tokens
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = (process.env.NEXT_PUBLIC_BASE_PATH || "") + "/login";
        }
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.location.href = (process.env.NEXT_PUBLIC_BASE_PATH || "") + "/login";
      }
    }
  }

  return res;
}
