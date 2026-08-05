import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('[API]', err?.response?.status, err?.message)
    return Promise.reject(err)
  },
)

export default http
