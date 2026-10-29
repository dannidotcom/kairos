import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/auth';
import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import LandingPage from './pages/LandingPage';
import LegalPage from './pages/LegalPage';
import DashboardPage from './pages/DashboardPage';
import LeadsPage from './pages/LeadsPage';
import SignalsPage from './pages/SignalsPage';
import CampaignsPage from './pages/CampaignsPage';
import UniboxPage from './pages/UniboxPage';
import IcpPage from './pages/IcpPage';
import SettingsPage from './pages/SettingsPage';
import BrandPage from './pages/BrandPage';
import InvitePage from './pages/InvitePage';
import { PageLoader } from './components/UI';

function Protected() { const { user, loading } = useAuth(); if (loading) return <PageLoader />; return user ? <Layout /> : <Navigate to="/login" replace />; }
export default function App() {
  return <Routes>
    <Route path="/" element={<LandingPage />} />
    <Route path="/mentions-legales" element={<LegalPage type="legal" />} />
    <Route path="/privacy" element={<LegalPage type="privacy" />} />
    <Route path="/terms" element={<LegalPage type="terms" />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/invite/:token" element={<InvitePage />} />
    <Route path="/app" element={<Protected />}>
      <Route index element={<DashboardPage />} />
      <Route path="leads" element={<LeadsPage />} />
      <Route path="signals" element={<SignalsPage />} />
      <Route path="campaigns" element={<CampaignsPage />} />
      <Route path="campaigns/:id" element={<CampaignsPage />} />
      <Route path="unibox" element={<UniboxPage />} />
      <Route path="unibox/:id" element={<UniboxPage />} />
      <Route path="icp" element={<IcpPage />} />
      <Route path="settings" element={<SettingsPage />} />
      {import.meta.env.DEV && <Route path="brand" element={<BrandPage />} />}
    </Route>
    <Route path="/app/*" element={<Navigate to="/app" replace />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}
