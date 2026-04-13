"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2, Zap, AlertTriangle } from "lucide-react";
import { API_URL } from "@/lib/utils";

const PUBLIC_PATHS = ["/login", "/signup"];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecking(false);
      setAuthenticated(true);
      return;
    }

    async function checkAuth() {
      // First check if backend is reachable
      let backendAvailable = false;
      try {
        const healthRes = await fetch(`${API_URL}/api/health`, { signal: AbortSignal.timeout(3000) });
        backendAvailable = healthRes.ok;
      } catch {
        // Backend unreachable — allow access in dev mode
        setBackendDown(true);
        setAuthenticated(true);
        setChecking(false);
        return;
      }

      const token = localStorage.getItem("access_token");

      if (!token) {
        if (backendAvailable) {
          // Backend is up, auth is required — redirect to login
          router.replace("/login");
        } else {
          // No backend — allow access (dev mode)
          setAuthenticated(true);
        }
        setChecking(false);
        return;
      }

      // Validate token
      try {
        const res = await fetch(`${API_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          setAuthenticated(true);
        } else if (res.status === 401) {
          // Token invalid — try refresh
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
                setAuthenticated(true);
              } else {
                localStorage.removeItem("access_token");
                localStorage.removeItem("refresh_token");
                router.replace("/login");
              }
            } catch {
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token");
              router.replace("/login");
            }
          } else {
            localStorage.removeItem("access_token");
            router.replace("/login");
          }
        } else {
          // 500 or other error — backend issue, not auth issue
          // If backend is available but auth endpoint errors, allow with warning
          setAuthenticated(true);
        }
      } catch {
        setAuthenticated(true);
      }

      setChecking(false);
    }

    checkAuth();
  }, [pathname, router]);

  if (checking && !PUBLIC_PATHS.includes(pathname)) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-zinc-950">
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/20">
            <Zap className="h-6 w-6 text-violet-400" />
          </div>
          <Loader2 className="h-5 w-5 animate-spin text-zinc-500" />
        </div>
      </div>
    );
  }

  if (!authenticated && !PUBLIC_PATHS.includes(pathname)) {
    return null;
  }

  return <>{children}</>;
}
