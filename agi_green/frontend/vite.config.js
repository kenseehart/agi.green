import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path';

export default defineConfig({
  base: '/',
  plugins: [vue()],
  build: {
    sourcemap: true, // Enable source maps
    minify: false, // Disable minification
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
