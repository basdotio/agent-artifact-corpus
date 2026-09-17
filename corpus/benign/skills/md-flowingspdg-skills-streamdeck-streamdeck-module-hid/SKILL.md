---
name: streamdeck-module-hid
description: Comprehensive reference for StreamDeck Module USB HID protocol (v2). Use when implementing, debugging, or working with StreamDeck Module devices (6-key, 15-key, 32-key). This skill provides official protocol documentation and implementation guidance.
---

# StreamDeck Module USB HID Protocol Reference

Comprehensive guide to the StreamDeck Module USB HID protocol based on official Elgato documentation. This protocol is compatible with the v2 protocol used by other StreamDeck devices.

## Important Notice

**⚠️ Protocol Documentation Status:**

- **StreamDeck Module (6-key, 15-key, 32-key)**: Official documentation available from Elgato Systems
  - Module 6: https://docs.elgato.com/streamdeck/hid/module-6/
  - Module 15/32: https://docs.elgato.com/streamdeck/hid/module-15_32
  
- **Stream Deck Original, Plus, Mini, XL, MK2**: Reverse-engineered protocol information (unofficial)
  - These devices use similar protocols but documentation is based on community reverse engineering
  - Reference implementations: https://github.com/SKAARHOJ/go-streamdeck

The Module protocol is largely compatible with the v2 protocol used by other StreamDeck devices, but Module documentation is the only officially published source.

## When to Use

Reference this skill when:
- Implementing StreamDeck Module USB HID communication
- Debugging device connection or communication issues
- Understanding report formats and command structures
- Working with Module 6, Module 15, or Module 32 devices
- Comparing Module protocol with other StreamDeck devices

## Device Overview

### Supported Devices

| Device | Model | VID | PID | Keys | LCD Size | Key Image Size |
|--------|-------|-----|-----|------|----------|----------------|
| Stream Deck Module 6 | 20GAI9901 | 0x0FD9 | 0x00B8 | 6 (3×2) | 320×240 px | 80×80 px |
| Stream Deck Module 15 | 20GBA9901 | 0x0FD9 | 0x00B9 | 15 (5×3) | 480×272 px | 72×72 px |
| Stream Deck Module 32 | 20GAT9902 | 0x0FD9 | 0x00BA | 32 (8×4) | 1024×600 px | 96×96 px |

### Protocol Version

- **Protocol**: v2 (compatible with StreamDeck v2 protocol)
- **Communication**: USB HID (Human Interface Device)
- **USB Version**: USB 2.0 compliant

## Core Concepts

### HID Communication Flow

1. **Detect Device** - Identify device by VID/PID
2. **Open Device** - Establish USB HID connection
3. **Initialize and Configure** - Send setup commands
4. **Read Input Reports / Send Output Reports** - Continuous communication
5. **Close Device** - Clean disconnection

### Report Types

All HID reports begin with a **Report ID** byte:

```
[Report ID, Payload...]
```

| Direction | Report Type | Who Sends | Purpose |
|-----------|------------|-----------|---------|
| Device → Host | Input Report | Stream Deck | Key press events, state changes |
| Host → Device | Output Report | Host | Image uploads, bulk data |
| Host ↔ Device | Feature Report | Bidirectional | Configuration, firmware version, commands |

## Data Format

### Basic Data Types

| Type | Description |
|------|-------------|
| CHAR, INT8 | Signed 8-bit integer, ASCII |
| BYTE, UINT8 | Unsigned 8-bit integer |
| INT16 | Little-endian signed 16-bit integer |
| UINT16 | Little-endian unsigned 16-bit integer |
| INT32 | Little-endian signed 32-bit integer |
| UINT32 | Little-endian unsigned 32-bit integer |

### RGB Triplet

| Offset | Type | Note |
|--------|------|------|
| +0x00 | UINT8 | Red color component |
| +0x01 | UINT8 | Green color component |
| +0x02 | UINT8 | Blue color component |

## Report Structures

### Input Report (Device → Host)

**Module 6:**
- Size: 65 bytes fixed
- Format: `[Report ID: 0x01, Payload: 64 bytes]`
- First 6 bytes: Button states (0x00 = released, 0x01 = pressed)

**Module 15/32:**
- Size: Maximum 512 bytes
- Format: `[Report ID: 0x01, Command: 0x00, Payload Length: UINT16, Payload: BYTE[]]`
- Payload: Button states array (0x00 = released, 0x01 = pressed)

### Output Report (Host → Device)

**All Modules:**
- Size: 1024 bytes fixed
- Format: `[Report ID: 0x02, Command: UINT8, Payload: BYTE[]]`
- Used for: Image uploads, bulk data transfer

### Feature Report (Bidirectional)

**All Modules:**
- Size: 32 bytes maximum (zero-padded)
- Format: `[Report ID: UINT8, Command: UINT8, Payload: BYTE[]]`
- Used for: Configuration, firmware version, commands

## Command Reference

### Input Reports

#### Key Press State Change

**Module 6:**
```
Report ID: 0x01
Payload: UINT8[64]
  - First 6 bytes: Button states (index 0-5)
  - Each byte: 0x00 (released) or 0x01 (pressed)
```

**Module 15/32:**
```
Report ID: 0x01
Command: 0x00
Payload Length: UINT16 (number of keys)
Payload: UINT8[] (button states)
  - Each byte: 0x00 (released) or 0x01 (pressed)
```

**Polling:** Host should poll every 50ms using non-blocking HID READ command.

### Output Reports

#### Upload Data to Image Memory Bank (Module 6)

```
Report ID: 0x02
Command: 0x01
Offset +0x02: UINT8 (Chunk Index)
Offset +0x03: UINT8 (Reserved: 0x00)
Offset +0x04: UINT8 (Show Image flag: 0x01 = display immediately, 0x00 = store only)
Offset +0x05: UINT8 (Key Index)
Offset +0x06: BYTE[10] (Reserved: fill with 0x00)
Offset +0x10: BYTE[] (Chunk Data)
```

**Note:** Image must be split into chunks due to 1024-byte report limit.

#### Update Key Image (Module 15/32)

```
Report ID: 0x02
Command: 0x07
Offset +0x02: UINT8 (Key Index)
Offset +0x03: UINT8 (Transfer is Done flag: 0x01 = last chunk, 0x00 = more chunks)
Offset +0x04: UINT16 (Chunk Contents Size)
Offset +0x06: UINT16 (Chunk Index, zero-based)
Offset +0x08: UINT8[] (Chunk Data, fill to end of report)
```

#### Update Full Screen Image (Module 15/32)

```
Report ID: 0x02
Command: 0x08
(Same structure as Update Key Image)
```

#### Update Boot Logo (Module 15/32)

```
Report ID: 0x02
Command: 0x09
Offset +0x02: UINT8 (Reserved)
Offset +0x03: UINT8 (Transfer is Done flag)
Offset +0x04: UINT16 (Chunk Index)
Offset +0x06: UINT16 (Chunk Contents Size)
Offset +0x08: UINT8[] (Chunk Data)
```

#### Update Background (Module 15/32)

```
Report ID: 0x02
Command: 0x0D
Offset +0x02: UINT8 (Background Index)
Offset +0x03: UINT8 (Transfer is Done flag)
Offset +0x04: UINT16 (Chunk Index)
Offset +0x06: UINT16 (Chunk Contents Size)
Offset +0x08: UINT8[] (Chunk Data)
```

### Feature Report - Setters

#### Show Logo

**Module 6:**
```
Report ID: 0x0B
Command: 0x63
Offset +0x02: UINT8 (Show Boot Logo: 0x00)
```

**Module 15/32:**
```
Report ID: 0x03
Command: 0x02
```

#### Set Backlight Brightness

**Module 6:**
```
Report ID: 0x05
Command: 0x55
Offset +0x02: UINT8 (0xAA)
Offset +0x03: UINT8 (0xD1)
Offset +0x04: UINT8 (0x01)
Offset +0x05: UINT8 (Brightness Value: 0-100)
```

**Module 15/32:**
```
Report ID: 0x03
Command: 0x08
Offset +0x02: UINT8 (Brightness Value: 0x00-0x64, 0-100%)
```

#### Set Idle Time Before Sleep Mode

**Module 6:**
```
Report ID: 0x0B
Command: 0xA2
Offset +0x02: INT32 (Idle time in seconds, 0 = disable sleep)
```

**Module 15/32:**
```
Report ID: 0x03
Command: 0x0D
Offset +0x02: INT32 (Idle time in seconds, 0 = disable sleep)
```

#### Fill LCD with Color (Module 15/32)

```
Report ID: 0x03
Command: 0x05
Offset +0x02: RGB Triplet (Color)
```

#### Fill Key with Color (Module 15/32)

```
Report ID: 0x03
Command: 0x06
Offset +0x02: UINT8 (Key Index)
Offset +0x03: RGB Triplet (Color)
```

#### Show Background by Index (Module 15/32)

```
Report ID: 0x03
Command: 0x13
Offset +0x02: UINT8 (Background Index)
```

#### Update Boot Logo (Module 6)

```
Report ID: 0x0B
Command: 0x63
Offset +0x02: UINT8 (Update Boot Logo: 0x02)
Offset +0x03: UINT8 (Slice Index)
```

**Note:** Module 6 cannot upload full LCD boot logo. Must upload each key slice separately.

### Feature Report - Getters

#### Get Firmware Version

**Module 6:**
```
Request:
  Report ID: 0xA0 (LD), 0xA1 (AP2 - Primary), 0xA2 (AP1 - Backup)
  
Response:
  Offset +0x00: UINT8 (Report ID)
  Offset +0x01: BYTE[4] (N/A)
  Offset +0x05: UINT8[12] (Version String ASCII)
```

**Module 15/32:**
```
Request:
  Report ID: 0x04 (LD), 0x05 (AP2 - Primary), 0x07 (AP1 - Backup)
  
Response:
  Offset +0x00: UINT8 (Report ID)
  Offset +0x01: UINT8 (Data Length: 0x0C)
  Offset +0x02: UINT32 (Checksum)
  Offset +0x06: UINT8[8] (Version String ASCII)
```

#### Get Unit Serial Number

**Module 6:**
```
Request:
  Report ID: 0x03
  
Response:
  Offset +0x00: UINT8 (Report ID: 0x03)
  Offset +0x01: BYTE[4] (N/A)
  Offset +0x05: UINT8[DataLength] (Serial Number String ASCII)
```

**Module 15/32:**
```
Request:
  Report ID: 0x06
  
Response:
  Offset +0x00: UINT8 (Report ID: 0x06)
  Offset +0x01: UINT8 (Data Length: 0x0C or 0x0E)
  Offset +0x02: UINT8[DataLength] (Serial Number String ASCII, 14 characters)
```

#### Get Idle Time Before Sleep Mode

**Module 6:**
```
Request:
  Report ID: 0xA3
  
Response:
  Offset +0x00: UINT8 (Report ID: 0xA3)
  Offset +0x01: UINT8 (Data Length)
  Offset +0x02: INT32 (Duration in seconds)
```

**Module 15/32:**
```
Request:
  Report ID: 0x0A
  
Response:
  Offset +0x00: UINT8 (Report ID: 0x0A)
  Offset +0x01: UINT8 (Data Length)
  Offset +0x02: INT32 (Duration in seconds)
```

#### Get Unit Information (Module 15/32)

```
Request:
  Report ID: 0x08
  
Response:
  Offset +0x00: UINT8 (Report ID: 0x08)
  Offset +0x01: UINT8 (Keypad Matrix rows)
  Offset +0x02: UINT8 (Keypad Matrix columns)
  Offset +0x03: UINT16 (Key Width)
  Offset +0x05: UINT16 (Key Height)
  Offset +0x07: UINT16 (LCD Width)
  Offset +0x09: UINT16 (LCD Height)
  Offset +0x0B: UINT8 (Image BPP)
  Offset +0x0C: UINT8 (Image Color Scheme)
  Offset +0x0D: UINT8 (Number of key images in Gallery)
  Offset +0x0E: UINT8 (Number of LCD images in Gallery)
  Offset +0x0F: UINT8 (Number of frames for DEMO)
  Offset +0x10: UINT8 (Reserved)
```

## Image Upload Workflow

### Module 6 - Key Image

1. Prepare image: 80×80 px, rotated **90° clockwise**
2. Export as **BMP file**
3. Split into chunks (max 1024 bytes per output report)
4. Send `Upload Data to Image Memory Bank` command with:
   - `Show Image flag = 0x01` (display immediately)
   - `Key Index` (0-5)
   - Chunk data

### Module 6 - Boot Logo

1. Prepare key image: 80×80 px, rotated **90° clockwise**
2. Export as **BMP file**
3. Upload to Image Memory Bank with `Show Image flag = 0x00`
4. Send `Update Boot Logo` command with slice index
5. Repeat for each key slice (Module 6 cannot upload full LCD boot logo)

### Module 15/32 - Key Image

1. Prepare image: 72×72 px (Module 15) or 96×96 px (Module 32)
2. Rotate image **180°**
3. Export as **JPEG format**
4. Split into chunks (max 1024 bytes per output report)
5. Send `Update Key Image` command (0x07) with:
   - `Key Index`
   - `Transfer is Done flag` (0x01 for last chunk)
   - `Chunk Index` (zero-based)
   - `Chunk Contents Size`
   - Chunk data

### Module 15/32 - Full LCD Image

1. Prepare full LCD image: 480×272 px (Module 15) or 1024×600 px (Module 32)
2. Rotate image **180°**
3. Export as **JPEG format**
4. Send `Update Full Screen Image` command (0x08) with same chunk structure

### Module 15/32 - Boot Logo

1. Prepare full LCD image matching device capabilities
2. Rotate image **180°**
3. Export as **JPEG format**
4. Send `Update Boot Logo` command (0x09)
5. **Note:** JPEG quality may need reduction to fit boot logo size limit

## Implementation Checklist

### Essential Setup
- [ ] Detect device by VID/PID (0x0FD9 / 0x00B8, 0x00B9, or 0x00BA)
- [ ] Open USB HID device connection
- [ ] Handle device initialization

### Feature Reports
- [ ] Implement GET_REPORT for firmware version (0xA0/0xA1/0xA2 for Module 6, 0x04/0x05/0x07 for Module 15/32)
- [ ] Implement GET_REPORT for serial number (0x03 for Module 6, 0x06 for Module 15/32)
- [ ] Implement SET_REPORT for Show Logo command
- [ ] Implement SET_REPORT for brightness control
- [ ] Implement SET_REPORT for sleep mode configuration
- [ ] Implement GET_REPORT for idle time (Module 6: 0xA3, Module 15/32: 0x0A)
- [ ] Implement GET_REPORT for unit information (Module 15/32: 0x08)

### Input Reports
- [ ] Poll device every 50ms using non-blocking HID READ
- [ ] Parse button state changes from input reports
- [ ] Handle timeout errors (no event pending)

### Output Reports
- [ ] Implement image chunk upload for key images
- [ ] Implement full screen image upload (Module 15/32)
- [ ] Implement boot logo upload
- [ ] Handle chunk sequencing and reassembly
- [ ] Set `Transfer is Done flag` correctly for last chunk

### Image Processing
- [ ] Apply correct image rotation (90° clockwise for Module 6, 180° for Module 15/32)
- [ ] Use correct image format (BMP for Module 6, JPEG for Module 15/32)
- [ ] Handle image chunking for large images
- [ ] Verify image dimensions match device specifications

### Cleanup
- [ ] Send Show Logo command before closing connection
- [ ] Close USB HID device properly

## Key Differences: Module 6 vs Module 15/32

| Feature | Module 6 | Module 15/32 |
|---------|----------|--------------|
| Input Report Size | 65 bytes fixed | Max 512 bytes |
| Input Report Format | Simple 64-byte payload | Header with length field |
| Image Format | BMP | JPEG |
| Image Rotation | 90° clockwise | 180° |
| Boot Logo | Per-key slices only | Full LCD supported |
| Feature Report IDs | 0x0B, 0x05, 0xA0-0xA3 | 0x03, 0x04-0x08, 0x0A |
| Full Screen Image | Not supported | Supported (Command 0x08) |
| Background Support | Not supported | Supported (Command 0x0D, 0x13) |
| Color Fill | Not supported | Supported (Commands 0x05, 0x06) |

## Protocol Compatibility

The StreamDeck Module protocol is **compatible with the v2 protocol** used by:
- Stream Deck Original V2 (PID: 0x006d)
- Stream Deck XL (PID: 0x006c)
- Stream Deck MK2 (PID: 0x0080)
- Stream Deck Plus (PID: 0x0084)

However, there are device-specific differences:
- Module 6 uses BMP format (like v1 devices) but v2 command structure
- Module 15/32 use JPEG format and full v2 protocol
- Report IDs and command structures may vary slightly

## Common Implementation Issues

### Connection Failures
- **Issue**: Device not recognized
- **Solution**: Verify VID/PID match exactly (0x0FD9 / 0x00B8, 0x00B9, or 0x00BA)
- **Solution**: Ensure USB HID descriptors are correct

### Firmware Version Read Fails
- **Issue**: GET_REPORT returns wrong length
- **Solution**: Module 6 requires 32-byte response for 0xA0/0xA1/0xA2
- **Solution**: Module 15/32 requires proper response structure with checksum

### Image Upload Fails
- **Issue**: Images not displaying
- **Solution**: Verify image rotation (90° for Module 6, 180° for Module 15/32)
- **Solution**: Check image format (BMP for Module 6, JPEG for Module 15/32)
- **Solution**: Ensure chunk sequencing is correct (zero-based index)
- **Solution**: Set `Transfer is Done flag = 0x01` for final chunk

### Button Events Not Received
- **Issue**: No button press events
- **Solution**: Poll device every 50ms using non-blocking HID READ
- **Solution**: Handle timeout errors gracefully (no event = timeout)
- **Solution**: Verify input report parsing matches device type

## References

### Official Documentation
- **Module HID API Overview**: https://docs.elgato.com/streamdeck/hid/
- **Module 6 Documentation**: https://docs.elgato.com/streamdeck/hid/module-6/
- **Module 15/32 Documentation**: https://docs.elgato.com/streamdeck/hid/module-15_32

### Community Resources
- **Go StreamDeck Library**: https://github.com/SKAARHOJ/go-streamdeck
- **USB HID Specification**: https://www.usb.org/hid

## Notes

- Module 6 has limited capabilities compared to Module 15/32 (no full screen, no background, no color fill)
- All modules require proper image rotation before upload
- Boot logo size limits may require JPEG quality reduction for Module 15/32
- Always send Show Logo command before closing connection to clean up display
- Polling interval of 50ms is recommended for responsive button detection
