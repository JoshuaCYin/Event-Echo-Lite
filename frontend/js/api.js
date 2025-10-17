// Reusable backend call function

import { API_BASE } from "./config.js";

export async function api(path, method = "GET", data = null, token = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const opts = { method, headers };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(API_BASE + path, opts);
  return res.json();
}