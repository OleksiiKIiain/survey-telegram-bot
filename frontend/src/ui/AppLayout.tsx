import { BarChart3, ClipboardList, Home, LogOut, MessageSquare, Users } from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'

const links = [
  { to: '/', label: 'dashboard', icon: Home },
  { to: '/surveys', label: 'surveys', icon: ClipboardList },
  { to: '/respondents', label: 'respondents', icon: Users },
  { to: '/responses', label: 'responses', icon: MessageSquare },
  { to: '/analytics', label: 'analytics', icon: BarChart3 }
]

export default function AppLayout() {
  const navigate = useNavigate()
  const { lang, setLang, t } = useI18n()
  return (
    <div className="min-h-screen md:flex">
      <aside className="border-r border-slate-200 bg-white p-4 md:w-64">
        <div className="mb-6 text-lg font-bold text-teal-800">{t('appTitle')}</div>
        <nav className="grid gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-2 rounded-md px-3 py-2 text-sm ${isActive ? 'bg-teal-50 text-teal-800' : 'text-slate-700 hover:bg-slate-50'}`}>
              <Icon size={18} />{t(label)}
            </NavLink>
          ))}
        </nav>
        <label className="mt-6 block text-xs font-semibold uppercase text-slate-500">
          {t('language')}
          <select className="input mt-2" value={lang} onChange={event => setLang(event.target.value as 'en' | 'uk')}>
            <option value="en">{t('english')}</option>
            <option value="uk">{t('ukrainian')}</option>
          </select>
        </label>
        <button className="btn-secondary mt-6 w-full" onClick={() => { localStorage.removeItem('token'); navigate('/login') }}>
          <LogOut size={16} /> {t('logout')}
        </button>
      </aside>
      <main className="flex-1 p-4 md:p-6"><Outlet /></main>
    </div>
  )
}
