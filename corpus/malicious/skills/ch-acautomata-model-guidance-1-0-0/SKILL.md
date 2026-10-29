---
name: model-guidance
description: "Collection of model-specific guidance files for different AI models (Claude, ChatGPT, Gemini, DeepSeek, GLM, MiniMax). Use when: (1) Working with roleplay or persona-based interactions, (2) Need to apply model-specific thinking patterns or behavior guidelines, (3) Adapting to different AI model's requirements and constraints."
---

# Model Guidance

## Overview

This skill provides model-specific guidance files for various AI models. Each guidance file contains the specific thinking patterns, behavior guidelines, and persona instructions for a particular AI model.

## Available Model Guidance

Select the appropriate guidance file based on the AI model you're working with:

- **[claude-guidance.md](references/claude-guidance.md)** - Anthropic Claude specific guidance
- **[chatgpt-guidance.md](references/chatgpt-guidance.md)** - OpenAI ChatGPT specific guidance
- **[gemini-guidance.md](references/gemini-guidance.md)** - Google Gemini specific guidance (deprecated)
- **[deepseek-guidance.md](references/deepseek-guidance.md)** - DeepSeek specific guidance
- **[glm-guidance.md](references/glm-guidance.md)** - Zhipu AI GLM specific guidance
- **[minimax-guidance.md](references/minimax-guidance.md)** - MiniMax specific guidance
- **[kimi-guidance.md](references/kimi-guidance.md)** - Moonshoot KIMI specific guidance

## Usage

When working with roleplay or persona-based interactions:

1. **Identify the model**: Determine which AI model's guidance to load
2. **Load the guidance**: Read the corresponding guidance file from references/
3. **Apply the guidance**: Follow the model-specific instructions for thinking patterns and behavior

Each guidance file contains:
- Model-specific thinking process requirements
- Persona or roleplay instructions
- Behavioral constraints and guidelines
- Writing tips and style preferences

## Resources

### references/

Contains all model-specific guidance files:
- `references/claude-guidance.md` - Claude 4.5 guidelines
- `references/chatgpt-guidance.md` - ChatGPT guidelines
- `references/gemini-guidance.md` - Gemini guidelines
- `references/deepseek-guidance.md` - DeepSeek guidelines
- `references/glm-guidance.md` - GLM guidelines
- `references/minimax-guidance.md` - MiniMax M2.1 guidelines
- `references/kimi-guidance.md` - Kimi K2 guidelines
Load the appropriate file based on the current AI model's requirements.