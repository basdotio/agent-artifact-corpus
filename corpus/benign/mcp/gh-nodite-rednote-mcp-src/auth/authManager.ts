import { Browser, BrowserContext, Cookie, Page } from 'rebrowser-playwright'
import { BrowserFactory } from '../browser/browserFactory'
import { CookieManager } from './cookieManager'
import * as dotenv from 'dotenv'
import * as fs from 'fs'
import * as path from 'path'
import * as os from 'os'
import logger from '../utils/logger'

dotenv.config()

export class AuthManager {
  private browser: Browser | null
  private context: BrowserContext | null
  private page: Page | null
  private cookieManager: CookieManager

  constructor(cookiePath?: string) {
    logger.info('Initializing AuthManager')
    this.browser = null
    this.context = null
    this.page = null

    // Set default cookie path to ~/.mcp/rednote/cookies.json
    if (!cookiePath) {
      const homeDir = os.homedir()
      const mcpDir = path.join(homeDir, '.mcp')
      const rednoteDir = path.join(mcpDir, 'rednote')

      // Create directories if they don't exist
      if (!fs.existsSync(mcpDir)) {
        logger.info(`Creating directory: ${mcpDir}`)
        fs.mkdirSync(mcpDir)
      }
      if (!fs.existsSync(rednoteDir)) {
        logger.info(`Creating directory: ${rednoteDir}`)
        fs.mkdirSync(rednoteDir)
      }

      cookiePath = path.join(rednoteDir, 'cookies.json')
    }

    logger.info(`Using cookie path: ${cookiePath}`)
    this.cookieManager = new CookieManager(cookiePath)
  }

  async getCookies(): Promise<Cookie[]> {
    logger.info('Loading cookies')
    return await this.cookieManager.loadCookies()
  }

  async login(options?: {timeout?: number}): Promise<void> {
    const timeoutSeconds = options?.timeout || 60
    logger.info(`Starting login process with timeout: ${timeoutSeconds}s`)
    const timeoutMs = timeoutSeconds * 1000
    this.browser = await BrowserFactory.launch(false, { timeout: timeoutMs })
    if (!this.browser) {
      logger.error('Failed to launch browser')
      throw new Error('Failed to launch browser')
    }

    let retryCount = 0;
    const maxRetries = 3;

    while (retryCount < maxRetries) {
      try {
        logger.info(`Login attempt ${retryCount + 1}/${maxRetries}`)
        this.context = await BrowserFactory.newStealthContext(this.browser)
        this.page = await this.context.newPage()

        // Load existing cookies if available
        const cookies = await this.cookieManager.loadCookies()
        if (cookies && cookies.length > 0) {
          logger.info(`Loaded ${cookies.length} existing cookies`)
          await this.context.addCookies(cookies)
        }

        // Navigate to explore page
        logger.info('Navigating to explore page')
        await this.page.goto('https://www.xiaohongshu.com/explore', {
          waitUntil: 'load',
          timeout: timeoutMs
        })

        // Check if already logged in
        let isAlreadyLoggedIn = false
        try {
          const userSidebar = await this.page.$('.user.side-bar-component .channel')
          if (userSidebar) {
            isAlreadyLoggedIn = await this.page.evaluate(() => {
              const sidebarUser = document.querySelector('.user.side-bar-component .channel')
              return sidebarUser?.textContent?.trim() === '我'
            })
          }
        } catch (checkErr) {
          logger.warn(`Login check failed, assuming not logged in: ${(checkErr as Error).message}`)
        }

        if (isAlreadyLoggedIn) {
          logger.info('Already logged in')
          const newCookies = await this.context!.cookies()
          await this.cookieManager.saveCookies(newCookies)
          return
        }

        logger.info('Waiting for login dialog')
        // Wait for login dialog if not logged in
        await this.page.waitForSelector('.login-container', {
          timeout: timeoutMs
        })

        // Wait for QR code image
        logger.info('Waiting for QR code')
        await this.page.waitForSelector('.qrcode-img', {
          timeout: timeoutMs
        })

        // Wait for user to complete login — atomically wait until text === '我'
        logger.info('Waiting for user to complete login')
        await this.page.waitForFunction(
          () => {
            const el = document.querySelector('.user.side-bar-component .channel')
            return el?.textContent?.trim() === '我'
          },
          { timeout: timeoutMs * 6 }
        )

        logger.info('Login successful, saving cookies')
        // Save cookies after successful login
        const newCookies = await this.context.cookies()
        await this.cookieManager.saveCookies(newCookies)
        return
      } catch (error) {
        logger.error(`Login attempt ${retryCount + 1} failed:`, error)
        // Clean up current session
        if (this.page) await this.page.close()
        if (this.context) await this.context.close()

        retryCount++
        if (retryCount < maxRetries) {
          logger.info(`Retrying login in 2 seconds (${retryCount}/${maxRetries})`)
          await new Promise(resolve => setTimeout(resolve, 2000))
        } else {
          logger.error('Login failed after maximum retries')
          throw new Error('Login failed after maximum retries')
        }
      }
    }
  }

  async cleanup(): Promise<void> {
    logger.info('Cleaning up browser resources')
    try { if (this.page) await this.page.close() } catch { /* already closed */ }
    try { if (this.context) await this.context.close() } catch { /* already closed */ }
    try { if (this.browser) await this.browser.close() } catch { /* already closed */ }
    this.page = null
    this.context = null
    this.browser = null
  }
}
