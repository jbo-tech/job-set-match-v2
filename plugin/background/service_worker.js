/**
 * service_worker.js — background script du plugin.
 *
 * Rôle : recevoir une demande d'analyse depuis le popup, injecter extract.js
 * dans l'onglet actif, puis POST /analyze sur le backend local avec le token
 * d'auth stocké dans browser.storage.local.
 *
 * Pattern message-based pour que le popup ne soit pas lié au cycle de vie
 * de la requête HTTP (il peut se fermer, la réponse est renvoyée via
 * storage.local en fallback si le port est coupé).
 */

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 120_000;

// -----------------------------------------------------------------------------
// Utilitaires storage
// -----------------------------------------------------------------------------

async function getBackendUrl() {
  const { backendUrl } = await browser.storage.local.get("backendUrl");
  return (backendUrl || DEFAULT_BACKEND_URL).replace(/\/+$/, "");
}

async function getAuthToken() {
  const { authToken } = await browser.storage.local.get("authToken");
  return (authToken || "").replace(/[^\x00-\x7F]/g, "-");
}

// -----------------------------------------------------------------------------
// Extraction page active
// -----------------------------------------------------------------------------

async function extractActiveTab() {
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) {
    throw new Error("Onglet actif introuvable");
  }

  // Refus des pages internes / vides
  if (
    !tab.url ||
    tab.url.startsWith("about:") ||
    tab.url.startsWith("moz-extension:") ||
    tab.url.startsWith("chrome:")
  ) {
    throw new Error("URL non supportée");
  }

  const results = await browser.scripting.executeScript({
    target: { tabId: tab.id },
    files: ["content/extract.js"],
  });

  if (!results || !results[0] || results[0].result == null) {
    throw new Error("Extraction impossible (CSP ou page protégée)");
  }

  return results[0].result;
}

// -----------------------------------------------------------------------------
// Appel backend
// -----------------------------------------------------------------------------

async function postAnalyze(payload, token) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const baseUrl = await getBackendUrl();

  try {
    const response = await fetch(`${baseUrl}/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Auth-Token": token,
      },
      body: JSON.stringify({
        url: payload.url,
        title: payload.title,
        content: payload.content,
        needs_fetch: payload.needsFetch,
      }),
      signal: controller.signal,
    });

    const data = await response.json().catch(() => ({
      status: "error",
      error: `HTTP ${response.status}`,
    }));

    if (!response.ok) {
      return {
        status: "error",
        error: data.error || `HTTP ${response.status}`,
      };
    }

    return data;
  } catch (err) {
    if (err.name === "AbortError") {
      return { status: "error", error: "Timeout (120s)" };
    }
    return { status: "error", error: String(err.message || err) };
  } finally {
    clearTimeout(timeout);
  }
}

// -----------------------------------------------------------------------------
// Pipeline complet appelé par le popup
// -----------------------------------------------------------------------------

async function runAnalysis() {
  const token = await getAuthToken();
  if (!token) {
    return {
      status: "error",
      error: "AUTH_TOKEN manquant — ouvre le popup et configure-le",
    };
  }

  try {
    const extracted = await extractActiveTab();
    return await postAnalyze(extracted, token);
  } catch (err) {
    return { status: "error", error: String(err.message || err) };
  }
}

// -----------------------------------------------------------------------------
// Canal de messages popup ↔ background
// -----------------------------------------------------------------------------

browser.runtime.onMessage.addListener((message) => {
  if (message && message.type === "analyze") {
    return runAnalysis();
  }
  return Promise.resolve({ status: "error", error: "Message inconnu" });
});
