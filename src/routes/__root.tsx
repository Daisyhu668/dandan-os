import { Outlet, createRootRoute, HeadContent, Scripts } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import '../styles/base.css'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
      { name: 'theme-color', content: '#509ffa' },
      { name: 'description', content: 'Dandan OS — 胡晓丹的金融、AI、旅行与生活。' },
      { name: 'robots', content: 'noindex, nofollow' },
      { title: 'Dandan / OS · 金融、AI 和念念远山' },
    ],
    links: [{ rel: 'icon', href: '/assets/favicon.svg', type: 'image/svg+xml' }],
  }),
  component: () => <Document><Outlet /></Document>,
})
function Document({children}: {children: ReactNode}) {
  return <html lang="zh-CN"><head><HeadContent /></head><body>{children}<Scripts /></body></html>
}
