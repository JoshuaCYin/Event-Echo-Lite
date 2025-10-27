// Cleaned up authentication and user management
import { api } from "./api.js";

export let token = localStorage.getItem("token") || null;

// Decode JWT payload
function decodeToken(t) {
  try {
    return JSON.parse(atob(t.split(".")[1]));
  } catch {
    return null;
  }
}

// Get role from current token
export function getRoleFromToken() {
  const token = localStorage.getItem("token");
  if (!token) return null;
  
  const payload = decodeToken(token);
  return payload ? payload.role : null;
}

// Check authentication and redirect if needed
export function checkAuthAndRedirect() {
  token = localStorage.getItem("token");
  const path = window.location.hash;
  
  // List of public pages that don't require auth
  const publicPages = [
    "#/", 
    "#/landing", 
    "#/landing-events", 
    "#/landing-calendar", 
    "#/landing-about",
    "#/login", 
    "#/register"
  ];
  
  if (!token) {
    // Not logged in - only redirect if trying to access protected page
    if (!publicPages.includes(path) && path !== "") {
      window.location.hash = "#/landing";
      return false;
    }
    return false;
  }
  
  // Token exists - verify it's valid
  const payload = decodeToken(token);
  if (!payload) {
    // Invalid token
    localStorage.removeItem("token");
    window.location.hash = "#/landing";
    return false;
  }
  
  // If visiting login/register but already logged in, redirect to home
  if (["#/login", "#/register"].includes(path)) {
    window.location.hash = "#/home";
    return true;
  }
  
  return true;
}

// Update user info in sidebar
export function updateUserInfo() {
  const token = localStorage.getItem("token");
  if (!token) return;
  
  const payload = decodeToken(token);
  if (!payload) return;
  
  const userName = document.getElementById("userName");
  const userRole = document.getElementById("userRole");
  
  // Fetch user info from /auth/me since JWT only has id and role
  if (userName) {
    // Show user ID temporarily
    userName.textContent = `User #${payload.sub}`;
    
    // Fetch full user info
    api("/auth/me", "GET", null, token).then(res => {
      if (res.display_name) {
        userName.textContent = res.display_name;
      } else if (res.email) {
        userName.textContent = res.email.split('@')[0];
      }
    }).catch(err => {
      console.log("Could not fetch user info:", err);
    });
  }
  
  if (userRole) {
    const roleText = {
      'admin': 'Administrator',
      'organizer': 'Event Organizer',
      'attendee': 'Attendee'
    };
    userRole.textContent = roleText[payload.role] || 'Attendee';
  }
}

// Login handler
export async function handleLogin(email, password) {
  try {
    const res = await api("/auth/login", "POST", { email, password });
    
    // Flask backend returns: {id, role, token}
    if (res.token) {
      localStorage.setItem("token", res.token);
      token = res.token;
      window.location.hash = "#/home";
      return { success: true, ...res };
    }
    
    // Check for error field
    if (res.error) {
      return { success: false, error: res.error };
    }
    
    return { success: false, error: "Login failed - no token received" };
  } catch (error) {
    console.error("Login error:", error);
    return { success: false, error: "Network error - check if backend is running on port 5000" };
  }
}

// Logout handler
export function handleLogout() {
  localStorage.removeItem("token");
  token = null;
  window.location.hash = "#/landing";
}