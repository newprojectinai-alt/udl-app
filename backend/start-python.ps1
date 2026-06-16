param(
  [switch]$Reload
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\.venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$uvicornArgs = @(
  "app:app",
  "--host", "0.0.0.0",
  "--port", "5000"
)

if ($Reload) {
  $uvicornArgs += @(
    "--reload",
    "--reload-exclude", ".venv/*",
    "--reload-exclude", "uploads/*",
    "--reload-exclude", "audio/*",
    "--reload-exclude", "renders/*",
    "--reload-exclude", "video_frames/*",
    "--reload-exclude", "manim_jobs/*"
  )
}

& .\.venv\Scripts\python.exe -m uvicorn @uvicornArgs
