# Upload diagnostics update

This diagnostic build changes the frontend upload handler to display the HTTP status and response body when `/api/upload-resume` returns a non-2xx response, including plain-text responses from a proxy or server.

This does not claim to fix the backend failure itself. Reproduce the upload and use the displayed HTTP status/detail together with the backend terminal output to identify the cause.

If the message reports a network error without an HTTP status, confirm the FastAPI server is running on `127.0.0.1:8000` and that Vite is running on port `5173`.
