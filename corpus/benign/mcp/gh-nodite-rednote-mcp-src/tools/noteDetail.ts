import { Note } from './rednoteTools'
import logger from '../utils/logger'
import { Page } from 'rebrowser-playwright'

export interface NoteDetail {
  title: string
  content: string
  tags: string[]
  imgs?: string[]
  videos?: string[]
  url: string
  author: string
  likes?: number
  collects?: number
  comments?: number
}

// Module-level export so unit tests can call this directly.
// IMPORTANT: keep in sync with the identical copy inside getContent below.
export function chineseUnitStrToNumber(str: string): number {
  if (str.includes('万')) {
    return Number(str.replace('万', '').trim()) * 10000
  }
  return Number(str)
}

export async function GetNoteDetail(page: Page): Promise<NoteDetail> {
  // Wait for content to load
  logger.info('Waiting for content to load')
  await page.waitForSelector('.note-container')
  await page.waitForSelector('.media-container')

  async function getContent() {
    // Browser-side copy — page.evaluate runs in a sandbox with no module scope.
    // IMPORTANT: keep in sync with the module-level chineseUnitStrToNumber above.
    function chineseUnitStrToNumber(str: string): number {
      if (str.includes('万')) {
        return Number(str.replace('万', '').trim()) * 10000
      } else {
        return Number(str)
      }
    }
    // Get main article content
    const article = document.querySelector('.note-container')
    if (!article) throw new Error('Article not found')

    // Get title from h1 or first text block
    const title =
      article.querySelector('#detail-title')?.textContent?.trim() ||
      article.querySelector('.title')?.textContent?.trim() ||
      ''

    // Get content from article text
    const contentBlock = article.querySelector('.note-scroller')
    if (!contentBlock) throw new Error('Content block not found')
    const content = contentBlock.querySelector('.note-content .note-text span')?.textContent?.trim() || ''
    // Get tags from article text
    const tags = Array.from(contentBlock?.querySelectorAll('.note-content .note-text a')).map((tag) => {
      return tag.textContent?.trim().replace('#', '') || ''
    })

    // Get author info
    const authorElement = article.querySelector('.author-container .info')
    const author = authorElement?.querySelector('.username')?.textContent?.trim() || ''

    const interactContainer = document.querySelector('.interact-container')
    const commentsNumber = interactContainer?.querySelector('.chat-wrapper .count')?.textContent?.trim() || ''
    const likesNumber = interactContainer?.querySelector('.like-wrapper .count')?.textContent?.trim() || ''

    const imgs = Array.from(document.querySelectorAll('.media-container img')).map((img) => {
      return img.getAttribute('src') || ''
    })

    const videos = Array.from(document.querySelectorAll('.media-container video')).map((video) => {
      return video.getAttribute('src') || ''
    })

    return {
      title,
      content,
      tags,
      author,
      imgs,
      videos,
      url: '',
      likes: chineseUnitStrToNumber(likesNumber),
      comments: chineseUnitStrToNumber(commentsNumber)
    } as Note
  }

  return await page.evaluate(getContent)
}
