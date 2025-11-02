// Updated router with proper sidebar/navbar visibility
import { loadPage } from "./utils.js";
import { checkAuthAndRedirect, updateUserInfo, updateNavbarForAuth, getRoleFromToken } from "./app.js";

const routes = {
  // Landing/Public Routes
  "#/": "landing/home.html",
  "#/landing": "landing/home.html",
  "#/landing-events": "landing/events.html",
  "#/landing-calendar": "landing/calendar.html",
  "#/landing-about": "landing/about.html",

  // Auth Routes
  "#/login": "pages/login.html",
  "#/register": "pages/register.html",
  
  // App/Protected Routes
  "#/dashboard": "pages/home.html", // Renamed from #/home
  "#/events": "pages/events.html",
  "#/calendar": "pages/calendar.html",
  "#/create-event": "pages/create-event.html",
  "#/planning": "pages/planning.html",
  "#/ai-chat": "pages/ai-chat.html",
  "#/profile": "pages/profile.html"
};

const landingPages = [
  "#/", 
  "#/landing", 
  "#/landing-events", 
  "#/landing-calendar", 
  "#/landing-about"
];
const authPages = ["#/login", "#/register"];

// --- Role-protected Pages ---
const adminOnlyPages = [
    "#/dashboard",
    "#/create-event",
    "#/planning"
];

async function router() {
  let path = window.location.hash || "#/landing";
  
  // Handle 404
  if (!routes[path]) {
    path = "#/landing"; // Default to landing page
    window.location.hash = path;
  }
  
  const isLandingPage = landingPages.includes(path);
  const isAuthPage = authPages.includes(path);
  
  const landingNavbar = document.getElementById("landingNavbar");
  const sidebar = document.getElementById("sidebar");
  const mobileHeader = document.getElementById("mobileHeader");
  const mainContent = document.querySelector(".main-content");
  
  updateNavbarForAuth();

  if (isLandingPage || isAuthPage) {
    // --- ON A PUBLIC PAGE (EITHER LANDING OR AUTH) ---
    
    if (landingNavbar) landingNavbar.style.display = "flex";
    if (sidebar) sidebar.style.display = "none";
    if (mobileHeader) mobileHeader.style.display = "none";
    
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
    
    const isAuthenticated = checkAuthAndRedirect();
    
    if (isAuthenticated) {
      // --- Role-based Page Access ---
      const role = getRoleFromToken();
      if (adminOnlyPages.includes(path) && (role !== 'admin' && role !== 'organizer')) {
          // Attendee trying to access admin page
          window.location.hash = "#/calendar"; // Redirect to their default
          return; // Stop execution
      }

      // Hide landing nav, show app UI
      if (landingNavbar) landingNavbar.style.display = "none";
      if (sidebar) sidebar.style.display = "flex";
      if (mobileHeader) {
        if (window.innerWidth <= 768) {
          mobileHeader.style.display = "flex";
        } else {
          mobileHeader.style.display = "none";
        }
      }
      
      // Reset main content margin and remove special layouts
      if (mainContent) {
        mainContent.style.marginLeft = "";
        mainContent.classList.remove("auth-layout");
        mainContent.classList.remove("landing-layout");
      }
      
      updateUserInfo();
      await loadPage(routes[path]);
    }
  }
  
  updateActiveNav(path);
}

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

function updateActiveNav(path) {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('href') === path) {
      item.classList.add('active');
    }
  });
  
  const landingNavLinks = document.querySelectorAll('#landingNavbar [data-nav]');
  landingNavLinks.forEach(link => {
    link.classList.remove('active');
  });

  let activeLandingNav = null;
  if (path === '#/landing' || path === '#/') {
    activeLandingNav = 'landing';
  } else if (path === '#/landing-events') {
    activeLandingNav = 'events';
  } else if (path === '#/landing-calendar') {
    activeLandingNav = 'calendar';
  } else if (path === '#/landing-about') {
    activeLandingNav = 'about';
  }
  
  if (activeLandingNav) {
    document.querySelectorAll(`[data-nav="${activeLandingNav}"]`).forEach(el => el.classList.add('active'));
  }
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

    // Close menu when *any* link is clicked
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        mobileMenu.classList.remove('active');
      });
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
