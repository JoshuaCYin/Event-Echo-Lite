// Loads pages and checks login state each time.

import { loadPage } from "./utils.js";
import { checkAuthAndRedirect } from "./app.js";

const routes = {
  "#/login": "pages/login.html",
  "#/register": "pages/register.html",
  "#/home": "pages/home.html",
  "#/events": "pages/events.html",
};

async function router() {
  const path = window.location.hash || "#/login";
  if (["#/login", "#/register"].includes(path)) {
    await loadPage(routes[path]);
  } else {
    checkAuthAndRedirect();
    await loadPage(routes[path]);
  }
}

window.addEventListener("hashchange", router);
window.addEventListener("DOMContentLoaded", router);