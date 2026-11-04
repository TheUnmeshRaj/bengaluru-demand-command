import { NextResponse } from "next/server";

export async function GET() {
  try {
    const response = await fetch("http://streaming:8000/state", {
      cache: "no-store",
    });
    if (!response.ok) {
      return NextResponse.json({ status: "offline" }, { status: 503 });
    }
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ status: "offline" }, { status: 503 });
  }
}
