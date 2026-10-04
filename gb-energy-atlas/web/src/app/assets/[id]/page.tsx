"use client";
import { use, useState } from "react";
import { Page } from "@/components/SiteHeader";
import AssetDetail from "@/components/AssetDetail";
import { ReportDialog } from "@/components/AtlasApp";
import { useJson } from "@/components/ui";
import type { Meta } from "@/lib/types";

export default function AssetPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: meta } = useJson<Meta>("/api/meta");
  const [tab, setTab] = useState("overview");
  const [report, setReport] = useState(false);
  return (
    <Page title="Asset" current="/assets" wide>
      <div className="panel" style={{ maxWidth: 1000 }}>
        <AssetDetail id={id} meta={meta} tab={tab} onTab={setTab} variant="page" onZoom={(lon, lat) => { window.location.href = `/?v=${lat},${lon},14&sel=${id}`; }} onReport={() => setReport(true)} />
      </div>
      <p><a href={`/?sel=${id}&d=1`}>← Show on the map</a></p>
      {report && <ReportDialog assetId={id} onClose={() => setReport(false)} />}
    </Page>
  );
}
