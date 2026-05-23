// Root component — defines routes: / (sector select) and /dashboard/:market
import { Routes, Route, Navigate } from 'react-router-dom'
import SectorSelectPage from '@/modules/sector-select/pages/sector-select-page'
import DashboardPage from '@/modules/dashboard/pages/dashboard-page'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SectorSelectPage />} />
      <Route path="/dashboard/:market" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
