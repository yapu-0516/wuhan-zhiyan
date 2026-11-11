import { computed, ref } from 'vue'
import { getSupportAccounts } from '@/api/support'
import type { OperatorAccount } from '@/types/support'

const STORAGE_KEY = 'cityeye.operator.id'
const accounts = ref<OperatorAccount[]>([])
const loading = ref(false)
const loaded = ref(false)
const currentId = ref(
  typeof window !== 'undefined' && window.localStorage
    ? window.localStorage.getItem(STORAGE_KEY) || 'A0001'
    : 'A0001'
)

async function load(force = false) {
  if (loading.value || (loaded.value && !force)) return accounts.value
  loading.value = true
  try {
    accounts.value = await getSupportAccounts()
    if (!accounts.value.some((item) => item.id === currentId.value)) {
      currentId.value = accounts.value.find((item) => item.status === 'active')?.id ?? ''
    }
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, currentId.value)
    }
    loaded.value = true
    return accounts.value
  } finally {
    loading.value = false
  }
}

function setCurrent(id: string) {
  currentId.value = id
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.setItem(STORAGE_KEY, id)
  }
}

export function useOperator() {
  const current = computed(
    () => accounts.value.find((item) => item.id === currentId.value) ?? accounts.value[0] ?? null
  )
  const currentName = computed(() => current.value?.name ?? '演示操作员')
  const currentRole = computed(() => current.value?.role ?? '')
  return {
    accounts,
    loading,
    loaded,
    currentId,
    current,
    currentName,
    currentRole,
    load,
    setCurrent
  }
}
