import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: {
    alias: [
      {
        find: /^@\/(.+)$/,
        replacement: `${fileURLToPath(new URL('./src', import.meta.url))}/$1`
      }
    ]
  },
  test: {
    environment: 'node',
    include: ['src/**/*.spec.ts'],
    restoreMocks: true
  }
})
