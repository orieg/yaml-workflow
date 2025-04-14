#!/bin/bash
set -e

# Function to show usage
show_usage() {
    echo "Usage: $0 [major|minor|patch]"
    echo "  major  - Increment major version (X.y.z -> X+1.0.0)"
    echo "  minor  - Increment minor version (x.Y.z -> x.Y+1.0)"
    echo "  patch  - Increment patch version (x.y.Z -> x.y.Z+1) [default]"
    exit 1
}

# Function to extract current version from pyproject.toml
get_current_version() {
    grep -m 1 'version = ' pyproject.toml | cut -d '"' -f 2
}

# Function to update version in pyproject.toml
update_version() {
    local new_version=$1
    sed -i.bak "s/version = \".*\"/version = \"$new_version\"/" pyproject.toml
    rm pyproject.toml.bak
}

# Function to get next dev version
get_next_dev_version() {
    local current=$1
    local increment_type=${2:-patch}  # Default to patch if not specified
    
    # Remove -dev suffix if present
    current=${current%-dev}
    
    # Split into major.minor.patch
    IFS='.' read -r major minor patch <<< "$current"
    
    case $increment_type in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            echo "Error: Invalid increment type '$increment_type'"
            show_usage
            ;;
    esac
    
    echo "$major.$minor.$patch-dev"
}

# Function to check if working directory is clean
check_working_directory() {
    if ! git diff-index --quiet HEAD --; then
        echo "Error: Working directory is not clean. Please commit or stash changes."
        exit 1
    fi
}

# Function to wait for GitHub workflow to complete
wait_for_workflow() {
    local tag=$1
    local max_attempts=30
    local attempt=1
    local sleep_time=20

    echo "Waiting for release workflow to complete..."
    while [ $attempt -le $max_attempts ]; do
        # Check if release exists
        if gh release view $tag &> /dev/null; then
            echo "Release $tag has been created successfully!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Release not ready yet, waiting ${sleep_time}s..."
        sleep $sleep_time
        attempt=$((attempt + 1))
    done

    echo "Error: Timeout waiting for release to be created"
    exit 1
}

# Main script

# Process command line arguments
increment_type="patch"  # Default to patch
if [ $# -gt 0 ]; then
    case $1 in
        major|minor|patch)
            increment_type=$1
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Error: Invalid argument '$1'"
            show_usage
            ;;
    esac
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed. Please install it first."
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: GitHub CLI is not authenticated. Please run 'gh auth login' first."
    exit 1
fi

# Ensure we're in the repository root
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must be run from repository root (pyproject.toml not found)"
    exit 1
fi

# Check working directory
check_working_directory

# Get current version
current_version=$(get_current_version)

if [[ $current_version != *"-dev"* ]]; then
    echo "Error: Current version ($current_version) is not a dev version"
    exit 1
fi

# Remove -dev suffix for release
release_version=${current_version%-dev}

# Update to release version
echo "Updating version to $release_version"
update_version "$release_version"

# Commit release version
git add pyproject.toml
git commit -m "Release version $release_version"
git push origin main

# Create and push tag
tag="v$release_version"
echo "Creating and pushing tag $tag"
git tag -a "$tag" -m "Release version $release_version"
git push origin "$tag"

# Wait for release workflow
wait_for_workflow "$tag"

# Update to next dev version
next_dev_version=$(get_next_dev_version "$release_version" "$increment_type")
echo "Bumping version to $next_dev_version ($increment_type increment)"
update_version "$next_dev_version"

# Commit dev version
git add pyproject.toml
git commit -m "Bump version to $next_dev_version"
git push origin main

echo "Release process completed successfully!"
echo "Released version: $release_version"
echo "New development version: $next_dev_version" 