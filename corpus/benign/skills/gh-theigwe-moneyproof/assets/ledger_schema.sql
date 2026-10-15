-- Starter double-entry, append-only ledger for PostgreSQL 13+.
-- Adapt names to your domain; keep the invariants.

CREATE TABLE currencies (
  code        CHAR(3) PRIMARY KEY,           -- ISO-4217
  minor_units SMALLINT NOT NULL CHECK (minor_units BETWEEN 0 AND 18)
);
INSERT INTO currencies VALUES ('NGN',2),('USD',2),('GHS',2),('KES',2),('JPY',0),('KWD',3);

CREATE TABLE ledger_accounts (
  id             BIGSERIAL PRIMARY KEY,
  code           TEXT NOT NULL UNIQUE,       -- e.g. 'merchant:123:available:NGN'
  owner_type     TEXT NOT NULL,              -- merchant | customer | platform | psp | bank
  owner_id       TEXT,
  purpose        TEXT NOT NULL,              -- available | pending | held | receivable | fees ...
  currency       CHAR(3) NOT NULL REFERENCES currencies(code),
  normal_balance TEXT NOT NULL CHECK (normal_balance IN ('debit','credit')),
  allow_negative BOOLEAN NOT NULL DEFAULT false,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ledger_transactions (
  id                      BIGSERIAL PRIMARY KEY,
  idempotency_key         TEXT NOT NULL UNIQUE,   -- e.g. 'capture:att_123'
  event_type              TEXT NOT NULL,          -- capture | refund | payout | fee | reversal ...
  reference_type          TEXT NOT NULL,          -- payment_attempt | refund | payout ...
  reference_id            TEXT NOT NULL,
  reverses_transaction_id BIGINT REFERENCES ledger_transactions(id),
  description             TEXT,
  actor                   TEXT NOT NULL,          -- user:42 | service:payouts | webhook:paystack
  correlation_id          TEXT,
  effective_at            TIMESTAMPTZ NOT NULL,   -- business time
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now()  -- system time
);

CREATE TABLE ledger_entries (
  id             BIGSERIAL PRIMARY KEY,
  transaction_id BIGINT NOT NULL REFERENCES ledger_transactions(id),
  account_id     BIGINT NOT NULL REFERENCES ledger_accounts(id),
  direction      TEXT   NOT NULL CHECK (direction IN ('debit','credit')),
  amount_minor   BIGINT NOT NULL CHECK (amount_minor > 0),
  currency       CHAR(3) NOT NULL REFERENCES currencies(code),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON ledger_entries (account_id, id);
CREATE INDEX ON ledger_entries (transaction_id);

-- Cached balance, maintained in the same transaction as entries.
-- balance_minor is signed in the account's normal direction.
CREATE TABLE account_balances (
  account_id    BIGINT PRIMARY KEY REFERENCES ledger_accounts(id),
  balance_minor BIGINT NOT NULL DEFAULT 0,
  version       BIGINT NOT NULL DEFAULT 0,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Invariant: append-only.
CREATE FUNCTION forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION '% on % is forbidden: ledger is append-only', TG_OP, TG_TABLE_NAME;
END $$;
CREATE TRIGGER entries_append_only BEFORE UPDATE OR DELETE ON ledger_entries
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER transactions_append_only BEFORE UPDATE OR DELETE ON ledger_transactions
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER entries_no_truncate BEFORE TRUNCATE ON ledger_entries
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();
CREATE TRIGGER transactions_no_truncate BEFORE TRUNCATE ON ledger_transactions
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();
-- Also: REVOKE UPDATE, DELETE, TRUNCATE ON ledger_entries, ledger_transactions FROM app_role;

-- Invariant: entry currency matches account currency; maintain cached balance.
-- Caveat: the negative-balance check runs per entry, so within one transaction post
-- credits to a non-negative account before debits, or defer the check to commit.
CREATE FUNCTION apply_entry() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE acct ledger_accounts%ROWTYPE; delta BIGINT; new_bal BIGINT;
BEGIN
  SELECT * INTO acct FROM ledger_accounts WHERE id = NEW.account_id;
  IF acct.currency <> NEW.currency THEN
    RAISE EXCEPTION 'currency mismatch: entry % vs account %', NEW.currency, acct.currency;
  END IF;
  delta := CASE WHEN NEW.direction = acct.normal_balance THEN NEW.amount_minor
                ELSE -NEW.amount_minor END;
  INSERT INTO account_balances (account_id) VALUES (NEW.account_id) ON CONFLICT DO NOTHING;
  UPDATE account_balances
     SET balance_minor = balance_minor + delta, version = version + 1, updated_at = now()
   WHERE account_id = NEW.account_id
  RETURNING balance_minor INTO new_bal;              -- row lock serialises concurrent postings
  IF new_bal < 0 AND NOT acct.allow_negative THEN
    RAISE EXCEPTION 'insufficient funds on account % (would be %)', acct.code, new_bal;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER entries_apply BEFORE INSERT ON ledger_entries
  FOR EACH ROW EXECUTE FUNCTION apply_entry();

-- Invariant: every transaction balances per currency, checked at COMMIT.
CREATE FUNCTION check_transaction_balanced() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE bad RECORD;
BEGIN
  SELECT currency,
         SUM(CASE WHEN direction='debit' THEN amount_minor ELSE -amount_minor END) AS net,
         COUNT(*) AS n
    INTO bad
    FROM ledger_entries WHERE transaction_id = NEW.transaction_id
   GROUP BY currency
  HAVING SUM(CASE WHEN direction='debit' THEN amount_minor ELSE -amount_minor END) <> 0
   LIMIT 1;
  IF FOUND THEN
    RAISE EXCEPTION 'ledger transaction % unbalanced in %: net %',
      NEW.transaction_id, bad.currency, bad.net;
  END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER entries_balanced AFTER INSERT ON ledger_entries
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION check_transaction_balanced();

-- Audit query: cached balances must equal ledger-derived balances (expect 0 rows).
CREATE VIEW balance_drift AS
SELECT a.id, a.code, b.balance_minor AS cached,
       COALESCE(SUM(CASE WHEN e.direction = a.normal_balance THEN e.amount_minor
                         ELSE -e.amount_minor END), 0) AS derived
  FROM ledger_accounts a
  LEFT JOIN account_balances b ON b.account_id = a.id
  LEFT JOIN ledger_entries  e ON e.account_id = a.id
 GROUP BY a.id, a.code, b.balance_minor
HAVING COALESCE(b.balance_minor,0) <> COALESCE(SUM(CASE WHEN e.direction = a.normal_balance
                                   THEN e.amount_minor ELSE -e.amount_minor END), 0);
