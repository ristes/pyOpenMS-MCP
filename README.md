# pyOpenMS-MCP

A Python project that exposes [pyOpenMS](https://pyopenms.readthedocs.io/) mass-spectrometry
functionality through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Features

* **Upload mzML files** — register local mzML files with a stable content-derived ID.
* **List / delete files** — manage your uploaded file collection.
* **Spectra summary** — report MS levels, RT range, and m/z range for a file.
* **Spectrum retrieval** — fetch the raw peak data for any individual spectrum.
* **Chromatogram summary** — list all chromatograms with RT range and peak intensity.
* **Peak picking** — run `PeakPickerHiRes` on profile-mode data.
* **Automatic caching** — every analysis result is cached on disk; repeated calls return
  instantly without re-loading the file.

## Installation

```bash
pip install pyopenms-mcp
```

Or from source:

```bash
git clone https://github.com/ristes/pyOpenMS-MCP.git
cd pyOpenMS-MCP
pip install -e .
```

## Quick start

### Run the MCP server (stdio transport)

```bash
pyopenms-mcp
```

The server communicates over **stdin/stdout** using the MCP protocol, so it can be wired
directly into any MCP-compatible client (e.g. Claude Desktop, VS Code MCP extension).

### Claude Desktop configuration

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pyopenms": {
      "command": "pyopenms-mcp"
    }
  }
}
```

## Available MCP tools

| Tool | Description |
|---|---|
| `upload_mzml(file_path)` | Register an mzML file by its local path |
| `list_mzml_files()` | List all uploaded files |
| `delete_mzml_file(file_id)` | Remove a file and its cached results |
| `get_spectra_summary(file_id)` | Summarize all spectra (MS levels, RT/m/z ranges) |
| `get_spectrum(file_id, spectrum_index)` | Retrieve a single spectrum's peak data |
| `get_chromatogram_summary(file_id)` | Summarize all chromatograms |
| `run_peak_picking(file_id, signal_to_noise)` | Run PeakPickerHiRes |

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `PYOPENMS_MCP_DATA_DIR` | `~/.pyopenms_mcp` | Directory for uploaded files and cache |

## Development

```bash
pip install -e .
pytest
```
