import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { store } from "./store.ts";

const text = (t: string) => ({ messages: [{ role: "user" as const, content: { type: "text" as const, text: t } }] });

function accountsContext(): string {
  const s = store();
  const accounts = s.accounts();
  if (!accounts.length) return "No bank accounts are linked yet.";
  return (
    "Linked accounts:\n" +
    accounts
      .map((a) => `- ${a.label ?? a.name ?? a.product ?? "account"} (uid ${a.uid}, ${a.currency}, ${s.data.sessions[a.session_id]?.bank.name ?? "?"})`)
      .join("\n")
  );
}

export function registerPrompts(server: McpServer): void {
  server.registerPrompt(
    "connect-bank",
    {
      title: "Connect a bank",
      description: "Walk the account holder through linking a bank (or renewing an expired consent).",
      argsSchema: { bank: z.string().optional().describe("Bank name, if known") },
    },
    ({ bank }) =>
      text(
        `Help me connect ${bank ? `my bank "${bank}"` : "a bank"} to this server.

1. If the exact bank name is unclear, call list_banks (optionally with search) and let me pick.
2. Call start_consent with the exact name. Show me the URL as a plain link and tell me to open it, log in at the bank and approve read-only access. Mention how long the consent lasts.
3. When I say I am done, call consent_status and list_accounts. Summarise what got linked.
4. Suggest a short label for each account based on its name and product, and offer to set them with set_account_label so I can refer to accounts by name.

${accountsContext()}`,
      ),
  );

  server.registerPrompt(
    "savings-scan",
    {
      title: "Savings scan",
      description:
        "For the vague 'how am I doing?' question. A 90-day scan that returns at most three findings ranked by money at stake and urgency: about to run short, a needless cost, or a regular payment that changed. Each with a concrete action. Not a monthly category review.",
    },
    () =>
      text(
        `Give me a 90-day money-saving scan: prevent harm or leave me better off. At most three findings.

1. Call list_accounts with include_balances, then get_transactions on each current account for the last 90 days (follow continuation keys). Skip loan and mortgage accounts for spending findings; note their booked balance only if cash is tight. Do not fetch any other window. If a range comes back empty, say the bank returned nothing.
2. Work out each account's role from what flows through it: everyday account (salary in, cards and bills out), transfer or holding account (mostly moves between my own accounts), savings, or liability. Use the role so you do not misread things: a transfer account running low means "top up", not "short before payday". Do not lead with the role; offer set_account_label only as a follow-up. Do not invent accounts I have not linked; if a payee suggests one (a card bill, a rent payment), say so.
3. Main currency is the one my income arrives in and my cards are paid from, not an empty travel wallet. Quote and rank in it. Do not invent exchange rates. If a charge was billed in another currency, keep the billed currency; show both only for a currency-fee finding.
4. Scan for: (a) running short: project the next low point from the usual cadence of income and bills, and flag overdraft or failed-payment risk if the booked balance looks tight. (b) needless cost: duplicates (same name, same amount, days apart), recurring charges that look forgotten or are new, a merchant whose amount stepped up, avoidable currency or card fees. (c) changed without asking: a regular debit rose, a regular credit shrank or missed, a new regular payment appeared. For each: amount at stake per month or per year, urgency (cash-tight first), confidence (low when names are vague or the history is short).
5. Output at most three findings, most expensive or most urgent first, and say in one line if you dropped others. Each finding: one sentence of fact, the amount, the confidence, then one concrete action (cancel, query this charge, top up before a date, connect the account a bill suggests). Give an estimated monthly or yearly saving when the finding is a cost; for running short, give a date instead. If nothing is worth doing, say so in one line and ask one useful question.
6. Offer, not perform: subscription-audit for the full recurring table, unusual-transactions if I suspect something is wrong beyond these three, build-budget if I want a plan.

${accountsContext()}`,
      ),
  );

  server.registerPrompt(
    "monthly-summary",
    {
      title: "Monthly summary",
      description: "Income, spending by category and the biggest items for one month, across all accounts.",
      argsSchema: { month: z.string().optional().describe("YYYY-MM, default last full month") },
    },
    ({ month }) =>
      text(
        `Give me a monthly financial summary for ${month ?? "the last full calendar month"}.

Steps:
1. Call list_accounts. Skip loan and mortgage accounts for spending; note their balance separately.
2. For every current account call get_transactions for the month (from the 1st to the last day). Follow continuation keys until you have everything.
3. Identify transfers between my own accounts: same amount, opposite sign, within two days, across two of my accounts. Exclude both legs from income and spending.
4. Categorise the rest. If a categorisation skill or rules file is available, use it; otherwise use sensible categories (housing, groceries, transport, eating out, subscriptions, shopping, health, kids, travel, income, other).
5. Present: total income, total spending, net, savings rate; a table of spending by category with the share of total; the ten largest single expenses; recurring items you noticed. Amounts in the account currency, no decimals.
6. Close with two or three observations worth acting on. Be concrete and short.

${accountsContext()}`,
      ),
  );

  server.registerPrompt(
    "subscription-audit",
    {
      title: "Subscription audit",
      description: "Find recurring charges, their yearly cost, price increases and anything new.",
      argsSchema: { months: z.string().optional().describe("How many months to look back, default 6") },
    },
    ({ months }) =>
      text(
        `Audit my recurring charges over the last ${months ?? "6"} months.

1. Call list_accounts, then get_transactions for each current account over the whole period (follow continuation keys).
2. Find debits that repeat with a regular cadence (monthly, quarterly, yearly) from the same counterparty or with the same description. Card payments to the same merchant with slightly varying amounts still count.
3. For each: name, cadence, latest amount, yearly cost, first seen, and whether the amount went up during the period.
4. Flag: subscriptions that started in the last two months, price increases, duplicates (same service charged twice), and anything that looks unused or forgotten.
5. Present a table sorted by yearly cost, the total per year, and a short list of candidates to cancel with the yearly saving for each.

${accountsContext()}`,
      ),
  );

  server.registerPrompt(
    "unusual-transactions",
    {
      title: "Unusual transactions",
      description: "Large, duplicated or first-time transactions in a recent window compared to the months before.",
      argsSchema: { days: z.string().optional().describe("Window in days, default 30") },
    },
    ({ days }) =>
      text(
        `Look for unusual transactions in the last ${days ?? "30"} days.

1. Call list_accounts, then for each current account get_transactions for the last ${days ?? "30"} days and, for comparison, the 90 days before that.
2. Report: single debits far larger than that counterparty's usual amount or than my typical spending; possible duplicate charges (same counterparty, same amount, within three days); counterparties that never appeared in the comparison period; incoming payments that are not salary or transfers from my own accounts; pending transactions older than a week.
3. For every item give date, account, counterparty, amount and a one-line reason it stood out. Skip anything that is clearly normal. If nothing is unusual, say so in one sentence.

${accountsContext()}`,
      ),
  );
  server.registerPrompt(
    "build-budget",
    {
      title: "Build a budget",
      description: "Turn the last months of real spending into a monthly budget per category, with a savings target and the levers that get there.",
      argsSchema: {
        months: z.string().optional().describe("Months of history to base it on, default 3"),
        savings_target: z.string().optional().describe("Amount or percentage of income to save each month, optional"),
      },
    },
    ({ months, savings_target }) =>
      text(
        `Build me a monthly budget from my real spending over the last ${months ?? "3"} full months${savings_target ? `, aiming to save ${savings_target} per month` : ""}.

1. Call list_accounts. Use the current accounts; note loans and mortgages separately.
2. Call get_transactions for each current account over the whole period (follow continuation keys). Exclude transfers between my own accounts (same amount, opposite sign, within two days, across two of my accounts).
3. Work out monthly income (salary and other regular credits) and categorise spending. Use a categorisation skill or rules file if one is available; otherwise sensible categories (housing, utilities, groceries, eating out, transport, subscriptions, shopping, health, kids, travel, insurance, other).
4. For each category give the monthly average and the range, and mark it fixed (rent, mortgage, insurance, subscriptions) or variable. Add a monthly reserve for bills that come quarterly or yearly.
5. Propose the budget: fixed items at their actual level, variable items at a realistic target, and show what the total leaves for saving against income. If a savings target was given and the numbers do not reach it, say which two or three variable categories would have to move, and by how much.
6. Present it as one table (category, average, proposed budget, fixed or variable), then the totals: income, budget, saving per month. Whole numbers in the account currency.
7. Offer two follow-ups: create_watch on the everyday account with a balance floor, and turning the budget into an artifact page that I can check against each month.

${accountsContext()}`,
      ),
  );
}
