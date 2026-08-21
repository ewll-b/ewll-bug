const normalizedBasePath = import.meta.env.BASE_URL.replace(/\/$/, '')

export function withAppBase(path: string, basePath = normalizedBasePath) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${basePath}${normalizedPath}` || '/'
}

export function withoutAppBase(pathname: string, basePath = normalizedBasePath) {
  if (!basePath) return pathname || '/'
  if (pathname === basePath) return '/'
  // 登录回跳只保存应用内路径，避免子路径前缀被 Router 再次拼接。
  return pathname.startsWith(`${basePath}/`) ? pathname.slice(basePath.length) : pathname
}
