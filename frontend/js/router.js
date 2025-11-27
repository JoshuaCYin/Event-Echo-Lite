// Main frontend router
import { loadPage } from "./utils.js";
import { checkAuthAndRedirect, updateUserInfo, updateNavbarForAuth, getRoleFromToken } from "./app.js";

const routes = {
  // --- Landing/Public Routes ---
  "#/": "landing/home.html",
  "#/landing": "landing/home.html",
  "#/landing-events": "landing/events.html",
  "#/landing-features": "landing/features.html",
  "#/landing-about": "landing/about.html",

  // --- Auth Routes ---
  "#/login": "pages/login.html",
  "#/register": "pages/register.html",
  
  // --- App/Protected Routes ---
  "#/dashboard": "pages/dashboard.html", // Admin/Org home
  "#/calendar": "pages/events.html", // Attendee home / Event Hub DEPRECATED
  "#/events": "pages/events.html",  // Event Hub
  "#/admin": "pages/admin.html", // Admin management

  // Event Creation Flow
  "#/create-event": "pages/create-event.html",   // The choice page
  "#/event-form": "pages/event-form.html",     // The standard form
  "#/event-wizard": "pages/event-wizard.html",  // The wizard form

  "#/planning": "pages/planning.html",
  "#/ai-chat": "pages/ai-chat.html",
  "#/profile": "pages/profile.html",
  "#/discover": "pages/discover.html",

  "#/profile-view": "pages/profile-view.html" // Read-only view of other users
};

// --- Public/Landing Pages ---
const landingPages = [
  "#/", 
  "#/landing", 
  "#/landing-events", 
  "#/landing-features",
  "#/landing-about"
];

// --- Auth Pages ---
const authPages = [
  "#/login",
  "#/register"
];

// --- Role-protected Pages ---
const adminOnlyPages = [
    "#/dashboard",
    "#/planning",
    "#/admin"
    // "/event-form" is open to all, but backend/form logic handles permissions
];

async function router() {
  let hash = window.location.hash || "#/landing"; // Default to landing
  let path = hash.split('?')[0]; // Extract base path without query params

  // Handle 404
  if (!routes[path]) { // This check now uses the base path
    path = "#/landing"; // Default to landing page
    window.location.hash = path;
  }
  
  // Handle 404
  if (!routes[path]) {
    path = "#/landing"; // Default to landing page
    window.location.hash = path;
  }
  
  // Determine page type
  const isLandingPage = landingPages.includes(path);
  const isAuthPage = authPages.includes(path);
  
  // Get UI elements
  const landingNavbar = document.getElementById("landingNavbar");
  const sidebar = document.getElementById("sidebar");
  const mobileHeader = document.getElementById("mobileHeader");
  const mainContent = document.querySelector(".main-content");
  
  updateNavbarForAuth(); // Update navbar links based on auth status

  if (isLandingPage || isAuthPage) {
    // --- ON A PUBLIC/LANDING OR AUTH PAGE ---
    if (landingNavbar) landingNavbar.style.display = "flex";
    if (sidebar) sidebar.style.display = "none";
    if (mobileHeader) mobileHeader.style.display = "none";
    
    // Adjust main content layout
    if (mainContent) {
      mainContent.style.marginLeft = "0";
      
      if (isAuthPage) {
        mainContent.classList.add("auth-layout");
        mainContent.classList.remove("landing-layout");
      } else {
        mainContent.classList.add("landing-layout");
        mainContent.classList.remove("auth-layout");
      }
    }
    
    await loadPage(routes[path]);

  } else {
    // --- ON A PROTECTED/APP PAGE ---
    
    const isAuthenticated = checkAuthAndRedirect(); // Redirects if not auth'd
    
    if (isAuthenticated) {
      // --- Role-based Page Access ---
      const role = getRoleFromToken();
      if (adminOnlyPages.includes(path) && (role !== 'admin' && role !== 'organizer')) {
          // Attendee trying to access admin page
          window.location.hash = "#/calendar"; // Redirect to their default
          return; // Stop execution
      }

      // Show/hide UI elements
      if (landingNavbar) landingNavbar.style.display = "none";
      if (sidebar) sidebar.style.display = "flex";
      if (mobileHeader) {
        if (window.innerWidth <= 768) { // Mobile breakpoint
          mobileHeader.style.display = "flex"; // Show on mobile
        } else {
          mobileHeader.style.display = "none"; // Hide on desktop
        }
      }
      
      // Reset main content layout
      if (mainContent) {
        mainContent.style.marginLeft = "";
        mainContent.classList.remove("auth-layout");
        mainContent.classList.remove("landing-layout");
      }
      
      // Update user info in sidebar
      updateUserInfo();
      await loadPage(routes[path]);
    }
  }
  
  updateActiveNav(path);
}

// Handle mobile header visibility on resize
window.addEventListener('resize', () => {
  const mobileHeader = document.getElementById("mobileHeader");
  const path = window.location.hash || "#/landing";
  const isPublicPage = landingPages.includes(path) || authPages.includes(path);
  
  if (!isPublicPage && mobileHeader) {
    if (window.innerWidth <= 768) {
      mobileHeader.style.display = "flex";
    } else {
      mobileHeader.style.display = "none";
    }
  }
});

// Update active nav items based on current path
function updateActiveNav(path) {
  const basePath = path.split('?')[0];
  
  // Update sidebar nav items
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.classList.remove('active');
    // Special handling for merged "Events & Calendar" tab
    if (basePath === '#/calendar' || basePath === '#/events') {
        if (item.getAttribute('href') === '#/calendar') {
            item.classList.add('active');
        }
    // Special handling for new Create flow
    } else if (basePath === '#/event-form' || basePath === '#/event-wizard') {
        if (item.getAttribute('href') === '#/create-event') {
            item.classList.add('active');
        }
    } else if (item.getAttribute('href') === basePath) {
      item.classList.add('active');
    }
  });
  
  // Update landing navbar links (both desktop and mobile)
  const landingNavLinks = document.querySelectorAll('.navbar-links a, .navbar-mobile-menu a');
  landingNavLinks.forEach(link => {
    link.classList.remove('active');
    const navPage = link.getAttribute('data-nav');
    
    if ((basePath === '#/landing' || basePath === '#/') && navPage === 'landing') {
      link.classList.add('active');
    } else if (basePath === '#/landing-events' && navPage === 'events') {
      link.classList.add('active');
    } else if (basePath === '#/landing-features' && navPage === 'features') {
      link.classList.add('active');
    } else if (basePath === '#/landing-about' && navPage === 'about') {
      link.classList.add('active');
    }
  });
}

function initializeLandingNavToggle() {
  const hamburger = document.getElementById('navbarHamburger');
  const mobileMenu = document.getElementById('navbarMobileMenu');

  if (hamburger && mobileMenu) {
    hamburger.addEventListener('click', (e) => {
      e.stopPropagation();
      hamburger.classList.toggle('active');
      mobileMenu.classList.toggle('active');
    });

    // Use event delegation on the menu itself
    mobileMenu.addEventListener('click', (e) => {
        // Check if the clicked element is a link
        if (e.target.tagName === 'A' || e.target.closest('a')) {
            hamburger.classList.remove('active');
            mobileMenu.classList.remove('active');
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!mobileMenu.contains(e.target) && !hamburger.contains(e.target)) {
        hamburger.classList.remove('active');
        mobileMenu.classList.remove('active');
      }
    });
  }
}

// Run router
window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", () => {
  initializeLandingNavToggle(); 
  router(); 
});