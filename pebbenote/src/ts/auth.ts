// OAuth2 device authorization grant (RFC 8628) against Keycloak
import { ISSUER } from "./env";

const CLIENT_ID = "pebbenote-watch";
const OIDC = `${ISSUER}/protocol/openid-connect`;

const ACCESS_KEY = "accessToken";
const REFRESH_KEY = "refreshToken";
const EXPIRES_KEY = "accessTokenExpiresAt";
// Refresh slightly early so a token doesn't expire mid-request
const EXPIRY_MARGIN_MS = 30_000;

export class NotSignedInError extends Error {
  constructor() {
    super("Not signed in");
    this.name = "NotSignedInError";
  }
}

export type DeviceFlow = {
  device_code: string;
  user_code: string;
  verification_uri_complete: string;
  expires_in: number;
  interval?: number;
};

type TokenResponse = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
};

type OAuthError = { error: string };

function postForm<T>(
  url: string,
  params: Record<string, string>,
): Promise<{ status: number; body: T }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
    xhr.onload = () => {
      try {
        resolve({ status: xhr.status, body: JSON.parse(xhr.responseText) });
      } catch (e) {
        reject(e);
      }
    };
    xhr.onerror = () => reject(new Error("Auth server unreachable"));
    xhr.send(
      Object.entries(params)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join("&"),
    );
  });
}

function storeTokens(tokens: TokenResponse) {
  localStorage.setItem(ACCESS_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  localStorage.setItem(
    EXPIRES_KEY,
    String(Date.now() + tokens.expires_in * 1000),
  );
}

export function signOut() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(EXPIRES_KEY);
}

export function isSignedIn(): boolean {
  return !!localStorage.getItem(REFRESH_KEY);
}

export async function getAccessToken(): Promise<string> {
  const access = localStorage.getItem(ACCESS_KEY);
  const expiresAt = Number(localStorage.getItem(EXPIRES_KEY));
  if (access && Date.now() < expiresAt - EXPIRY_MARGIN_MS) return access;

  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) throw new NotSignedInError();

  const { status, body } = await postForm<TokenResponse | OAuthError>(
    `${OIDC}/token`,
    {
      grant_type: "refresh_token",
      client_id: CLIENT_ID,
      refresh_token: refresh,
    },
  );
  if (status === 200) {
    storeTokens(body as TokenResponse);
    return (body as TokenResponse).access_token;
  }
  // Refresh token was revoked or expired - only a new sign in helps
  if ((body as OAuthError).error === "invalid_grant") {
    signOut();
    throw new NotSignedInError();
  }
  throw new Error(`Token refresh failed: ${status}`);
}

export async function startDeviceFlow(): Promise<DeviceFlow> {
  const { status, body } = await postForm<DeviceFlow>(`${OIDC}/auth/device`, {
    client_id: CLIENT_ID,
  });
  if (status !== 200) throw new Error(`Device flow failed: ${status}`);
  return body;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Resolves true once the user approved the device, false if the flow ended.
export async function pollDeviceFlow(flow: DeviceFlow): Promise<boolean> {
  let intervalMs = (flow.interval ?? 5) * 1000;
  const deadline = Date.now() + flow.expires_in * 1000;
  while (Date.now() < deadline) {
    await sleep(intervalMs);
    console.log("Checking flow");
    const { status, body } = await postForm<TokenResponse | OAuthError>(
      `${OIDC}/token`,
      {
        grant_type: "urn:ietf:params:oauth:grant-type:device_code",
        client_id: CLIENT_ID,
        device_code: flow.device_code,
      },
    );
    if (status === 200) {
      console.log("Flow worked, signed in");
      storeTokens(body as TokenResponse);
      return true;
    }
    const { error } = body as OAuthError;
    if (error === "slow_down") intervalMs += 5000;
    else if (error !== "authorization_pending") {
      console.error("Flow failed");
      return false;
    }
  }
  console.error("Flow timed out");
  return false;
}
