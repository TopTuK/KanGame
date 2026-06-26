import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export const gamesApi = {
  list: () => api.get('/games'),
  create: (data) => api.post('/games', data),
  get: (id) => api.get(`/games/${id}`),
  assignWorker: (id, worker_id, card_id) =>
    api.post(`/games/${id}/assign-worker`, { worker_id, card_id }),
  pullCard: (id, card_id) => api.post(`/games/${id}/pull-card`, { card_id }),
  pullBacklog: (id, card_type) => api.post(`/games/${id}/pull-backlog`, { card_type }),
  pullExpedite: (id) => api.post(`/games/${id}/pull-expedite`),
  startWork: (id) => api.post(`/games/${id}/start-work`),
  endDay: (id) => api.post(`/games/${id}/end-day`),
}

export default api
