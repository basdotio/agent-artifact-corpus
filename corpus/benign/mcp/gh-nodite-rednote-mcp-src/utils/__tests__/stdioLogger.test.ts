import { createStdioLogger } from '../stdioLogger'

jest.mock('../logger')

describe('createStdioLogger', () => {
  let cleanup: () => void
  let originalStdoutWrite: typeof process.stdout.write
  let originalStderrWrite: typeof process.stderr.write

  beforeAll(() => {
    originalStdoutWrite = process.stdout.write
    originalStderrWrite = process.stderr.write
  })

  afterEach(() => {
    // Always restore even if test throws
    if (cleanup) cleanup()
    // Reset to the true originals to prevent bind-accumulation across tests
    process.stdout.write = originalStdoutWrite
    process.stderr.write = originalStderrWrite
  })

  it('replaces process.stdout.write after calling createStdioLogger', () => {
    const writeBefore = process.stdout.write
    cleanup = createStdioLogger('/tmp/test.log')
    expect(process.stdout.write).not.toBe(writeBefore)
  })

  it('replaces process.stderr.write after calling createStdioLogger', () => {
    const writeBefore = process.stderr.write
    cleanup = createStdioLogger('/tmp/test.log')
    expect(process.stderr.write).not.toBe(writeBefore)
  })

  it('restores process.stdout.write when cleanup is called', () => {
    cleanup = createStdioLogger('/tmp/test.log')
    const patchedWrite = process.stdout.write
    cleanup()
    // After cleanup, the write function should no longer be the patched version
    expect(process.stdout.write).not.toBe(patchedWrite)
  })

  it('restores process.stderr.write when cleanup is called', () => {
    cleanup = createStdioLogger('/tmp/test.log')
    const patchedWrite = process.stderr.write
    cleanup()
    // After cleanup, the write function should no longer be the patched version
    expect(process.stderr.write).not.toBe(patchedWrite)
  })
})
