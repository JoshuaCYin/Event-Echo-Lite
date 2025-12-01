import { API_BASE } from "./config.js";

export async function api(path, method = "GET", data = null, token = null) {
  const headers = { "Content-Type": "application/json" };

  // Auto-detect token if not explicitly provided
  if (!token) {
    token = localStorage.getItem("token");
  }

  // Include Authorization header if token exists
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const opts = { method, headers };
  if (data) opts.body = JSON.stringify(data);

  try {
    const res = await fetch(API_BASE + path, opts);

    if (res.status === 401) {
      // Special case: Login 401 means invalid credentials, not session expiry
      if (path === "/auth/login") {
        const errData = await res.json().catch(() => ({}));
        let errorMsg = errData.error || "Invalid email or password";
        // Map generic backend error to user-friendly message
        if (errorMsg === "Invalid credentials") {
          errorMsg = "Invalid email or password";
        }
        return {
          error: errorMsg,
          status: 401
        };
      }

      console.warn("Session expired (401). Logging out...");
      localStorage.removeItem("token");

      // Redirect to login immediately
      window.location.hash = "#/login";

      // Return a structured error so the caller knows what happened
      return { error: "Session expired", status: 401 };
    }

    // Handle other non-OK statuses (400, 403, 500)
    if (!res.ok) {
      // Try to parse error message from JSON, fallback to status text
      const errData = await res.json().catch(() => ({}));
      return {
        error: errData.error || `Request failed (${res.status})`,
        status: res.status
      };
    }

    // Success
    return await res.json();

  } catch (error) {
    console.error("API Network Error:", error);
    return { error: "Network error - check your connection", status: 0 };
  }
}