import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/japan-etf-analyzer/',
  server: {
    host: '0.0.0.0',
    port: 3902,
  },
})
