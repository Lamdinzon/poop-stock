import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  preview: {
    // Railway（跟其他 PaaS）會用動態網域打進來，Vite預設只認識localhost，
    // 這裡放行所有網域，不然正式部署後會被Vite的Host檢查擋下來。
    allowedHosts: true,
  },
})
