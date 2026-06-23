import { useEffect, useState } from 'react'
import { api } from '../api'
import { useI18n } from '../i18n'

export default function Respondents() {
  const { t } = useI18n()
  const [rows, setRows] = useState<any[]>([])
  useEffect(() => { api.get('/respondents').then(r => setRows(r.data)) }, [])
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t('respondents')}</h1>
      <div className="panel overflow-auto"><table className="w-full text-sm"><thead><tr className="text-left text-slate-500"><th className="py-2">{t('telegramId')}</th><th>{t('username')}</th><th>{t('name')}</th><th>{t('sessions')}</th></tr></thead><tbody>{rows.map(r => <tr className="border-t" key={r.id}><td className="py-2">{r.telegram_id}</td><td>{r.username}</td><td>{r.first_name} {r.last_name}</td><td>{r.sessions_count}</td></tr>)}</tbody></table></div>
    </div>
  )
}
