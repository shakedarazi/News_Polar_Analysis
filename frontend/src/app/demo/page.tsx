"use client";

import { useEffect, useState } from "react";
import { DemoDashboard } from "@/components/demo/DemoDashboard";
import "./demo.css";

/**
 * Kiosk wall screen: 5 AI agents collaborating live (16:9, fullscreen).
 * Renders as a fixed full-viewport layer above the app chrome — the demo
 * layer intentionally does not reuse the site's shell/nav.
 *
 * ?mock=1 forces the scripted mock stream (no backend needed).
 */
export default function DemoPage() {
  // read the query string on the client only (avoids a Suspense boundary
  // for useSearchParams during prerender)
  const [forceMock, setForceMock] = useState<boolean | null>(null);
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setForceMock(params.get("mock") === "1");
  }, []);

  if (forceMock === null) {
    return <div className="demo-kiosk" aria-hidden />;
  }
  return <DemoDashboard forceMock={forceMock} />;
}
