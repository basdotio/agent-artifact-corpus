# Animation Patterns

Wzorce animacji dla portfolio Pawla Lipowczana. Uzywa Framer Motion 12 i CSS transitions.

## Framer Motion Variants

### Fade In Up (Standard Entry)

Domyslna animacja wejscia dla elementow:

```jsx
const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' }
  }
};

// Usage
<motion.div
  initial="initial"
  animate="animate"
  variants={fadeInUp}
>
  Content
</motion.div>
```

### Stagger Children

Animacja z opoznieniem dla list elementow:

```jsx
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: 'easeOut' }
  }
};

// Usage
<motion.div
  initial="hidden"
  whileInView="visible"
  viewport={{ once: true, amount: 0.3 }}
  variants={containerVariants}
>
  {items.map((item, i) => (
    <motion.div key={i} variants={itemVariants}>
      {item}
    </motion.div>
  ))}
</motion.div>
```

### Scale on Hover

Efekt powiekszenia przy hover:

```jsx
// Simple scale
<motion.div
  whileHover={{ scale: 1.05 }}
  transition={{ type: 'spring', stiffness: 300 }}
>

// With lift (cards)
<motion.div
  whileHover={{ y: -10 }}
  transition={{ type: 'spring', stiffness: 300 }}
>
```

### Page Transitions

Animacje przejsc miedzy stronami:

```jsx
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    y: -20,
    transition: { duration: 0.3 }
  }
};

// Usage in page component
<motion.main
  variants={pageVariants}
  initial="initial"
  animate="animate"
  exit="exit"
>
```

## Scroll-Triggered Animations

### whileInView Pattern

```jsx
<motion.div
  initial={{ opacity: 0, y: 30 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true, amount: 0.3 }}
  transition={{ duration: 0.6, ease: 'easeOut' }}
>
```

### Viewport Options

```jsx
viewport={{
  once: true,      // Animate only once
  amount: 0.3,     // Trigger when 30% visible
  margin: '-100px' // Trigger 100px before entering viewport
}}
```

### Section Entry Animation

```jsx
const sectionVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      duration: 0.6,
      staggerChildren: 0.1
    }
  }
};

<motion.section
  initial="hidden"
  whileInView="visible"
  viewport={{ once: true, amount: 0.2 }}
  variants={sectionVariants}
>
```

## CSS Transitions

### Button Hover

```css
.button {
  transition: all 0.3s ease;
}

.button:hover {
  transform: scale(1.05);
  box-shadow: 0 0 30px rgba(0, 255, 157, 0.3);
}
```

### Card Hover

```css
.card {
  transition: all 0.3s ease;
}

.card:hover {
  transform: translateY(-10px);
  border-color: rgba(0, 255, 157, 0.3);
  box-shadow: 0 0 30px rgba(0, 255, 157, 0.15);
}
```

### Link Color Transition

```css
.link {
  transition: color 0.2s ease;
}

.link:hover {
  color: #00ff9d;
}
```

### Image Zoom

```css
.image-container {
  overflow: hidden;
}

.image {
  transition: transform 0.5s ease;
}

.image-container:hover .image {
  transform: scale(1.05);
}
```

## Specific Component Animations

### Hero Section

#### Logo Glow Pulse

```jsx
const logoVariants = {
  initial: { opacity: 0, scale: 0.8 },
  animate: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.8, ease: 'easeOut' }
  }
};

// CSS for glow pulse
@keyframes glow-pulse {
  0%, 100% { filter: drop-shadow(0 0 20px rgba(0, 255, 157, 0.3)); }
  50% { filter: drop-shadow(0 0 40px rgba(0, 255, 157, 0.6)); }
}

.logo-glow {
  animation: glow-pulse 3s ease-in-out infinite;
}
```

#### Text Reveal

```jsx
const textReveal = {
  hidden: { opacity: 0, y: 50 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.8,
      ease: [0.6, 0.01, 0.05, 0.95]
    }
  }
};
```

### Statistics Counter

```jsx
const CountUp = ({ end, duration = 2 }) => {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (inView) {
      let start = 0;
      const increment = end / (duration * 60);
      const timer = setInterval(() => {
        start += increment;
        if (start >= end) {
          setCount(end);
          clearInterval(timer);
        } else {
          setCount(Math.floor(start));
        }
      }, 1000 / 60);
      return () => clearInterval(timer);
    }
  }, [inView, end, duration]);

  return <span ref={ref}>{count}</span>;
};
```

### Mobile Menu

```jsx
const menuVariants = {
  closed: {
    opacity: 0,
    x: '100%',
    transition: { duration: 0.3, ease: 'easeInOut' }
  },
  open: {
    opacity: 1,
    x: 0,
    transition: { duration: 0.3, ease: 'easeInOut' }
  }
};

const menuItemVariants = {
  closed: { opacity: 0, x: 20 },
  open: { opacity: 1, x: 0 }
};

<AnimatePresence>
  {isOpen && (
    <motion.div
      variants={menuVariants}
      initial="closed"
      animate="open"
      exit="closed"
      className="fixed inset-0 bg-[#0a0e1a]/95 backdrop-blur-md"
    >
      <motion.nav variants={containerVariants}>
        {links.map((link) => (
          <motion.a variants={menuItemVariants}>{link}</motion.a>
        ))}
      </motion.nav>
    </motion.div>
  )}
</AnimatePresence>
```

### Network Background (Canvas)

```jsx
useEffect(() => {
  const canvas = canvasRef.current;
  const ctx = canvas.getContext('2d');
  let animationId;

  const particles = [];
  const particleCount = 100;

  // Initialize particles
  for (let i = 0; i < particleCount; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.5,
      vy: (Math.random() - 0.5) * 0.5,
      radius: Math.random() * 2 + 1
    });
  }

  const animate = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Update and draw particles
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;

      // Wrap around edges
      if (p.x < 0) p.x = canvas.width;
      if (p.x > canvas.width) p.x = 0;
      if (p.y < 0) p.y = canvas.height;
      if (p.y > canvas.height) p.y = 0;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(0, 255, 157, 0.5)';
      ctx.fill();
    });

    // Draw connections
    particles.forEach((p1, i) => {
      particles.slice(i + 1).forEach(p2 => {
        const dx = p1.x - p2.x;
        const dy = p1.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 150) {
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(0, 255, 157, ${0.2 * (1 - dist / 150)})`;
          ctx.stroke();
        }
      });
    });

    animationId = requestAnimationFrame(animate);
  };

  animate();

  return () => cancelAnimationFrame(animationId);
}, []);
```

## Performance Guidelines

### Do's

- Use `transform` and `opacity` only for animations
- Use `will-change` sparingly and only when needed
- Use `requestAnimationFrame` for canvas animations
- Use `once: true` for scroll animations to prevent re-triggering
- Debounce scroll/resize handlers

### Don'ts

- Never animate `width`, `height`, `top`, `left`, `margin`, `padding`
- Don't use `will-change: auto` or apply to too many elements
- Don't run heavy calculations in animation loops
- Don't forget to cleanup animation frames on unmount

### Framer Motion Optimization

```jsx
// Use layout animations sparingly
<motion.div layout /> // Can be expensive

// Prefer simple transforms
<motion.div animate={{ x: 100 }} /> // Good
<motion.div animate={{ left: 100 }} /> // Bad

// Use layoutId for shared element transitions
<motion.div layoutId="shared-element" />
```

### Reduced Motion Support

```jsx
// Respect user preferences
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

const variants = prefersReducedMotion
  ? { initial: {}, animate: {} }
  : { initial: { opacity: 0 }, animate: { opacity: 1 } };
```

## Animation Timing Reference

| Animation | Duration | Easing |
|-----------|----------|--------|
| Hover states | 300ms | ease |
| Page transitions | 500ms | easeOut |
| Element entry | 600ms | easeOut |
| Stagger delay | 100ms | - |
| Logo pulse | 3000ms | ease-in-out |
| Image zoom | 500ms | ease |
| Menu slide | 300ms | easeInOut |
