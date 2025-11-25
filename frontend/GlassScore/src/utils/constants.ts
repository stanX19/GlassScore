// Make BASE_URL mutable so we can default to localhost and switch to Render if localhost isn't reachable.
const envProvided = (import.meta as any).env && (import.meta as any).env.VITE_API_BASE_URL;
const localhostUrl = 'http://localhost:8000';

// Export a live-binding so other modules see updates if we switch the backend at runtime.
export let BASE_URL: string = envProvided || localhostUrl;
