import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api } from '../api/client'
import type { FeedPayload, ProjectRecord, ReportRecord, SimulationRecord, TaskRecord } from '../types'

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

export const useWorkspaceStore = defineStore('workspace', () => {
  const projects = ref<ProjectRecord[]>([])
  const currentProject = ref<ProjectRecord | null>(null)
  const currentSimulation = ref<SimulationRecord | null>(null)
  const currentFeed = ref<FeedPayload | null>(null)
  const currentReport = ref<ReportRecord | null>(null)
  const tasks = ref<Record<string, TaskRecord>>({})
  const loading = ref(false)

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  async function loadProject(projectId: string) {
    currentProject.value = await api.getProject(projectId)
    return currentProject.value
  }

  async function loadSimulation(simulationId: string) {
    currentSimulation.value = await api.getSimulation(simulationId)
    return currentSimulation.value
  }

  async function loadFeed(simulationId: string) {
    currentFeed.value = await api.getFeed(simulationId)
    return currentFeed.value
  }

  async function loadReport(reportId: string) {
    currentReport.value = await api.getReport(reportId)
    return currentReport.value
  }

  async function trackTask(taskId: string, onTick?: () => Promise<void>) {
    while (true) {
      const task = await api.getTask(taskId)
      tasks.value[taskId] = task
      if (onTick) {
        await onTick()
      }
      if (task.status === 'completed' || task.status === 'failed') {
        return task
      }
      await sleep(2000)
    }
  }

  return {
    projects,
    currentProject,
    currentSimulation,
    currentFeed,
    currentReport,
    tasks,
    loading,
    loadProjects,
    loadProject,
    loadSimulation,
    loadFeed,
    loadReport,
    trackTask,
  }
})
