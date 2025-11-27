// Handles loading page fragments into the main app container
export async function loadPage(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to load page: ${res.status} ${res.statusText}`);
    }
    const html = await res.text();
    const container = document.getElementById("app");
    container.innerHTML = html;

    // Re-execute any <script type="module"> tags
    container.querySelectorAll("script[type='module']").forEach((oldScript) => {
      const newScript = document.createElement("script");
      newScript.type = "module";
      
      // Copy all attributes
      for (const attr of oldScript.attributes) {
        newScript.setAttribute(attr.name, attr.value);
      }
      
      newScript.textContent = oldScript.textContent;
      
      // Replace the old script with the new one to trigger execution
      oldScript.parentNode.replaceChild(newScript, oldScript);
    });
  } catch (error) {
    console.error("Error loading page:", error);
    const container = document.getElementById("app");
    container.innerHTML = `<div class="error-message">Error loading page ${url}. Please try refreshing.</div>`;
  }
}
