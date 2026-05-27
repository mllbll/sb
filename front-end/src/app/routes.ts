import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Overview } from "./pages/Overview";
import { CrowdModule } from "./pages/CrowdModule";
import { FightModule } from "./pages/FightModule";
import { FallModule } from "./pages/FallModule";
import { LoginPage } from "./pages/LoginPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    Component: LoginPage,
  },
  {
    path: "/",
    Component: ProtectedRoute,
    children: [
      {
        Component: Layout,
        children: [
          { index: true, Component: Overview },
          { path: "crowd", Component: CrowdModule },
          { path: "fight", Component: FightModule },
          { path: "fall", Component: FallModule },
        ],
      },
    ],
  },
]);
