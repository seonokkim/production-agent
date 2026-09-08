import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AssetsPage } from "@/pages/AssetsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { MultimodalRagPage } from "@/pages/MultimodalRagPage";
import { ProjectPage } from "@/pages/ProjectPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { ScenePage } from "@/pages/ScenePage";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/scenes/:id" element={<ScenePage />} />
        <Route path="/assets" element={<AssetsPage />} />
        <Route path="/search-agent" element={<MultimodalRagPage />} />
      </Routes>
    </AppShell>
  );
}
