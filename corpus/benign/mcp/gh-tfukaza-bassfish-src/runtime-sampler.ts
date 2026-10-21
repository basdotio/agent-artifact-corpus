import type { DiagnosticFields } from './diagnostic-events.js';

/** Pure gap detection allows clock jumps and system suspension to be tested without host sleeps. */
export class RuntimeSampler {
  private previousWall?: number;
  private previousMono?: number;
  private stalled = false;
  private maxGapMs = 0;
  sample(
    wallMs: number,
    monoMs: number,
    mainGapMs: number,
  ): Array<{ event: string; fields: DiagnosticFields }> {
    const events: Array<{ event: string; fields: DiagnosticFields }> = [];
    if (this.previousWall !== undefined && this.previousMono !== undefined) {
      const wallGapMs = wallMs - this.previousWall,
        samplerGapMs = monoMs - this.previousMono;
      if (samplerGapMs > 2000)
        events.push({
          event: 'runtime.sampler_gap',
          fields: { samplerGapMs, wallGapMs, cause: 'unknown' },
        });
      if (Math.abs(wallGapMs - samplerGapMs) > 2000)
        events.push({
          event: 'runtime.clock_changed',
          fields: {
            wallGapMs,
            samplerGapMs,
            offsetChangeMs: wallGapMs - samplerGapMs,
            cause: 'clock_change_or_suspend',
          },
        });
    }
    if (mainGapMs > 2000) {
      this.maxGapMs = Math.max(this.maxGapMs, mainGapMs);
      events.push({
        event: this.stalled ? 'runtime.stall_ongoing' : 'runtime.stall_started',
        fields: { gapMs: mainGapMs },
      });
      this.stalled = true;
    } else if (this.stalled) {
      events.push({ event: 'runtime.stall_recovered', fields: { maxGapMs: this.maxGapMs } });
      this.stalled = false;
      this.maxGapMs = 0;
    }
    this.previousWall = wallMs;
    this.previousMono = monoMs;
    return events;
  }
}
