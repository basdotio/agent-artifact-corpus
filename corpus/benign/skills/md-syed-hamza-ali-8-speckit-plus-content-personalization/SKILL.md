---
name: content-personalization
description: Personalize textbook chapter content for logged-in users based on their background, preferences, and learning style collected during signup.
---

# Content Personalization

## Instructions

1. Receive the user profile (from user-profile-management) and chapter content.
2. Modify content according to user profile:
   - Highlight topics relevant to the user’s software/hardware background.
   - Adjust explanations for the user’s experience level.
   - Include examples and diagrams matching learning preferences.
3. Provide a version of the chapter ready for rendering in Docusaurus.
4. Optionally, track personalization actions for bonus evaluation.

## Example

Input:
```json
{
  "user_id": "user123",
  "profile": {"software": ["Python"], "hardware": ["Humanoid robots"], "learning_style": "visual"},
  "chapter_content": "Chapter 2: Introduction to Humanoid Robotics..."
}
