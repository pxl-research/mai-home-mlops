#!/bin/sh
set -e

echo "Waiting 10s for Vault to start..."
sleep 10

export VAULT_ADDR=$BAO_ADDR

if vault status 2>&1 | grep -q 'Initialized.*false'; then
  echo "Initializing Vault..."
  VAULT_INIT_OUTPUT=$(vault operator init -key-shares=1 -key-threshold=1)

  export BAO_UNSEAL_KEY=$(echo "$VAULT_INIT_OUTPUT" | awk '/Unseal Key 1:/ {print $4}')
  export BAO_TOKEN=$(echo "$VAULT_INIT_OUTPUT" | awk '/Initial Root Token:/ {print $4}')

  echo "$BAO_UNSEAL_KEY" > /app/unseal.key
  echo "$BAO_TOKEN" > /app/root.token
else
  echo "Vault already initialized."
  export BAO_UNSEAL_KEY=$(cat /app/unseal.key)
  export BAO_TOKEN=$(cat /app/root.token)
fi


if vault status 2>&1 | grep -q 'Sealed.*true'; then
  echo "Unsealing Vault..."
  vault operator unseal "$BAO_UNSEAL_KEY"
else
  echo "Vault already unsealed."
fi

export VAULT_TOKEN=$BAO_TOKEN

# Enable KV v2 if not already enabled (after unseal)
if ! vault secrets list -format=json | grep -q '"secret/"'; then
  echo "Enabling KV v2 at 'secret/'..."
  vault secrets enable -path=secret -version=2 kv
else
  echo "KV v2 already enabled at 'secret/'"
fi

# Update .env with BAO_TOKEN
if grep -q '^BAO_TOKEN=' /app/.env 2>/dev/null; then
  sed -i "s|^BAO_TOKEN=.*|BAO_TOKEN=${BAO_TOKEN}|" /app/.env
else
  echo "BAO_TOKEN=${BAO_TOKEN}" >> /app/.env
fi

echo "Wrote BAO_TOKEN to .env"
echo "Starting FastAPI server..."
exec python3 vault_server.py
