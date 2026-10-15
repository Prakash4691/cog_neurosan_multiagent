from pathlib import Path

from neuro_san_studio.commands.project_environment import ProjectEnvironment

# Point neuro-san at this project's manifest, coded tools and MCP config, the same way `ns chat` does.
_project_environment = ProjectEnvironment(str(Path(__file__).resolve().parent.parent))
_project_environment.load_env_file()
_project_environment.apply()
