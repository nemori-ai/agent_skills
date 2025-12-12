"""CLI entry point for agent-skills.

Provides commands for installing, uninstalling, and listing skills.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent_skills.cli.installer import DEFAULT_SKILLS_DIR, SkillInstaller


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="agent-skills",
        description="Manage AI agent skills - install, uninstall, and list skills from Git repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Install a skill from GitHub
  agent-skills install https://github.com/user/my-skill.git

  # Install with a specific version/tag
  agent-skills install https://github.com/user/my-skill.git --ref v1.0.0

  # Install with a custom name
  agent-skills install https://github.com/user/my-skill.git --name custom-name

  # Install to a custom directory
  agent-skills install https://github.com/user/my-skill.git --dir ./my-project/skills

  # Install from a subdirectory of a large repo (sparse checkout)
  agent-skills install https://github.com/metabase/metabase.git --path .claude/skills/clojure-review

  # Uninstall a skill
  agent-skills uninstall my-skill

  # List all skills
  agent-skills list

  # List only skills installed via CLI
  agent-skills list --installed
        """,
    )

    # Global options
    parser.add_argument(
        "--dir", "-d",
        type=str,
        default=None,
        help=f"Skills directory (default: {DEFAULT_SKILLS_DIR})",
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Install command
    install_parser = subparsers.add_parser(
        "install",
        help="Install a skill from a Git repository",
        description="Clone a skill from a Git repository and install it to the skills directory.",
    )
    install_parser.add_argument(
        "url",
        help="Git repository URL",
    )
    install_parser.add_argument(
        "--ref", "-r",
        type=str,
        default=None,
        help="Git ref (branch, tag, or commit) to checkout",
    )
    install_parser.add_argument(
        "--name", "-n",
        type=str,
        default=None,
        help="Custom name for the skill (only for single-skill repositories)",
    )
    install_parser.add_argument(
        "--dir", "-d",
        type=str,
        dest="subdir",
        default=None,
        help=f"Skills directory (default: {DEFAULT_SKILLS_DIR})",
    )
    install_parser.add_argument(
        "--path", "-p",
        type=str,
        default=None,
        help="Path within repository to install (for large repos with skills in subdirectories)",
    )

    # Uninstall command
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="Uninstall a skill",
        description="Remove an installed skill from the skills directory.",
    )
    uninstall_parser.add_argument(
        "name",
        help="Name of the skill to uninstall",
    )
    uninstall_parser.add_argument(
        "--dir", "-d",
        type=str,
        dest="subdir",
        default=None,
        help=f"Skills directory (default: {DEFAULT_SKILLS_DIR})",
    )

    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List installed skills",
        description="List all skills in the skills directory.",
    )
    list_parser.add_argument(
        "--installed", "-i",
        action="store_true",
        help="Only show skills installed via CLI",
    )
    list_parser.add_argument(
        "--dir", "-d",
        type=str,
        dest="subdir",
        default=None,
        help=f"Skills directory (default: {DEFAULT_SKILLS_DIR})",
    )

    return parser


def _get_skills_dir(args: argparse.Namespace) -> str | None:
    """Get skills directory from args, preferring subcommand option over global."""
    # Subcommand --dir takes precedence
    if hasattr(args, "subdir") and args.subdir:
        return args.subdir
    # Fall back to global --dir
    return args.dir


def cmd_install(args: argparse.Namespace) -> int:
    """Handle the install command."""
    installer = SkillInstaller(skills_dir=_get_skills_dir(args))

    print(f"Installing from {args.url}...")
    if args.ref:
        print(f"  Using ref: {args.ref}")
    if args.path:
        print(f"  Using path: {args.path}")

    result = installer.install(
        url=args.url,
        ref=args.ref,
        name=args.name,
        path=args.path,
    )

    if result.success:
        print(f"✓ {result.message}")
        if result.skill_path:
            print(f"  Location: {result.skill_path}")
        return 0
    else:
        print(f"✗ {result.message}", file=sys.stderr)
        return 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Handle the uninstall command."""
    installer = SkillInstaller(skills_dir=_get_skills_dir(args))

    result = installer.uninstall(name=args.name)

    if result.success:
        print(f"✓ {result.message}")
        return 0
    else:
        print(f"✗ {result.message}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """Handle the list command."""
    installer = SkillInstaller(skills_dir=_get_skills_dir(args))

    skills = installer.list_skills(installed_only=args.installed)

    if not skills:
        skills_dir = _get_skills_dir(args) or DEFAULT_SKILLS_DIR
        print(f"No skills found in {skills_dir}")
        return 0

    # Print header
    print(f"Skills in {installer.skills_dir}:")
    print()

    for skill in skills:
        # Format skill info
        name_display = skill.name
        if skill.is_installed:
            name_display = f"{skill.name} [installed]"

        print(f"  {name_display}")
        if skill.description:
            print(f"    {skill.description}")
        if skill.source:
            source_info = skill.source
            if skill.ref:
                source_info += f" @ {skill.ref}"
            print(f"    Source: {source_info}")
        print()

    # Print summary
    total = len(skills)
    installed_count = sum(1 for s in skills if s.is_installed)
    print(f"Total: {total} skill(s), {installed_count} installed via CLI")

    return 0


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command specified, print help
    if args.command is None:
        parser.print_help()
        return 0

    # Dispatch to command handler
    if args.command == "install":
        return cmd_install(args)
    elif args.command == "uninstall":
        return cmd_uninstall(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
