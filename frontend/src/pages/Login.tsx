import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useI18n } from '../i18n'

export default function Login() {
  const navigate = useNavigate()
  const { lang, setLang, t } = useI18n()
  const [email, setEmail] = useState('admin@example.com')
  const [password, setPassword] = useState('admin12345')
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('token', data.access_token)
      navigate('/')
    } catch {
      setError(t('invalidLogin'))
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <form onSubmit={submit} className="panel w-full max-w-sm">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h1 className="mb-1 text-2xl font-bold text-slate-900">{t('adminLogin')}</h1>
            <p className="text-sm text-slate-500">{t('loginSubtitle')}</p>
          </div>
          <select className="input w-28" value={lang} onChange={event => setLang(event.target.value as 'en' | 'uk')}>
            <option value="en">EN</option>
            <option value="uk">UA</option>
          </select>
        </div>
        <label className="mb-3 block text-sm font-medium">{t('email')}<input className="input mt-1" value={email} onChange={e => setEmail(e.target.value)} /></label>
        <label className="mb-4 block text-sm font-medium">{t('password')}<input className="input mt-1" type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
        {error && <div className="mb-3 rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</div>}
        <button className="btn-primary w-full">{t('signIn')}</button>
      </form>
    </main>
  )
}
