import { useSearchParams } from 'react-router-dom'
import { useLiveQuery } from '../hooks/useLiveQuery'
import { useI18n } from '../i18n'
import { AnswerRow, Survey } from '../types'

export default function Responses() {
  const { lang, t } = useI18n()
  const [searchParams, setSearchParams] = useSearchParams()
  const surveyId = searchParams.get('survey_id') || ''
  const setSurveyId = (id: string) => setSearchParams(current => {
    const next = new URLSearchParams(current)
    if (id) next.set('survey_id', id)
    else next.delete('survey_id')
    return next
  }, { replace: true })
  const { data: surveys } = useLiveQuery<Survey[]>('/surveys')
  const { data: answers, error } = useLiveQuery<AnswerRow[]>(
    `/responses/answers${surveyId ? `?survey_id=${surveyId}` : ''}`
  )

  const surveyTitle = (survey: Survey) => (
    lang === 'uk' ? survey.title_uk || survey.title : survey.title_en || survey.title
  )

  const questionText = (answer: AnswerRow) => (
    lang === 'uk' ? answer.question_text_uk || answer.question_text : answer.question_text_en || answer.question_text
  )

  const answerValue = (answer: AnswerRow) => {
    if (answer.text_value) return answer.text_value
    if (answer.number_value !== null && answer.number_value !== undefined) return String(answer.number_value)
    if (answer.option_id) {
      return lang === 'uk' ? answer.option_text_uk || answer.option_text : answer.option_text_en || answer.option_text
    }
    const optionTexts = lang === 'uk' ? answer.option_texts_uk : answer.option_texts_en
    return optionTexts?.length ? optionTexts.join(', ') : (answer.option_texts || []).join(', ')
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('responses')}</h1>
        <select className="input max-w-xs" value={surveyId} onChange={event => setSurveyId(event.target.value)}>
          <option value="">{t('allSurveys')}</option>
          {(surveys || []).map(survey => <option value={survey.id} key={survey.id}>{surveyTitle(survey)}</option>)}
        </select>
      </div>

      {error && <p role="status" className="text-sm text-red-700">{t('refreshError')}</p>}
      {!answers && !error && <p role="status">{t('loading')}</p>}

      <div className="panel overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="py-2">{t('session')}</th>
              <th>{t('question')}</th>
              <th>{t('answer')}</th>
              <th>{t('date')}</th>
            </tr>
          </thead>
          <tbody>
            {(answers || []).map(answer => (
              <tr className="border-t" key={answer.id}>
                <td className="py-2">#{answer.session_id}</td>
                <td>{questionText(answer)}</td>
                <td>{answerValue(answer)}</td>
                <td>{new Date(answer.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
