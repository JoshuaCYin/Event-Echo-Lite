// Cleaned up authentication and user management
import { api } from "./api.js";  // Use the api.js function instead

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
    "#/login", 
    "#/register", 
    "#/", 
    "#/landing", 
    "#/landing-events", 
    "#/landing-calendar", 
    "#/landing-about"
  ];
  
  if (!token) {
    // Not logged in - only redirect if trying to access protected page
    if (!publicPages.includes(path) && path !== "") {
      // **FIX:** Redirect to landing page, not login
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
    // **FIX:** Redirect to landing page, not login
    window.location.hash = "#/landing";
    return false;
  }
  
  // If visiting login/register but already logged in, redirect to app home
  if (["#/login", "#/register"].includes(path)) {
    // Redirect to app home or calendar
    window.location.hash = "#/home"; 
    return true;
  }
  
  return true; // User is authenticated and on a valid page
}

// Update user info in sidebar
export function updateUserInfo() {
  // ... (this function is unchanged)
  const token = localStorage.getItem("token");
  if (!token) return;
  
  const payload = decodeToken(token);
  if (!payload) return;
  
  const userName = document.getElementById("userName");
  const userRole = document.getElementById("userRole");
  
  if (userName) {
    userName.textContent = `User #${payload.sub}`;
    
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
  // ... (this function is unchanged)
  try {
    const res = await api("/auth/login", "POST", { email, password });
    
    if (res.token) {
      localStorage.setItem("token", res.token);
      token = res.token;
      window.location.hash = "#/home"; // Redirect to app home on login
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
}


// **NEW FUNCTION (Moved from landing/index.html)**
// Check if user is logged in and update landing navbar buttons
export function updateNavbarForAuth() {
  const token = localStorage.getItem('token');
  const navbarActions = document.getElementById('navbarActions');
  const navbarMobileActions = document.getElementById('navbarMobileActions');
  
  if (token) {
    // User is logged in - show "Go to Dashboard" button
    if (navbarActions) {
      navbarActions.innerHTML = `
        <a href="#/home" class="navbar-btn navbar-btn-primary">Go to Dashboard</a>
      `;
    }
    
    if (navbarMobileActions) {
      navbarMobileActions.innerHTML = `
        <a href="#/home" class="navbar-btn navbar-btn-primary" style="color: #5a4dbf;">Go to Dashboard</a>
      `;
    }
  } else {
    // User is logged out - show default "Login" / "Sign Up" buttons
     if (navbarActions) {
      navbarActions.innerHTML = `
        <a href="#/login" class="navbar-btn navbar-btn-secondary">Login</a>
        <a href="#/register" class="navbar-btn navbar-btn-primary">Sign Up</a>
      `;
    }
    
    if (navbarMobileActions) {
      navbarMobileActions.innerHTML = `
        <a href="#/login" class="navbar-btn navbar-btn-secondary">Login</a>
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