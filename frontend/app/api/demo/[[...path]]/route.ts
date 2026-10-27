import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const { path = [] } = await context.params;
  const suffix = path.join("/");
  if (!/^runs(?:\/[a-f0-9]{32}(?:\/(?:approve|cancel))?)?$/.test(suffix)) {
    return NextResponse.json({ detail: "Unknown demo endpoint" }, { status: 404 });
  }
  if (request.method === "POST") {
    const origin = request.headers.get("origin");
    if (origin && origin !== request.nextUrl.origin) {
      return NextResponse.json({ detail: "Origin rejected" }, { status: 403 });
    }
  }
  const body = request.method === "POST" ? await request.text() : undefined;
  if (body && body.length > 4096) return new NextResponse(null, { status: 413 });
  try {
    const upstream = await fetch(
      (process.env.REPOPILOT_BACKEND || "http://127.0.0.1:8000") + "/api/demo/" + suffix,
      { method: request.method, body, headers: { "Content-Type": "application/json" },
        cache: "no-store", signal: AbortSignal.timeout(10000), redirect: "error" },
    );
    return new NextResponse(await upstream.text(), {
      status: upstream.status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Local engine is unavailable. Start the backend or inspect the recorded replay." }, { status: 503 });
  }
}
export { proxy as GET, proxy as POST };
