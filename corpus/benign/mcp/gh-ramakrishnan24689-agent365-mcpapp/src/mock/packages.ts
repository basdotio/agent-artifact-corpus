/**
 * Mock data — 50 agents with realistic distribution across publisher types.
 * Shapes match Microsoft Graph beta /copilot/admin/catalog/packages responses.
 */
import type { Agent, PublisherType, AgentStatus, RiskLevel } from "../types.js";

const PUBLISHERS: { type: PublisherType; name: string; platform: string }[] = [
  { type: "Microsoft", name: "Microsoft Corporation", platform: "Microsoft 365" },
  { type: "CopilotStudio", name: "Contoso Corp", platform: "Copilot Studio" },
  { type: "ThirdParty", name: "Acme Inc", platform: "Third Party" },
  { type: "AgentsToolkit", name: "Contoso Dev Team", platform: "Agents Toolkit" },
  { type: "Others", name: "Legacy Systems", platform: "Custom" },
];

const CHANNELS = ["Teams", "Web", "Outlook", "SharePoint", "Copilot"];
const ELEMENT_TYPES = ["bot", "declarativeAgent", "customEngineAgent", "officeAddIn"];
const STATUSES: AgentStatus[] = ["Active", "Active", "Active", "Active", "Blocked"];

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pickN<T>(arr: T[], min: number, max: number): T[] {
  const n = min + Math.floor(Math.random() * (max - min + 1));
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, n);
}

function generateAgent(index: number): Agent {
  const publisher = PUBLISHERS[index % PUBLISHERS.length];
  const status = pick(STATUSES);
  const riskLevels: RiskLevel[] = ["none", "none", "none", "none", "low", "medium", "high"];
  const deployOptions = ["all", "some", "none"];

  return {
    id: `pkg-${String(index).padStart(4, "0")}-${crypto.randomUUID().slice(0, 8)}`,
    displayName: AGENT_NAMES[index % AGENT_NAMES.length],
    description: AGENT_DESCRIPTIONS[index % AGENT_DESCRIPTIONS.length],
    publisherType: publisher.type,
    publisherName: publisher.name,
    platform: publisher.platform,
    status,
    channels: pickN(CHANNELS, 1, 3),
    elementTypes: pickN(ELEMENT_TYPES, 1, 2),
    activeUsers: status === "Active" ? Math.floor(Math.random() * 5000) : 0,
    deployedTo: pick(deployOptions),
    availableTo: pick(deployOptions),
    lastModifiedDateTime: new Date(2025, Math.floor(Math.random() * 5), Math.floor(Math.random() * 28) + 1).toISOString(),
    owner: Math.random() > 0.2 ? {
      id: `user-${String(index).padStart(3, "0")}`,
      displayName: OWNER_NAMES[index % OWNER_NAMES.length],
      mail: `${OWNER_NAMES[index % OWNER_NAMES.length].toLowerCase().replace(" ", ".")}@contoso.com`,
    } : undefined,
    riskLevel: pick(riskLevels),
    sensitivity: pick(["general", "confidential", "highly-confidential", undefined] as any),
    categories: pickN(["Productivity", "Development", "HR", "Finance", "IT", "Security"], 1, 3),
    appId: `app-${crypto.randomUUID().slice(0, 8)}`,
    version: `${Math.floor(Math.random() * 3) + 1}.${Math.floor(Math.random() * 10)}.${Math.floor(Math.random() * 10)}`,
  };
}

const AGENT_NAMES = [
  "HR Onboarding Assistant", "IT Helpdesk Bot", "Sales Copilot Pro",
  "Finance Approvals Agent", "Legal Document Reviewer", "Customer Support AI",
  "Marketing Campaign Manager", "Engineering Sprint Planner", "Compliance Monitor",
  "Data Analytics Helper", "Travel Booking Agent", "Procurement Assistant",
  "Employee Wellness Bot", "Meeting Scheduler Pro", "Knowledge Base Navigator",
  "Incident Response Agent", "Invoice Processing Bot", "Talent Acquisition AI",
  "Project Status Reporter", "Security Alert Monitor", "Inventory Manager",
  "Training Curriculum Planner", "Benefits Enrollment Helper", "Expense Report Agent",
  "Contract Negotiation AI", "Supply Chain Optimizer", "Quality Assurance Bot",
  "Onboarding Buddy", "Performance Review Assistant", "Feedback Collection Agent",
  "Release Notes Generator", "API Documentation Bot", "Code Review Helper",
  "Design System Assistant", "Accessibility Checker", "Localization Agent",
  "Content Moderator", "Brand Guidelines Bot", "Social Media Manager",
  "Event Planning Assistant", "Facilities Request Bot", "Parking Reservation Agent",
  "Cafeteria Menu Bot", "Shuttle Schedule Helper", "Badge Access Manager",
  "Visitor Check-in Agent", "Room Booking Assistant", "Equipment Rental Bot",
  "Software License Manager", "Password Reset Helper",
];

const AGENT_DESCRIPTIONS = [
  "Streamlines employee onboarding with automated task assignment and document collection.",
  "Resolves common IT issues and escalates complex problems to human agents.",
  "Provides real-time sales insights and automates CRM updates.",
  "Routes financial approvals through proper channels with audit trails.",
  "Reviews legal documents for compliance and flags potential issues.",
  "Handles customer inquiries across channels with context awareness.",
  "Creates and optimizes marketing campaigns with AI-driven insights.",
  "Plans sprints, tracks velocity, and generates standup summaries.",
  "Monitors regulatory compliance and alerts on policy violations.",
  "Helps teams analyze data with natural language queries.",
  "Books travel arrangements within policy and budget constraints.",
  "Manages procurement workflows from request to delivery.",
  "Promotes employee wellness with personalized recommendations.",
  "Finds optimal meeting times across complex schedules.",
  "Searches organizational knowledge bases with semantic understanding.",
  "Coordinates incident response with automated runbook execution.",
  "Processes invoices with OCR and routes for approval.",
  "Screens candidates and schedules interviews automatically.",
  "Generates project status reports from multiple data sources.",
  "Monitors security alerts and initiates response protocols.",
  "Tracks inventory levels and triggers replenishment orders.",
  "Plans training curricula based on skill gaps and goals.",
  "Guides employees through benefits enrollment options.",
  "Automates expense report creation and policy checking.",
  "Assists with contract terms analysis and negotiation strategies.",
  "Optimizes supply chain logistics with predictive analytics.",
  "Runs automated QA tests and reports quality metrics.",
  "Helps new hires navigate their first 90 days.",
  "Facilitates performance review processes and goal tracking.",
  "Collects and analyzes feedback from multiple channels.",
  "Generates release notes from commit messages and PRs.",
  "Creates and maintains API documentation automatically.",
  "Reviews code changes and suggests improvements.",
  "Helps designers follow and maintain the design system.",
  "Checks content for accessibility compliance issues.",
  "Manages translation workflows across supported languages.",
  "Moderates user-generated content for policy violations.",
  "Ensures content follows brand guidelines.",
  "Schedules and optimizes social media posts.",
  "Plans corporate events with vendor management.",
  "Handles facilities maintenance and repair requests.",
  "Manages parking reservations and availability.",
  "Displays daily cafeteria menus and handles dietary requests.",
  "Provides shuttle schedules and real-time tracking.",
  "Manages badge access provisioning and revocation.",
  "Handles visitor pre-registration and check-in.",
  "Books meeting rooms with equipment and catering.",
  "Manages equipment rental and return tracking.",
  "Tracks software license usage and compliance.",
  "Guides users through secure password reset flows.",
];

const OWNER_NAMES = [
  "Jane Smith", "John Davis", "Sarah Chen", "Mike Johnson", "Emily Wong",
  "Alex Rivera", "Chris Martinez", "Pat Taylor", "Jordan Lee", "Sam Wilson",
  "Morgan Brown", "Casey Anderson", "Riley Thompson", "Avery White", "Quinn Harris",
  "Drew Clark", "Jamie Lewis", "Skyler Robinson", "Dakota Walker", "Reese Hall",
];

// Generate 50 mock agents
export const MOCK_AGENTS: Agent[] = Array.from({ length: 50 }, (_, i) => generateAgent(i));
