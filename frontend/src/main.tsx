import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles.css'
import { I18nProvider } from './i18n'
import AppLayout from './ui/AppLayout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Surveys from './pages/Surveys'
import SurveyEditor from './pages/SurveyEditor'
import SurveyDetails from './pages/SurveyDetails'
import Respondents from './pages/Respondents'
import Responses from './pages/Responses'
import Analytics from './pages/Analytics'

function Protected({ children }: { children: React.ReactNode }) {
  return localStorage.getItem('token') ? <>{children}</> : <Navigate to="/login" />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <I18nProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Protected><AppLayout /></Protected>}>
            <Route index element={<Dashboard />} />
            <Route path="surveys" element={<Surveys />} />
            <Route path="surveys/new" element={<SurveyEditor />} />
            <Route path="surveys/:id" element={<SurveyDetails />} />
            <Route path="surveys/:id/edit" element={<SurveyEditor />} />
            <Route path="respondents" element={<Respondents />} />
            <Route path="responses" element={<Responses />} />
            <Route path="analytics" element={<Analytics />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </I18nProvider>
  </React.StrictMode>
)
