/**
 * Mock users data — for owner lookup and reassignment.
 */
import type { User } from "../types.js";

export const MOCK_USERS: User[] = [
  { id: "user-001", displayName: "Jane Smith", mail: "jane.smith@contoso.com", jobTitle: "IT Admin", department: "IT" },
  { id: "user-002", displayName: "John Davis", mail: "john.davis@contoso.com", jobTitle: "Security Lead", department: "Security" },
  { id: "user-003", displayName: "Sarah Chen", mail: "sarah.chen@contoso.com", jobTitle: "Engineering Manager", department: "Engineering" },
  { id: "user-004", displayName: "Mike Johnson", mail: "mike.johnson@contoso.com", jobTitle: "Product Manager", department: "Product" },
  { id: "user-005", displayName: "Emily Wong", mail: "emily.wong@contoso.com", jobTitle: "Data Scientist", department: "Analytics" },
  { id: "user-006", displayName: "Alex Rivera", mail: "alex.rivera@contoso.com", jobTitle: "DevOps Engineer", department: "Platform" },
  { id: "user-007", displayName: "Chris Martinez", mail: "chris.martinez@contoso.com", jobTitle: "Compliance Officer", department: "Legal" },
  { id: "user-008", displayName: "Pat Taylor", mail: "pat.taylor@contoso.com", jobTitle: "HR Director", department: "HR" },
  { id: "user-009", displayName: "Jordan Lee", mail: "jordan.lee@contoso.com", jobTitle: "Finance Manager", department: "Finance" },
  { id: "user-010", displayName: "Sam Wilson", mail: "sam.wilson@contoso.com", jobTitle: "Support Lead", department: "Support" },
];
