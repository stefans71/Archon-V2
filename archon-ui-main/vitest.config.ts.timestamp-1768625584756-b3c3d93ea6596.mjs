// vitest.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
var __vite_injected_original_dirname = "/root/archon-remote/archon-ui-main";
var vitest_config_default = defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./tests/setup.ts",
    include: [
      "src/**/*.test.{ts,tsx}",
      // Colocated tests in features
      "src/**/*.spec.{ts,tsx}",
      "tests/**/*.test.{ts,tsx}",
      // Tests in tests directory  
      "tests/**/*.spec.{ts,tsx}",
      "test/components.test.tsx",
      "test/pages.test.tsx",
      "test/user_flows.test.tsx",
      "test/errors.test.tsx",
      "test/services/projectService.test.ts",
      "test/components/project-tasks/DocsTab.integration.test.tsx",
      "test/config/api.test.ts",
      "test/components/settings/OllamaConfigurationPanel.test.tsx",
      "test/components/settings/OllamaInstanceHealthIndicator.test.tsx",
      "test/components/settings/OllamaModelDiscoveryModal.test.tsx"
    ],
    exclude: ["node_modules", "dist", ".git", ".cache", "test.backup", "*.backup/**", "test-backups"],
    reporters: ["dot", "json"],
    outputFile: {
      json: "./public/test-results/test-results.json"
    },
    testTimeout: 1e4,
    // 10 seconds timeout
    hookTimeout: 1e4,
    // 10 seconds for setup/teardown
    coverage: {
      provider: "v8",
      reporter: [
        "text",
        "text-summary",
        "html",
        "json",
        "json-summary",
        "lcov"
      ],
      reportsDirectory: "./public/test-results/coverage",
      clean: false,
      // Don't clean the directory as it may be in use
      reportOnFailure: true,
      // Generate coverage reports even when tests fail
      exclude: [
        "node_modules/",
        "tests/",
        "**/*.d.ts",
        "**/*.config.*",
        "**/mockData.ts",
        "**/*.test.{ts,tsx}",
        "src/env.d.ts",
        "coverage/**",
        "dist/**",
        "public/**",
        "**/*.stories.*",
        "**/*.story.*"
      ],
      include: [
        "src/**/*.{ts,tsx}"
      ],
      thresholds: {}
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src")
    }
  }
});
export {
  vitest_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZXN0LmNvbmZpZy50cyJdLAogICJzb3VyY2VSb290IjogImZpbGU6Ly8vcm9vdC9hcmNob24tcmVtb3RlL2FyY2hvbi11aS1tYWluLyIsCiAgInNvdXJjZXNDb250ZW50IjogWyJjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZGlybmFtZSA9IFwiL3Jvb3QvYXJjaG9uLXJlbW90ZS9hcmNob24tdWktbWFpblwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiL3Jvb3QvYXJjaG9uLXJlbW90ZS9hcmNob24tdWktbWFpbi92aXRlc3QuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9yb290L2FyY2hvbi1yZW1vdGUvYXJjaG9uLXVpLW1haW4vdml0ZXN0LmNvbmZpZy50c1wiOy8vLyA8cmVmZXJlbmNlIHR5cGVzPVwidml0ZXN0XCIgLz5cbmltcG9ydCB7IGRlZmluZUNvbmZpZyB9IGZyb20gJ3ZpdGUnXG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnXG5pbXBvcnQgcGF0aCBmcm9tICdwYXRoJ1xuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbcmVhY3QoKV0sXG4gIHRlc3Q6IHtcbiAgICBnbG9iYWxzOiB0cnVlLFxuICAgIGVudmlyb25tZW50OiAnanNkb20nLFxuICAgIHNldHVwRmlsZXM6ICcuL3Rlc3RzL3NldHVwLnRzJyxcbiAgICBpbmNsdWRlOiBbXG4gICAgICAnc3JjLyoqLyoudGVzdC57dHMsdHN4fScsICAgICAvLyBDb2xvY2F0ZWQgdGVzdHMgaW4gZmVhdHVyZXNcbiAgICAgICdzcmMvKiovKi5zcGVjLnt0cyx0c3h9JyxcbiAgICAgICd0ZXN0cy8qKi8qLnRlc3Que3RzLHRzeH0nLCAgIC8vIFRlc3RzIGluIHRlc3RzIGRpcmVjdG9yeSAgXG4gICAgICAndGVzdHMvKiovKi5zcGVjLnt0cyx0c3h9JyxcbiAgICAgICd0ZXN0L2NvbXBvbmVudHMudGVzdC50c3gnLFxuICAgICAgJ3Rlc3QvcGFnZXMudGVzdC50c3gnLCBcbiAgICAgICd0ZXN0L3VzZXJfZmxvd3MudGVzdC50c3gnLFxuICAgICAgJ3Rlc3QvZXJyb3JzLnRlc3QudHN4JyxcbiAgICAgICd0ZXN0L3NlcnZpY2VzL3Byb2plY3RTZXJ2aWNlLnRlc3QudHMnLFxuICAgICAgJ3Rlc3QvY29tcG9uZW50cy9wcm9qZWN0LXRhc2tzL0RvY3NUYWIuaW50ZWdyYXRpb24udGVzdC50c3gnLFxuICAgICAgJ3Rlc3QvY29uZmlnL2FwaS50ZXN0LnRzJyxcbiAgICAgICd0ZXN0L2NvbXBvbmVudHMvc2V0dGluZ3MvT2xsYW1hQ29uZmlndXJhdGlvblBhbmVsLnRlc3QudHN4JyxcbiAgICAgICd0ZXN0L2NvbXBvbmVudHMvc2V0dGluZ3MvT2xsYW1hSW5zdGFuY2VIZWFsdGhJbmRpY2F0b3IudGVzdC50c3gnLFxuICAgICAgJ3Rlc3QvY29tcG9uZW50cy9zZXR0aW5ncy9PbGxhbWFNb2RlbERpc2NvdmVyeU1vZGFsLnRlc3QudHN4J1xuICAgIF0sXG4gICAgZXhjbHVkZTogWydub2RlX21vZHVsZXMnLCAnZGlzdCcsICcuZ2l0JywgJy5jYWNoZScsICd0ZXN0LmJhY2t1cCcsICcqLmJhY2t1cC8qKicsICd0ZXN0LWJhY2t1cHMnXSxcbiAgICByZXBvcnRlcnM6IFsnZG90JywgJ2pzb24nXSxcbiAgICBvdXRwdXRGaWxlOiB7IFxuICAgICAganNvbjogJy4vcHVibGljL3Rlc3QtcmVzdWx0cy90ZXN0LXJlc3VsdHMuanNvbicgXG4gICAgfSxcbiAgICB0ZXN0VGltZW91dDogMTAwMDAsIC8vIDEwIHNlY29uZHMgdGltZW91dFxuICAgIGhvb2tUaW1lb3V0OiAxMDAwMCwgLy8gMTAgc2Vjb25kcyBmb3Igc2V0dXAvdGVhcmRvd25cbiAgICBjb3ZlcmFnZToge1xuICAgICAgcHJvdmlkZXI6ICd2OCcsXG4gICAgICByZXBvcnRlcjogW1xuICAgICAgICAndGV4dCcsIFxuICAgICAgICAndGV4dC1zdW1tYXJ5JywgXG4gICAgICAgICdodG1sJywgXG4gICAgICAgICdqc29uJywgXG4gICAgICAgICdqc29uLXN1bW1hcnknLFxuICAgICAgICAnbGNvdidcbiAgICAgIF0sXG4gICAgICByZXBvcnRzRGlyZWN0b3J5OiAnLi9wdWJsaWMvdGVzdC1yZXN1bHRzL2NvdmVyYWdlJyxcbiAgICAgIGNsZWFuOiBmYWxzZSwgLy8gRG9uJ3QgY2xlYW4gdGhlIGRpcmVjdG9yeSBhcyBpdCBtYXkgYmUgaW4gdXNlXG4gICAgICByZXBvcnRPbkZhaWx1cmU6IHRydWUsIC8vIEdlbmVyYXRlIGNvdmVyYWdlIHJlcG9ydHMgZXZlbiB3aGVuIHRlc3RzIGZhaWxcbiAgICAgIGV4Y2x1ZGU6IFtcbiAgICAgICAgJ25vZGVfbW9kdWxlcy8nLFxuICAgICAgICAndGVzdHMvJyxcbiAgICAgICAgJyoqLyouZC50cycsXG4gICAgICAgICcqKi8qLmNvbmZpZy4qJyxcbiAgICAgICAgJyoqL21vY2tEYXRhLnRzJyxcbiAgICAgICAgJyoqLyoudGVzdC57dHMsdHN4fScsXG4gICAgICAgICdzcmMvZW52LmQudHMnLFxuICAgICAgICAnY292ZXJhZ2UvKionLFxuICAgICAgICAnZGlzdC8qKicsXG4gICAgICAgICdwdWJsaWMvKionLFxuICAgICAgICAnKiovKi5zdG9yaWVzLionLFxuICAgICAgICAnKiovKi5zdG9yeS4qJyxcbiAgICAgIF0sXG4gICAgICBpbmNsdWRlOiBbXG4gICAgICAgICdzcmMvKiovKi57dHMsdHN4fScsXG4gICAgICBdLFxuICAgICAgdGhyZXNob2xkczoge31cbiAgICB9LFxuICB9LFxuICByZXNvbHZlOiB7XG4gICAgYWxpYXM6IHtcbiAgICAgICdAJzogcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgJy4vc3JjJyksXG4gICAgfSxcbiAgfSxcbn0pICJdLAogICJtYXBwaW5ncyI6ICI7QUFDQSxTQUFTLG9CQUFvQjtBQUM3QixPQUFPLFdBQVc7QUFDbEIsT0FBTyxVQUFVO0FBSGpCLElBQU0sbUNBQW1DO0FBS3pDLElBQU8sd0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLENBQUM7QUFBQSxFQUNqQixNQUFNO0FBQUEsSUFDSixTQUFTO0FBQUEsSUFDVCxhQUFhO0FBQUEsSUFDYixZQUFZO0FBQUEsSUFDWixTQUFTO0FBQUEsTUFDUDtBQUFBO0FBQUEsTUFDQTtBQUFBLE1BQ0E7QUFBQTtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsTUFDQTtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsTUFDQTtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsTUFDQTtBQUFBLE1BQ0E7QUFBQSxNQUNBO0FBQUEsSUFDRjtBQUFBLElBQ0EsU0FBUyxDQUFDLGdCQUFnQixRQUFRLFFBQVEsVUFBVSxlQUFlLGVBQWUsY0FBYztBQUFBLElBQ2hHLFdBQVcsQ0FBQyxPQUFPLE1BQU07QUFBQSxJQUN6QixZQUFZO0FBQUEsTUFDVixNQUFNO0FBQUEsSUFDUjtBQUFBLElBQ0EsYUFBYTtBQUFBO0FBQUEsSUFDYixhQUFhO0FBQUE7QUFBQSxJQUNiLFVBQVU7QUFBQSxNQUNSLFVBQVU7QUFBQSxNQUNWLFVBQVU7QUFBQSxRQUNSO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxNQUNGO0FBQUEsTUFDQSxrQkFBa0I7QUFBQSxNQUNsQixPQUFPO0FBQUE7QUFBQSxNQUNQLGlCQUFpQjtBQUFBO0FBQUEsTUFDakIsU0FBUztBQUFBLFFBQ1A7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLE1BQ0Y7QUFBQSxNQUNBLFNBQVM7QUFBQSxRQUNQO0FBQUEsTUFDRjtBQUFBLE1BQ0EsWUFBWSxDQUFDO0FBQUEsSUFDZjtBQUFBLEVBQ0Y7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLE9BQU87QUFBQSxJQUN0QztBQUFBLEVBQ0Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
