import { chineseUnitStrToNumber } from '../noteDetail'

jest.mock('../../utils/logger')

describe('chineseUnitStrToNumber', () => {
  it('converts 万 integer', () => {
    expect(chineseUnitStrToNumber('1万')).toBe(10000)
  })

  it('converts 万 decimal', () => {
    expect(chineseUnitStrToNumber('1.2万')).toBe(12000)
  })

  it('converts 万 with space before unit', () => {
    expect(chineseUnitStrToNumber('1.5 万')).toBe(15000)
  })

  it('converts plain number string', () => {
    expect(chineseUnitStrToNumber('123')).toBe(123)
  })

  it('converts zero', () => {
    expect(chineseUnitStrToNumber('0')).toBe(0)
  })

  it('converts empty string to 0', () => {
    expect(chineseUnitStrToNumber('')).toBe(0)
  })

  it('converts large 万 number', () => {
    expect(chineseUnitStrToNumber('100万')).toBe(1000000)
  })
})
