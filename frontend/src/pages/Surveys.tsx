import { Edit, Eye, Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useI18n } from '../i18n'
import { Survey } from '../types'
import StatusBadge from '../ui/StatusBadge'

export default function Surveys() {
  const { lang, t } = useI18n()
  const [surveys, setSurveys] = useState<Survey[]>([])
  const load = () => api.get('/surveys').then(r => setSurveys(r.data))
  useEffect(() => { void load() }, [])
  const surveyTitle = (survey: Survey) => (
    lang === 'uk' ? survey.title_uk || survey.title : survey.title_en || survey.title
  )
  async function remove(id: number) {
    if (confirm(t('deleteSurveyConfirm'))) {
      await api.delete(`/surveys/${id}`)
      load()
    }
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h1 className="text-2xl font-bold">{t('surveys')}</h1><Link className="btn-primary" to="/surveys/new"><Plus size={16} /> {t('newSurvey')}</Link></div>
      <div className="panel overflow-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-slate-500"><th className="py-2">{t('title')}</th><th>{t('status')}</th><th>{t('questions')}</th><th>{t('responses')}</th><th></th></tr></thead>
          <tbody>{surveys.map(s => <tr className="border-t" key={s.id}><td className="py-3 font-medium">{surveyTitle(s)}</td><td><StatusBadge status={s.status} /></td><td>{s.questions_count}</td><td>{s.responses_count}</td><td className="flex justify-end gap-2 py-2"><Link className="btn-secondary" to={`/surveys/${s.id}`}><Eye size={15} /></Link><Link className="btn-secondary" to={`/surveys/${s.id}/edit`}><Edit size={15} /></Link><button className="btn-secondary" onClick={() => remove(s.id)}><Trash2 size={15} /></button></td></tr>)}</tbody>
        </table>
      </div>
    </div>
  )
}
