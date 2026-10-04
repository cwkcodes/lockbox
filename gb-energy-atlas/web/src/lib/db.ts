import { Pool, types, type QueryResultRow } from "pg";

// numeric (1700) and bigint (20) arrive as strings by default; every numeric in this schema fits a double.
types.setTypeParser(1700, (v) => parseFloat(v));
types.setTypeParser(20, (v) => parseInt(v, 10));
types.setTypeParser(1082, (v) => v); // keep DATE as plain YYYY-MM-DD (no timezone shifts)

const globalForPg = globalThis as unknown as { __atlasPool?: Pool };

export const pool: Pool =
  globalForPg.__atlasPool ??
  new Pool({
    connectionString: process.env.DATABASE_URL ?? "postgresql://atlas:atlas_dev@127.0.0.1:5432/atlas",
    max: 10,
    idleTimeoutMillis: 30_000,
    statement_timeout: 20_000,
  });
if (process.env.NODE_ENV !== "production") globalForPg.__atlasPool = pool;

export async function query<T extends QueryResultRow = QueryResultRow>(text: string, params: unknown[] = []): Promise<T[]> {
  const res = await pool.query<T>(text, params as never[]);
  return res.rows;
}

export async function queryOne<T extends QueryResultRow = QueryResultRow>(text: string, params: unknown[] = []): Promise<T | null> {
  const rows = await query<T>(text, params);
  return rows[0] ?? null;
}
