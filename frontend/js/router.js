// Updated router with landing pages and proper sidebar visibility
import { loadPage } from "./utils.js";
import { checkAuthAndRedirect, updateUserInfo, getRoleFromToken } from "./app.js";

const routes = {
  // Landing pages (public)
  "": "pages/landing.html",
  "#/": "pages/landing.html",
  "#/landing": "pages/landing.html",
  "#/landing-events": "pages/landing-events.html",
  "#/landing-calendar": "pages/landing-calendar.html",
  "#/landing-about": "pages/landing-about.html",
  
  // Auth pages
  "#/login": "pages/login.html",
  "#/register": "pages/register.html",
  
  // Authenticated pages
  "#/home": "pages/home.html",
  "#/events": "pages/events.html",
  "#/calendar": "pages/calendar.html",
  "#/create-event": "pages/create-event.html",
  "#/planning": "pages/planning.html",
  "#/ai-chat": "pages/ai-chat.html",
  "#/profile": "pages/profile.html"
};

const landingPages = ["", "#/", "#/landing", "#/landing-events", "#/landing-calendar", "#/landing-about"];
const authPages = ["#/login", "#/register"];
const protectedPages = ["#/home", "#/events", "#/calendar", "#/create-event", "#/planning", "#/ai-chat", "#/profile"];
const adminOrganizerOnly = ["#/create-event", "#/planning"];

async function loadLandingNavbar() {
  const navbarContainer = document.getElementById("landingNavbarContainer");
  if (!navbarContainer) return;
  
  try {
    const response = await fetch("pages/landing-index.html");
    const html = await response.text();
    navbarContainer.innerHTML = html;
    
    // Re-execute scripts in the navbar
    navbarContainer.querySelectorAll("script[type='module']").forEach((oldScript) => {
      const newScript = document.createElement("script");
      newScript.type = "module";
      newScript.textContent = oldScript.textContent;
      navbarContainer.appendChild(newScript);
    });
  } catch (error) {
    console.error("Failed to load landing navbar:", error);
  }
}

async function router() {
  let path = window.location.hash || "#/landing";
  
  // Normalize empty hash to #/landing
  if (path === "" || path === "#") {
    path = "#/landing";
    window.location.hash = path;
  }
  
  console.log("Router: Current path:", path);
  
  // Check if route exists
  if (!routes[path]) {
    console.warn("Route not found:", path, "- redirecting to landing");
    window.location.hash = "#/landing";
    return;
  }
  
  // Get elements
  const sidebar = document.getElementById("sidebar");
  const mobileHeader = document.getElementById("mobileHeader");
  const mainContent = document.querySelector(".main-content");
  const landingNavbarContainer = document.getElementById("landingNavbarContainer");
  
  // Check if user is authenticated
  const token = localStorage.getItem("token");
  const isAuthenticated = !!token;
  
  console.log("Router: Is authenticated:", isAuthenticated);
  
  // Determine page type
  const isLandingPage = landingPages.includes(path);
  const isAuthPage = authPages.includes(path);
  const isProtectedPage = protectedPages.includes(path);
  
  console.log("Router: Page type - Landing:", isLandingPage, "Auth:", isAuthPage, "Protected:", isProtectedPage);
  
  // Handle landing pages
  if (isLandingPage) {
    console.log("Router: Loading landing page");
    // Show landing navbar, hide app sidebar
    if (sidebar) sidebar.style.display = "none";
    if (mobileHeader) mobileHeader.style.display = "none";
    if (landingNavbarContainer) {
      landingNavbarContainer.style.display = "block";
      await loadLandingNavbar();
    }
    
    if (mainContent) {
      mainContent.style.marginLeft = "0";
      mainContent.classList.remove("auth-page");
      mainContent.classList.add("landing-content");
    }
    
    await loadPage(routes[path]);
    return;
  }
  
  // Handle auth pages (login/register)
  if (isAuthPage) {
    console.log("Router: Loading auth page");
    // If already logged in, redirect to home
    if (isAuthenticated) {
      console.log("Router: Already authenticated, redirecting to home");
      window.location.hash = "#/home";
      return;
    }
    
    // Hide all navigation
    if (sidebar) sidebar.style.display = "none";
    if (mobileHeader) mobileHeader.style.display = "none";
    if (landingNavbarContainer) landingNavbarContainer.style.display = "none";
    
    if (mainContent) {
      mainContent.style.marginLeft = "0";
      mainContent.classList.add("auth-page");
      mainContent.classList.remove("landing-content");
    }
    
    await loadPage(routes[path]);
    return;
  }
  
  // Handle protected pages
  if (isProtectedPage) {
    console.log("Router: Loading protected page");
    // Check authentication
    if (!checkAuthAndRedirect()) {
      console.log("Router: Not authenticated, redirecting to landing");
      window.location.hash = "#/landing";
      return;
    }
    
    // Check role-based access for admin/organizer pages
    if (adminOrganizerOnly.includes(path)) {
      const role = getRoleFromToken();
      console.log("Router: Checking role for protected page. User role:", role);
      if (role !== "admin" && role !== "organizer") {
        alert("You don't have permission to access this page.");
        window.location.hash = "#/home";
        return;
      }
    }
    
    // Show app sidebar, hide landing navbar
    if (landingNavbarContainer) landingNavbarContainer.style.display = "none";
    if (sidebar) sidebar.style.display = "flex";
    
    // Handle mobile header visibility
    if (mobileHeader) {
      if (window.innerWidth <= 768) {
        mobileHeader.style.display = "flex";
      } else {
        mobileHeader.style.display = "none";
      }
    }
    
    if (mainContent) {
      mainContent.style.marginLeft = "";
      mainContent.classList.remove("auth-page");
      mainContent.classList.remove("landing-content");
    }
    
    // Update user info in sidebar
    updateUserInfo();
    
    // Update active nav item
    updateActiveNav(path);
    
    await loadPage(routes[path]);
    return;
  }
  
  // Default: redirect to landing
  console.log("Router: No match, redirecting to landing");
  window.location.hash = "#/landing";
}

// Handle window resize for mobile header
window.addEventListener('resize', () => {
  const mobileHeader = document.getElementById("mobileHeader");
  const path = window.location.hash || "#/landing";
  const isProtectedPage = protectedPages.includes(path);
  
  if (isProtectedPage && mobileHeader) {
    if (window.innerWidth <= 768) {
      mobileHeader.style.display = "flex";
    } else {
      mobileHeader.style.display = "none";
    }
  }
});

function updateActiveNav(path) {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('href') === path) {
      item.classList.add('active');
    }
  });
}

// Initialize router
console.log("Router: Initializing...");
window.addEventListener("hashchange", () => {
  console.log("Router: Hash changed to", window.location.hash);
  router();
});
window.addEventListener("DOMContentLoaded", () => {
  console.log("Router: DOM loaded, initial route:", window.location.hash);
  router();
});

// Call router immediately if DOM is already loaded
if (document.readyState === "loading") {
  console.log("Router: Waiting for DOM...");
} else {
  console.log("Router: DOM already loaded, calling router now");
  router();
}