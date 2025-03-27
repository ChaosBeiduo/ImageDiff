// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  app: {
    head: {
      title: 'ImageDiff',
      htmlAttrs: {
        lang: 'en',
      },
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
      ]
    }
  },
  compatibilityDate: '2025-03-25',
  devtools: { enabled: true },
  nitro: {
    devProxy: {
      "/api/": {
        target: "http://127.0.0.1:8000/api/",
        changeOrigin: true,
        prependPath: true,
      },
    },
  },
  modules: ['@nuxt/image']
})