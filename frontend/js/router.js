import { loadPage } from "./utils.js";

const routes = {
  "/login": "pages/login.html",
  "/register": "pages/register.html",
  "/events": "pages/events.html",
  "/home": "pages/home.html",
};

function router() {
  const rawHash = window.location.hash || "#/login";
  const path = rawHash.replace(/^#/, "");
  const page = routes[path] || routes["/login"];
  loadPage(page);
}

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);