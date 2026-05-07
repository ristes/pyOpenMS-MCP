"""pyOpenMS MCP — exposes pyOpenMS functionality through the MCP protocol."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pyopenms-mcp")
except PackageNotFoundError:
    __version__ = "0.1.0"
