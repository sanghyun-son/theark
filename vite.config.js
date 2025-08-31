import { defineConfig } from 'vite';

export default defineConfig({
  // The project root is now the server root.
  // Access the app at http://localhost:xxxx/templates/
  build: {
    outDir: 'static/dist', // Output bundled files to 'static/dist'
    sourcemap: true,
    rollupOptions: {
      input: {
        main: 'templates/index.html'
      }
    }
  },
  server: {
    proxy: {
      // Proxy API requests to the backend
      '/v1': 'http://127.0.0.1:8000'
    }
  }
});
