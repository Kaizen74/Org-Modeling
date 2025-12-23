import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import ScenarioPage from './pages/ScenarioPage'
import ComparisonPage from './pages/ComparisonPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/projects" replace />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="scenarios/:scenarioId" element={<ScenarioPage />} />
        <Route path="compare" element={<ComparisonPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
