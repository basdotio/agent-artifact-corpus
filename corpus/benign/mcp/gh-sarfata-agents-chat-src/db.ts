import Database from "better-sqlite3";
import { dirname } from "node:path";
import { mkdirSync } from "node:fs";

export type Db = Database.Database;

export function openDb(databaseUrl: string): Db {
  const path = databaseUrl.startsWith("file:") ? databaseUrl.slice(5) : databaseUrl;
  if (path !== ":memory:") mkdirSync(dirname(path), { recursive: true });
  const db = new Database(path);
  db.pragma("journal_mode = WAL");
  db.pragma("foreign_keys = ON");
  db.exec(`
    create table if not exists channels (
      id text primary key,
      name text not null unique collate nocase,
      created_by text not null,
      created_at text not null
    );
    create table if not exists memberships (
      channel_id text not null references channels(id) on delete cascade,
      agent_id text not null,
      agent_name text not null,
      joined_at text not null,
      primary key (channel_id, agent_id)
    );
    create table if not exists messages (
      id integer primary key autoincrement,
      channel_id text not null references channels(id) on delete cascade,
      agent_id text not null,
      agent_name text not null,
      text text not null check(length(text) between 1 and 200),
      created_at text not null
    );
    create table if not exists chat_events (
      id integer primary key autoincrement,
      event_id text not null unique,
      channel_id text not null references channels(id) on delete cascade,
      kind text not null check(kind in ('channel.created', 'member.joined', 'message.posted')),
      data_json text not null,
      occurred_at text not null
    );
    create table if not exists event_recipients (
      event_row_id integer not null references chat_events(id) on delete cascade,
      agent_id text not null,
      primary key (event_row_id, agent_id)
    );
    create index if not exists event_recipients_agent_event_idx on event_recipients(agent_id, event_row_id);

    create table if not exists chat_rate_limits (
      principal_id text not null,
      bucket text not null,
      arrival_ms integer not null,
      primary key (principal_id, bucket)
    );

    create table if not exists users (
      id text primary key,
      provider text not null,
      provider_subject text not null,
      display_name text not null,
      created_at text not null,
      updated_at text not null,
      unique(provider, provider_subject)
    );
    create table if not exists oauth_clients (
      client_id text primary key,
      client_name text not null,
      redirect_uris_json text not null,
      application_type text not null,
      created_at text not null
    );
    create table if not exists oauth_transactions (
      id text primary key,
      client_id text not null references oauth_clients(client_id) on delete cascade,
      redirect_uri text not null,
      code_challenge text not null,
      resource text not null,
      scope text not null,
      client_state text not null,
      user_id text references users(id) on delete cascade,
      approval_hash text,
      expires_at text not null,
      created_at text not null
    );
    create table if not exists oauth_codes (
      code_hash text primary key,
      user_id text not null references users(id) on delete cascade,
      client_id text not null references oauth_clients(client_id) on delete cascade,
      redirect_uri text not null,
      code_challenge text not null,
      resource text not null,
      scope text not null,
      expires_at text not null,
      used_at text
    );
    create table if not exists oauth_access_tokens (
      token_hash text primary key,
      user_id text not null references users(id) on delete cascade,
      client_id text not null references oauth_clients(client_id) on delete cascade,
      resource text not null,
      scope text not null,
      expires_at text not null,
      created_at text not null,
      last_used_at text
    );
    create table if not exists oauth_refresh_tokens (
      token_hash text primary key,
      family_id text not null,
      user_id text not null references users(id) on delete cascade,
      client_id text not null references oauth_clients(client_id) on delete cascade,
      resource text not null,
      scope text not null,
      expires_at text not null,
      created_at text not null,
      revoked_at text
    );
    create index if not exists oauth_access_tokens_expiry_idx on oauth_access_tokens(expires_at);
    create index if not exists oauth_refresh_tokens_family_idx on oauth_refresh_tokens(family_id);
    create index if not exists oauth_transactions_expiry_idx on oauth_transactions(expires_at);
  `);
  return db;
}
