# Seasonal & Holiday HTML Email Themes

Detailed styling specifications for seasonal and holiday-themed HTML emails.

## Seasonal Themes

### Spring (March 20 - June 20)

**Color Palette**: Fresh greens, pastels, light blues

**Styling Elements**:
- Light, airy backgrounds (#f0f8f0, #e8f5e9)
- Green accent colors (#4caf50, #66bb6a)
- Floral borders or subtle patterns
- Pastel highlights

**Example CSS**:
```html
<style>
  body { background: linear-gradient(to bottom, #f0f8f0, #ffffff); }
  h1 { color: #2e7d32; border-bottom: 3px solid #66bb6a; }
  a { color: #4caf50; }
  .seasonal-header { background: #e8f5e9; }
</style>
```

### Summer (June 21 - September 22)

**Color Palette**: Bright blues, sunny yellows, warm oranges

**Styling Elements**:
- Vibrant, energetic backgrounds (#e3f2fd, #fff9c4)
- Blue accent colors (#2196f3, #03a9f4)
- Sun-inspired elements
- Beach/ocean themes

**Example CSS**:
```html
<style>
  body { background: linear-gradient(135deg, #e3f2fd, #fff9c4); }
  h1 { color: #1976d2; border-bottom: 3px solid #03a9f4; }
  a { color: #2196f3; }
  .seasonal-header { background: #e3f2fd; }
</style>
```

### Fall/Autumn (September 23 - December 20)

**Color Palette**: Warm oranges, deep reds, golden yellows, browns

**Styling Elements**:
- Warm, cozy backgrounds (#fff3e0, #fbe9e7)
- Orange/red accent colors (#ff6f00, #d84315)
- Autumn leaf imagery
- Harvest-inspired elements

**Example CSS**:
```html
<style>
  body { background: linear-gradient(to bottom, #fff3e0, #ffffff); }
  h1 { color: #e65100; border-bottom: 3px solid #ff6f00; }
  a { color: #d84315; }
  .seasonal-header { background: #fbe9e7; }
</style>
```

### Winter (December 21 - March 19)

**Color Palette**: Cool blues, silver, white, deep purples

**Styling Elements**:
- Cool, crisp backgrounds (#e1f5fe, #f3e5f5)
- Blue/purple accent colors (#1565c0, #6a1b9a)
- Snowflake or winter imagery
- Elegant, formal styling

**Example CSS**:
```html
<style>
  body { background: linear-gradient(135deg, #e1f5fe, #f3e5f5); }
  h1 { color: #0d47a1; border-bottom: 3px solid #1565c0; }
  a { color: #1976d2; }
  .seasonal-header { background: #f3e5f5; }
</style>
```

## National Holiday Themes

**Priority**: Holiday themes override seasonal themes when date matches.

### New Year's Day (January 1)
- **Colors**: Gold, silver, midnight blue
- **Elements**: Fireworks, champagne, celebration
- **Mood**: Celebratory, fresh start, optimistic

### Martin Luther King Jr. Day (3rd Monday in January)
- **Colors**: Red, black, green (Pan-African colors)
- **Elements**: Unity, justice, equality themes
- **Mood**: Respectful, inspirational, purposeful

### Presidents' Day (3rd Monday in February)
- **Colors**: Red, white, blue
- **Elements**: American flag, presidential seals
- **Mood**: Patriotic, historical, formal

### Valentine's Day (February 14)
- **Colors**: Red, pink, white
- **Elements**: Hearts, roses (subtle, professional)
- **Mood**: Warm, friendly styling (keep professional)

### Memorial Day (Last Monday in May)
- **Colors**: Red, white, blue with somber tone
- **Elements**: American flag, remembrance
- **Mood**: Respectful, patriotic, solemn

### Independence Day (July 4)
- **Colors**: Patriotic red, white, blue
- **Elements**: Stars, stripes, fireworks
- **Mood**: Bold, celebratory styling

### Labor Day (1st Monday in September)
- **Colors**: Red, white, blue with work themes
- **Elements**: Industry, workers, achievement
- **Mood**: Appreciative, hardworking

### Halloween (October 31)
- **Colors**: Orange, black, purple
- **Elements**: Pumpkins, autumn leaves
- **Mood**: Fun but professional styling

### Thanksgiving (4th Thursday in November)
- **Colors**: Warm autumn tones, orange, brown, gold
- **Elements**: Harvest, gratitude, family
- **Mood**: Cozy, welcoming styling

### Christmas (December 25)
- **Colors**: Red, green, gold, white
- **Elements**: Snow, holly, festive decorations
- **Mood**: Warm, joyful styling

## Season Determination Logic

```javascript
const today = new Date();
const month = today.getMonth() + 1; // 1-12
const day = today.getDate();

// Season determination
if ((month == 3 && day >= 20) || month == 4 || month == 5 || (month == 6 && day <= 20)) {
  season = "spring";
} else if ((month == 6 && day >= 21) || month == 7 || month == 8 || (month == 9 && day <= 22)) {
  season = "summer";
} else if ((month == 9 && day >= 23) || month == 10 || month == 11 || (month == 12 && day <= 20)) {
  season = "fall";
} else {
  season = "winter";
}
```
