import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'http://localhost:8000/openapi.json',
  output: 'src/client',
  plugins: [{
    name: '@hey-api/client-next',
    runtimeConfigPath: '@/hey-api'
  }]
});
