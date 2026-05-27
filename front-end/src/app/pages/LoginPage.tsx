import { useState, useRef, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [loginVal, setLoginVal] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loginRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loginRef.current?.focus();
  }, []);

  // If already authenticated, redirect away
  useEffect(() => {
    if (isAuthenticated) navigate("/", { replace: true });
  }, [isAuthenticated, navigate]);

  const canSubmit = loginVal.trim().length > 0 && password.trim().length > 0 && !loading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError("");
    try {
      await login(loginVal, password);
      navigate("/", { replace: true });
    } catch {
      setError("Неверный логин или пароль");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: "100%",
    background: "#0d1117",
    border: "1px solid #30363d",
    borderRadius: 6,
    padding: "8px 12px",
    color: "#e6edf3",
    fontSize: 13,
    outline: "none",
    boxSizing: "border-box",
    fontFamily: "'Inter', sans-serif",
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontSize: 12,
    color: "#8b949e",
    marginBottom: 6,
    fontFamily: "'Inter', sans-serif",
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "#0d1117",
        backgroundImage:
          "linear-gradient(#161b22 1px, transparent 1px), linear-gradient(90deg, #161b22 1px, transparent 1px)",
        backgroundSize: "28px 28px",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div
        style={{
          width: 400,
          background: "#161b22",
          border: "1px solid #30363d",
          borderRadius: 12,
          padding: 32,
        }}
      >
        {/* Typography header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ fontSize: 22, fontWeight: 600, color: "#e6edf3", letterSpacing: "-0.02em" }}>
            REU Secure
          </div>
          <div style={{ fontSize: 11, color: "#6e7681", marginTop: 4 }}>
            Система безопасности РЭУ им. Г.В. Плеханова
          </div>
        </div>

        <form onSubmit={handleSubmit} autoComplete="on">
          {/* Login field */}
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle} htmlFor="login-input">Логин</label>
            <input
              id="login-input"
              ref={loginRef}
              type="text"
              autoComplete="username"
              value={loginVal}
              onChange={e => setLoginVal(e.target.value)}
              placeholder="Введите логин"
              style={inputStyle}
              onFocus={e => {
                e.currentTarget.style.borderColor = "#1f6feb";
                e.currentTarget.style.boxShadow = "0 0 0 3px #1f6feb20";
              }}
              onBlur={e => {
                e.currentTarget.style.borderColor = "#30363d";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
          </div>

          {/* Password field */}
          <div style={{ marginBottom: 12 }}>
            <label style={labelStyle} htmlFor="password-input">Пароль</label>
            <div style={{ position: "relative" }}>
              <input
                id="password-input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Введите пароль"
                style={{ ...inputStyle, paddingRight: 38 }}
                onFocus={e => {
                  e.currentTarget.style.borderColor = "#1f6feb";
                  e.currentTarget.style.boxShadow = "0 0 0 3px #1f6feb20";
                }}
                onBlur={e => {
                  e.currentTarget.style.borderColor = "#30363d";
                  e.currentTarget.style.boxShadow = "none";
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(v => !v)}
                style={{
                  position: "absolute",
                  right: 10,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "none",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                  color: "#6e7681",
                  display: "flex",
                  alignItems: "center",
                }}
                tabIndex={-1}
                aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"}
              >
                {showPassword
                  ? <EyeOff style={{ width: 15, height: 15 }} />
                  : <Eye style={{ width: 15, height: 15 }} />}
              </button>
            </div>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit}
            style={{
              width: "100%",
              padding: "9px 0",
              borderRadius: 6,
              border: "none",
              fontSize: 13,
              fontWeight: 500,
              fontFamily: "'Inter', sans-serif",
              cursor: canSubmit ? "pointer" : "not-allowed",
              background: canSubmit ? "#1f6feb" : "#1f6feb40",
              color: canSubmit ? "#ffffff" : "#8b949e",
              transition: "background 0.15s",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
            }}
            onMouseEnter={e => { if (canSubmit) e.currentTarget.style.background = "#388bfd"; }}
            onMouseLeave={e => { if (canSubmit) e.currentTarget.style.background = "#1f6feb"; }}
          >
            {loading ? (
              <>
                <span
                  style={{
                    width: 13,
                    height: 13,
                    borderRadius: "50%",
                    border: "2px solid #ffffff40",
                    borderTopColor: "#ffffff",
                    animation: "spin 0.7s linear infinite",
                    display: "inline-block",
                    flexShrink: 0,
                  }}
                />
                Вход...
              </>
            ) : (
              "Войти"
            )}
          </button>

          {/* Error message */}
          {error && (
            <div
              style={{
                marginTop: 12,
                background: "#f8514915",
                border: "1px solid #f8514940",
                borderRadius: 6,
                padding: "8px 12px",
                color: "#f85149",
                fontSize: 12,
              }}
            >
              {error}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
