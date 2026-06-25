import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export const gamesApi = {
  list: () => api.get('/games'),
  create: (data) => api.post('/games', data),
  get: (id) => api.get(`/games/${id}`),
  resolveEvent: (id) => api.post(`/games/${id}/resolve-event`),
  allocate: (id, allocations) => api.post(`/games/${id}/allocate`, { allocations }),
  moveCard: (id, card_id, target_column) => api.post(`/games/${id}/move-card`, { card_id, target_column }),
  endDay: (id) => api.post(`/games/${id}/end-day`),
}

export default api
