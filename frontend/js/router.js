// Updated router with proper sidebar visibility and role-based access
import { loadPage } from "./utils.js";
import { checkAuthAndRedirect, updateUserInfo, getRoleFromToken } from "./app.js";

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

// Pages that require organizer or admin role
const restrictedPages = ["#/create-event", "#/home", "#/planning"];

function updateSidebarForRole(role) {
  console.log("Updating sidebar for role:", role); // Debug log
  
  const restrictedNavItems = document.querySelectorAll('[data-page="home"], [data-page="create-event"], [data-page="planning"]');
  
  console.log("Found restricted items:", restrictedNavItems.length); // Debug log
  
  if (role === "attendee") {
    // Hide restricted items for attendees
    restrictedNavItems.forEach(item => {
      console.log("Hiding item:", item.getAttribute('data-page')); // Debug log
      item.style.display = "none";
    });
  } else {
    // Show all items for organizers and admins
    restrictedNavItems.forEach(item => {
      item.style.display = "flex";
    });
  }
}

async function router() {
  const path = window.location.hash || "#/login";
  const isPublicPage = publicPages.includes(path);
  
  // Get elements
  const sidebar = document.getElementById("sidebar");
  const mobileHeader = document.getElementById("mobileHeader");
  const mainContent = document.querySelector(".main-content");
  
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
      // Check role-based access
      const role = getRoleFromToken();
      console.log("User role:", role); // Debug log
      
      if (restrictedPages.includes(path) && role === "attendee") {
        // Redirect attendees away from restricted pages
        window.location.hash = "#/calendar";
        return;
      }
      
      // Show sidebar for authenticated pages
      if (sidebar) {
        sidebar.style.display = "flex";
        
        // Wait a tiny bit to ensure DOM is ready, then hide restricted items
        setTimeout(() => {
          updateSidebarForRole(role);
        }, 10);
      }
      
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

function updateActiveNav(path) {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.classList.remove('active');
    if (item.getAttribute('href') === path) {
      item.classList.add('active');
    }
  });
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

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);