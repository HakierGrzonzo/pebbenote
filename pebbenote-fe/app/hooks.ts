import { useNavigate } from "react-router";

export const TOKEN_KEY = "pebble-token";

export function useAppToken() {
  const token = localStorage.getItem(TOKEN_KEY);
  const navigate = useNavigate();

  if (token === null) {
    navigate("/login");
    return;
  }

  return token;
}
