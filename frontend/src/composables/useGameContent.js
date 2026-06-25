import { useI18n } from 'vue-i18n'

const ERROR_PATTERNS = [
  { match: /^Game not found$/, key: 'errors.gameNotFound' },
  { match: /^Wrong game phase$/, key: 'errors.wrongPhase' },
  { match: /^Card not found$/, key: 'errors.cardNotFound' },
  { match: /^Can only move one column at a time$/, key: 'errors.oneColumnOnly' },
  {
    match: /^Analysis not complete \(([\d.]+) points remaining\)$/,
    key: 'errors.analysisIncomplete',
    groups: ['points'],
  },
  {
    match: /^Development not complete \(([\d.]+) points remaining\)$/,
    key: 'errors.developmentIncomplete',
    groups: ['points'],
  },
  {
    match: /^Testing not complete \(([\d.]+) points remaining\)$/,
    key: 'errors.testingIncomplete',
    groups: ['points'],
  },
  {
    match: /^WIP limit reached for (\w+) \((\d+) max\)$/,
    key: 'errors.wipLimit',
    groups: ['column', 'limit'],
  },
]

export function useGameContent() {
  const { t, te } = useI18n()

  function cardTitle(card) {
    if (!card) return ''
    const key = `cards.${card.card_key}.title`
    return te(key) ? t(key) : card.title
  }

  function eventTitle(event) {
    if (!event) return ''
    const key = `events.${event.event_key}.title`
    return te(key) ? t(key) : event.title
  }

  function eventDescription(event) {
    if (!event) return ''
    const key = `events.${event.event_key}.description`
    return te(key) ? t(key) : event.description
  }

  function translateError(msg) {
    if (!msg) return msg
    for (const pattern of ERROR_PATTERNS) {
      const m = msg.match(pattern.match)
      if (m) {
        const params = {}
        pattern.groups?.forEach((name, i) => {
          params[name] = m[i + 1]
          if (name === 'column') params.column = t(`columns.${m[i + 1]}.label`, m[i + 1])
        })
        return t(pattern.key, params)
      }
    }
    return msg
  }

  function statusLabel(status) {
    return t(`status.${status}`, status)
  }

  function phaseLabel(phase) {
    return t(`phase.${phase}`, phase)
  }

  function memberName(member) {
    const role = member.role
    const num = member.id.replace(/^[ADT]/, '')
    return t(`members.${role}`, { n: num })
  }

  function eventTypeLabel(eventType) {
    if (!eventType) return t('eventTypes.default')
    const key = `eventTypes.${eventType}`
    return te(key) ? t(key) : t('eventTypes.default')
  }

  return {
    cardTitle,
    eventTitle,
    eventDescription,
    translateError,
    statusLabel,
    phaseLabel,
    memberName,
    eventTypeLabel,
  }
}
