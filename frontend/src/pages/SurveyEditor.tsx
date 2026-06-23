import { FormEvent, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { useI18n } from '../i18n'
import { Question, QuestionType, SurveyStatus } from '../types'

const emptyQuestion = (): Question => ({ text: '', text_en: '', text_uk: '', type: 'free_text', is_required: true, position: 0, scale_min: 1, scale_max: 5, options: [] })

function hasCyrillic(value?: string | null) {
  return /[А-Яа-яІіЇїЄєҐґ]/.test(value || '')
}

function splitLocalized(base?: string | null, en?: string | null, uk?: string | null) {
  const enValue = en || ''
  const ukValue = uk || ''
  if (!ukValue && hasCyrillic(enValue)) return { en: '', uk: enValue }
  if (!enValue && !ukValue && hasCyrillic(base)) return { en: '', uk: base || '' }
  if (!enValue && !ukValue) return { en: base || '', uk: '' }
  return { en: enValue, uk: ukValue }
}

export default function SurveyEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useI18n()
  const [title, setTitle] = useState('')
  const [titleUk, setTitleUk] = useState('')
  const [description, setDescription] = useState('')
  const [descriptionUk, setDescriptionUk] = useState('')
  const [status, setStatus] = useState<SurveyStatus>('draft')
  const [questions, setQuestions] = useState<Question[]>([])
  const [translating, setTranslating] = useState(false)
  const [savedMessage, setSavedMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    if (id) api.get(`/surveys/${id}`).then(r => {
      const titlePair = splitLocalized(r.data.title, r.data.title_en, r.data.title_uk)
      const descriptionPair = splitLocalized(r.data.description, r.data.description_en, r.data.description_uk)
      setTitle(titlePair.en)
      setTitleUk(titlePair.uk)
      setDescription(descriptionPair.en)
      setDescriptionUk(descriptionPair.uk)
      setStatus(r.data.status)
      setQuestions((r.data.questions || []).map((question: Question) => ({
        ...question,
        text: splitLocalized(question.text, question.text_en, question.text_uk).en,
        text_uk: splitLocalized(question.text, question.text_en, question.text_uk).uk,
        options: (question.options || []).map(option => ({
          ...option,
          text: splitLocalized(option.text, option.text_en, option.text_uk).en,
          text_uk: splitLocalized(option.text, option.text_en, option.text_uk).uk,
        }))
      })))
    })
  }, [id])

  function updateQuestion(index: number, patch: Partial<Question>) {
    setQuestions(qs => qs.map((q, i) => i === index ? { ...q, ...patch } : q))
  }

  function setOptions(index: number, text: string) {
    updateQuestion(index, { options: text.split('\n').filter(Boolean).map((item, pos) => ({ text: item, text_en: item, text_uk: questions[index]?.options?.[pos]?.text_uk || '', position: pos })) })
  }

  function setOptionsUk(index: number, text: string) {
    const ukLines = text.split('\n')
    updateQuestion(index, {
      options: ukLines.filter(Boolean).map((item, pos) => ({
        text: questions[index]?.options?.[pos]?.text || '',
        text_en: questions[index]?.options?.[pos]?.text_en || questions[index]?.options?.[pos]?.text || '',
        text_uk: item,
        position: pos
      }))
    })
  }

  async function translateText(text: string, source_lang: 'en' | 'uk', target_lang: 'en' | 'uk') {
    if (!text.trim()) return ''
    const { data } = await api.post('/translate', { text, source_lang, target_lang })
    return data.translated_text as string
  }

  async function translatePair(uk: string, en: string) {
    if (uk.trim() && !en.trim()) return { uk, en: await translateText(uk, 'uk', 'en') }
    if (en.trim() && !uk.trim()) return { uk: await translateText(en, 'en', 'uk'), en }
    return { uk, en }
  }

  async function translateAll() {
    setTranslating(true)
    setSavedMessage('')
    try {
      const titlePair = await translatePair(titleUk, title)
      setTitle(titlePair.en)
      setTitleUk(titlePair.uk)

      const descriptionPair = await translatePair(descriptionUk, description)
      setDescription(descriptionPair.en)
      setDescriptionUk(descriptionPair.uk)

      const translatedQuestions: Question[] = []
      for (const question of questions) {
        const questionPair = await translatePair(question.text_uk || '', question.text || '')
        const translatedOptions = []
        for (const option of question.options || []) {
          const optionPair = await translatePair(option.text_uk || '', option.text || '')
          translatedOptions.push({ ...option, text: optionPair.en, text_en: optionPair.en, text_uk: optionPair.uk })
        }
        translatedQuestions.push({
          ...question,
          text: questionPair.en,
          text_en: questionPair.en,
          text_uk: questionPair.uk,
          options: translatedOptions
        })
      }
      setQuestions(translatedQuestions)
    } finally {
      setTranslating(false)
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSavedMessage('')
    setErrorMessage('')
    const baseTitle = titleUk || title
    const baseDescription = descriptionUk || description
    const normalizedQuestions = questions.map((q, i) => ({
      ...q,
      text: q.text_uk || q.text || '',
      text_en: q.text,
      position: i,
      options: (q.options || []).map((option, pos) => ({
        ...option,
        text: option.text_uk || option.text || '',
        text_en: option.text,
        text_uk: option.text_uk || '',
        position: pos
      }))
    }))
    try {
      if (id) {
        await api.patch(`/surveys/${id}`, { title: baseTitle, title_en: title, title_uk: titleUk, description: baseDescription, description_en: description, description_uk: descriptionUk, status })
        for (const [index, question] of normalizedQuestions.entries()) {
          const payload = question
          if (question.id) await api.patch(`/surveys/${id}/questions/${question.id}`, payload)
          else await api.post(`/surveys/${id}/questions`, payload)
        }
        setSavedMessage(t('changesSaved'))
      } else {
        const payload = { title: baseTitle, title_en: title, title_uk: titleUk, description: baseDescription, description_en: description, description_uk: descriptionUk, status, questions: normalizedQuestions }
        const { data } = await api.post('/surveys', payload)
        navigate(`/surveys/${data.id}`)
      }
    } catch {
      setErrorMessage('Не вдалося зберегти зміни. Перевірте поля питань і варіантів.')
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h1 className="text-2xl font-bold">{id ? t('editSurvey') : t('createSurvey')}</h1>
      {savedMessage && <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">{savedMessage}</div>}
      {errorMessage && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{errorMessage}</div>}
      <section className="panel space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm font-medium">{t('title')} UA<input className="input mt-1" value={titleUk} onChange={e => setTitleUk(e.target.value)} /></label>
          <label className="text-sm font-medium">{t('title')} EN<input className="input mt-1" value={title} onChange={e => setTitle(e.target.value)} /></label>
          <label className="text-sm font-medium">{t('description')} UA<textarea className="input mt-1 min-h-24" value={descriptionUk} onChange={e => setDescriptionUk(e.target.value)} /></label>
          <label className="text-sm font-medium">{t('description')} EN<textarea className="input mt-1 min-h-24" value={description} onChange={e => setDescription(e.target.value)} /></label>
        </div>
        <label className="block text-sm font-medium md:max-w-md">{t('status')}<select className="input mt-1" value={status} onChange={e => setStatus(e.target.value as SurveyStatus)}><option value="draft">{t('draft')}</option><option value="active">{t('active')}</option><option value="closed">{t('closed')}</option></select></label>
        <div className="flex flex-wrap gap-2 md:col-span-2">
          <button type="button" className="btn-primary" disabled={translating} onClick={translateAll}>{translating ? t('translating') : t('translate')}</button>
        </div>
      </section>
      <section className="space-y-3">
        <div className="flex items-center justify-between"><h2 className="font-semibold">{t('questions')}</h2><button type="button" className="btn-secondary" onClick={() => setQuestions([...questions, emptyQuestion()])}>{t('addQuestion')}</button></div>
        {questions.map((q, index) => (
          <div className="panel" key={q.id ?? index}>
            <div className="grid gap-3 md:grid-cols-4">
              <label className="text-sm font-medium md:col-span-2">{t('question')} UA<input className="input mt-1" value={q.text_uk || ''} onChange={e => updateQuestion(index, { text_uk: e.target.value })} /></label>
              <label className="text-sm font-medium md:col-span-2">{t('question')} EN<input className="input mt-1" value={q.text} onChange={e => updateQuestion(index, { text: e.target.value })} /></label>
              <label className="text-sm font-medium">{t('questionType')}<select className="input mt-1" value={q.type} onChange={e => updateQuestion(index, { type: e.target.value as QuestionType })}><option value="single_choice">{t('singleChoice')}</option><option value="multiple_choice">{t('multipleChoice')}</option><option value="free_text">{t('freeText')}</option><option value="scale">{t('scale')}</option></select></label>
              <label className="flex items-end gap-2 text-sm"><input type="checkbox" checked={q.is_required} onChange={e => updateQuestion(index, { is_required: e.target.checked })} /> {t('required')}</label>
            </div>
            {(q.type === 'single_choice' || q.type === 'multiple_choice') && <div className="mt-3 grid gap-3 md:grid-cols-2"><label className="block text-sm font-medium">{t('optionsOnePerLine')} UA<textarea className="input mt-1" value={(q.options || []).map(o => o.text_uk || '').join('\n')} onChange={e => setOptionsUk(index, e.target.value)} /></label><label className="block text-sm font-medium">{t('optionsOnePerLine')} EN<textarea className="input mt-1" value={(q.options || []).map(o => o.text).join('\n')} onChange={e => setOptions(index, e.target.value)} /></label></div>}
            {q.type === 'scale' && <div className="mt-3 grid gap-3 md:grid-cols-2"><label className="text-sm font-medium">{t('min')}<input className="input mt-1" type="number" value={q.scale_min || 1} onChange={e => updateQuestion(index, { scale_min: Number(e.target.value) })} /></label><label className="text-sm font-medium">{t('max')}<input className="input mt-1" type="number" value={q.scale_max || 5} onChange={e => updateQuestion(index, { scale_max: Number(e.target.value) })} /></label></div>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button type="button" className="btn-secondary" onClick={() => setQuestions(questions.filter((_, i) => i !== index))}>{t('remove')}</button>
            </div>
          </div>
        ))}
        <button type="button" className="btn-secondary w-full" onClick={() => setQuestions([...questions, emptyQuestion()])}>{t('addQuestion')}</button>
      </section>
      <button className="btn-primary">{t('saveSurvey')}</button>
    </form>
  )
}
