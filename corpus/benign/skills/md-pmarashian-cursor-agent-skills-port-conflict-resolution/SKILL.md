---
name: port-conflict-resolution
description: Check port availability before starting server, provide patterns for killing processes on ports, document automatic port selection strategies, include fallback port ranges, and provide health check patterns. Use when dev server fails to start due to port conflicts.
---

# Port Conflict Resolution

## Overview

Patterns for resolving port conflicts when starting development servers. Check port availability, kill conflicting processes, and use fallback strategies.

## Check Port Availability Before Starting Server

### Pattern 1: Check Port Before Start

**Verify port is available** before starting server:

```bash
# Check if port is in use
lsof -i :3000

# If port is free, start server
if ! lsof -i :3000; then
  npm run dev
else
  echo "Port 3000 is in use"
fi
```

### Pattern 2: Check Multiple Ports

**Check common ports** for availability:

```bash
# Check common ports
for port in 3000 5173 8080; do
  if ! lsof -i :$port; then
    echo "Port $port is available"
    break
  fi
done
```

### Pattern 3: Port Detection Script

**Create reusable script**:

```bash
#!/bin/bash
# check-port.sh

PORT=${1:-3000}

if lsof -i :$PORT > /dev/null 2>&1; then
  echo "Port $PORT is in use"
  exit 1
else
  echo "Port $PORT is available"
  exit 0
fi
```

## Kill Processes on Ports

### Pattern 1: Kill Process by Port

**Kill process using specific port**:

```bash
# Find process using port
lsof -i :3000

# Kill process (replace PID with actual process ID)
kill -9 <PID>

# Or one-liner
lsof -ti :3000 | xargs kill -9
```

### Pattern 2: Kill Safely

**Check if it's a dev server** before killing:

```bash
# Check process name
lsof -i :3000 | grep -i "node\|vite\|dev"

# Kill only if it's a dev server
lsof -ti :3000 | xargs -I {} sh -c 'ps -p {} -o comm= | grep -i "node\|vite" && kill -9 {}'
```

### Pattern 3: Kill All Node Processes

**Kill all node processes** (use with caution):

```bash
# Kill all node processes
pkill -9 node

# Or more specific
pkill -9 -f "vite\|npm\|node.*dev"
```

## Automatic Port Selection Strategies

### Pattern 1: Try Ports Sequentially

**Try ports in order** until one is available:

```bash
# Try ports sequentially
for port in 3000 3001 3002 5173; do
  if ! lsof -i :$port; then
    PORT=$port npm run dev
    break
  fi
done
```

### Pattern 2: Use Vite's Auto Port

**Let Vite select available port**:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: 3000,
    strictPort: false, // Allow port selection
  },
});
```

**Note**: This makes port detection harder - check terminal output for actual port.

### Pattern 3: Port Range

**Try ports in range**:

```bash
# Try ports 3000-3010
for port in {3000..3010}; do
  if ! lsof -i :$port; then
    PORT=$port npm run dev
    break
  fi
done
```

## Fallback Port Ranges

### Common Fallback Ports

**Use these ports as fallbacks**:

- **3000**: Default for many projects
- **3001**: First fallback
- **5173**: Vite default
- **8080**: Common alternative
- **4000**: Another common choice

### Pattern: Fallback Port Selection

```bash
# Try common ports
PORTS=(3000 3001 5173 8080 4000)

for port in "${PORTS[@]}"; do
  if ! lsof -i :$port; then
    PORT=$port npm run dev
    echo "Server started on port $port"
    break
  fi
done
```

## Health Check Patterns

### Pattern 1: Poll Server Health

**Poll server until ready**:

```bash
# Poll server health
for i in {1..10}; do
  if curl -s http://localhost:3000 > /dev/null; then
    echo "Server is ready"
    break
  fi
  sleep 2
done
```

### Pattern 2: Check Health Endpoint

**Check health endpoint** (if available):

```bash
# Check health endpoint
curl -s http://localhost:3000/health

# Or check root
curl -s http://localhost:3000 | head -1
```

### Pattern 3: Wait for Server Message

**Wait for server ready message**:

```bash
# Start server and wait for "Local:" message
npm run dev | grep -m 1 "Local:"
```

## Complete Port Resolution Workflow

### Workflow 1: Check and Start

```bash
# 1. Check if port is available
if lsof -i :3000; then
  echo "Port 3000 is in use"
  
  # 2. Try to kill process
  lsof -ti :3000 | xargs kill -9
  
  # 3. Wait a moment
  sleep 1
  
  # 4. Check again
  if lsof -i :3000; then
    echo "Failed to free port, trying alternative"
    PORT=3001 npm run dev
  else
    npm run dev
  fi
else
  npm run dev
fi
```

### Workflow 2: Automatic Port Selection

```bash
# Try ports sequentially
PORTS=(3000 3001 5173 8080)

for port in "${PORTS[@]}"; do
  if ! lsof -i :$port; then
    PORT=$port npm run dev &
    SERVER_PID=$!
    
    # Wait for server to be ready
    for i in {1..10}; do
      if curl -s http://localhost:$port > /dev/null; then
        echo "Server started on port $port"
        break
      fi
      sleep 1
    done
    
    break
  fi
done
```

## Best Practices

1. **Check port before starting**: Avoid conflicts
2. **Kill old dev servers**: Free up ports
3. **Use fallback ports**: Have alternatives ready
4. **Poll for server health**: Verify server is ready
5. **Document port usage**: Note which port is used

## Resources

- `dev-server-port-detection` skill - Port discovery patterns
- `vite-agent` skill - Vite configuration
- `pre-flight-checklist` skill - Environment validation
