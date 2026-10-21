import { CookieManager } from '../cookieManager'
import type { Cookie } from 'rebrowser-playwright'

jest.mock('../../utils/logger')

jest.mock('fs', () => {
  const actualFs = jest.requireActual('fs')
  const fsMock = {
    ...actualFs,
    existsSync: jest.fn(),
    mkdirSync: jest.fn(),
    promises: {
      ...actualFs.promises,
      writeFile: jest.fn().mockResolvedValue(undefined),
      readFile: jest.fn().mockResolvedValue('[]'),
      unlink: jest.fn().mockResolvedValue(undefined),
    },
  }
  return { ...fsMock, default: fsMock }
})

// eslint-disable-next-line @typescript-eslint/no-require-imports
const fs = require('fs')

const COOKIE_PATH = '/tmp/test-cookies.json'
const COOKIE_DIR = '/tmp'

const sampleCookies: Cookie[] = [
  {
    name: 'session',
    value: 'abc123',
    domain: '.xiaohongshu.com',
    path: '/',
    expires: -1,
    httpOnly: false,
    secure: false,
    sameSite: 'Lax',
  },
]

describe('CookieManager', () => {
  let manager: CookieManager

  beforeEach(() => {
    jest.clearAllMocks()
    manager = new CookieManager(COOKIE_PATH)
  })

  describe('saveCookies', () => {
    it('writes file when directory exists', async () => {
      fs.existsSync.mockReturnValue(true)

      await manager.saveCookies(sampleCookies)

      expect(fs.mkdirSync).not.toHaveBeenCalled()
      expect(fs.promises.writeFile).toHaveBeenCalledWith(
        COOKIE_PATH,
        JSON.stringify(sampleCookies, null, 2)
      )
    })

    it('creates directory then writes file when directory does not exist', async () => {
      fs.existsSync.mockReturnValue(false)

      await manager.saveCookies(sampleCookies)

      expect(fs.mkdirSync).toHaveBeenCalledWith(COOKIE_DIR, { recursive: true })
      expect(fs.promises.writeFile).toHaveBeenCalledWith(
        COOKIE_PATH,
        JSON.stringify(sampleCookies, null, 2)
      )
    })
  })

  describe('loadCookies', () => {
    it('returns empty array when file does not exist', async () => {
      fs.existsSync.mockReturnValue(false)

      const result = await manager.loadCookies()

      expect(result).toEqual([])
      expect(fs.promises.readFile).not.toHaveBeenCalled()
    })

    it('reads and parses cookies when file exists', async () => {
      fs.existsSync.mockReturnValue(true)
      fs.promises.readFile.mockResolvedValue(JSON.stringify(sampleCookies))

      const result = await manager.loadCookies()

      expect(fs.promises.readFile).toHaveBeenCalledWith(COOKIE_PATH, 'utf-8')
      expect(result).toEqual(sampleCookies)
    })
  })

  describe('clearCookies', () => {
    it('deletes file when it exists', async () => {
      fs.existsSync.mockReturnValue(true)

      await manager.clearCookies()

      expect(fs.promises.unlink).toHaveBeenCalledWith(COOKIE_PATH)
    })

    it('does nothing when file does not exist', async () => {
      fs.existsSync.mockReturnValue(false)

      await manager.clearCookies()

      expect(fs.promises.unlink).not.toHaveBeenCalled()
    })
  })
})
