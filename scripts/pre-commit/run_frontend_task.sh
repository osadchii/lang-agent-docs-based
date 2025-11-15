#!/usr/bin/env bash

# Run a frontend npm script after ensuring Node >= 18 is available.

set -euo pipefail

TASK="${1:-}"
if [[ -z "${TASK}" ]]; then
    echo "Usage: $0 <npm-script>" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="${REPO_ROOT}/frontend"
NVM_SCRIPT="${HOME}/.nvm/nvm.sh"

ensure_node() {
    local current_major=""
    if command -v node >/dev/null 2>&1; then
        local version
        version="$(node -v 2>/dev/null || true)"
        version="${version#v}"
        current_major="${version%%.*}"
    fi

    if [[ -n "${current_major}" && "${current_major}" -ge 18 ]]; then
        return
    fi

    if [[ -s "${NVM_SCRIPT}" ]]; then
        export NVM_AUTO_USE=0
        # shellcheck disable=SC1090
        set +e
        source "${NVM_SCRIPT}"
        set -e
        if [[ -f "${FRONTEND_DIR}/.nvmrc" ]]; then
            pushd "${FRONTEND_DIR}" >/dev/null
            nvm use >/dev/null
            popd >/dev/null
        else
            nvm use 20 >/dev/null
        fi

        # Re-check to ensure we now have a modern Node.
        local resolved_major
        resolved_major="$(node -v 2>/dev/null | sed 's/^v//' | cut -d. -f1)"
        if [[ -n "${resolved_major}" && "${resolved_major}" -ge 18 ]]; then
            return
        fi
    fi

    echo "Node.js >= 18 is required for frontend lint/format hooks." >&2
    echo "Install Node 20+ or configure NVM/Volta to expose it in PATH." >&2
    exit 1
}

ensure_node
cd "${FRONTEND_DIR}"
npm run "${TASK}"
