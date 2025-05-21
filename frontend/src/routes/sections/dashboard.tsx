import { lazy, Suspense } from 'react';
import { Outlet, Navigate, useRoutes } from 'react-router-dom';

// guards
import AuthGuard from '../../auth/guard/auth-guard';

// config
import { paths } from '../paths';

// components
const SuspenseOutlet = () => (
  <Suspense fallback={<div>Loading...</div>}>
    <Outlet />
  </Suspense>
);

// ----------------------------------------------------------------------

// DASHBOARD
const DashboardLayout = lazy(() => import('../../layouts/dashboard'));
const IndexPage = lazy(() => import('../../pages/dashboard/app'));
const UserProfilePage = lazy(() => import('../../pages/dashboard/user/profile'));
const UserCardsPage = lazy(() => import('../../pages/dashboard/user/cards'));
const UserListPage = lazy(() => import('../../pages/dashboard/user/list'));
const UserAccountPage = lazy(() => import('../../pages/dashboard/user/account'));
const UserCreatePage = lazy(() => import('../../pages/dashboard/user/create'));
const UserEditPage = lazy(() => import('../../pages/dashboard/user/edit'));

// PRODUCT
const ProductListPage = lazy(() => import('../../pages/dashboard/product/list'));
const ProductDetailsPage = lazy(() => import('../../pages/dashboard/product/details'));
const ProductCreatePage = lazy(() => import('../../pages/dashboard/product/create'));
const ProductEditPage = lazy(() => import('../../pages/dashboard/product/edit'));

// INVOICE
const InvoiceListPage = lazy(() => import('../../pages/dashboard/invoice/list'));
const InvoiceDetailsPage = lazy(() => import('../../pages/dashboard/invoice/details'));
const InvoiceCreatePage = lazy(() => import('../../pages/dashboard/invoice/create'));
const InvoiceEditPage = lazy(() => import('../../pages/dashboard/invoice/edit'));

// MCA APPLICATION
const ApplicationListPage = lazy(() => import('../../pages/dashboard/application/list'));
const ApplicationDetailPage = lazy(() => import('../../pages/dashboard/application/details'));
const ApplicationCreatePage = lazy(() => import('../../pages/dashboard/application/create'));

// WEBHOOK CONFIG
const WebhookConfigPage = lazy(() => import('../../pages/dashboard/webhook-config'));

// ----------------------------------------------------------------------

export default function DashboardRoutes() {
  return useRoutes([
    {
      path: 'dashboard',
      element: (
        <AuthGuard>
          <DashboardLayout>
            <SuspenseOutlet />
          </DashboardLayout>
        </AuthGuard>
      ),
      children: [
        { element: <Navigate to={paths.dashboard.root} replace />, index: true },
        { path: 'app', element: <IndexPage /> },
        {
          path: 'user',
          children: [
            { element: <Navigate to={paths.dashboard.user.root} replace />, index: true },
            { path: 'profile', element: <UserProfilePage /> },
            { path: 'cards', element: <UserCardsPage /> },
            { path: 'list', element: <UserListPage /> },
            { path: 'new', element: <UserCreatePage /> },
            { path: 'account', element: <UserAccountPage /> },
            { path: ':id/edit', element: <UserEditPage /> },
          ],
        },
        {
          path: 'product',
          children: [
            { element: <Navigate to={paths.dashboard.product.root} replace />, index: true },
            { path: 'list', element: <ProductListPage /> },
            { path: 'new', element: <ProductCreatePage /> },
            { path: ':id', element: <ProductDetailsPage /> },
            { path: ':id/edit', element: <ProductEditPage /> },
          ],
        },
        {
          path: 'invoice',
          children: [
            { element: <Navigate to={paths.dashboard.invoice.root} replace />, index: true },
            { path: 'list', element: <InvoiceListPage /> },
            { path: 'new', element: <InvoiceCreatePage /> },
            { path: ':id', element: <InvoiceDetailsPage /> },
            { path: ':id/edit', element: <InvoiceEditPage /> },
          ],
        },
        {
          path: 'application',
          children: [
            { element: <Navigate to={paths.dashboard.application.root} replace />, index: true },
            { path: 'list', element: <ApplicationListPage /> },
            { path: 'new', element: <ApplicationCreatePage /> },
            { path: ':id', element: <ApplicationDetailPage /> },
          ],
        },
        { path: 'webhook-config', element: <WebhookConfigPage /> },
      ],
    },
  ]);
}