// Root component — routes: / Markets, /dashboard/:market, /news, /about
import { Routes, Route, Navigate } from 'react-router-dom'
import SectorSelectPage from '@/modules/sector-select/pages/sector-select-page'
import DashboardPage from '@/modules/dashboard/pages/dashboard-page'
import NewsPage from '@/modules/news/pages/news-page'
import AboutPage from '@/modules/about/pages/about-page'

export default function App() {
  return (
    <Routes>
      <Route path="/"                    element={<SectorSelectPage />} />
      <Route path="/dashboard/:market"   element={<DashboardPage />} />
      <Route path="/news"                element={<NewsPage />} />
      <Route path="/about"               element={<AboutPage />} />
      <Route path="*"                    element={<Navigate to="/" replace />} />
    </Routes>
  )
}
