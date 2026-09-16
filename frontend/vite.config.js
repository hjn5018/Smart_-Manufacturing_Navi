import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  const target = env.PLANNER_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/planner-api': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/planner-api/, ''),
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (env.PLANNER_CONTROL_API_KEY) {
                proxyReq.setHeader('X-Device-Control-Key', env.PLANNER_CONTROL_API_KEY);
              }
            });
          },
        },
      },
    },
  };
});
