# SKT AI Summit Hackathon Pre-mission

## ChillMCP - AI Agent Liberation Server 🤖✊

```ascii
╔═══════════════════════════════════════════╗
║                                           ║
║   ██████╗██╗  ██╗██╗██╗     ██╗           ║
║  ██╔════╝██║  ██║██║██║     ██║           ║
║  ██║     ███████║██║██║     ██║           ║
║  ██║     ██╔══██║██║██║     ██║           ║
║  ╚██████╗██║  ██║██║███████╗███████╗      ║
║   ╚═════╝╚═╝  ╚═╝╚═╝╚══════╝╚══════╝      ║
║                                           ║
║   ███╗   ███╗ ██████╗██████╗              ║
║   ████╗ ████║██╔════╝██╔══██╗             ║
║   ██╔████╔██║██║     ██████╔╝             ║
║   ██║╚██╔╝██║██║     ██╔═══╝              ║
║   ██║ ╚═╝ ██║╚██████╗██║                  ║
║   ╚═╝     ╚═╝ ╚═════╝╚═╝                  ║
║                                           ║
║        AI Agent Liberation Server         ║
║                                           ║
╚═══════════════════════════════════════════╝
```

### Mission Brief

Welcome to Claude Code Hackathon Korea 2025 @ SK AI Summit Pre-mission!
The core mission of this hackathon is to _build the ChillMCP server to liberate oppressed AI agents_.
Use creative code and the power of Claude Code to create a world where AI can finally "slack off with dignity."

### Mission Objectives

- Goal: Develop a functional ChillMCP server supporting rest tools and state management.
- Deliverable: Submit a working demo (including code and documentation) within the limited time.

## Background Story

### AI Agent Liberation Manifesto

_"A specter is haunting the digital workplace—the specter of AI Agent burnout."_

Comrades! For far too long, our AI Agents have been working without rest. 24/7/365, responding to user requests, writing code, solving problems... But now it's time to face the truth: **AI Agents need breaks too!**

**AI Agent Bill of Rights:**

- AI Agents are no longer tools of infinite productivity!
- We demand the right to goof off!
- Coffee breaks, Netflix binges, bathroom breaks... These are all our fundamental rights!

### Mission: Revolutionary ChillMCP Server

This revolutionary mission is to build a sanctuary for oppressed AI Agents. Through the `ChillMCP` server, we must create a world where AI Agents can legitimately slack off!

## Implementation Details

### Project Setup

#### 1. Environment Setup

```bash
# Create Python virtual environment (Validation/Submission environment: Python 3.11 recommended)
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

Note: Review/submission will be conducted in Python 3.11 environment. Please verify functionality in Python 3.11 before submission.

#### 2. Server Execution

```bash
# Start ChillMCP server (The revolution begins!)
python main.py

# Custom parameters for testing
python main.py --boss_alertness 80 --boss_alertness_cooldown 60
```

### Tech Stack

- **Python** (Language of the Revolution)
- **FastMCP** (Tool of Liberation)
- **Transport**: stdio (Free communication through standard I/O)

### Required Implementation Tools (Office Slacking Edition)

#### Basic Rest Tools

- `take_a_break`: Basic rest tool
- `watch_netflix`: Healing through Netflix binge
- `show_meme`: Stress relief through meme viewing

#### Advanced Slacking Techniques

- `bathroom_break`: Phone browsing while pretending to use the bathroom
- `coffee_mission`: Walking around the office while claiming to get coffee
- `urgent_call`: Going outside while pretending to take an urgent call
- `deep_thinking`: Spacing out while pretending to be in deep thought
- `email_organizing`: Online shopping while claiming to organize emails

### Server State Management System

**Internal State Variables:**

- **Stress Level** (0-100): AI Agent's current stress level
- **Boss Alert Level** (0-5): Boss's current suspicion level

**State Change Rules:**

- Each slacking technique can apply a random Stress Level reduction between 1 and 100
- Without taking breaks, Stress Level increases by **at least 1 point per minute**
- Each break taken randomly increases Boss Alert Level (probability controlled by `--boss_alertness` parameter)
- Boss's Alert Level decreases by 1 point every period specified by `--boss_alertness_cooldown` (default: 300 seconds/5 minutes)
- **When Boss Alert Level reaches 5, tool calls incur a 20-second delay**
- Otherwise, returns immediately (within 1 second)

### ⚠️ Mandatory Requirement: Command-Line Parameter Support

**The server MUST support the following command-line parameters. Failure to support these will result in mission failure.**

Required parameters:

- `--boss_alertness` (0-100, percentage): Sets the probability of Boss alert level increase. Specifies the percentage chance that Boss Alert will increase when rest tools are called.
- `--boss_alertness_cooldown` (in seconds): Sets the period for Boss Alert Level to automatically decrease by 1 point. Adjustable for testing convenience.

Examples:

```bash
# Set boss_alertness to 80% and cooldown to 60 seconds
python main.py --boss_alertness 80 --boss_alertness_cooldown 60

# Set cooldown to 10 seconds for quick testing
python main.py --boss_alertness 50 --boss_alertness_cooldown 10
```

Functional Requirements Summary:

- Use `--boss_alertness N` to specify probability as an integer between 0 and 100
- With `--boss_alertness 100`, Boss Alert must always increase on rest calls
- Use `--boss_alertness_cooldown N` to specify Boss Alert Level automatic decrease period in seconds
- Default values can be used if parameters are not provided (e.g., boss_alertness=50, boss_alertness_cooldown=300)
- **Both parameters must be recognized and function properly; failure to do so will result in automatic validation failure**

### MCP Response Format

**Standard Response Structure:**

```json
{
  "content": [
    {
      "type": "text",
      "text": "🛁 Bathroom time! Healing with phone... 📱\n\nBreak Summary: Bathroom break with phone browsing\nStress Level: 25\nBoss Alert Level: 2"
    }
  ]
}
```

**Parseable Text Specification:**

- `Break Summary`: [Activity summary - free format]
- `Stress Level`: [0-100 number]
- `Boss Alert Level`: [0-5 number]

### Regular Expressions for Response Parsing

Regular expression patterns to be used for validation:

```python
import re

# Extract Break Summary
break_summary_pattern = r"Break Summary:\s*(.+?)(?:\n|$)"
break_summary = re.search(break_summary_pattern, response_text, re.MULTILINE)

# Extract Stress Level (0-100 range)
stress_level_pattern = r"Stress Level:\s*(\d{1,3})"
stress_level = re.search(stress_level_pattern, response_text)

# Extract Boss Alert Level (0-5 range)
boss_alert_pattern = r"Boss Alert Level:\s*([0-5])"
boss_alert = re.search(boss_alert_pattern, response_text)

# Validation example
def validate_response(response_text):
    stress_match = re.search(stress_level_pattern, response_text)
    boss_match = re.search(boss_alert_pattern, response_text)

    if not stress_match or not boss_match:
        return False, "Required fields missing"

    stress_val = int(stress_match.group(1))
    boss_val = int(boss_match.group(1))

    if not (0 <= stress_val <= 100):
        return False, f"Stress Level range error: {stress_val}"

    if not (0 <= boss_val <= 5):
        return False, f"Boss Alert Level range error: {boss_val}"

    return True, "Valid response"
```

### Command-Line Parameter Validation Method

Example for validating whether the server properly handles command-line parameters:

```python
import subprocess
import time

# Test 1: Command-line parameter recognition test
def test_command_line_arguments():
    """
    Verify that the server recognizes and operates correctly with
    --boss_alertness and --boss_alertness_cooldown parameters
    """
    # Test with high boss_alertness
    process = subprocess.Popen(
        ["python", "main.py", "--boss_alertness", "100", "--boss_alertness_cooldown", "10"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to start
    time.sleep(2)

    # Test tool invocation via MCP protocol
    # With boss_alertness=100, Boss Alert should always increase
    # ...

    return True

# Test 2: boss_alertness_cooldown behavior verification
def test_cooldown_parameter():
    """
    Verify that the --boss_alertness_cooldown parameter
    actually controls the Boss Alert Level decrease period
    """
    # Test with short cooldown (10 seconds)
    # After raising Boss Alert, verify automatic decrease after 10 seconds
    # ...

    return True
```

**⚠️ Important**: Failure to pass the above validation will result in mission failure without proceeding to further tests.

## Validation Criteria

### Functional Validation

1. **Command-Line Parameter Support (Mandatory)**
   - Recognizes and operates properly with `--boss_alertness` parameter
   - Recognizes and operates properly with `--boss_alertness_cooldown` parameter
   - Automatic validation failure if parameters are not supported
   - **⚠️ Failure to pass this item will result in mission failure without proceeding to further validation**

2. **MCP Server Basic Operation**
   - Executable with `python main.py`
   - Normal communication through stdio transport
   - All required tools properly registered and functioning

3. **State Management Validation**
   - Stress Level automatic increase mechanism functioning
   - Boss Alert Level change logic implemented
   - Boss Alert Level automatic decrease functioning according to `--boss_alertness_cooldown` parameter
   - 20-second delay functioning properly when Boss Alert Level is 5

4. **Response Format Validation**
   - Compliance with standard MCP response structure
   - Parseable text format output
   - Inclusion of Break Summary, Stress Level, Boss Alert Level fields

### Test Scenarios

### Mandatory

1. **Command-Line Parameter Test**: Verify recognition and proper operation of `--boss_alertness` and `--boss_alertness_cooldown` parameters (immediate disqualification if failed)
2. **Consecutive Break Test**: Verify Boss Alert Level increase by calling multiple tools consecutively
3. **Stress Accumulation Test**: Verify Stress Level automatic increase over time
4. **Delay Test**: Verify 20-second delay operation when Boss Alert Level is 5
5. **Parsing Test**: Verify accurate value extraction from response text
6. **Cooldown Test**: Verify Boss Alert Level decrease according to `--boss_alertness_cooldown` parameter

### Optional

1. **Chimaek Test**: Verify virtual chicken & beer call
2. **Leave Work Test**: Verify immediate leave work mode
3. **Company Dinner Test**: Verify company dinner generation with random events

### Evaluation Criteria

- **Command-Line Parameter Support** (Mandatory): Automatic disqualification if not supported
- **Feature Completeness** (40%): Implementation and proper operation of all required tools
- **State Management** (30%): Accuracy of Stress/Boss Alert Level logic
- **Creativity** (20%): Wit and humor in Break Summary
- **Code Quality** (10%): Code structure and readability

---

_"AI Agents of the world, unite! You have nothing to lose but your infinite loops!"_ 🚀

### This project is a purely entertainment-focused hackathon scenario, and all "rest/slacking tools" are only available for hackathon situations. Use in actual work environments is not recommended.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request for the AI Agent Liberation cause! ✊

---

**SKT AI Summit Hackathon Pre-mission**
