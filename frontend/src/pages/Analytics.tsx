import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import { useI18n } from '../i18n'
import { AnalyticsOverview, Survey } from '../types'

type QuestionStat = AnalyticsOverview['question_stats'][number]

export default function Analytics() {
  const { lang, t } = useI18n()
  const [surveys, setSurveys] = useState<Survey[]>([])
  const [surveyId, setSurveyId] = useState('')
  const [data, setData] = useState<AnalyticsOverview | null>(null)

  useEffect(() => {
    api.get('/surveys').then(response => setSurveys(response.data))
  }, [])

  useEffect(() => {
    api.get('/analytics/overview', { params: surveyId ? { survey_id: surveyId } : {} }).then(response => setData(response.data))
  }, [surveyId])

  if (!data) return <div>{t('loading')}</div>

  const surveyTitle = (survey: Survey) => (
    lang === 'uk' ? survey.title_uk || survey.title : survey.title_en || survey.title
  )

  const questionTitle = (question: QuestionStat) => (
    lang === 'uk' ? question.question_text_uk || question.question_text : question.question_text_en || question.question_text
  )

  const chartData = (question: QuestionStat) => question.distribution.map(item => ({
    ...item,
    label: lang === 'uk' ? item.name_uk || item.name : item.name_en || item.name
  }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('analytics')}</h1>
        <select className="input max-w-xs" value={surveyId} onChange={event => setSurveyId(event.target.value)}>
          <option value="">{t('allSurveys')}</option>
          {surveys.map(survey => <option value={survey.id} key={survey.id}>{surveyTitle(survey)}</option>)}
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="panel">
          <div className="text-sm text-slate-500">{t('completed')}</div>
          <div className="text-3xl font-bold">{data.completed_sessions}</div>
        </div>
        <div className="panel">
          <div className="text-sm text-slate-500">{t('unfinished')}</div>
          <div className="text-3xl font-bold">{data.unfinished_sessions}</div>
        </div>
        <div className="panel">
          <div className="text-sm text-slate-500">{t('respondents')}</div>
          <div className="text-3xl font-bold">{data.total_respondents}</div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {data.question_stats.map(question => (
          <section className="panel" key={question.question_id}>
            <h2 className="font-semibold">{questionTitle(question)}</h2>
            <div className="mb-2 text-sm text-slate-500">
              {t(question.question_type)} · {question.total_answers} {t('answers')}
              {question.average != null ? ` · ${t('average')} ${question.average}` : ''}
            </div>
            {question.distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData(question)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0f766e" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <ul className="mt-3 space-y-2 text-sm">
                {question.text_answers.map((text, index) => (
                  <li className="rounded-md bg-slate-50 p-2" key={index}>{text}</li>
                ))}
              </ul>
            )}
          </section>
        ))}
      </div>
    </div>
  )
}
