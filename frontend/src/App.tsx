// Root component — routes: / Home, /dashboard/:market, /news, /about
import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from '@/modules/home/pages/home-page'
import DashboardPage from '@/modules/dashboard/pages/dashboard-page'
import NewsPage from '@/modules/news/pages/news-page'
import AboutPage from '@/modules/about/pages/about-page'

export default function App() {
  return (
    <Routes>
      <Route path="/"                    element={<HomePage />} />
      <Route path="/dashboard/:market"   element={<DashboardPage />} />
      <Route path="/news"                element={<NewsPage />} />
      <Route path="/about"               element={<AboutPage />} />
      <Route path="*"                    element={<Navigate to="/" replace />} />
    </Routes>
  )
}
