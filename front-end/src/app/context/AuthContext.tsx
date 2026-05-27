import { createContext, useContext, useReducer, useEffect, ReactNode } from "react";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";
const TOKEN_KEY = "reu_secure_token";

export interface AuthUser {
  login: string;
  role: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: AuthUser | null;
  isLoading: boolean;
}

type AuthAction =
  | { type: "INIT_DONE"; payload: { isAuthenticated: boolean; user: AuthUser | null } }
  | { type: "LOGIN_START" }
  | { type: "LOGIN_SUCCESS"; payload: AuthUser }
  | { type: "LOGIN_FAIL" }
  | { type: "LOGOUT" };

function reducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "INIT_DONE":
      return { isAuthenticated: action.payload.isAuthenticated, user: action.payload.user, isLoading: false };
    case "LOGIN_START":
      return { ...state, isLoading: true };
    case "LOGIN_SUCCESS":
      return { isAuthenticated: true, user: action.payload, isLoading: false };
    case "LOGIN_FAIL":
      return { ...state, isLoading: false };
    case "LOGOUT":
      return { isAuthenticated: false, user: null, isLoading: false };
    default:
      return state;
  }
}

interface AuthContextType extends AuthState {
  loginFn: (login: string, password: string) => Promise<void>;
  logoutFn: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  user: null,
  isLoading: true,
  loginFn: async () => {},
  logoutFn: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, {
    isAuthenticated: false,
    user: null,
    isLoading: true,
  });

  // Initialise from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      // Optimistically authenticated — TODO: GET /api/auth/me for token verification
      dispatch({ type: "INIT_DONE", payload: { isAuthenticated: true, user: { login: "operator", role: "operator" } } });
    } else {
      dispatch({ type: "INIT_DONE", payload: { isAuthenticated: false, user: null } });
    }
  }, []);

  const loginFn = async (login: string, password: string): Promise<void> => {
    dispatch({ type: "LOGIN_START" });
    try {
      if (USE_MOCK) {
        await new Promise(resolve => setTimeout(resolve, 800));
        if (!login.trim() || !password.trim()) {
          dispatch({ type: "LOGIN_FAIL" });
          throw new Error("invalid_credentials");
        }
        localStorage.setItem(TOKEN_KEY, "mock-token");
        dispatch({ type: "LOGIN_SUCCESS", payload: { login, role: "operator" } });
      } else {
        const res = await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ login, password }),
        });
        if (!res.ok) {
          dispatch({ type: "LOGIN_FAIL" });
          throw new Error("invalid_credentials");
        }
        const data = await res.json() as { token: string; user: AuthUser };
        localStorage.setItem(TOKEN_KEY, data.token);
        dispatch({ type: "LOGIN_SUCCESS", payload: data.user });
      }
    } catch (err) {
      dispatch({ type: "LOGIN_FAIL" });
      throw err;
    }
  };

  const logoutFn = () => {
    localStorage.removeItem(TOKEN_KEY);
    dispatch({ type: "LOGOUT" });
  };

  return (
    <AuthContext.Provider value={{ ...state, loginFn, logoutFn }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  return useContext(AuthContext);
}
