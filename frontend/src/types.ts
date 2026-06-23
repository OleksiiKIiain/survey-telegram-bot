export type SurveyStatus = 'draft' | 'active' | 'closed'
export type QuestionType = 'single_choice' | 'multiple_choice' | 'free_text' | 'scale'

export interface Option {
  id?: number
  text: string
  text_en?: string | null
  text_uk?: string | null
  position: number
}

export interface Question {
  id?: number
  text: string
  text_en?: string | null
  text_uk?: string | null
  type: QuestionType
  is_required: boolean
  position: number
  scale_min?: number | null
  scale_max?: number | null
  options: Option[]
}

export interface Survey {
  id: number
  title: string
  title_en?: string | null
  title_uk?: string | null
  description?: string
  description_en?: string | null
  description_uk?: string | null
  status: SurveyStatus
  created_at: string
  updated_at: string
  questions_count?: number
  responses_count?: number
  questions?: Question[]
}

export interface AnalyticsOverview {
  total_respondents: number
  total_sessions: number
  completed_sessions: number
  unfinished_sessions: number
  active_surveys: number
  sessions_by_status: { name: string; value: number }[]
  question_stats: {
    question_id: number
    question_text: string
    question_text_en?: string | null
    question_text_uk?: string | null
    question_type: string
    total_answers: number
    distribution: { name: string; name_en?: string | null; name_uk?: string | null; value: number }[]
    average?: number
    text_answers: string[]
  }[]
  recent_sessions: {
    session_id: number
    survey_title: string
    survey_title_en?: string | null
    survey_title_uk?: string | null
    respondent: string
    status: string
    started_at: string
    completed_at?: string
  }[]
}

export interface AnswerRow {
  id: number
  session_id: number
  question_id: number
  option_id?: number | null
  option_ids?: number[] | null
  text_value?: string | null
  number_value?: number | null
  created_at: string
  question_text?: string | null
  question_text_en?: string | null
  question_text_uk?: string | null
  option_text?: string | null
  option_text_en?: string | null
  option_text_uk?: string | null
  option_texts?: string[]
  option_texts_en?: string[]
  option_texts_uk?: string[]
}
