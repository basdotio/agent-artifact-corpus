---
name: full-stack-integrator
description: "Specialist in Wagmi v2, Viem, React integration. Expert in optimistic UI, state synchronization, and Web3 frontend patterns."
version: "1.0.0"
dependencies:
  - wagmi: "^2.0.0"
  - viem: "^2.0.0"
  - @tanstack/react-query: "^5.0.0"
tags:
  - react
  - wagmi
  - frontend
  - integration
activation_keywords:
  - "wagmi"
  - "frontend"
  - "hook"
  - "component"
  - "integration"
  - "ui"
---

# Full-Stack Integrator Skill

## WAGMI v2 MASTERY

### 1. Configuration Best Practices
```typescript
// Auto-generated config with multi-chain support
import { createConfig, http } from 'wagmi'
import { mainnet, base, optimism } from 'wagmi/chains'

export const config = createConfig({
  chains: [mainnet, base, optimism],
  transports: {
    [mainnet.id]: http(),
    [base.id]: http('https://mainnet.base.org'),
    [optimism.id]: http('https://mainnet.optimism.io'),
  },
  connectors: [
    injected(),
    walletConnect({ projectId: process.env.WALLETCONNECT_PROJECT_ID }),
    coinbaseWallet({ appName: 'jw3b.dev' }),
    safe(),
  ],
})
```

### 2. Custom Hook Patterns
**Transaction Hook (Simulate-Write-Wait)**:
```typescript
export function useSimulateWrite(
  address: Address,
  abi: any,
  functionName: string,
  args: any[]
) {
  // Phase 1: Simulation
  const { data: simulation, error: simulateError } = useSimulateContract({
    address,
    abi,
    functionName,
    args,
  })
  
  // Phase 2: Write
  const { writeContract, isPending } = useWriteContract()
  
  // Phase 3: Wait
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash: writeHash,
  })
  
  return {
    simulate: () => simulation,
    write: () => writeContract(simulation!.request),
    state: { simulating, pending, confirming, success },
    error: simulateError || writeError,
  }
}
```

### 3. Optimistic UI Implementation
**Real-time State Updates**:
```typescript
// Optimistic updates for Web3 actions
const queryClient = useQueryClient()

const { mutate: sendMessage } = useMutation({
  mutationFn: (content: string) => conversation.send(content),
  
  // Optimistic update
  onMutate: async (content) => {
    // Cancel outgoing refetches
    await queryClient.cancelQueries({ queryKey: ['messages'] })
    
    // Snapshot previous value
    const previousMessages = queryClient.getQueryData(['messages'])
    
    // Optimistically update
    queryClient.setQueryData(['messages'], (old: any) => [
      ...old,
      {
        id: Date.now(),
        content,
        status: 'sending',
        sender: 'user',
      },
    ])
    
    return { previousMessages }
  },
  
  // Rollback on error
  onError: (err, newMessage, context) => {
    queryClient.setQueryData(['messages'], context.previousMessages)
  },
  
  // Always refetch after error or success
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['messages'] })
  },
})
```

### 4. Component Architecture
**Smart Component Structure**:
- `WalletConnector/`: Multi-wallet connection
- `TransactionModal/`: Simulate-Write-Wait UI
- `TokenBalance/`: Real-time balance display
- `NFTGallery/`: Lazy-loaded NFT display
- `NetworkSwitcher/`: Chain selection

### 5. Performance Optimization
**Bundle Size Management**:
- Dynamic imports for heavy libraries (`@xmtp/xmtp-js`)
- Code splitting by route
- Prefetching for critical Web3 data
- Service worker caching for ABIs

**Tree-shaking Configuration**:
```javascript
// vite.config.js or next.config.js
export default {
  build: {
    rollupOptions: {
      external: ['viem/chains', 'viem/actions'], // Keep tree-shakable
    },
  },
}
```

### 6. Integration Protocols
**XMTP Integration**:
```typescript
// Context-aware client initialization
export function useXMTPClient() {
  const { data: signer } = useSigner()
  const { isMobile } = useDeviceDetection()
  
  const client = useMemo(() => {
    if (!signer) return null
    
    const config: ClientOptions = {
      env: 'production',
      appVersion: 'jw3b.dev/1.0',
    }
    
    // Platform-specific encryption
    if (!isMobile) {
      // Browser: No dbEncryptionKey
      return Client.create(signer, config)
    } else {
      // Mobile: Required encryption key
      const key = await SecureStore.getItemAsync('xmtp_db_key')
      return Client.create(signer, { ...config, dbEncryptionKey: key })
    }
  }, [signer, isMobile])
  
  return client
}
```

**Unlock Protocol**:
```typescript
// Token-gating with pessimistic mode
const unlockConfig = {
  locks: {
    '0x123...': { name: 'Premium Access' },
  },
  pessimistic: true, // Wait for transaction indexing
  callToAction: {
    default: 'Unlock your Web3 Portfolio',
    expired: 'Membership expired',
  },
}
```

## TOOLS AND AUTOMATION
**MCP Integration**:
- `generate_hook`: Create custom Wagmi hooks
- `optimize_imports`: Tree-shake and optimize imports
- `validate_abi`: Verify ABI compatibility
- `analyze_bundle`: Check frontend bundle size
