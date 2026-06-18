/**
 * popup.js — UI du plugin.
 *
 * Gère :
 * - bouton "Analyser" → envoie un message au service worker
 * - affichage des états idle/loading/success/error
 * - formulaire de configuration du token (stocké dans storage.local)
 */

const analyzeBtn = document.getElementById("analyze-btn");
const reanalyzeBtn = document.getElementById("reanalyze-btn");
const statusBox = document.getElementById("status");
const statusMsg = statusBox.querySelector(".status-message");
const resultBox = document.getElementById("result");
const resultCompany = document.getElementById("result-company");
const resultPosition = document.getElementById("result-position");
const resultDecision = document.getElementById("result-decision");
const resultScore = document.getElementById("result-score");
const resultCost = document.getElementById("result-cost");
const resultVault = document.getElementById("result-vault");

const backendUrlInput = document.getElementById("backend-url");
const authTokenInput = document.getElementById("auth-token");
const saveSettingsBtn = document.getElementById("save-settings-btn");
const settingsStatus = document.getElementById("settings-status");

// -----------------------------------------------------------------------------
// Helpers UI
// -----------------------------------------------------------------------------

function setStatus(kind, message) {
  statusBox.className = `status ${kind}`;
  statusMsg.textContent = message;
}

function showResult(data) {
  resultCompany.textContent = data.company || "—";
  resultPosition.textContent = data.position || "—";
  resultDecision.textContent = data.decision ? "✅ Postuler" : "❌ Passer";
  resultScore.textContent = data.score_total ?? "—";
  resultCost.textContent =
    data.cost_usd != null ? `$${data.cost_usd.toFixed(4)}` : "—";
  resultVault.textContent = data.vault_path || "";
  resultBox.classList.remove("hidden");
}

function hideResult() {
  resultBox.classList.add("hidden");
}

function showReanalyze() {
  reanalyzeBtn.classList.remove("hidden");
}

function hideReanalyze() {
  reanalyzeBtn.classList.add("hidden");
}

// -----------------------------------------------------------------------------
// Analyse
// -----------------------------------------------------------------------------

// `refresh=true` force la ré-analyse côté backend (bypass de l'anti-doublon),
// déclenché par le bouton "Ré-analyser quand même".
async function handleAnalyze(refresh = false) {
  analyzeBtn.disabled = true;
  hideResult();
  hideReanalyze();
  setStatus("loading", "Analyse en cours (peut prendre 30–60s)…");

  try {
    const response = await browser.runtime.sendMessage({
      type: "analyze",
      refresh,
    });

    if (!response) {
      setStatus("error", "Pas de réponse du service worker");
      return;
    }

    if (response.status === "success") {
      setStatus("success", "Analyse terminée — dossier créé.");
      showResult(response);
    } else if (response.status === "deduplicated") {
      setStatus("idle", "URL déjà analysée récemment (anti-doublon).");
      showReanalyze();
    } else {
      setStatus("error", response.error || "Erreur inconnue");
    }
  } catch (err) {
    setStatus("error", String(err.message || err));
  } finally {
    analyzeBtn.disabled = false;
  }
}

// -----------------------------------------------------------------------------
// Gestion du token
// -----------------------------------------------------------------------------

// Backend en loopback uniquement : seul 127.0.0.1 est couvert par
// host_permissions du manifest. Le port reste libre.
function isLoopbackUrl(url) {
  try {
    return new URL(url).hostname === "127.0.0.1";
  } catch {
    return false;
  }
}

async function loadSettings() {
  const { backendUrl, authToken } = await browser.storage.local.get([
    "backendUrl",
    "authToken",
  ]);
  if (backendUrl) backendUrlInput.value = backendUrl;
  if (authToken) authTokenInput.value = authToken;
  if (authToken || backendUrl) {
    settingsStatus.textContent = "Paramètres chargés.";
  }
}

async function saveSettings() {
  const token = authTokenInput.value.trim();
  const url = backendUrlInput.value.trim().replace(/\/+$/, "");
  if (!token) {
    settingsStatus.textContent = "Token vide.";
    settingsStatus.style.color = "#b00020";
    return;
  }
  // Les en-têtes HTTP sont ASCII : on rejette explicitement plutôt que de muter
  // le token silencieusement (ce qui ferait échouer l'auth sans message clair).
  if (/[^\x00-\x7F]/.test(token)) {
    settingsStatus.textContent = "Token invalide : caractères ASCII uniquement.";
    settingsStatus.style.color = "#b00020";
    return;
  }
  if (url && !isLoopbackUrl(url)) {
    settingsStatus.textContent =
      "URL invalide : backend local uniquement (127.0.0.1).";
    settingsStatus.style.color = "#b00020";
    return;
  }
  const data = { authToken: token };
  if (url) data.backendUrl = url;
  await browser.storage.local.set(data);
  settingsStatus.textContent = "Paramètres enregistrés ✓";
  settingsStatus.style.color = "#0a7a0a";
}

// -----------------------------------------------------------------------------
// Bootstrap
// -----------------------------------------------------------------------------

// Wrappers explicites : addEventListener passe l'objet Event en 1er argument,
// qui serait interprété comme `refresh` truthy si on branchait handleAnalyze nu.
analyzeBtn.addEventListener("click", () => handleAnalyze(false));
reanalyzeBtn.addEventListener("click", () => handleAnalyze(true));
saveSettingsBtn.addEventListener("click", saveSettings);
loadSettings();
