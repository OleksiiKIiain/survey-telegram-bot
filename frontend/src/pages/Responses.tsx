import { useEffect, useState } from 'react'
import { api } from '../api'
import { useI18n } from '../i18n'
import { AnswerRow, Survey } from '../types'

export default function Responses() {
  const { lang, t } = useI18n()
  const [surveys, setSurveys] = useState<Survey[]>([])
  const [surveyId, setSurveyId] = useState('')
  const [answers, setAnswers] = useState<AnswerRow[]>([])

  useEffect(() => {
    api.get('/surveys').then(response => setSurveys(response.data))
  }, [])

  useEffect(() => {
    api.get('/responses/answers', { params: surveyId ? { survey_id: surveyId } : {} }).then(response => setAnswers(response.data))
  }, [surveyId])

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
          {surveys.map(survey => <option value={survey.id} key={survey.id}>{surveyTitle(survey)}</option>)}
        </select>
      </div>

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
            {answers.map(answer => (
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
