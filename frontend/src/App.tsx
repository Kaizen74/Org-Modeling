import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import GradeConfig from './pages/GradeConfig'
import Upload from './pages/Upload'
import Metrics from './pages/Metrics'
import AIAnalysis from './pages/AIAnalysis'
import OrgChart from './pages/OrgChart'
import WorkActivities from './pages/WorkActivities'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/grades" element={<GradeConfig />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/analysis" element={<AIAnalysis />} />
        <Route path="/work-activities" element={<WorkActivities />} />
        <Route path="/org-chart" element={<OrgChart />} />
      </Routes>
    </Layout>
  )
}

export default App
