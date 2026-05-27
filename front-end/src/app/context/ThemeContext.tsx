import { createContext, useContext, useState, ReactNode } from "react";

export interface Theme {
  bg: string;
  surface: string;
  surface2: string;
  hover: string;
  border: string;
  borderLight: string;
  text: string;
  textSec: string;
  textMuted: string;
  isDark: boolean;
}

const dark: Theme = {
  bg: "#0d1117",
  surface: "#161b22",
  surface2: "#1c2128",
  hover: "#21262d",
  border: "#30363d",
  borderLight: "#21262d",
  text: "#e6edf3",
  textSec: "#8b949e",
  textMuted: "#6e7681",
  isDark: true,
};

const light: Theme = {
  bg: "#f6f8fa",
  surface: "#ffffff",
  surface2: "#f6f8fa",
  hover: "#eaeef2",
  border: "#d0d7de",
  borderLight: "#eaeef2",
  text: "#1f2328",
  textSec: "#636c76",
  textMuted: "#848d97",
  isDark: false,
};

interface ThemeContextType {
  t: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextType>({ t: dark, toggle: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [isDark, setIsDark] = useState(true);
  return (
    <ThemeContext.Provider value={{ t: isDark ? dark : light, toggle: () => setIsDark(d => !d) }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
