/** Vitest configuration */
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    // 複数の waitFor を連鎖する非同期テスト（TopPage の絞り込み等）は、全体並列実行時の
    // CPU 競合で稀に waitFor が時間内に解決せず flaky になる。負荷スパイクへの余裕(testTimeout)＋
    // 環境起因の単発フレークを吸収する自動リトライ(retry)で安定化する（真の破綻は全リトライ落ちで検知）。
    testTimeout: 15000,
    retry: 2,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json'],
      exclude: ['node_modules/', 'src/__tests__/', '**/*.d.ts', '**/*.test.*'],
      thresholds: {
        statements: 70,
        branches: 70,
        functions: 70,
        lines: 70,
      },
    },
  },
})
