# Astro Clock - Justfile
# A command runner for common development tasks

# Load environment from .env file
set dotenv-load := true

# Export environment variables from shell to recipes
set export := true

# Default recipe - show available commands
default:
    @just --list --unsorted
