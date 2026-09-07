import { NavLink, Route, Routes } from "react-router-dom";
import { AssetsPage } from "../pages/AssetsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { ProjectPage } from "../pages/ProjectPage";
import { ScenePage } from "../pages/ScenePage";

export function App() {
  return (
    <div className="app-shell">
      <nav className="topnav">
        <div className="brand">Production Agent</div>
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : undefined)}>
          Dashboard
        </NavLink>
        <NavLink to="/assets" className={({ isActive }) => (isActive ? "active" : undefined)}>
          Assets
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/scenes/:id" element={<ScenePage />} />
        <Route path="/assets" element={<AssetsPage />} />
      </Routes>
    </div>
  );
}
