#!/bin/sh
# install.sh — set up jobset&match-v2 on this machine. Idempotent.
#
# - creates central provider keys dir if absent
# - creates ~/.config/jobset-match/ with config.yaml
# - creates .env from template if absent
# - installs Python dependencies via uv
# - installs Playwright chromium

set -eu

REPO_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG_DIR="${HOME}/.config/jobset-match"
KEYS_DIR="${HOME}/.config/llm-provider-keys"

# --- Central provider keys store ---
mkdir -p "$KEYS_DIR"
chmod 700 "$KEYS_DIR"
if [ ! -f "$KEYS_DIR/providers.env" ]; then
    if [ -f "$REPO_DIR/providers.env.example" ]; then
        cp "$REPO_DIR/providers.env.example" "$KEYS_DIR/providers.env"
    else
        cat > "$KEYS_DIR/providers.env" <<'TMPL'
# Central LLM provider API keys — fill in your keys.
# Shared across projects. chmod 600 this file.
OPENAI_API_KEY=
MISTRAL_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
BRAVE_API_KEY=
TMPL
    fi
    chmod 600 "$KEYS_DIR/providers.env"
    echo "Created $KEYS_DIR/providers.env — fill in your API keys."
else
    echo "Central keys store already exists: $KEYS_DIR/providers.env"
fi

# --- Business config ---
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
    cp "$REPO_DIR/config.example.yaml" "$CONFIG_DIR/config.yaml"
    echo "Copied config template to $CONFIG_DIR/config.yaml — customize vault paths and models."
else
    echo "Config already exists: $CONFIG_DIR/config.yaml"
fi

# --- Project .env (project-specific only) ---
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    chmod 600 "$REPO_DIR/.env"
    echo "Created $REPO_DIR/.env — set AUTH_TOKEN and OBSIDIAN_VAULT_PATH."
else
    # Fix permissions if too open
    perms=$(stat -c "%a" "$REPO_DIR/.env" 2>/dev/null || stat -f "%Lp" "$REPO_DIR/.env")
    if [ "$perms" != "600" ]; then
        chmod 600 "$REPO_DIR/.env"
        echo "Fixed .env permissions: $perms -> 600"
    fi
fi

# --- Python dependencies ---
if command -v uv >/dev/null 2>&1; then
    (cd "$REPO_DIR" && uv sync --extra dev)
    echo "Dependencies installed."

    if command -v playwright >/dev/null 2>&1 || (cd "$REPO_DIR" && uv run playwright --version >/dev/null 2>&1); then
        echo "Installing Playwright chromium..."
        if (cd "$REPO_DIR" && uv run playwright install chromium); then
            echo "Playwright chromium installed."
        else
            echo "----------------------------------------"
            echo "Playwright chromium bundle unavailable."
            echo "Falling back to system chromium..."
            echo
            SYSTEM_CHROMIUM=""
            for candidate in \
                /snap/bin/chromium \
                /usr/bin/chromium-browser \
                /usr/bin/chromium \
                /usr/bin/google-chrome-stable \
                /usr/bin/google-chrome \
                /usr/bin/brave-browser \
                /usr/bin/microsoft-edge; do
                if [ -x "$candidate" ]; then
                    SYSTEM_CHROMIUM="$candidate"
                    break
                fi
            done
            if [ -n "$SYSTEM_CHROMIUM" ]; then
                echo "Found: $SYSTEM_CHROMIUM"
                if grep -q "^PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=" "$REPO_DIR/.env" 2>/dev/null; then
                    sed -i "s|^PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=.*|PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$SYSTEM_CHROMIUM|" "$REPO_DIR/.env"
                else
                    echo "PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$SYSTEM_CHROMIUM" >> "$REPO_DIR/.env"
                fi
                echo "→ Set PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$SYSTEM_CHROMIUM in .env"
                echo "  The app will use the system browser for PDF capture."
            else
                echo "No system chromium found."
                echo
                echo "Install one of:"
                echo "  sudo snap install chromium"
                echo "  sudo apt install chromium-browser"
                echo
                echo "Then re-run ./install.sh or set manually:"
                echo "  PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/path/to/chromium"
            fi
            echo "----------------------------------------"
        fi
    fi
else
    echo "WARNING: uv not found. Install it: https://docs.astral.sh/uv/getting-started/installation/"
    echo "Then run: cd $REPO_DIR && uv sync --extra dev && uv run playwright install chromium"
fi

echo
echo "Setup complete."
echo "  Config:  $CONFIG_DIR/config.yaml"
echo "  Keys:    $KEYS_DIR/providers.env"
echo "  Env:     $REPO_DIR/.env"
echo
echo "Next:"
echo "  1. Edit $CONFIG_DIR/config.yaml (vault paths, model choices)"
echo "  2. Edit $REPO_DIR/.env (AUTH_TOKEN, OBSIDIAN_VAULT_PATH)"
echo "  3. Edit $KEYS_DIR/providers.env (API keys — if not done already)"
echo "  4. uv run uvicorn app.main:app --reload"
