export declare const SERVICES: readonly ["advisor", "compliance", "config-manager", "content-sources", "hbi", "malware", "notifications", "patch", "playbook-dispatcher", "rbac", "remediations", "ros", "tasks", "vulnerability"];
export type Service = (typeof SERVICES)[number];
export declare function getKslUrl(service: Service): string;
//# sourceMappingURL=services.d.ts.map