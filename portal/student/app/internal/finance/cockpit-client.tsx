"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  CockpitStatusPayload,
  HeroPayload,
  DecisionsPayload,
  TabPayload,
  DrillEntry,
} from "./lib/types"
import { fetchTab, fetchDrill } from "./lib/api"
import { Topbar } from "./components/cockpit-shell/topbar"
import { HeroGrid } from "./components/cockpit-shell/hero-grid"
import { DecisionsList } from "./components/cockpit-shell/decisions-list"
import { TabsBar, type TabDef } from "./components/cockpit-shell/tabs-bar"
import { DrillPanel } from "./components/cockpit-shell/drill-panel"
import { ChatPanel } from "./components/cockpit-shell/chat-panel"
import { ActivityFeed } from "./components/cockpit-shell/activity-feed"
import { TabContent, TabLoading, TabError } from "./components/tabs/tab-content"

interface InitialState {
  status: CockpitStatusPayload
  hero: HeroPayload
  decisions: DecisionsPayload
}

export function CockpitClient({ initial }: { initial: InitialState }) {
  const [activeTab, setActiveTab] = useState<string>("budget")

  // Lazy-fetched tab content. Keyed by tab id; undefined = not requested.
  const [tabCache, setTabCache] = useState<Record<string, TabPayload>>({})
  const [tabLoading, setTabLoading] = useState<Record<string, boolean>>({})
  const [tabError, setTabError] = useState<Record<string, string | null>>({})

  // Lazy-fetched drill content.
  const [activeDrillKey, setActiveDrillKey] = useState<string | null>(null)
  const [drillCache, setDrillCache] = useState<Record<string, DrillEntry>>({})
  const [drillLoading, setDrillLoading] = useState(false)
  const [drillError, setDrillError] = useState<string | null>(null)

  const counts = initial.status.tab_counts
  const tabs: TabDef[] = useMemo(() => [
    { id: "budget", label: "Budget & Burn" },
    { id: "placements", label: "Placements" },
    { id: "providers", label: "Providers", count: counts.providers },
    { id: "transactions", label: "Transactions", count: counts.transactions },
    { id: "reporting", label: "ESD Reporting", count: counts.reporting },
    { id: "audit", label: "Audit Readiness", count: counts.audit },
  ], [counts])

  const loadTab = useCallback(async (tabId: string) => {
    if (tabCache[tabId] || tabLoading[tabId]) return
    setTabLoading((s) => ({ ...s, [tabId]: true }))
    setTabError((s) => ({ ...s, [tabId]: null }))
    try {
      const payload = await fetchTab(tabId)
      setTabCache((s) => ({ ...s, [tabId]: payload }))
    } catch (err) {
      setTabError((s) => ({ ...s, [tabId]: String(err) }))
    } finally {
      setTabLoading((s) => ({ ...s, [tabId]: false }))
    }
  }, [tabCache, tabLoading])

  // Kick off the first-tab fetch on mount so the user sees Budget content
  // without an explicit click.
  useEffect(() => {
    void loadTab(activeTab)
  }, [activeTab, loadTab])

  const openDrill = useCallback(async (key: string) => {
    setActiveDrillKey(key)
    if (drillCache[key]) return
    setDrillLoading(true)
    setDrillError(null)
    try {
      const entry = await fetchDrill(key)
      setDrillCache((s) => ({ ...s, [key]: entry }))
    } catch (err) {
      setDrillError(String(err))
    } finally {
      setDrillLoading(false)
    }
  }, [drillCache])

  const closeDrill = useCallback(() => {
    setActiveDrillKey(null)
    setDrillError(null)
  }, [])

  const activeTabLabel = tabs.find((t) => t.id === activeTab)?.label ?? activeTab

  const tabPayload = tabCache[activeTab]
  const tabFetchError = tabError[activeTab]

  const activeDrill: DrillEntry | null = activeDrillKey ? drillCache[activeDrillKey] ?? null : null

  return (
    <>
      <div className="cockpit-app">
        <div className="cockpit-main">
          <Topbar today={initial.status.as_of} />
          <HeroGrid
            status={initial.status}
            hero={initial.hero}
            onOpen={openDrill}
          />
          <DecisionsList decisions={initial.decisions} onOpen={openDrill} />
          <TabsBar tabs={tabs} activeId={activeTab} onChange={setActiveTab} />
          {tabFetchError ? (
            <TabError tabId={activeTab} error={tabFetchError} onRetry={() => loadTab(activeTab)} />
          ) : tabPayload ? (
            <TabContent payload={tabPayload} onOpen={openDrill} />
          ) : (
            <TabLoading tabId={activeTab} />
          )}
          <ActivityFeed />
        </div>
        <ChatPanel activeTab={activeTabLabel} />
      </div>
      <DrillPanel
        entry={activeDrill}
        loading={drillLoading && !activeDrill}
        error={drillError}
        onClose={closeDrill}
      />
    </>
  )
}
