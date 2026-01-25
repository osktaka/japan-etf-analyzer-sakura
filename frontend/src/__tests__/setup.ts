/** Test setup file */
import { vi, afterEach } from 'vitest'
import '@testing-library/jest-dom/vitest'

// Mock CSS modules
const mockCSSModule = new Proxy(
  {},
  {
    get: (_, prop) => (typeof prop === 'string' ? prop : undefined),
  }
)

// Global mocks for CSS modules
vi.mock('*.module.css', () => mockCSSModule)

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
class ResizeObserverMock {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: ResizeObserverMock,
})

// Cleanup after each test
afterEach(() => {
  vi.clearAllMocks()
})
