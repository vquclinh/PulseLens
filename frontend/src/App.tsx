// Root component — public home, nested intelligence workspace, and analyst chat
import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from '@/modules/home/pages/home-page'
import WorkspacePage from '@/modules/workspace'
import ChatPage from '@/modules/chat/pages/chat-page'
import NewsPage from '@/modules/news/pages/news-page'

export default function App() {
  return (
    <Routes>
      <Route path="/"                    element={<HomePage />} />
      <Route path="/workspace"           element={<WorkspacePage view="overview" />} />
      <Route path="/workspace/evidence"  element={<WorkspacePage view="evidence" />} />
      <Route path="/workspace/pricing"   element={<WorkspacePage view="pricing" />} />
      <Route path="/workspace/signals"   element={<WorkspacePage view="signals" />} />
      <Route path="/workspace/companies" element={<WorkspacePage view="companies" />} />
      <Route path="/workspace/pipeline"  element={<WorkspacePage view="pipeline" />} />
      <Route path="/chat"                element={<ChatPage />} />

      <Route path="/dashboard"           element={<Navigate to="/workspace" replace />} />
      <Route path="/dashboard/:market"   element={<Navigate to="/workspace" replace />} />
      <Route path="/evidence"            element={<Navigate to="/workspace/evidence" replace />} />
      <Route path="/pricing"             element={<Navigate to="/workspace/pricing" replace />} />
      <Route path="/signals"             element={<Navigate to="/workspace/signals" replace />} />
      <Route path="/companies"           element={<Navigate to="/workspace/companies" replace />} />
      <Route path="/pipeline"            element={<Navigate to="/workspace/pipeline" replace />} />
      <Route path="/about"               element={<Navigate to="/workspace/pipeline" replace />} />

      <Route path="/news"                element={<NewsPage />} />
      <Route path="*"                    element={<Navigate to="/" replace />} />
    </Routes>
  )
}
