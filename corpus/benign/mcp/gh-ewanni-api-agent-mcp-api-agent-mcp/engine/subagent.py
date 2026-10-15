import asyncio

MAX_PARALLEL_SUBAGENTS = 3
subagent_semaphore = asyncio.Semaphore(MAX_PARALLEL_SUBAGENTS)
