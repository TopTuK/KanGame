import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

export const gamesApi = {
  list: () => api.get('/games'),
  create: (data) => api.post('/games', data),
  get: (id) => api.get(`/games/${id}`),
  assignWorker: (id, worker_id, card_id) =>
    api.post(`/games/${id}/assign-worker`, { worker_id, card_id }),
  pullCard: (id, card_id) => api.post(`/games/${id}/pull-card`, { card_id }),
  startWork: (id) => api.post(`/games/${id}/start-work`),
  endDay: (id) => api.post(`/games/${id}/end-day`),
}

export const demoApi = {
  create: () => api.post('/demo'),
  assignWorker: (id, worker_id, card_id) =>
    api.post(`/demo/${id}/assign-worker`, { worker_id, card_id }),
  pullCard: (id, card_id) => api.post(`/demo/${id}/pull-card`, { card_id }),
  startWork: (id) => api.post(`/demo/${id}/start-work`),
  endDay: (id) => api.post(`/demo/${id}/end-day`),
}

export const authApi = {
  me: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  updateMe: (data) => api.patch('/auth/me', data),
}

export const leaderboardApi = {
  top: () => api.get('/leaderboard'),
}

export default api
