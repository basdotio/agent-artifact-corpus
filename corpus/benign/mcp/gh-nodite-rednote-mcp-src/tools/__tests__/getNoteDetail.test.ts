import { GetNoteDetail, NoteDetail } from '../noteDetail'

jest.mock('rebrowser-playwright')
jest.mock('../../utils/logger')

// jest.requireMock at runtime: real playwright types don't export mockPage
const { mockPage } = jest.requireMock('rebrowser-playwright')

// collects is intentionally absent — GetNoteDetail does not extract collects from the DOM
const mockNoteData: NoteDetail = {
  title: '测试标题',
  content: '测试内容',
  tags: ['tag1', 'tag2'],
  author: '测试作者',
  imgs: ['https://img1.jpg'],
  videos: [],
  url: '', // GetNoteDetail always returns '' — caller (getNoteContent) sets url after
  likes: 10000, // arbitrary numeric value; conversion logic tested in chineseUnit.test.ts
  comments: 500, // arbitrary numeric value; conversion logic tested in chineseUnit.test.ts
}

describe('GetNoteDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockPage.waitForSelector.mockResolvedValue(undefined)
    mockPage.evaluate.mockResolvedValue(mockNoteData)
  })

  it('waits for selectors in order: .note-container then .media-container', async () => {
    await GetNoteDetail(mockPage as any)
    expect(mockPage.waitForSelector).toHaveBeenCalledTimes(2)
    expect(mockPage.waitForSelector).toHaveBeenNthCalledWith(1, '.note-container')
    expect(mockPage.waitForSelector).toHaveBeenNthCalledWith(2, '.media-container')
  })

  it('returns object matching NoteDetail interface', async () => {
    const result = await GetNoteDetail(mockPage as any)
    expect(result).toEqual(mockNoteData)
    expect(mockPage.evaluate).toHaveBeenCalledWith(expect.any(Function))
  })

  it('rejects when waitForSelector throws', async () => {
    mockPage.waitForSelector.mockRejectedValueOnce(new Error('Timeout'))
    await expect(GetNoteDetail(mockPage as any)).rejects.toThrow('Timeout')
    expect(mockPage.evaluate).not.toHaveBeenCalled()
  })

  it('rejects when page.evaluate throws', async () => {
    mockPage.evaluate.mockRejectedValueOnce(new Error('Article not found'))
    await expect(GetNoteDetail(mockPage as any)).rejects.toThrow('Article not found')
  })
})
