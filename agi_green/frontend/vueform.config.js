// vueform.config.(js|ts)

import en from '@vueform/vueform/locales/en'
import tailwind from '@vueform/vueform/dist/tailwind'
import { defineConfig } from '@vueform/vueform'
import builder from '@vueform/builder/plugin'

export default defineConfig({
  theme: tailwind,
  locales: { en },
  locale: 'en',
  apiKey: 'u5uk-fzq2-u141-vxww-9zzs',
  plugins: [
    builder,
  ],
})
