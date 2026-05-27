import { useNavigate } from "react-router";
import { useAuthContext } from "../context/AuthContext";

export function useAuth() {
  const navigate = useNavigate();
  const { loginFn, logoutFn, ...state } = useAuthContext();

  const login = async (loginStr: string, password: string): Promise<void> => {
    await loginFn(loginStr, password);
  };

  const logout = () => {
    logoutFn();
    navigate("/login", { replace: true });
  };

  return { ...state, login, logout };
}
