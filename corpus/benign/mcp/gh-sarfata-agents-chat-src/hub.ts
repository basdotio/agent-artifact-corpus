import { EventEmitter } from "node:events";

export class EventHub {
  private readonly emitter = new EventEmitter();

  onEvent(agentId: string, listener: (eventRowId: number) => void): () => void {
    const name = `agent:${agentId}`;
    this.emitter.on(name, listener);
    return () => this.emitter.off(name, listener);
  }

  publish(agentIds: string[], eventRowId: number): void {
    for (const agentId of agentIds) this.emitter.emit(`agent:${agentId}`, eventRowId);
  }
}
