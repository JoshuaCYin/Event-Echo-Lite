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

  // Token exists - verify it's valid structure
  const payload = decodeToken(token);
  if (!payload) {
    // Invalid token structure
    localStorage.removeItem("token");
    window.location.hash = "#/landing";
    return false;
  }

  // Check Expiration Client-Side (Optional but good for UX)
  const now = Math.floor(Date.now() / 1000);
  if (payload.exp && payload.exp < now) {
    console.warn("Token expired (client-side check). Logging out.");
    handleLogout();
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
      // If 401, do not update name
      if (res.status === 401) return;

      // Prefer full name if available
      if (res.first_name || res.last_name) {
        // Use first and last name
        userName.textContent = `${res.first_name || ''} ${res.last_name || ''}`.trim();
      } else if (res.email) {
        // Fallback to email prefix
        userName.textContent = res.email.split('@')[0];
      } else {
        // Only show fallback ID if it's NOT an error
        if (!res.error) {
          userName.textContent = `User #${payload.sub}`;
        }
      }
    }).catch(err => {
      console.log("Could not fetch user info:", err);
      // Only fallback on network errors, not auth errors
      // userName.textContent = `User #${payload.sub}`; 
    });
  }
}

// Login handler
export async function handleLogin(email, password) {
  try {
    const res = await api("/auth/login", "POST", { email, password });

    // On success, store token
    if (res.token) {
      localStorage.setItem("token", res.token);
      token = res.token;

      // --- Role-based Redirect on Login ---
      const payload = decodeToken(res.token);
      if (payload.role === 'admin' || payload.role === 'organizer') {
        window.location.hash = "#/dashboard";
      } else {
        window.location.hash = "#/calendar";
      }

      return { success: true, ...res };
    }

    // Handle login errors
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

// Konami
const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
let konamiIndex = 0;

document.addEventListener('keydown', (e) => {
  if (e.key === konamiCode[konamiIndex]) {
    konamiIndex++;
    if (konamiIndex === konamiCode.length) {
      konamiIndex = 0;
      showVerseToast();
    }
  } else {
    konamiIndex = 0;
  }
});

// Amen
let amenBuffer = '';
const amenCode = 'amen';

document.addEventListener('keydown', (e) => {
  // Only track letters
  if (e.key.length === 1 && e.key.match(/[a-z]/i)) {
    amenBuffer += e.key.toLowerCase();
    if (amenBuffer.length > amenCode.length) {
      amenBuffer = amenBuffer.slice(-amenCode.length);
    }
    if (amenBuffer === amenCode) {
      showVerseToast();
      amenBuffer = ''; // Reset buffer
    }
  }
});

function showVerseToast() {
  const verses = [
    "For I know the plans I have for you, declares the Lord, plans to prosper you and not to harm you, plans to give you hope and a future. - Jeremiah 29:11",
    "Trust in the Lord with all your heart and lean not on your own understanding. - Proverbs 3:5",
    "I can do all this through him who gives me strength. - Philippians 4:13",
    "But those who hope in the Lord will renew their strength. They will soar on wings like eagles. - Isaiah 40:31",
    "Be strong and courageous. Do not be afraid; do not be discouraged, for the Lord your God will be with you wherever you go. - Joshua 1:9",
    "Teach us to number our days, that we may gain a heart of wisdom. - Psalm 90:12"
  ];
  const randomVerse = verses[Math.floor(Math.random() * verses.length)];

  // Create toast element
  const toast = document.createElement('div');
  toast.style.position = 'fixed';
  toast.style.bottom = '20px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.backgroundColor = 'var(--primary-color, #6f42c1)';
  toast.style.color = 'white';
  toast.style.padding = '1rem 2rem';
  toast.style.borderRadius = '8px';
  toast.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
  toast.style.zIndex = '9999';
  toast.style.textAlign = 'center';
  toast.style.fontSize = '1.1rem';
  toast.style.maxWidth = '90%';
  toast.style.animation = 'fadeInOut 4s forwards';

  // Add animation styles if not present
  if (!document.getElementById('toast-style')) {
    const style = document.createElement('style');
    style.id = 'toast-style';
    style.innerHTML = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translate(-50%, 20px); }
                10% { opacity: 1; transform: translate(-50%, 0); }
                90% { opacity: 1; transform: translate(-50%, 0); }
                100% { opacity: 0; transform: translate(-50%, -20px); }
            }
        `;
    document.head.appendChild(style);
  }

  toast.textContent = randomVerse;
  document.body.appendChild(toast);

  setTimeout(() => {
    document.body.removeChild(toast);
  }, 5000);
}