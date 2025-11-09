import type { CreateClientConfig } from './client/client.gen';

export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: 'http://localhost:8000',
    headers: {
      "x-temp-key": "7e0367b4-5eb2-4b31-94db-20f2e838be22"
  }
});
