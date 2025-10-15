/**
 * API_BASES Configuration
 * 
 * This file contains the base URLs for different microservices in the application.
 * Each service corresponds to a specific module and provides a consistent base URL
 * for making API requests.
 * 
 * @type {Object}
 * @property {string} auth - Base URL for the authentication service.
 * @property {string} events - Base URL for the events service.
 * @property {string} notifications - Base URL for the notifications service.
 * @property {string} ai - Base URL for the AI service.
 * 
 * With this setup we need to add this to the top of any JS file that needs to talk to a backend (e.g. app.js):
 * import { API_BASES } from './config.js';
 * 
 * Locally, we’ll run each backend service on its own port (5000 = auth, 5001 = events, etc.).
 * When we deploy, the host gives each service a real web address such as:
 * auth: https://auth.eventecho.site
 * events: https://events.eventecho.site
 * The ports stay in our local config file only, and on the servers we just update the URLs in config.js to the hosted ones.
 */

export const API_BASES = {
  auth: "http://localhost:8080",
  events: "http://localhost:5001",
  notifications: "http://localhost:5002",
  ai: "http://localhost:5003"
};