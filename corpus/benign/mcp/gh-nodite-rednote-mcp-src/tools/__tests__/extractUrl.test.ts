import { RedNoteTools } from '../rednoteTools'

jest.mock('rebrowser-playwright')
jest.mock('../../auth/authManager')
jest.mock('../../utils/logger')

describe('RedNoteTools.extractRedBookUrl', () => {
  let tools: RedNoteTools

  beforeEach(() => {
    tools = new RedNoteTools()
  })

  it('extracts xhslink URL embedded in share text', () => {
    const input = '60 坚定 👆去小红书看看吧！http://xhslink.com/a/abc123 复制本条信息'
    expect(tools.extractRedBookUrl(input)).toBe('http://xhslink.com/a/abc123')
  })

  it('returns bare xhslink URL unchanged', () => {
    expect(tools.extractRedBookUrl('http://xhslink.com/xyz')).toBe('http://xhslink.com/xyz')
  })

  it('extracts xiaohongshu.com URL', () => {
    expect(tools.extractRedBookUrl('https://www.xiaohongshu.com/explore/abc123')).toBe(
      'https://www.xiaohongshu.com/explore/abc123'
    )
  })

  it('stops xiaohongshu URL at Chinese comma', () => {
    expect(tools.extractRedBookUrl('https://www.xiaohongshu.com/abc，其他内容')).toBe(
      'https://www.xiaohongshu.com/abc'
    )
  })

  it('returns plain text unchanged when no URL present', () => {
    expect(tools.extractRedBookUrl('这是一段普通文字')).toBe('这是一段普通文字')
  })

  it('returns empty string unchanged', () => {
    expect(tools.extractRedBookUrl('')).toBe('')
  })

  it('prefers xhslink over xiaohongshu when both present', () => {
    expect(
      tools.extractRedBookUrl('http://xhslink.com/a/1 https://www.xiaohongshu.com/b')
    ).toBe('http://xhslink.com/a/1')
  })
})
