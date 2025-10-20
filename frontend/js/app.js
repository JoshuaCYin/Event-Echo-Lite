// CODE IS FLAWED, NEEDS TO BE REWRITTEN, especially at checkAuthAndRedirect()

// Handles register, login, and create event actions.

import { API_BASE } from "./config.js";

let token = null;

// Helper to send JSON requests
async function api(path, method = "GET", data = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const opts = { method, headers };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(API_BASE + path, opts);
  return res.json();
}

// Register
window.registerUser = async () => {
  // Info fields
  const email = document.querySelector("#regEmail").value;
  const pass = document.querySelector("#regPass").value;
  const name = document.querySelector("#regName").value;

  // Send
  const res = await api("/auth/register", "POST", { email, password: pass, display_name: name });
  document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
};

// Login
window.loginUser = async () => {
  // Info fields
  const email = document.querySelector("#logEmail").value;
  const pass = document.querySelector("#logPass").value;

  // Send
  const res = await api("/auth/login", "POST", {
    email,
    password: pass
  });
  token = res.token;
  document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
};

// Create Event
window.createEvent = async () => {
  // Info fields
  const title = document.querySelector("#evTitle").value;
  const start = document.querySelector("#evStart").value;
  const end = document.querySelector("#evEnd").value;
  const location = document.querySelector("#evLocation").value;

  // Send
  const res = await api("/events/", "POST", {
    title,
    start_time: start,
    end_time: end,
    location
  });
  document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
};

// Centralized auth/redirect logic
export function checkAuthAndRedirect() {
  const token = localStorage.getItem("token");
  if (!token) return; // not logged in, stay on login/register

  // Decode JWT (simple way to read role)
  const payload = JSON.parse(atob(token.split(".")[1]));
  const role = payload.role || "attendee";

  // Redirect by role
  // if (["attendee", "organizer", "admin"].includes(role)) {
  //   window.location.hash = "#/home";
  // }
}
