// ----------------------------------------------------------------------

function path(root: string, sublink: string) {
  return `${root}${sublink}`;
}

// ----------------------------------------------------------------------

const ROOTS = {
  AUTH: '/auth',
  DASHBOARD: '/dashboard',
};

// ----------------------------------------------------------------------

export const paths = {
  // AUTH
  auth: {
    root: ROOTS.AUTH,
    login: path(ROOTS.AUTH, '/login'),
    register: path(ROOTS.AUTH, '/register'),
    verify: path(ROOTS.AUTH, '/verify'),
    resetPassword: path(ROOTS.AUTH, '/reset-password'),
    newPassword: path(ROOTS.AUTH, '/new-password'),
  },
  // DASHBOARD
  dashboard: {
    root: ROOTS.DASHBOARD,
    user: {
      root: path(ROOTS.DASHBOARD, '/user'),
      account: path(ROOTS.DASHBOARD, '/user/account'),
      list: path(ROOTS.DASHBOARD, '/user/list'),
      new: path(ROOTS.DASHBOARD, '/user/new'),
      edit: (id: string) => path(ROOTS.DASHBOARD, `/user/${id}/edit`),
    },
    product: {
      root: path(ROOTS.DASHBOARD, '/product'),
      list: path(ROOTS.DASHBOARD, '/product/list'),
      new: path(ROOTS.DASHBOARD, '/product/new'),
      details: (id: string) => path(ROOTS.DASHBOARD, `/product/${id}`),
      edit: (id: string) => path(ROOTS.DASHBOARD, `/product/${id}/edit`),
    },
    invoice: {
      root: path(ROOTS.DASHBOARD, '/invoice'),
      list: path(ROOTS.DASHBOARD, '/invoice/list'),
      new: path(ROOTS.DASHBOARD, '/invoice/new'),
      details: (id: string) => path(ROOTS.DASHBOARD, `/invoice/${id}`),
      edit: (id: string) => path(ROOTS.DASHBOARD, `/invoice/${id}/edit`),
    },
    // New MCA application routes
    application: {
      root: path(ROOTS.DASHBOARD, '/application'),
      list: path(ROOTS.DASHBOARD, '/application/list'),
      details: (id: string) => path(ROOTS.DASHBOARD, `/application/${id}`),
    },
    // New webhook configuration route
    webhookConfig: path(ROOTS.DASHBOARD, '/webhook-config'),
  },
};

// ----------------------------------------------------------------------

export const MOCK_ID = '8c6d1110-5bd2-11ec-bf63-0242ac130002';

export const DEMO = {
  auth: {
    login: paths.auth.login,
    register: paths.auth.register,
  },
  dashboard: {
    user: {
      account: paths.dashboard.user.account,
      list: paths.dashboard.user.list,
      new: paths.dashboard.user.new,
      edit: paths.dashboard.user.edit(MOCK_ID),
    },
    product: {
      list: paths.dashboard.product.list,
      new: paths.dashboard.product.new,
      details: paths.dashboard.product.details(MOCK_ID),
      edit: paths.dashboard.product.edit(MOCK_ID),
    },
    invoice: {
      list: paths.dashboard.invoice.list,
      new: paths.dashboard.invoice.new,
      details: paths.dashboard.invoice.details(MOCK_ID),
      edit: paths.dashboard.invoice.edit(MOCK_ID),
    },
    // New MCA application demo routes
    application: {
      list: paths.dashboard.application.list,
      details: paths.dashboard.application.details(MOCK_ID),
    },
    // New webhook configuration demo route
    webhookConfig: paths.dashboard.webhookConfig,
  },
};