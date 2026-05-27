import { RouterProvider } from "react-router";
import { router } from "./routes";
import { ThemeProvider } from "./context/ThemeContext";
import { AppProvider } from "./store/appStore";
import { AuthProvider } from "./context/AuthContext";

export default function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <ThemeProvider>
          <RouterProvider router={router} />
        </ThemeProvider>
      </AppProvider>
    </AuthProvider>
  );
}
