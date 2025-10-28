// Handles loading page fragments

export async function loadPage(url) {
  const res = await fetch(url);
  const html = await res.text();
  const container = document.getElementById("app");
  container.innerHTML = html;

  // Re-execute any <script type="module"> tags
  container.querySelectorAll("script[type='module']").forEach((oldScript) => {
    const newScript = document.createElement("script");
    newScript.type = "module";
    newScript.textContent = oldScript.textContent;
    container.appendChild(newScript);
  });
}