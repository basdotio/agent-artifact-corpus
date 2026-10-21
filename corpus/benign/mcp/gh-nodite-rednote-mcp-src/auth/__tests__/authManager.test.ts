import { AuthManager } from '../authManager'
import type { Cookie } from 'rebrowser-playwright'

jest.mock('rebrowser-playwright')
jest.mock('../../browser/browserFactory', () => ({
  BrowserFactory: {
    launch: jest.fn(),
    newStealthContext: jest.fn(),
  },
}))
jest.mock('../cookieManager')
jest.mock('../../utils/logger', () => ({
  __esModule: true,
  default: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
  },
}))

// jest.requireMock at runtime: real playwright types don't export mockPage/mockContext/mockBrowser
const { mockPage, mockContext, mockBrowser } = jest.requireMock('rebrowser-playwright')

jest.mock('fs', () => {
  const fsMock = {
    existsSync: jest.fn().mockReturnValue(true),
    mkdirSync: jest.fn(),
    promises: {
      writeFile: jest.fn().mockResolvedValue(undefined),
      readFile: jest.fn(),
      unlink: jest.fn().mockResolvedValue(undefined),
    },
  }
  return { ...fsMock, default: fsMock }
})

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { CookieManager } = require('../cookieManager')

const COOKIE_PATH = '/tmp/test-cookies.json'
const sampleCookies: Cookie[] = [
  {
    name: 'session',
    value: 'abc',
    domain: '.xiaohongshu.com',
    path: '/',
    expires: -1,
    httpOnly: false,
    secure: false,
    sameSite: 'Lax',
  },
]

describe('AuthManager', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    CookieManager.mockImplementation(() => ({
      loadCookies: jest.fn().mockResolvedValue([]),
      saveCookies: jest.fn().mockResolvedValue(undefined),
      clearCookies: jest.fn().mockResolvedValue(undefined),
    }))
    const { BrowserFactory } = jest.requireMock('../../browser/browserFactory')
    BrowserFactory.launch.mockResolvedValue(mockBrowser)
    BrowserFactory.newStealthContext.mockResolvedValue(mockContext)
    mockContext.newPage.mockResolvedValue(mockPage)  // re-wire after clearAllMocks
  })

  describe('getCookies', () => {
    it('returns cookies from CookieManager.loadCookies', async () => {
      const mockLoad = jest.fn().mockResolvedValue(sampleCookies)
      CookieManager.mockImplementation(() => ({ loadCookies: mockLoad }))

      const auth = new AuthManager(COOKIE_PATH)
      const result = await auth.getCookies()

      expect(mockLoad).toHaveBeenCalled()
      expect(result).toEqual(sampleCookies)
    })
  })

  describe('login', () => {
    it('completes without error when cookies exist and evaluate returns logged-in', async () => {
      const mockSave = jest.fn().mockResolvedValue(undefined)
      CookieManager.mockImplementation(() => ({
        loadCookies: jest.fn().mockResolvedValue(sampleCookies),
        saveCookies: mockSave,
      }))

      mockPage.$.mockResolvedValue({ textContent: '我' })
      mockPage.evaluate.mockResolvedValue(true)
      mockContext.cookies.mockResolvedValue(sampleCookies)

      const auth = new AuthManager(COOKIE_PATH)
      await auth.login()

      expect(mockContext.addCookies).toHaveBeenCalledWith(sampleCookies)
      expect(mockContext.cookies).toHaveBeenCalled()
      expect(mockSave).toHaveBeenCalled()
    })

    it('completes without error when no cookies, waitForSelector resolves, and waitForFunction resolves', async () => {
      const mockSave = jest.fn().mockResolvedValue(undefined)
      CookieManager.mockImplementation(() => ({
        loadCookies: jest.fn().mockResolvedValue([]),
        saveCookies: mockSave,
      }))

      mockPage.$.mockResolvedValue(null)
      mockPage.waitForSelector.mockResolvedValue(undefined)
      mockPage.waitForFunction.mockResolvedValue(undefined)
      mockContext.cookies.mockResolvedValue(sampleCookies)

      const auth = new AuthManager(COOKIE_PATH)
      await auth.login()

      expect(mockSave).toHaveBeenCalled()
    })

    it('throws "Login failed after maximum retries" when all 3 retries fail', async () => {
      CookieManager.mockImplementation(() => ({
        loadCookies: jest.fn().mockResolvedValue([]),
        saveCookies: jest.fn(),
      }))

      mockPage.$.mockResolvedValue(null)
      mockPage.waitForSelector.mockResolvedValue(undefined)
      mockPage.waitForFunction.mockRejectedValue(new Error('Timeout exceeded'))

      jest.useFakeTimers()
      try {
        const auth = new AuthManager(COOKIE_PATH)
        const loginPromise = auth.login()
        const expectPromise = expect(loginPromise).rejects.toThrow('Login failed after maximum retries')
        await jest.runAllTimersAsync()
        await expectPromise
      } finally {
        jest.useRealTimers()
      }
    })
  })

  describe('cleanup', () => {
    it('calls page.close and context.close after login', async () => {
      CookieManager.mockImplementation(() => ({
        loadCookies: jest.fn().mockResolvedValue(sampleCookies),
        saveCookies: jest.fn().mockResolvedValue(undefined),
      }))

      mockPage.$.mockResolvedValue({ textContent: '我' })
      mockPage.evaluate.mockResolvedValue(true)
      mockContext.cookies.mockResolvedValue(sampleCookies)

      const auth = new AuthManager(COOKIE_PATH)
      await auth.login()

      jest.clearAllMocks()
      await auth.cleanup()

      expect(mockPage.close).toHaveBeenCalledTimes(1)
      expect(mockContext.close).toHaveBeenCalledTimes(1)
    })
  })
})
