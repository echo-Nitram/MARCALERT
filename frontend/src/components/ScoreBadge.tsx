interface Props {
  score: number
  size?: 'sm' | 'md'
}

export default function ScoreBadge({ score, size = 'md' }: Props) {
  const color =
    score >= 90 ? 'bg-red-100 text-red-800' :
    score >= 75 ? 'bg-orange-100 text-orange-800' :
    score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-gray-100 text-gray-600'

  const cls = size === 'sm'
    ? 'badge text-xs px-2 py-0.5 font-bold'
    : 'badge px-2.5 py-1 font-bold'

  return <span className={`${cls} ${color}`}>{score.toFixed(0)}/100</span>
}
