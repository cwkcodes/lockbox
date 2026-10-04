import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  const token = process.env.ADMIN_TOKEN;
  const body = await req.json().catch(() => ({}));
  if (!token || (process.env.NODE_ENV === "production" && token === "change-me")) return NextResponse.json({ error: "admin is disabled until ADMIN_TOKEN is set" }, { status: 403 });
  if (typeof body.token !== "string" || body.token.length !== token.length || body.token !== token) return NextResponse.json({ error: "invalid token" }, { status: 401 });
  const res = NextResponse.json({ ok: true });
  res.cookies.set("atlas_admin", token, { httpOnly: true, sameSite: "strict", secure: process.env.NODE_ENV === "production", path: "/", maxAge: 8 * 3600 });
  return res;
}
