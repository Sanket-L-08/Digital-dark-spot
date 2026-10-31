## What it does

- Accepts a research question.
- Lets the user add multiple source titles, URLs, and pasted text.
- Creates a structured preliminary report.
- Flags question terms not detected in the pasted material.
- Uses simple rules to find some possible cross-source conflicts.
- Flags sources with missing dates or older years.
- Generates a verification checklist.

## Important limitation

This is **prototype v0.1**. The current analysis is rule-based, not a trained AI model. It does not automatically browse or download URLs. Users paste source text themselves. A rule-based flag is only a clue for manual review; it does not prove a detail is missing or that two claims truly conflict.

## Requirements

- Python 3.10 or newer
- Visual Studio Code
- Internet connection only to install Flask (the app itself runs locally)

## Run in VS Code

1. Open **Terminal → New Terminal**.

2. Install dependencies:

   ```bash
  pip install -r requirements.txt
   ```

   For codespaces write

   ```bash 
   cd /workspaces/Digital-dark-spot/digital_dark_spot_vscode
   ```
Later

    ```bash
    python3 -m pip install -r requirements.txt
    ```

4. Start the server:

   ```bash
   python app.py
    ```
   
   For codespaces write

    ```bash
   python3 app.py
    ```

6. Open this address in your browser:

   http://127.0.0.1:5000

7. Click **Load example**, then **Analyze sources** to test the interface.

## Project structure

```text
digital_dark_spot_vscode/
├── app.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
```
