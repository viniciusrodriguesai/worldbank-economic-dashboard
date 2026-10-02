# Deploy the actual dashboard on Render

The root `render.yaml` declares a **free** Python API and a static React site. No database or paid compute is declared. Both run the repository's existing application code.

1. Create the API service from the blueprint. Its runtime command binds to Render's PORT; `/health` checks liveness.
2. Create the static frontend. Set `BACKEND_URL` to the API's actual public HTTPS origin (no `/api` suffix). The build passes this to `VITE_API_BASE_URL`.
3. Set the API's `CORS_ORIGINS` to the actual frontend HTTPS origin, without a trailing slash or path. The two actual URLs must be obtained from Render, not guessed from service names.
4. Rebuild the frontend after changing BACKEND_URL and redeploy the API after changing CORS_ORIGINS.
5. Verify `/health`, `/countries` and a Brazil indicator request, then load the frontend, compare countries and export a CSV. Inspect the exact-origin CORS response.
6. Only then add the verified live-demo URL to the README/profile.

The API root routes do not have an `/api` prefix: that prefix belongs to the existing nginx/local proxy configuration. Render's separate frontend uses the direct public API origin instead.

The blueprint passed the official Render JSON schema. The frontend was built with an explicit HTTPS API origin and its existing tests were run.

Free services can sleep and upstream World Bank requests can fail or be slow. No successful public deployment is claimed from a blueprint alone. The existing container/nginx deployment remains an alternative; this blueprint does not imply that nginx's production throttling is present in front of the Render-native API.

[Render free services](https://render.com/docs/free) · [Blueprint reference](https://render.com/docs/blueprint-spec).
