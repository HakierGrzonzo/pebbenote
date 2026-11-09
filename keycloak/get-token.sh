#!/bin/bash
# Prints an access token for the local backend, using password login.
#
# Local development only: it uses the Keycloak admin account from
# docker-compose.yml to create, when missing, a public "pebbenote-dev" client
# with password login enabled and the given user.
#
# Usage: keycloak/get-token.sh [username] [password]
#   curl -H "Authorization: Bearer $(keycloak/get-token.sh)" localhost:8000/note/

set -euo pipefail

USERNAME="${1:-dev}"
PASSWORD="${2:-devpassword}"

KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
REALM="${REALM:-pebbenote}"
CLIENT_ID="pebbenote-dev"
KC_ADMIN="${KC_ADMIN:-admin}"
KC_ADMIN_PASSWORD="${KC_ADMIN_PASSWORD:-admin}"

ADMIN_API="$KEYCLOAK_URL/admin/realms/$REALM"

admin_token=$(
  curl -sf "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=admin-cli \
    --data-urlencode "username=$KC_ADMIN" \
    --data-urlencode "password=$KC_ADMIN_PASSWORD" |
    jq -r .access_token
)

admin() {
  curl -sf -H "Authorization: Bearer $admin_token" \
    -H "Content-Type: application/json" "$@"
}

clients=$(admin "$ADMIN_API/clients" -G --data-urlencode "clientId=$CLIENT_ID")
if [ "$(jq length <<<"$clients")" -eq 0 ]; then
  # The audience scope makes the backend accept the token. The realm import
  # has no "basic" scope, so the sub claim gets its own mapper.
  admin -X POST "$ADMIN_API/clients" -d @- <<EOF
{
  "clientId": "$CLIENT_ID",
  "enabled": true,
  "publicClient": true,
  "standardFlowEnabled": false,
  "directAccessGrantsEnabled": true,
  "defaultClientScopes": ["pebbenote-be-audience"],
  "protocolMappers": [
    {
      "name": "sub",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-sub-mapper",
      "config": {"access.token.claim": "true", "introspection.token.claim": "true"}
    }
  ]
}
EOF
  echo "Created client $CLIENT_ID" >&2
fi

users=$(admin "$ADMIN_API/users" -G --data-urlencode "username=$USERNAME" -d exact=true)
if [ "$(jq length <<<"$users")" -eq 0 ]; then
  # A complete profile, otherwise Keycloak asks to finish setting up the account
  jq -n --arg user "$USERNAME" --arg password "$PASSWORD" '{
    username: $user,
    enabled: true,
    email: "\($user)@example.com",
    emailVerified: true,
    firstName: $user,
    lastName: "Dev",
    credentials: [{type: "password", value: $password, temporary: false}]
  }' | admin -X POST "$ADMIN_API/users" -d @-
  echo "Created user $USERNAME" >&2
fi

response=$(
  curl -s "$KEYCLOAK_URL/realms/$REALM/protocol/openid-connect/token" \
    -d grant_type=password -d "client_id=$CLIENT_ID" \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD"
)
token=$(jq -r '.access_token // empty' <<<"$response")
if [ -z "$token" ]; then
  echo "Login failed: $response" >&2
  exit 1
fi
echo "$token"
