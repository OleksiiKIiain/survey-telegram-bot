import { useEffect, useState } from 'react'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useI18n } from '../i18n'
import { AnalyticsOverview } from '../types'

export default function Dashboard() {
  const { lang, t } = useI18n()
  const [data, setData] = useState<AnalyticsOverview | null>(null)
  useEffect(() => { api.get('/analytics/overview').then(r => setData(r.data)) }, [])
  if (!data) return <div>{t('loading')}</div>
  const sessionTitle = (session: AnalyticsOverview['recent_sessions'][number]) => (
    lang === 'uk' ? session.survey_title_uk || session.survey_title : session.survey_title_en || session.survey_title
  )
  const statusData = data.sessions_by_status.map(item => ({
    ...item,
    label: t(String(item.name))
  }))
  const cards = [
    [t('respondents'), data.total_respondents],
    [t('sessions'), data.total_sessions],
    [t('completed'), data.completed_sessions],
    [t('activeSurveys'), data.active_surveys]
  ]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('dashboard')}</h1>
      <div className="grid gap-4 md:grid-cols-4">{cards.map(([label, value]) => (
        <div className="panel" key={label}><div className="text-sm text-slate-500">{label}</div><div className="mt-2 text-3xl font-bold">{value}</div></div>
      ))}</div>
      <div className="grid gap-4 lg:grid-cols-2">
        <section className="panel"><h2 className="mb-3 font-semibold">{t('sessionsByStatus')}</h2><ResponsiveContainer width="100%" height={260}><BarChart data={statusData}><XAxis dataKey="label" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0f766e" /></BarChart></ResponsiveContainer></section>
        <section className="panel"><h2 className="mb-3 font-semibold">{t('recentSessions')}</h2><div className="overflow-auto"><table className="w-full text-sm"><tbody>{data.recent_sessions.map(s => <tr className="border-t" key={s.session_id}><td className="py-2">{sessionTitle(s)}</td><td>{s.respondent}</td><td>{t(s.status)}</td></tr>)}</tbody></table></div></section>
      </div>
    </div>
  )
}
