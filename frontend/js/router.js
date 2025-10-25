// Updated router with proper sidebar visibility
import { loadPage } from "./utils.js";
import { checkAuthAndRedirect, updateUserInfo } from "./app.js";

const routes = {
  "#/login": "pages/login.html",
  "#/register": "pages/register.html",
  "#/home": "pages/home.html",
  "#/events": "pages/events.html",
  "#/calendar": "pages/calendar.html",
  "#/create-event": "pages/create-event.html",
  "#/planning": "pages/planning.html",
  "#/ai-chat": "pages/ai-chat.html",
  "#/profile": "pages/profile.html"
};

const publicPages = ["#/login", "#/register"];

async function router() {
  const path = window.location.hash || "#/login";
  const isPublicPage = publicPages.includes(path);
  
  // Get elements
  const sidebar = document.getElementById("sidebar");
  const mobileHeader = document.getElementById("mobileHeader");
  const mainContent = document.querySelector(".main-content");
  const app = document.getElementById("app");
  
  if (isPublicPage) {
    // Hide sidebar for login/register
    if (sidebar) sidebar.style.display = "none";
    if (mobileHeader) mobileHeader.style.display = "none";
    if (mainContent) {
      mainContent.style.marginLeft = "0";
      mainContent.classList.add("auth-page");
    }
    await loadPage(routes[path]);
  } else {
    // Check auth for protected pages
    const isAuthenticated = checkAuthAndRedirect();
    
    if (isAuthenticated) {
      // Show sidebar for authenticated pages
      if (sidebar) sidebar.style.display = "flex";
      if (mobileHeader) {
        // Only show mobile header on small screens
        if (window.innerWidth <= 768) {
          mobileHeader.style.display = "flex";
        } else {
          mobileHeader.style.display = "none";
        }
      }
      if (mainContent) {
        mainContent.style.marginLeft = "";
        mainContent.classList.remove("auth-page");
      }
      
      // Update user info in sidebar
      updateUserInfo();
      
      // Update active nav item
      updateActiveNav(path);
      
      await loadPage(routes[path]);
    }
  }
}

// Handle window resize to show/hide mobile header
window.addEventListener('resize', () => {
  const mobileHeader = document.getElementById("mobileHeader");
  const path = window.location.hash || "#/login";
  const isPublicPage = publicPages.includes(path);
  
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
}

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);