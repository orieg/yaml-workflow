#!/bin/bash
set -e

# Configuration
WORKFLOW_TIMEOUT=${WORKFLOW_TIMEOUT:-600}  # 10 minutes default
WORKFLOW_CHECK_INTERVAL=${WORKFLOW_CHECK_INTERVAL:-20}
MAX_ATTEMPTS=$((WORKFLOW_TIMEOUT / WORKFLOW_CHECK_INTERVAL))

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

# Function to validate version format
validate_version() {
    local version=$1
    if ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-dev)?$'; then
        echo "Error: Invalid version format: $version"
        exit 1
    fi
}

# Function to compare versions
compare_versions() {
    local version1=$1
    local version2=$2
    
    # Remove -dev suffix for comparison
    version1=${version1%-dev}
    version2=${version2%-dev}
    
    # For minor releases, we want to allow releasing the current dev version
    if [ "$3" = "minor" ]; then
        return 0
    fi
    
    # Convert versions to comparable numbers
    local v1=$(echo "$version1" | awk -F. '{ printf("%d%03d%03d", $1,$2,$3); }')
    local v2=$(echo "$version2" | awk -F. '{ printf("%d%03d%03d", $1,$2,$3); }')
    
    if [ "$v1" -le "$v2" ]; then
        echo "Error: New version ($version1) must be greater than current version ($version2)"
        exit 1
    fi
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
            patch=0  # Reset patch version for minor bump
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
    local attempt=1

    echo "Waiting for release workflow to complete..."
    echo "Timeout set to ${WORKFLOW_TIMEOUT}s (checking every ${WORKFLOW_CHECK_INTERVAL}s)"
    
    while [ $attempt -le $MAX_ATTEMPTS ]; do
        # Check if release exists
        if gh release view $tag &> /dev/null; then
            echo "Release $tag has been created successfully!"
            return 0
        fi
        echo "Attempt $attempt/$MAX_ATTEMPTS: Release not ready yet, waiting ${WORKFLOW_CHECK_INTERVAL}s..."
        sleep $WORKFLOW_CHECK_INTERVAL
        attempt=$((attempt + 1))
    done

    echo "Error: Timeout waiting for release to be created after ${WORKFLOW_TIMEOUT}s"
    exit 1
}

# Function to validate GitHub token and permissions
check_github_token() {
    if ! gh auth status &> /dev/null; then
        echo "Error: GitHub authentication failed. Please check your token."
        exit 1
    fi
    
    # Check if token has necessary permissions
    if ! gh auth status | grep -q "read:org"; then
        echo "Warning: GitHub token may not have all required permissions."
        echo "Please ensure the token has: repo, read:org, and workflow permissions."
    fi
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
check_github_token

# Ensure we're in the repository root
if [ ! -f "pyproject.toml" ]; then
    echo "Error: Must be run from repository root (pyproject.toml not found)"
    exit 1
fi

# Check working directory
check_working_directory

# Get current version
current_version=$(get_current_version)

# Validate current version format
validate_version "$current_version"

if [[ $current_version != *"-dev"* ]]; then
    echo "Error: Current version ($current_version) is not a dev version"
    exit 1
fi

# Remove -dev suffix for release
release_version=${current_version%-dev}

# Validate release version format and ensure it's greater than the last release
validate_version "$release_version"
compare_versions "$release_version" "$current_version" "minor"

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