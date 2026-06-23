import { useI18n } from '../i18n'

export default function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n()
  const cls = status === 'active' ? 'bg-emerald-100 text-emerald-700' : status === 'closed' ? 'bg-slate-200 text-slate-700' : 'bg-amber-100 text-amber-700'
  return <span className={`badge ${cls}`}>{t(status)}</span>
}
