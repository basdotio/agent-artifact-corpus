# Copilot Optimization Summary

This document details the newly created tools and optimizations applied to the system to reduce token exhaustion, enhance spatial understanding, and improve autonomous planning.

## 1. Token Exhaustion Avoidance
**Goal**: Prevent the `WorkerClient` from returning massive geometric or structural data payloads that crash the LLM context window.
- **Implementation**: 
  - A strict 800,000 character limit was placed on the `HandleMessage` tool execution response.
  - If a payload exceeds this, the payload is intercepted and replaced with a prompt: `ERROR: Payload too large... Please use 'get_lightweight_summary' or filter 'isolate_ids'.`
  - **Tool Updated**: Core WebSocket response loop in C#.

## 2. Geometry Understanding Optimization (Tier 1 Abstraction)
**Goal**: Allow the LLM to understand what an element is (Beam, Column, Slab, Wall) and its orientation without feeding it heavy raw vertices.
- **Implementation**:
  - **New Tool Created**: `get_lightweight_summary`
  - **C# Logic**: Uses `Plane.FitPlaneToPoints` on object vertices to create a perfectly oriented bounding box, avoiding the pitfalls of world-axis bounding boxes for rotated objects.
  - **Classification**: Analyzes the proportions of the bounding box (Length vs Width vs Height) and its verticality (`Z-axis` alignment) to classify elements.
  - **Result**: Returns a JSON object with `Element_Type`, `Dimensions`, `Location`, and `Orientation` using less than 1% of the tokens of raw geometry.

## 3. 4-Way Isolate Screenshot Strategy
**Goal**: Get multi-angle visual understanding of isolated geometry without overflowing the image token limit.
- **Implementation**:
  - **Tool Updated**: `take_screenshot` (or `take_rhino_screenshot`)
  - **Isolate Logic**: It saves the visibility state (`IsHidden`) of every object in the document, hides everything not in `isolate_ids`, takes the screenshot, and seamlessly restores the visibility state.
  - **4-Way Mode**: If requested, it cycles through `Top`, `Front`, `Right`, and `Perspective` views, forcing a `ZoomExtents` on the isolated objects, and returns 4 low-resolution (256x256) Base64 images simultaneously.

## 4. Smart Conversation History (Token Saving)
**Goal**: Prevent long, drawn-out conversations from exceeding the Google Gemini context limit over time.
- **Implementation**:
  - **Backend Logic (`agent.py`)**: Before every LLM request, the system counts characters in the conversation history.
  - **Background Summarization**: If the history exceeds 150,000 characters, it slices out the oldest messages, runs a rapid background LLM generation to summarize them into a `[System Context Summary]`, and injects that summary back into the history while retaining recent messages intact.

## 5. Planner Mode & Isolated Scratch Space
**Goal**: Force the LLM to plan complex tasks step-by-step and allow user approval before making massive code changes.
- **Implementation**:
  - **New Tools Created**: `write_plan` and `write_task_list`
  - **Backend Intercept (`agent.py`)**: These tools are intercepted before hitting the local C# worker.
  - **Session Isolation**: Plans are saved in `nextra.rhino.v01/scratch/<session_id>/plan.md` to completely prevent cross-talk between different users.
  - **Read/Update Capabilities**: The `read_file` tool was intercepted to automatically map to the user's isolated scratch folder. The LLM can overwrite its task list to track progress.
  - **Approval Gate**: When a plan is created, the system halts generation and prompts the UI: *"Do you approve me to execute this step-by-step?"*
