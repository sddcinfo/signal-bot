#!/bin/bash
#
# Signal CLI Installation Script (Simplified)
# Handles existing installations, provides update options, and robust error handling.
#

# Exit on any error
set -e

# --- Pre-flight Checks ---
# Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: This script requires superuser privileges for installation."
  echo "Please run with sudo: sudo $0 $*"
  exit 1
fi

# --- Command Line Options ---
FORCE=false
UPDATE=false
SKIP_CHECKS=false

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        --force) 
            FORCE=true
            shift
            ;; 
        --update)
            UPDATE=true
            shift
            ;; 
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;; 
        --help|-h) 
            echo "Signal CLI Installer"
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force       Force reinstall even if signal-cli is working."
            echo "  --update      Update to a newer version if available."
            echo "  --skip-checks Skip pre-installation checks."
            echo "  --help        Show this help message."
            echo ""
            echo "Examples:"
            echo "  $0              # Install signal-cli (skips if already working)."
            echo "  $0 --force     # Force reinstall even if working."
            echo "  $0 --update    # Update to a newer version."
            exit 0
            ;; 
        *)
            echo "ERROR: Unknown option: $arg"
            echo "Use --help for usage information."
            exit 1
            ;; 
    esac
done

echo "========================================="
echo "Signal CLI Installer (Simplified)"
echo "========================================="
echo ""

# --- Version Handling ---
echo "INFO: Fetching the latest version from GitHub..."
LATEST_VERSION=$(curl -s "https://api.github.com/repos/AsamK/signal-cli/releases/latest" | grep '"tag_name"' | sed -E 's/.*"v?([^\"]+)".*/\1/')

FALLBACK_VERSION="0.13.18"

if [ -z "$LATEST_VERSION" ]; then
    echo "WARNING: Could not fetch the latest version from GitHub. Using fallback: $FALLBACK_VERSION"
    VERSION="$FALLBACK_VERSION"
else
    echo "INFO: Latest version found on GitHub: $LATEST_VERSION"
    VERSION="$LATEST_VERSION"
fi

echo "INFO: Target signal-cli version: $VERSION"

# --- Step 0: Check Existing Installation ---
if [ "$SKIP_CHECKS" = false ]; then
    echo ""
    echo "--- Step 0: Checking existing installation... ---"
    
    if ! command -v signal-cli &> /dev/null; then
        echo "INFO: No existing signal-cli installation found. Proceeding with installation."
    else
        echo "INFO: Found existing signal-cli installation."
        
        if ! EXISTING_VERSION_OUTPUT=$(signal-cli --version 2>&1); then
            echo "WARNING: Existing signal-cli found but is not working properly."
            if [ "$FORCE" = false ]; then
                echo "ERROR: Cannot determine installed version. Please fix the existing installation or run this script with --force."
                exit 1
            else
                echo "INFO: --force is set, proceeding with re-installation."
            fi
        else
            echo "INFO: Existing installation works: $EXISTING_VERSION_OUTPUT"
            EXISTING_VER_NUM=$(echo "$EXISTING_VERSION_OUTPUT" | sed -n 's/.*signal-cli \([0-9.]*\).*/\1/p')
            
            if [ -z "$EXISTING_VER_NUM" ]; then
                echo "WARNING: Could not determine installed version number."
                if [ "$FORCE" = false ]; then
                    echo "ERROR: Cannot parse version. Please fix installation or run with --force."
                    exit 1
                else
                    echo "INFO: --force is set, proceeding with re-installation."
                fi
            else
                echo "INFO: Current version: $EXISTING_VER_NUM"
                echo "INFO: Target version: $VERSION"

                if [ "$EXISTING_VER_NUM" = "$VERSION" ]; then
                    if [ "$FORCE" = false ]; then
                        echo "SUCCESS: signal-cli $VERSION is already installed and up-to-date."
                        echo "Use --force to reinstall anyway."
                        exit 0
                    else
                        echo "INFO: Version is the same, but --force is set. Proceeding with re-installation."
                    fi
                else
                    HIGHEST_VERSION=$(printf '%s\n' "$VERSION" "$EXISTING_VER_NUM" | sort -V | tail -n1)
                    
                    if [ "$HIGHEST_VERSION" = "$EXISTING_VER_NUM" ]; then
                        if [ "$FORCE" = false ]; then
                            echo "INFO: Installed version ($EXISTING_VER_NUM) is newer than the target version ($VERSION)."
                            echo "Use --force to downgrade/reinstall."
                            exit 0
                        else
                            echo "INFO: --force is set. Proceeding with downgrade/reinstall."
                        fi
                    else
                        if [ "$UPDATE" = true ] || [ "$FORCE" = true ]; then
                            echo "INFO: Newer version available. Proceeding with update."
                        else
                            echo "WARNING: A newer version ($VERSION) is available."
                            echo "Use --update to upgrade, or --force to reinstall."
                            exit 0
                        fi
                    fi
                fi
            fi
        fi
    fi
fi


# --- Step 1: Check Dependencies ---
echo ""
echo "--- Step 1: Checking dependencies... ---"
if command -v java &> /dev/null; then
    JAVA_VERSION_OUTPUT=$(java -version 2>&1 | head -n 1)
    echo "INFO: Java found: $JAVA_VERSION_OUTPUT"
    
    # A simpler, more robust way to check Java version
    MAJOR_VERSION=$(echo "$JAVA_VERSION_OUTPUT" | sed -E 's/.* version "([0-9]+).*/\1/' | head -n1)
    if [ "$MAJOR_VERSION" = "1" ]; then
        MAJOR_VERSION=$(echo "$JAVA_VERSION_OUTPUT" | sed -E 's/.* version "1\.([0-9]+).*/\1/' | head -n1)
    fi

    if [ -z "$MAJOR_VERSION" ]; then
        echo "WARNING: Could not determine Java major version. Please ensure it is 17 or higher."
    elif [ "$MAJOR_VERSION" -lt 17 ]; then
        echo "WARNING: Java version $MAJOR_VERSION found, but version 17+ is recommended."
    else
        echo "INFO: Java version $MAJOR_VERSION is 17+. Good."
    fi
else
    echo "ERROR: Java not found!"
    echo "Please install Java 17 or later. e.g., sudo apt-get install openjdk-17-jre"
    exit 1
fi

if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
    echo "ERROR: Neither wget nor curl found!"
    echo "Please install one of them to proceed. e.g., sudo apt-get install wget"
    exit 1
fi


# --- Step 2: Download ---
echo ""
echo "--- Step 2: Downloading signal-cli... ---"
echo "INFO: Cleaning up old temporary files..."
rm -f /tmp/signal-cli-*.tar.gz
rm -rf /tmp/signal-cli-*

DOWNLOAD_URL="https://github.com/AsamK/signal-cli/releases/download/v${VERSION}/signal-cli-${VERSION}-Linux-native.tar.gz"
TEMP_FILE="/tmp/signal-cli-${VERSION}.tar.gz"

echo "INFO: Downloading from: $DOWNLOAD_URL"

if command -v wget &> /dev/null; then
    if ! wget -q --show-progress "$DOWNLOAD_URL" -O "$TEMP_FILE"; then
        echo "ERROR: Download failed with wget."
        exit 1
    fi
elif command -v curl &> /dev/null; then
    if ! curl -# -L "$DOWNLOAD_URL" -o "$TEMP_FILE"; then
        echo "ERROR: Download failed with curl."
        exit 1
    fi
fi

if [ ! -f "$TEMP_FILE" ] || [ "$(stat -c%s "$TEMP_FILE")" -lt 1000000 ]; then
    echo "ERROR: Download failed or the file is too small."
    exit 1
fi

FILE_SIZE_MB=$(( $(stat -c%s "$TEMP_FILE") / 1024 / 1024 ))
echo "SUCCESS: Downloaded successfully (${FILE_SIZE_MB} MB)."


# --- Step 3: Extract ---
echo ""
echo "--- Step 3: Extracting archive... ---"
cd /tmp

echo "INFO: Extracting $TEMP_FILE..."
if ! tar xzf "$TEMP_FILE"; then
    echo "ERROR: Extraction failed. The downloaded file may be corrupt."
    exit 1
fi

if [ -d "/tmp/signal-cli-${VERSION}" ]; then
    EXTRACTED_ITEM="/tmp/signal-cli-${VERSION}"
    IS_DIR=true
elif [ -f "/tmp/signal-cli" ]; then
    EXTRACTED_ITEM="/tmp/signal-cli"
    IS_DIR=false
else
    echo "ERROR: Extraction failed - no recognized file or directory found."
    ls -la /tmp/signal* 2>/dev/null || echo "No signal files found in /tmp"
    exit 1
fi
echo "SUCCESS: Extracted successfully."


# --- Step 4: Install ---
echo ""
echo "--- Step 4: Installing signal-cli... ---"
TARGET_DIR="/opt/signal-cli-${VERSION}"

if [ -d "$TARGET_DIR" ]; then
    echo "INFO: Removing old installation at $TARGET_DIR..."
    rm -rf "$TARGET_DIR"
fi

mkdir -p "$TARGET_DIR/bin"

if [ "$IS_DIR" = true ]; then
    echo "INFO: Installing from directory..."
    mv "$EXTRACTED_ITEM"/* "$TARGET_DIR/"
else
    echo "INFO: Installing native binary..."
    mv "$EXTRACTED_ITEM" "$TARGET_DIR/bin/signal-cli"
fi

chmod -R 755 "$TARGET_DIR"
chmod +x "$TARGET_DIR/bin/signal-cli"
echo "INFO: Installed to $TARGET_DIR"


# --- Step 5: Create Symlink ---
echo ""
echo "--- Step 5: Creating symlink... ---"
mkdir -p /usr/local/bin
ln -sf "$TARGET_DIR/bin/signal-cli" /usr/local/bin/signal-cli
echo "SUCCESS: Symlink created at /usr/local/bin/signal-cli"


# --- Step 6: Verify Installation ---
echo ""
echo "--- Step 6: Verifying installation... ---"
if /usr/local/bin/signal-cli --version &> /dev/null; then
    VERSION_OUTPUT=$(/usr/local/bin/signal-cli --version 2>&1)
    echo "SUCCESS: Installation verified. $VERSION_OUTPUT"
else
    echo "WARNING: Verification command failed. Check your PATH or try running again."
fi

if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
    echo "WARNING: /usr/local/bin is not in your PATH."
    echo "You may need to run 'export PATH=/usr/local/bin:$PATH' or add it to your shell profile."
fi


# --- Cleanup ---
rm -f "$TEMP_FILE"
rm -rf /tmp/signal-cli-*


# --- Final Summary ---
echo ""
echo "========================================="
echo "Installation Complete!"
echo "========================================="
echo ""
echo "signal-cli has been installed to:"
echo "  Binary: $TARGET_DIR/bin/signal-cli"
  echo "  Symlink: /usr/local/bin/signal-cli"
echo ""
echo "Test the installation by running:"
echo "  signal-cli --version"
echo ""