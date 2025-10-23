// CODE IS FLAWED, NEEDS TO BE REWRITTEN, especially at checkAuthAndRedirect()

// Handles register, login, and create event actions.

import { API_BASE } from "./config.js";

export let token = localStorage.getItem("token") || null;

// Generic JSON API helper
export async function api(path, method = "GET", data = null) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const opts = { method, headers };
  if (data) opts.body = JSON.stringify(data);
  const res = await fetch(API_BASE + path, opts);
  return res.json();
}

// ======= AUTH MANAGEMENT =======

// Decode JWT payload (simple)
function decodeToken(t) {
  try {
    return JSON.parse(atob(t.split(".")[1]));
  } catch {
    return null;
  }
}

// Check authentication and handle redirects
/*
checkAuthAndRedirect() runs whenever a route is loaded.
 > If not logged in, redirects to #/login.
 > If logged in, redirects away from #/login or #/register.
 > Sets sidebar visibility by checking JWT role.
*/
export function checkAuthAndRedirect() {
  token = localStorage.getItem("token");
  const path = window.location.hash;

  if (!token) {
    // if user not logged in, block protected pages
    if (path !== "#/login" && path !== "#/register") {
      window.location.hash = "#/login";
    }
    return;
  }

  // Token exists — decode and handle role visibility
  const payload = decodeToken(token);
  if (!payload) {
    localStorage.removeItem("token");
    window.location.hash = "#/login";
    return;
  }

  const role = payload.role || "attendee";

  // Sidebar role-based visibility
  const roleLinks = document.getElementById("roleLinks");
  if (roleLinks) {
    // if user is admin or organizer, the appropriate sidebar links are displayed, and not if otherwise
    if (["organizer", "admin"].includes(role)) {
      roleLinks.classList.remove("hidden");
    } else {
      roleLinks.classList.add("hidden");
    }
  }

  // If visiting login/register but already logged in, redirect to home
  if (["#/login", "#/register"].includes(path)) {
    window.location.hash = "#/home";
  }
}

// ======= LOGIN / LOGOUT HELPERS =======

// handleLogin() stores token and redirects.
export async function handleLogin(email, password) {
  const res = await api("/auth/login", "POST", { email, password });
  if (res.token) {
    localStorage.setItem("token", res.token);
    token = res.token;
    window.location.hash = "#/home";
  }

  window.location.hash = "#/home";
  window.location.reload(); // refresh to update sidebar/nav

  return res;
}

// handleLogout() clears token and goes to login page.
export function handleLogout() {
  localStorage.removeItem("token");
  token = null;
  window.location.hash = "#/login";
  window.location.reload(); // refresh to hide sidebar
}

// OLD
// // Register
// window.registerUser = async () => {
//   const email = document.querySelector("#regEmail").value;
//   const pass = document.querySelector("#regPass").value;
//   const name = document.querySelector("#regName").value;
//   const res = await api("/auth/register", "POST", { email, password: pass, display_name: name });
//   document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
// };

// // Login
// window.loginUser = async () => {
//   const email = document.querySelector("#logEmail").value;
//   const pass = document.querySelector("#logPass").value;
//   const res = await api("/auth/login", "POST", { email, password: pass });
//   token = res.token;
//   document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
// };

// // Create Event
// window.createEvent = async () => {
//   const title = document.querySelector("#evTitle").value;
//   const start = document.querySelector("#evStart").value;
//   const end = document.querySelector("#evEnd").value;
//   const location = document.querySelector("#evLocation").value;
//   const res = await api("/events/", "POST", { title, start_time: start, end_time: end, location });
//   document.querySelector("#output").textContent = JSON.stringify(res, null, 2);
// };

// // Centralized auth/redirect logic
// export function checkAuthAndRedirect() {
//   const token = localStorage.getItem("token");
//   if (!token) return; // not logged in, stay on login/register

//   // Decode JWT (simple way to read role)
//   const payload = JSON.parse(atob(token.split(".")[1]));
//   const role = payload.role || "attendee";

//   // Redirect by role
//   // if (["attendee", "organizer", "admin"].includes(role)) {
//   //   window.location.hash = "#/home";
//   // }
// }
