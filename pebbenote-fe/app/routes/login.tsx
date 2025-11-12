import { Navigate, useSearchParams } from "react-router";
import { TOKEN_KEY } from "~/hooks";

export default function Login() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  if (token === null) {
    return (
      <>
        <h1>Sorry!</h1>
        <p>You must enter this url via the pebble app</p>
      </>
    );
  }
  localStorage.setItem(TOKEN_KEY, token);
  return <Navigate to="/" />;
}
