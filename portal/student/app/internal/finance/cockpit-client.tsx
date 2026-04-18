"use client"

import { useMemo, useState } from "react"
import type { CockpitFixture, DrillEntry } from "./lib/types"
import { Topbar } from "./components/cockpit-shell/topbar"
import { HeroGrid } from "./components/cockpit-shell/hero-grid"
import { DecisionsList } from "./components/cockpit-shell/decisions-list"
import { TabsBar, type TabDef } from "./components/cockpit-shell/tabs-bar"
import { DrillPanel } from "./components/cockpit-shell/drill-panel"
import { ChatPanel } from "./components/cockpit-shell/chat-panel"
import { ActivityFeed } from "./components/cockpit-shell/activity-feed"
import { TabContent } from "./components/tabs/tab-content"

export function CockpitClient({ data }: { data: CockpitFixture }) {
  const [activeTab, setActiveTab] = useState<string>("budget")
  const [activeDrillKey, setActiveDrillKey] = useState<string | null>(null)

  const tabs: TabDef[] = useMemo(
    () => [
      { id: "budget", label: "Budget & Burn" },
      { id: "placements", label: "Placements" },
      { id: "providers", label: "Providers", count: data.providers.active.length },
      { id: "transactions", label: "Transactions", count: 53 },
      { id: "reporting", label: "ESD Reporting", count: 2 },
      { id: "audit", label: "Audit Readiness" },
    ],
    [data.providers.active.length],
  )

  const activeDrill: DrillEntry | null = activeDrillKey
    ? (data.drills[activeDrillKey] ?? null)
    : null

  function openDrill(key: string) {
    if (!data.drills[key]) {
      // Surface broken drill keys in the console exactly the way the
      // HTML cockpit's openDrill() does. Validation runs on the Python
      // side at build time so this branch should never fire — but keep
      // the warn for parity.
      console.warn("No drill content for:", key)
      return
    }
    setActiveDrillKey(key)
  }
  function closeDrill() {
    setActiveDrillKey(null)
  }

  const activeTabLabel = tabs.find((t) => t.id === activeTab)?.label ?? activeTab

  return (
    <div className="cockpit-surface">
      <div className="cockpit-app">
        <div className="cockpit-main">
          <Topbar today={data.summary.today} />
          <HeroGrid data={data} onOpen={openDrill} />
          <DecisionsList items={data.action_items} onOpen={openDrill} />
          <TabsBar tabs={tabs} activeId={activeTab} onChange={setActiveTab} />
          <TabContent tab={activeTab} data={data} onOpen={openDrill} />
          <ActivityFeed />
        </div>
        <ChatPanel activeTab={activeTabLabel} />
      </div>
      <DrillPanel entry={activeDrill} onClose={closeDrill} />
    </div>
  )
}
