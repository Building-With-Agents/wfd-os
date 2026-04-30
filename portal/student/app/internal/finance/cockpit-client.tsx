"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import type {
  ActivityPayload,
  CockpitStatusPayload,
  HeroPayload,
  DecisionsPayload,
  TabPayload,
  DrillEntry,
} from "./lib/types"
import { fetchTab, fetchDrill } from "./lib/api"
import { CockpitShell } from "../_shared/cockpit-shell"
import { HeroGrid } from "../_shared/hero/hero-grid"
import { TabsBar, type TabDef } from "../_shared/tabs-bar"
import { DrillPanel } from "../_shared/drill/drill-panel"
import { Topbar } from "./components/cockpit-shell/topbar"
import { DecisionsList } from "./components/cockpit-shell/decisions-list"
import { ActivityFeed } from "./components/cockpit-shell/activity-feed"
import { BroadChat } from "./components/chat/broad-chat"
import { FinanceChatProvider } from "./components/chat/finance-chat-context"
import { TabContent, TabLoading, TabError } from "./components/tabs/tab-content"

interface InitialState {
  status: CockpitStatusPayload
  hero: HeroPayload
  decisions: DecisionsPayload
  activity: ActivityPayload
}

export function CockpitClient({ initial }: { initial: InitialState }) {
  const [activeTab, setActiveTab] = useState<string>("budget")

  const [tabCache, setTabCache] = useState<Record<string, TabPayload>>({})
  const [tabLoading, setTabLoading] = useState<Record<string, boolean>>({})
  const [tabError, setTabError] = useState<Record<string, string | null>>({})

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

  const tabPayload = tabCache[activeTab]
  const tabFetchError = tabError[activeTab]

  const activeDrill: DrillEntry | null = activeDrillKey ? drillCache[activeDrillKey] ?? null : null

  // The four hero cells come straight from the API payload — its shape
  // (drill_key + label/value/subtitle + optional value_suffix /
  // status_chip / live_minutes_ago) is assignable to the shared
  // HeroGridCell contract.
  const heroCells = [
    initial.hero.backbone,
    initial.hero.placements,
    initial.hero.cash,
    initial.hero.flags,
  ]

  return (
    <FinanceChatProvider>
      <CockpitShell
        main={
          <>
            <Topbar today={initial.status.as_of} />
            <div className="cockpit-hero">
              <div className="cockpit-hero-eyebrow">
                Status as of {initial.status.as_of} — {initial.status.months_remaining} months remaining
              </div>
              <h1 className="cockpit-hero-title cockpit-display">Are we okay?</h1>
              <p className="cockpit-hero-subtitle">
                A daily glance at runway, placements, and what needs your attention this week.
              </p>
              <HeroGrid cells={heroCells} onOpen={openDrill} />
            </div>
            <DecisionsList decisions={initial.decisions} onOpen={openDrill} />
            <TabsBar tabs={tabs} activeId={activeTab} onChange={setActiveTab} />
            {tabFetchError ? (
              <TabError tabId={activeTab} error={tabFetchError} onRetry={() => loadTab(activeTab)} />
            ) : tabPayload ? (
              <TabContent payload={tabPayload} onOpen={openDrill} />
            ) : (
              <TabLoading tabId={activeTab} />
            )}
            <ActivityFeed activity={initial.activity} />
          </>
        }
        chat={<BroadChat onOpenDrill={openDrill} />}
      />
      <DrillPanel
        entry={activeDrill}
        loading={drillLoading && !activeDrill}
        error={drillError}
        onClose={closeDrill}
      />
    </FinanceChatProvider>
  )
}
