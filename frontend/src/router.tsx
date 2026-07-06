/**
 * Code-based route tree: root layout with a homepage and a video page.
 */

import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from '@tanstack/react-router'
import { AppLayout } from '@/components/app-layout'
import { HomePage } from '@/pages/home-page'
import { VideoPage } from '@/pages/video-page'

const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

// Layout route wraps every page with the shared sidebar + header.
const layoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'layout',
  component: AppLayout,
})

const homeRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/',
  component: HomePage,
})

const videoRoute = createRoute({
  getParentRoute: () => layoutRoute,
  path: '/video/$id',
  component: VideoPage,
})

const routeTree = rootRoute.addChildren([
  layoutRoute.addChildren([homeRoute, videoRoute]),
])

export const router = createRouter({ routeTree })

// Register the router instance for full type-safety across the app.
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
