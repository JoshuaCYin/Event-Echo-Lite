// Handles loading page fragments with better error handling
export async function loadPage(url) {
  console.log("Utils: Loading page:", url);
  
  try {
    const res = await fetch(url);
    
    if (!res.ok) {
      throw new Error(`Failed to load ${url}: ${res.status} ${res.statusText}`);
    }
    
    const html = await res.text();
    const container = document.getElementById("app");
    
    if (!container) {
      console.error("Utils: App container not found!");
      return;
    }
    
    container.innerHTML = html;
    console.log("Utils: Page loaded successfully");
    
    // Re-execute any <script type="module"> tags
    container.querySelectorAll("script[type='module']").forEach((oldScript) => {
      const newScript = document.createElement("script");
      newScript.type = "module";
      newScript.textContent = oldScript.textContent;
      container.appendChild(newScript);
    });
    
  } catch (error) {
    console.error("Utils: Error loading page:", error);
    const container = document.getElementById("app");
    if (container) {
      container.innerHTML = `
        <div style="padding: 2rem; text-align: center;">
          <h2 style="color: #f56565; margin-bottom: 1rem;">Page Load Error</h2>
          <p style="color: #718096;">Failed to load: ${url}</p>
          <p style="color: #718096; font-size: 0.875rem; margin-top: 0.5rem;">${error.message}</p>
          <button onclick="window.location.hash='#/landing'" style="margin-top: 1rem; padding: 0.75rem 1.5rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; cursor: pointer;">
            Return to Home
          </button>
        </div>
      `;
    }
  }
}