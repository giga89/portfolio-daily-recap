# Docker Setup for Portfolio Daily Recap

This project has been dockerized to allow easy execution on both Linux and Windows environments.

## Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop) installed and running.

## Quick Start

1.  **Clone the repository** (if you haven't already).

2.  **Configuration**:
    Copy `.env.example` to `.env` and fill in your credentials.
    ```bash
    cp .env.example .env
    ```
    *Note: For `GOOGLE_SHEETS_CREDENTIALS`, if you have a JSON file, you might need to adjust the code to read from a mounted file, or paste the minified JSON string into the `.env` variable.*

3.  **Build and Run**:
    Run the following command to build the image and execute the script:
    ```bash
    docker compose up --build
    ```

    The script will run, generate the recap in the `output/` folder (mounted from your host), send the Telegram message (if configured), and then exit.

4.  **Check Output**:
    You can find the generated `recap.txt` and images in the local `output/` directory.

## Troubleshooting

- **Playwright Errors**: The Docker image installs `chromium`. If you encounter browser errors, ensure you are not passing incompatible browser launch arguments (like `--headful` in a headless container without display).
- **Permissions**: On Linux, if you have permission issues with the `output` directory, ensure the user running docker has write access or run with `sudo`.

## Manual Build (without Compose)

```bash
# Build the image
docker build -t portfolio-recap .

# Run the container (passing env file)
docker run --env-file .env -v $(pwd)/output:/app/output portfolio-recap
```
