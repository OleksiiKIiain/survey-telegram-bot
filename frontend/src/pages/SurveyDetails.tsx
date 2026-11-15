import { Download, Edit } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, downloadFile } from '../api'
import { useI18n } from '../i18n'
import { Survey } from '../types'
import StatusBadge from '../ui/StatusBadge'

export default function SurveyDetails() {
  const { id } = useParams()
  const { lang, t } = useI18n()
  const [survey, setSurvey] = useState<Survey | null>(null)
  useEffect(() => { api.get(`/surveys/${id}`).then(r => setSurvey(r.data)) }, [id])
  if (!survey) return <div>{t('loading')}</div>
  const title = lang === 'uk' ? survey.title_uk || survey.title : survey.title_en || survey.title
  const description = lang === 'uk' ? survey.description_uk || survey.description : survey.description_en || survey.description
  const questionText = (question: NonNullable<Survey['questions']>[number]) => (
    lang === 'uk' ? question.text_uk || question.text : question.text_en || question.text
  )
  const optionText = (option: NonNullable<Survey['questions']>[number]['options'][number]) => (
    lang === 'uk' ? option.text_uk || option.text : option.text_en || option.text
  )
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">{title}</h1><StatusBadge status={survey.status} /></div>
        <div className="flex gap-2">
          <Link className="btn-secondary" to={`/surveys/${id}/edit`}><Edit size={16} /> {t('edit')}</Link>
          <button className="btn-secondary" onClick={() => downloadFile(`/export/surveys/${id}.csv`, `survey-${id}.csv`)}><Download size={16} /> {t('csv')}</button>
          <button className="btn-secondary" onClick={() => downloadFile(`/export/surveys/${id}.xlsx`, `survey-${id}.xlsx`)}><Download size={16} /> {t('excel')}</button>
        </div>
      </div>
      <p className="text-slate-600">{description}</p>
      <section className="space-y-3">{survey.questions?.map(q => (
        <div className="panel" key={q.id}>
          <div className="flex justify-between gap-3"><h2 className="font-semibold">{q.position + 1}. {questionText(q)}</h2><span className="text-sm text-slate-500">{t(q.type)}</span></div>
          {q.options?.length > 0 && <ul className="mt-2 list-disc pl-5 text-sm text-slate-600">{q.options.map(o => <li key={o.id}>{optionText(o)}</li>)}</ul>}
        </div>
      ))}</section>
    </div>
  )
}
