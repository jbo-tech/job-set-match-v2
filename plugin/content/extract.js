/**
 * extract.js — injecté via scripting.executeScript dans l'onglet actif.
 *
 * Extrait un contenu "propre" depuis la page courante pour envoi au backend.
 * Stratégie : retirer les balises bruyantes (script, style, nav, header,
 * footer, aside, form), puis prendre body.innerText. Si le résultat est
 * trop court (< 200 chars) on lève un flag needsFetch pour que le backend
 * tente un fetch HTTP direct.
 */

(function extractPageContent() {
  // Aligné sur AnalyzeRequest.content (max_length=50_000) côté backend : on
  // n'écarte pas du contenu que le serveur accepterait.
  const MAX_CHARS = 50000;
  const MIN_CHARS = 200;
  const NOISE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
  ];

  // On clone le body pour ne pas muter la page (autrement l'utilisateur verrait
  // les éléments supprimés).
  const bodyClone = document.body ? document.body.cloneNode(true) : null;
  if (!bodyClone) {
    return {
      title: document.title || "",
      url: window.location.href,
      content: "",
      needsFetch: true,
    };
  }

  for (const selector of NOISE_SELECTORS) {
    for (const el of bodyClone.querySelectorAll(selector)) {
      el.remove();
    }
  }

  // innerText préserve les retours à la ligne visuels, contrairement à
  // textContent qui écrase tout.
  let text = (bodyClone.innerText || "").trim();

  // Compression des blancs/lignes vides
  text = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");

  // Troncature douce
  if (text.length > MAX_CHARS) {
    text = text.slice(0, MAX_CHARS);
  }

  return {
    title: document.title || "",
    url: window.location.href,
    content: text,
    needsFetch: text.length < MIN_CHARS,
  };
})();
