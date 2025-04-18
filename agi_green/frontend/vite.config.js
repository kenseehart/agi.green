import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@agi.green': path.resolve(__dirname, './src'),
    },
  },
  build: {
    sourcemap: true, // Enable source maps for debugging
    lib: {
      entry: path.resolve(__dirname, 'src/main.js'),
      name: 'AgiGreen',
      formats: ['es', 'umd'],
      fileName: (format) => `agi.green.${format}.js`
    },
    rollupOptions: {
      external: ['vue', 'primevue'],
      output: {
        exports: 'named',
        globals: {
          vue: 'Vue',
          primevue: 'PrimeVue'
        },
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === 'style.css') {
            return 'agi.green.css';
          }
          return assetInfo.name;
        }
      }
    },
    cssCodeSplit: false
  }
})
