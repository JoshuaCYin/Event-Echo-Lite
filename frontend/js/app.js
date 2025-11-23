// Cleaned up authentication and user management
import { api } from "./api.js";
import { API_BASE } from "./config.js";

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
  const path = window.location.hash || "#/landing";
  
  // List of public pages that don't require auth
  const publicPages = [
    "#/login", 
    "#/register", 
    "#/", 
    "#/landing", 
    "#/landing-events", 
    "#/landing-features", 
    "#/landing-about"
  ];
  
  if (!token) {
    // Not logged in - only redirect if trying to access protected page
    if (!publicPages.includes(path) && path !== "") {
      window.location.hash = "#/landing"; 
      return false;
    }
    return false; // User is on a public page, no redirect needed
  }
  
  // Token exists - verify it's valid
  const payload = decodeToken(token);
  if (!payload) {
    // Invalid token
    localStorage.removeItem("token");
    window.location.hash = "#/landing";
    return false;
  }

  // --- Role-based Redirect Logic ---
  const role = payload.role;
  
  // If visiting login/register but already logged in, redirect to app home
  if (["#/login", "#/register"].includes(path)) {
    if (role === 'admin' || role === 'organizer') {
        window.location.hash = "#/dashboard"; // Admin/Org go to Dashboard
    } else {
        window.location.hash = "#/calendar"; // Attendees go to Calendar
    }
    return true;
  }
  
  return true; // User is authenticated and on a valid page
}

// Update user info in sidebar
export function updateUserInfo() {
  const token = localStorage.getItem("token");
  if (!token) return;
  
  const payload = decodeToken(token);
  if (!payload) return;
  
  const userName = document.getElementById("userName");
  const userRole = document.getElementById("userRole");
  
  // Set default role text
  if (userRole) {
    const roleText = {
      'admin': 'Administrator',
      'organizer': 'Event Organizer',
      'attendee': 'Attendee'
    };
    userRole.textContent = roleText[payload.role] || 'Attendee';
  }

  // Fetch full user info for display name
  if (userName) {
    api("/auth/me", "GET", null, token).then(res => {
      if (res.first_name || res.last_name) {
        // Use first and last name
        userName.textContent = `${res.first_name || ''} ${res.last_name || ''}`.trim();
      } else if (res.email) {
        // Fallback to email prefix
        userName.textContent = res.email.split('@')[0];
      } else {
        // Fallback to user ID from token
         userName.textContent = `User #${payload.sub}`;
      }
    }).catch(err => {
      console.log("Could not fetch user info:", err);
      // Fallback to user ID from token
      userName.textContent = `User #${payload.sub}`;
    });
  }
}

// Login handler
export async function handleLogin(email, password) {
  try {
    const res = await api("/auth/login", "POST", { email, password });
    
    if (res.token) {
      localStorage.setItem("token", res.token);
      token = res.token;
      
      // --- Role-based Redirect on Login ---
      const payload = decodeToken(res.token);
      if (payload.role === 'admin' || payload.role === 'organizer') {
        window.location.hash = "#/dashboard"; // Admin/Org go to Dashboard
      } else {
        window.location.hash = "#/calendar"; // Attendees go to Calendar
      }
      
      return { success: true, ...res };
    }
    
    if (res.error) {
      return { success: false, error: res.error };
    }
    
    return { success: false, error: "Login failed - no token received" };
  } catch (error) {
    console.error("Login error:", error);
    return { success: false, error: "Network error - check if backend is running" };
  }
}

// Logout handler
export function handleLogout() {
  localStorage.removeItem("token");
  token = null;
  window.location.hash = "#/landing"; // Redirect to landing page on logout
  // Force a reload to clear all state
  window.location.reload();
}

// Check if user is logged in and update landing navbar buttons
export function updateNavbarForAuth() {
  const token = localStorage.getItem('token');
  const navbarActions = document.getElementById('navbarActions');
  const navbarMobileActions = document.getElementById('navbarMobileActions');
  
  const payload = decodeToken(token);
  let dashboardUrl = "#/calendar"; // Default for attendees
  if (payload && (payload.role === 'admin' || payload.role === 'organizer')) {
    dashboardUrl = "#/dashboard"; // Admin/Org go to Dashboard
  }

  if (token) {
    // User is logged in - show "Go to App" button
    if (navbarActions) {
      navbarActions.innerHTML = `
        <a href="${dashboardUrl}" class="navbar-btn navbar-btn-primary">Go to App</a>
      `;
    }
    
    if (navbarMobileActions) {
      navbarMobileActions.innerHTML = `
        <a href="${dashboardUrl}" class="navbar-btn navbar-btn-primary" style="color: #5a4dbf;">Go to App</a>
      `;
    }
  } else {
    // User is logged out - show default "Log In" / "Sign Up" buttons
     if (navbarActions) {
      navbarActions.innerHTML = `
        <a href="#/login" class="navbar-btn navbar-btn-secondary">Log In</a>
        <a href="#/register" class="navbar-btn navbar-btn-primary">Sign Up</a>
      `;
    }
    
    if (navbarMobileActions) {
      navbarMobileActions.innerHTML = `
        <a href="#/login" class="navbar-btn navbar-btn-secondary">Log In</a>
        <a href="#/register" class="navbar-btn navbar-btn-primary" style="color: #5a4dbf;">Sign Up</a>
      `;
    }
  }
  
  // Also listen for storage changes (e.g., login/logout in another tab)
  window.addEventListener('storage', (e) => {
    if (e.key === 'token') {
      updateNavbarForAuth();
    }
  });
}

