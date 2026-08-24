function createStorage() {
  const store = new Map<string, string>()
  return {
    get length() {
      return store.size
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null
    },
    getItem(key: string) {
      return store.get(String(key)) ?? null
    },
    setItem(key: string, value: string) {
      store.set(String(key), String(value))
    },
    removeItem(key: string) {
      store.delete(String(key))
    },
    clear() {
      store.clear()
    },
  }
}

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: createStorage(),
})
