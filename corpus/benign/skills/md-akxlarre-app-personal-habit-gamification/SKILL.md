---
name: habit-gamification
description: Sistema de gamificación para formación de hábitos con rachas, deuda de bloques, streak freezes y mecánicas basadas en aversión a la pérdida. Úsalo cuando implementes sistemas de accountability, gamificación de productividad, o tracking de hábitos.
---

# Habit Gamification System

Sistema completo de gamificación basado en los principios de Atomic Habits y psicología de la aversión a la pérdida (loss aversion). Diseñado específicamente para Life Blocks App.

## Fundamentos Psicológicos

### Aversión a la Pérdida (Loss Aversion)
El dolor de perder una racha de 50 días es **2.5x más intenso** que la satisfacción de iniciar una nueva. Este principio impulsa el cumplimiento diario.

### Efecto de Dotación (Endowment Effect)
Una vez que el usuario "posee" una racha, la valora más que antes de conseguirla. Cada día completado aumenta la inversión emocional.

### Sesgo de Consistencia
Los humanos buscan mantener patrones de comportamiento establecidos. Una racha visible refuerza este sesgo.

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    USER COMPLETES BLOCK                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. CHECK DAILY COMPLETION                                  │
│     • ¿Es el primer bloque completado hoy?                  │
│     • ¿Bloque marcado como "crítico"?                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  2. UPDATE STREAK                                           │
│     • current_count++                                       │
│     • Si current > longest → longest = current              │
│     • last_completed = today                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  3. CHECK MILESTONE                                         │
│     • ¿current_count en [7, 14, 30, 50, 100, 365]?         │
│     • Trigger celebration animation                        │
│     • Award achievement badge                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  4. CLEAR DEBT (if exists)                                  │
│     • Remover bloque de "deuda de hábitos"                  │
│     • Actualizar streak debt counter                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    USER SKIPS BLOCK                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. CHECK STREAK FREEZE AVAILABILITY                        │
│     • ¿Tiene Streak Freeze disponible?                     │
│     • ¿Usuario quiere usarlo?                               │
└────────────┬───────────────────────┬────────────────────────┘
            YES                      NO
             │                        │
             ▼                        ▼
┌──────────────────────────┐  ┌─────────────────────────────┐
│  USE FREEZE              │  │  BREAK STREAK               │
│  • freeze_count--        │  │  • current_count = 0        │
│  • Streak preserved      │  │  • Show loss animation      │
│  • No debt               │  │  • Trigger "recovery mode"  │
└──────────────────────────┘  └────────────┬────────────────┘
                                           │
                                           ▼
                              ┌────────────────────────────┐
                              │  ADD TO DEBT QUEUE         │
                              │  • Si bloque es crítico    │
                              │  • debt_count++            │
                              │  • Show tomorrow           │
                              └────────────────────────────┘
```

## Schema de Datos

### Tabla: streaks

```sql
CREATE TABLE streaks (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  block_name TEXT NOT NULL,          -- "Deep Work", "Gym", "Reset Nocturno"
  current_count INTEGER DEFAULT 0,
  longest_count INTEGER DEFAULT 0,
  last_completed DATE,
  freeze_count INTEGER DEFAULT 2,    -- Resetea cada mes
  freeze_used_this_month INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  
  UNIQUE(user_id, block_name)
);

CREATE INDEX idx_streaks_user ON streaks(user_id);
CREATE INDEX idx_streaks_current ON streaks(current_count DESC);
```

### Tabla: habit_debt

```sql
CREATE TABLE habit_debt (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  block_id TEXT NOT NULL,
  block_name TEXT NOT NULL,
  original_date DATE NOT NULL,       -- Fecha original que se skipeo
  due_date DATE NOT NULL,            -- Fecha límite para completar
  status TEXT DEFAULT 'pending',     -- 'pending' | 'completed' | 'forgiven'
  completed_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_debt_user ON habit_debt(user_id);
CREATE INDEX idx_debt_status ON habit_debt(status);
CREATE INDEX idx_debt_due_date ON habit_debt(due_date);
```

### Tabla: achievements

```sql
CREATE TABLE achievements (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  achievement_type TEXT NOT NULL,    -- 'streak_7', 'streak_30', 'debt_free_week'
  block_name TEXT,
  earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
  metadata TEXT                      -- JSON con detalles extra
);

CREATE INDEX idx_achievements_user ON achievements(user_id);
CREATE INDEX idx_achievements_type ON achievements(achievement_type);
```

## Servicio de Streaks (Angular)

```typescript
// src/app/features/habits/services/streak.service.ts
import { Injectable, inject, signal, computed } from '@angular/core';
import { SQLiteService } from '@core/database/sqlite.service';
import { AnimationService } from '@core/animations/animation.service';

export interface Streak {
  id: string;
  userId: string;
  blockName: string;
  currentCount: number;
  longestCount: number;
  lastCompleted: string | null;
  freezeCount: number;
  freezeUsedThisMonth: number;
}

export interface HabitDebt {
  id: number;
  userId: string;
  blockId: string;
  blockName: string;
  originalDate: string;
  dueDate: string;
  status: 'pending' | 'completed' | 'forgiven';
}

const MILESTONES = [7, 14, 30, 50, 100, 365];
const MAX_FREEZE_PER_MONTH = 2;

@Injectable({ providedIn: 'root' })
export class StreakService {
  private sqlite = inject(SQLiteService);
  private animations = inject(AnimationService);
  
  // Estado reactivo
  streaks = signal<Streak[]>([]);
  debtedBlocks = signal<HabitDebt[]>([]);
  
  // Computeds
  totalStreaks = computed(() => 
    this.streaks().reduce((sum, s) => sum + s.currentCount, 0)
  );
  
  longestStreak = computed(() => 
    Math.max(...this.streaks().map(s => s.longestCount), 0)
  );
  
  pendingDebts = computed(() => 
    this.debtedBlocks().filter(d => d.status === 'pending').length
  );
  
  availableFreezes = computed(() => 
    this.streaks().reduce((sum, s) => sum + s.freezeCount, 0)
  );
  
  /**
   * Completar bloque y actualizar racha
   */
  async completeBlock(
    userId: string, 
    blockId: string, 
    blockName: string
  ): Promise<void> {
    const today = new Date().toISOString().split('T')[0];
    
    // 1. Obtener racha actual
    let streak = await this.getStreak(userId, blockName);
    
    if (!streak) {
      // Primera vez que completa este bloque
      streak = await this.createStreak(userId, blockName);
    }
    
    // 2. Verificar si ya completó hoy (evitar doble conteo)
    if (streak.lastCompleted === today) {
      console.warn('Block already completed today');
      return;
    }
    
    // 3. Verificar si rompió racha (más de 1 día sin completar)
    const daysSinceLastCompletion = this.getDaysDifference(
      streak.lastCompleted,
      today
    );
    
    if (daysSinceLastCompletion > 1) {
      // Racha rota, resetear
      await this.resetStreak(streak.id);
      streak.currentCount = 0;
    }
    
    // 4. Incrementar racha
    const newCount = streak.currentCount + 1;
    const newLongest = Math.max(newCount, streak.longestCount);
    
    await this.sqlite.db.run(
      `UPDATE streaks 
       SET current_count = ?,
           longest_count = ?,
           last_completed = ?,
           updated_at = CURRENT_TIMESTAMP
       WHERE id = ?`,
      [newCount, newLongest, today, streak.id]
    );
    
    // 5. Actualizar señal reactiva
    this.streaks.update(streaks => 
      streaks.map(s => 
        s.id === streak.id 
          ? { ...s, currentCount: newCount, longestCount: newLongest, lastCompleted: today }
          : s
      )
    );
    
    // 6. Verificar milestone
    if (MILESTONES.includes(newCount)) {
      await this.triggerMilestone(userId, blockName, newCount);
    }
    
    // 7. Limpiar deuda si existe
    await this.clearDebt(userId, blockId);
  }
  
  /**
   * Skipear bloque con opción de Streak Freeze
   */
  async skipBlock(
    userId: string,
    blockId: string,
    blockName: string,
    isCritical: boolean,
    useFreeze: boolean = false
  ): Promise<{ streakBroken: boolean; debtAdded: boolean }> {
    const streak = await this.getStreak(userId, blockName);
    
    if (!streak) {
      return { streakBroken: false, debtAdded: false };
    }
    
    let streakBroken = false;
    let debtAdded = false;
    
    if (useFreeze && streak.freezeCount > 0) {
      // Usar Streak Freeze
      await this.useStreakFreeze(streak.id);
      console.log('Streak preserved with freeze');
    } else {
      // Romper racha
      await this.breakStreak(streak.id, blockName);
      streakBroken = true;
      
      // Si es bloque crítico, agregar a deuda
      if (isCritical) {
        await this.addToDebt(userId, blockId, blockName);
        debtAdded = true;
      }
    }
    
    return { streakBroken, debtAdded };
  }
  
  /**
   * Usar Streak Freeze
   */
  private async useStreakFreeze(streakId: string): Promise<void> {
    await this.sqlite.db.run(
      `UPDATE streaks 
       SET freeze_count = freeze_count - 1,
           freeze_used_this_month = freeze_used_this_month + 1
       WHERE id = ?`,
      [streakId]
    );
    
    this.streaks.update(streaks =>
      streaks.map(s =>
        s.id === streakId
          ? { ...s, freezeCount: s.freezeCount - 1, freezeUsedThisMonth: s.freezeUsedThisMonth + 1 }
          : s
      )
    );
  }
  
  /**
   * Romper racha (con animación de pérdida)
   */
  private async breakStreak(streakId: string, blockName: string): Promise<void> {
    await this.sqlite.db.run(
      `UPDATE streaks 
       SET current_count = 0,
           updated_at = CURRENT_TIMESTAMP
       WHERE id = ?`,
      [streakId]
    );
    
    this.streaks.update(streaks =>
      streaks.map(s =>
        s.id === streakId ? { ...s, currentCount: 0 } : s
      )
    );
    
    // Trigger animación de pérdida
    this.animations.playStreakLost(blockName);
  }
  
  /**
   * Agregar bloque a deuda de hábitos
   */
  private async addToDebt(
    userId: string,
    blockId: string,
    blockName: string
  ): Promise<void> {
    const today = new Date().toISOString().split('T')[0];
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const dueDate = tomorrow.toISOString().split('T')[0];
    
    await this.sqlite.db.run(
      `INSERT INTO habit_debt 
       (user_id, block_id, block_name, original_date, due_date, status)
       VALUES (?, ?, ?, ?, ?, 'pending')`,
      [userId, blockId, blockName, today, dueDate]
    );
    
    // Actualizar señal
    await this.loadDebtedBlocks(userId);
  }
  
  /**
   * Limpiar deuda al completar bloque
   */
  private async clearDebt(userId: string, blockId: string): Promise<void> {
    const result = await this.sqlite.db.query(
      `SELECT id FROM habit_debt 
       WHERE user_id = ? AND block_id = ? AND status = 'pending'
       LIMIT 1`,
      [userId, blockId]
    );
    
    if (result.values && result.values.length > 0) {
      const debtId = result.values[0].id;
      
      await this.sqlite.db.run(
        `UPDATE habit_debt 
         SET status = 'completed',
             completed_at = CURRENT_TIMESTAMP
         WHERE id = ?`,
        [debtId]
      );
      
      // Actualizar señal
      await this.loadDebtedBlocks(userId);
    }
  }
  
  /**
   * Trigger milestone (7, 30, 100 días)
   */
  private async triggerMilestone(
    userId: string,
    blockName: string,
    days: number
  ): Promise<void> {
    // 1. Registrar achievement
    const achievementId = `${userId}_${blockName}_${days}`;
    
    await this.sqlite.db.run(
      `INSERT OR IGNORE INTO achievements 
       (id, user_id, achievement_type, block_name, metadata)
       VALUES (?, ?, ?, ?, ?)`,
      [
        achievementId,
        userId,
        `streak_${days}`,
        blockName,
        JSON.stringify({ days, timestamp: new Date().toISOString() })
      ]
    );
    
    // 2. Trigger animación de celebración
    this.animations.playStreakMilestone(blockName, days);
    
    // 3. Mostrar notificación
    // TODO: Integrar con NotificationService
  }
  
  /**
   * Resetear racha a 0
   */
  private async resetStreak(streakId: string): Promise<void> {
    await this.sqlite.db.run(
      `UPDATE streaks 
       SET current_count = 0
       WHERE id = ?`,
      [streakId]
    );
  }
  
  /**
   * Obtener racha de un bloque
   */
  private async getStreak(userId: string, blockName: string): Promise<Streak | null> {
    const result = await this.sqlite.db.query(
      `SELECT * FROM streaks 
       WHERE user_id = ? AND block_name = ?`,
      [userId, blockName]
    );
    
    return result.values?.[0] || null;
  }
  
  /**
   * Crear nueva racha
   */
  private async createStreak(userId: string, blockName: string): Promise<Streak> {
    const id = crypto.randomUUID();
    
    await this.sqlite.db.run(
      `INSERT INTO streaks 
       (id, user_id, block_name, current_count, longest_count, freeze_count)
       VALUES (?, ?, ?, 0, 0, ?)`,
      [id, userId, blockName, MAX_FREEZE_PER_MONTH]
    );
    
    return {
      id,
      userId,
      blockName,
      currentCount: 0,
      longestCount: 0,
      lastCompleted: null,
      freezeCount: MAX_FREEZE_PER_MONTH,
      freezeUsedThisMonth: 0
    };
  }
  
  /**
   * Calcular diferencia de días
   */
  private getDaysDifference(dateStr1: string | null, dateStr2: string): number {
    if (!dateStr1) return Infinity;
    
    const date1 = new Date(dateStr1);
    const date2 = new Date(dateStr2);
    const diffTime = Math.abs(date2.getTime() - date1.getTime());
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }
  
  /**
   * Cargar rachas del usuario
   */
  async loadStreaks(userId: string): Promise<void> {
    const result = await this.sqlite.db.query(
      'SELECT * FROM streaks WHERE user_id = ?',
      [userId]
    );
    
    this.streaks.set(result.values || []);
  }
  
  /**
   * Cargar bloques en deuda
   */
  async loadDebtedBlocks(userId: string): Promise<void> {
    const result = await this.sqlite.db.query(
      `SELECT * FROM habit_debt 
       WHERE user_id = ? AND status = 'pending'
       ORDER BY due_date ASC`,
      [userId]
    );
    
    this.debtedBlocks.set(result.values || []);
  }
  
  /**
   * Resetear Streak Freezes (mensual)
   */
  async resetMonthlyFreezes(userId: string): Promise<void> {
    await this.sqlite.db.run(
      `UPDATE streaks 
       SET freeze_count = ?,
           freeze_used_this_month = 0
       WHERE user_id = ?`,
      [MAX_FREEZE_PER_MONTH, userId]
    );
    
    await this.loadStreaks(userId);
  }
  
  /**
   * Perdonar deuda (manual)
   */
  async forgiveDebt(debtId: number): Promise<void> {
    await this.sqlite.db.run(
      `UPDATE habit_debt 
       SET status = 'forgiven'
       WHERE id = ?`,
      [debtId]
    );
    
    // Actualizar señal
    this.debtedBlocks.update(debts =>
      debts.filter(d => d.id !== debtId)
    );
  }
}
```

## Componente de Visualización de Racha

```typescript
// src/app/features/habits/components/streak-badge/streak-badge.component.ts
@Component({
  selector: 'app-streak-badge',
  standalone: true,
  imports: [CommonModule, BadgeModule],
  template: `
    <div class="streak-badge" [class.milestone]="isMilestone()">
      <div class="fire-icon" #fireIcon>
        🔥
      </div>
      <div class="counter">
        <span class="current">{{ streak().currentCount }}</span>
        <span class="label">días</span>
      </div>
      @if (streak().longestCount > streak().currentCount) {
        <div class="longest">
          Récord: {{ streak().longestCount }}
        </div>
      }
    </div>
  `,
  styles: [`
    .streak-badge {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      padding: 1rem;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 1rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      
      &.milestone {
        animation: glow 2s infinite alternate;
      }
      
      .fire-icon {
        font-size: 3rem;
        filter: drop-shadow(0 0 10px rgba(255, 165, 0, 0.5));
      }
      
      .counter {
        display: flex;
        flex-direction: column;
        align-items: center;
        
        .current {
          font-size: 2.5rem;
          font-weight: bold;
          color: white;
        }
        
        .label {
          font-size: 0.875rem;
          color: rgba(255, 255, 255, 0.8);
        }
      }
      
      .longest {
        font-size: 0.75rem;
        color: rgba(255, 255, 255, 0.6);
      }
    }
    
    @keyframes glow {
      from {
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      }
      to {
        box-shadow: 0 0 20px rgba(255, 165, 0, 0.8);
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class StreakBadgeComponent implements AfterViewInit {
  @ViewChild('fireIcon') fireIcon!: ElementRef;
  
  streak = input.required<Streak>();
  
  private animations = inject(AnimationService);
  
  isMilestone = computed(() => 
    MILESTONES.includes(this.streak().currentCount)
  );
  
  ngAfterViewInit() {
    if (this.isMilestone()) {
      this.animations.playStreakAnimation(
        this.fireIcon.nativeElement,
        this.streak().currentCount
      );
    }
  }
}
```

## Componente de Deuda de Hábitos

```typescript
// src/app/features/habits/components/debt-queue/debt-queue.component.ts
@Component({
  selector: 'app-debt-queue',
  standalone: true,
  imports: [CommonModule, CardModule, ButtonModule],
  template: `
    <div class="debt-queue">
      <h3>Bloques Pendientes (Deuda)</h3>
      
      @if (debts().length === 0) {
        <div class="empty-state">
          <span class="icon">✅</span>
          <p>¡Sin deudas! Estás al día con tus hábitos.</p>
        </div>
      } @else {
        <div class="debt-list">
          @for (debt of debts(); track debt.id) {
            <p-card>
              <div class="debt-item">
                <div class="info">
                  <strong>{{ debt.blockName }}</strong>
                  <small>Pendiente desde {{ debt.originalDate | date }}</small>
                  <small class="due">Vence: {{ debt.dueDate | date }}</small>
                </div>
                <div class="actions">
                  <p-button 
                    label="Completar ahora"
                    icon="pi pi-check"
                    (onClick)="completeDebt(debt)"
                  />
                  <p-button 
                    label="Perdonar"
                    icon="pi pi-times"
                    severity="secondary"
                    (onClick)="forgiveDebt(debt)"
                  />
                </div>
              </div>
            </p-card>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .debt-queue {
      padding: 1rem;
      
      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
        padding: 2rem;
        
        .icon {
          font-size: 4rem;
        }
      }
      
      .debt-list {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        
        .debt-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          
          .info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            
            .due {
              color: var(--red-500);
              font-weight: 600;
            }
          }
          
          .actions {
            display: flex;
            gap: 0.5rem;
          }
        }
      }
    }
  `]
})
export class DebtQueueComponent {
  debts = input.required<HabitDebt[]>();
  
  private streakService = inject(StreakService);
  
  async completeDebt(debt: HabitDebt) {
    // Completar bloque y limpiar deuda
    await this.streakService.completeBlock(
      debt.userId,
      debt.blockId,
      debt.blockName
    );
  }
  
  async forgiveDebt(debt: HabitDebt) {
    await this.streakService.forgiveDebt(debt.id);
  }
}
```

## Estrategias de Retención

### 1. Recovery Mode
Cuando se rompe una racha larga (30+ días), activar "modo recuperación":
- Ofrecer 1 Streak Freeze extra
- Enviar notificación motivacional
- Mostrar progreso histórico para no desmoralizarse

### 2. Milestone Rewards
- 7 días: Badge "Constante"
- 30 días: Badge "Comprometido"
- 100 días: Badge "Imparable"
- 365 días: Badge "Leyenda"

### 3. Social Proof
Mostrar estadísticas de otros usuarios (anónimas):
- "El 80% de usuarios con racha de 30+ días usan Streak Freeze"
- "Promedio de racha más larga: 45 días"

---

**Versión**: 1.0.0  
**Última actualización**: 2025-01-30  
**Basado en**: Atomic Habits (James Clear) + Hooked (Nir Eyal)
