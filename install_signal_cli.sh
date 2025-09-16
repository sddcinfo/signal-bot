#!/bin/bash
#
# Signal CLI Installation Script with Existing Installation Handling
# Handles existing installations, provides update options, and robust error handling
#

# Exit on any error
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Command line options
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
            echo "  --force       Force reinstall even if signal-cli is working"
            echo "  --update      Update to newer version if available"
            echo "  --skip-checks Skip pre-installation checks"
            echo "  --help        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Install signal-cli (skip if already working)"
            echo "  $0 --force           # Force reinstall even if working"
            echo "  $0 --update          # Update to newer version"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "========================================="
echo "Signal CLI Installer (Enhanced Version)"
echo "========================================="
echo ""

# Use latest available version
VERSION="0.13.18"
echo "Target signal-cli version: $VERSION"

# Step 0: Check existing installation
if [ "$SKIP_CHECKS" = false ]; then
    echo ""
    echo "Step 0: Checking existing installation..."
    EXISTING_VERSION=""
    EXISTING_WORKING=false

    # Check if signal-cli exists and works
    if command -v signal-cli &> /dev/null; then
        echo -e "${BLUE}Found existing signal-cli installation${NC}"

        # Try to get version
        if EXISTING_VERSION=$(signal-cli --version 2>&1); then
            EXISTING_WORKING=true
            echo -e "${GREEN}✓ Existing installation works: $EXISTING_VERSION${NC}"

            # Extract version number for comparison
            if [[ $EXISTING_VERSION =~ signal-cli\ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
                EXISTING_VER_NUM="${BASH_REMATCH[1]}"
                echo "Current version: $EXISTING_VER_NUM"
                echo "Target version: $VERSION"

                if [ "$EXISTING_VER_NUM" = "$VERSION" ]; then
                    if [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
                        echo -e "${GREEN}✓ signal-cli $VERSION is already installed and working!${NC}"
                        echo ""
                        echo "Use --force to reinstall or --update to check for updates"
                        exit 0
                    fi
                elif [ "$UPDATE" = true ]; then
                    echo -e "${YELLOW}Update available: $EXISTING_VER_NUM → $VERSION${NC}"
                elif [ "$FORCE" = false ]; then
                    echo -e "${YELLOW}Different version installed. Use --force to reinstall or --update to update${NC}"
                    exit 0
                fi
            fi
        else
            echo -e "${YELLOW}⚠ Existing signal-cli found but not working properly${NC}"
            echo "Will reinstall..."
        fi
    else
        echo "No existing signal-cli installation found"
    fi

    if [ "$EXISTING_WORKING" = true ] && [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
        echo -e "${YELLOW}signal-cli is already installed and working.${NC}"
        echo "Use --force to reinstall anyway, or --update to update to newer version"
        exit 0
    fi
fi

# Step 1: Check Java
echo ""
echo "Step 1: Checking Java..."
if command -v java &> /dev/null; then
    JAVA_VERSION_OUTPUT=$(java -version 2>&1 | head -n 1)
    echo -e "${GREEN}✓ Java found: $JAVA_VERSION_OUTPUT${NC}"

    # Extract major version number
    if [[ $JAVA_VERSION_OUTPUT =~ \"([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        MAJOR="${BASH_REMATCH[1]}"
        if [ "$MAJOR" -lt "17" ] && [ "$MAJOR" != "1" ]; then
            echo -e "${YELLOW}⚠ Java $MAJOR found, but 17+ recommended${NC}"
        fi
    elif [[ $JAVA_VERSION_OUTPUT =~ version\ \"([0-9]+) ]]; then
        MAJOR="${BASH_REMATCH[1]}"
        if [ "$MAJOR" -lt "17" ]; then
            echo -e "${YELLOW}⚠ Java $MAJOR found, but 17+ recommended${NC}"
        fi
    fi
else
    echo -e "${RED}✗ Java not found!${NC}"
    echo ""
    echo "Installing Java is required. Run one of these commands:"
    echo "  Ubuntu/Debian: sudo apt-get install openjdk-17-jre"
    echo "  RHEL/CentOS:   sudo yum install java-17-openjdk"
    echo "  Arch:          sudo pacman -S jre17-openjdk"
    exit 1
fi

# Step 2: Download
echo ""
echo "Step 2: Downloading signal-cli..."
DOWNLOAD_URL="https://github.com/AsamK/signal-cli/releases/download/v${VERSION}/signal-cli-${VERSION}-Linux-native.tar.gz"
TEMP_FILE="/tmp/signal-cli-${VERSION}.tar.gz"

# Remove old file if exists
rm -f "$TEMP_FILE"

echo "Downloading from: $DOWNLOAD_URL"
echo "Saving to: $TEMP_FILE"
echo ""

# Download with progress bar and error handling
if command -v wget &> /dev/null; then
    if ! wget --progress=bar:force "$DOWNLOAD_URL" -O "$TEMP_FILE" 2>&1 | \
        grep --line-buffered "%" | \
        sed -u -e "s/\.\.\.\.\.\.//g" | \
        awk '{printf("\rDownloading: %s", $0)}'; then
        echo -e "\n${RED}✗ Download failed with wget${NC}"
        exit 1
    fi
    echo ""  # New line after progress
elif command -v curl &> /dev/null; then
    if ! curl -# -L "$DOWNLOAD_URL" -o "$TEMP_FILE"; then
        echo -e "${RED}✗ Download failed with curl${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Neither wget nor curl found!${NC}"
    echo "Install wget with: sudo apt-get install wget"
    exit 1
fi

# Verify download
if [ ! -f "$TEMP_FILE" ]; then
    echo -e "${RED}✗ Download failed - file not found${NC}"
    exit 1
fi

FILE_SIZE=$(stat -c%s "$TEMP_FILE" 2>/dev/null || stat -f%z "$TEMP_FILE" 2>/dev/null || wc -c < "$TEMP_FILE")
FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
echo -e "${GREEN}✓ Downloaded successfully (${FILE_SIZE_MB} MB)${NC}"

if [ "$FILE_SIZE" -lt 1000000 ]; then
    echo -e "${RED}✗ File too small, download may have failed${NC}"
    exit 1
fi

# Step 3: Extract
echo ""
echo "Step 3: Extracting archive..."
cd /tmp

# Clean up any existing extracted files first to prevent conflicts
echo "Cleaning up existing extracted files..."
rm -rf /tmp/signal-cli /tmp/signal-cli-* 2>/dev/null || true

# Now extract with error handling
echo "Extracting $TEMP_FILE..."
if ! tar xzf "$TEMP_FILE"; then
    echo -e "${RED}✗ Extraction failed${NC}"
    echo "This could be due to:"
    echo "  - Corrupted download"
    echo "  - Insufficient disk space"
    echo "  - Permissions issues"
    exit 1
fi

# Check what was extracted - could be a directory or a single binary
if [ -f "/tmp/signal-cli" ]; then
    echo "Found native binary: /tmp/signal-cli"
    BINARY_TYPE="native"
elif [ -d "/tmp/signal-cli" ]; then
    echo "Found directory: /tmp/signal-cli"
    EXTRACTED_DIR="signal-cli"
    BINARY_TYPE="directory"
elif [ -d "/tmp/signal-cli-${VERSION}" ]; then
    echo "Found directory: /tmp/signal-cli-${VERSION}"
    EXTRACTED_DIR="signal-cli-${VERSION}"
    BINARY_TYPE="directory"
else
    echo -e "${RED}✗ Extraction failed - no signal-cli binary or directory found${NC}"
    echo "Contents of /tmp:"
    ls -la /tmp/signal* 2>/dev/null || echo "No signal files found"
    exit 1
fi
echo -e "${GREEN}✓ Extracted successfully${NC}"

# Step 4: Install
echo ""
echo "Step 4: Installing signal-cli..."
echo "This requires sudo access to install to /opt"

# Create /opt if it doesn't exist
sudo mkdir -p /opt

if [ "$BINARY_TYPE" = "native" ]; then
    # Handle native binary
    echo "Installing native binary..."

    # Create directory structure
    TARGET_DIR="/opt/signal-cli-${VERSION}"
    sudo mkdir -p "$TARGET_DIR/bin"

    # Copy binary
    sudo cp "/tmp/signal-cli" "$TARGET_DIR/bin/signal-cli"
    sudo chmod +x "$TARGET_DIR/bin/signal-cli"
    echo -e "${GREEN}✓ Native binary installed to $TARGET_DIR/bin/signal-cli${NC}"

else
    # Handle directory installation (traditional Java distribution)
    TARGET_DIR="/opt/signal-cli-${VERSION}"

    # Remove old installation if exists
    if [ -d "$TARGET_DIR" ]; then
        echo "Removing old installation..."
        sudo rm -rf "$TARGET_DIR"
    fi

    # Move to /opt with version name
    sudo mv "/tmp/$EXTRACTED_DIR" "$TARGET_DIR"
    echo -e "${GREEN}✓ Directory moved to $TARGET_DIR${NC}"

    # Set permissions
    sudo chmod +x "$TARGET_DIR/bin/signal-cli"
    sudo chmod -R 755 "$TARGET_DIR"
fi

# Step 5: Create symlink
echo ""
echo "Step 5: Creating symlink..."
sudo mkdir -p /usr/local/bin
sudo rm -f /usr/local/bin/signal-cli  # Remove old symlink if exists
sudo ln -s "$TARGET_DIR/bin/signal-cli" /usr/local/bin/signal-cli
echo -e "${GREEN}✓ Symlink created at /usr/local/bin/signal-cli${NC}"

# Step 6: Set permissions on symlink target
echo ""
echo "Step 6: Verifying permissions..."
sudo chmod +x "$TARGET_DIR/bin/signal-cli"
echo -e "${GREEN}✓ Permissions set${NC}"

# Step 7: Verify installation
echo ""
echo "Step 7: Verifying installation..."

# Test direct execution
if "$TARGET_DIR/bin/signal-cli" --version &> /dev/null; then
    VERSION_OUTPUT=$("$TARGET_DIR/bin/signal-cli" --version 2>&1)
    echo -e "${GREEN}✓ Direct execution works: $VERSION_OUTPUT${NC}"
else
    echo -e "${YELLOW}⚠ Direct execution test failed, but installation may still work${NC}"
fi

# Test symlink
if /usr/local/bin/signal-cli --version &> /dev/null; then
    echo -e "${GREEN}✓ Symlink works${NC}"
else
    echo -e "${YELLOW}⚠ Symlink test failed, checking PATH...${NC}"
fi

# Check if /usr/local/bin is in PATH
if [[ ":$PATH:" == *":/usr/local/bin:"* ]]; then
    echo -e "${GREEN}✓ /usr/local/bin is in PATH${NC}"
else
    echo -e "${YELLOW}⚠ /usr/local/bin is not in PATH${NC}"
    echo "Add to PATH by running:"
    echo '  export PATH=/usr/local/bin:$PATH'
    echo "Or add to ~/.bashrc for permanent effect"
fi

# Cleanup
rm -f "$TEMP_FILE"
rm -rf /tmp/signal-cli /tmp/signal-cli-* 2>/dev/null || true

# Final summary
echo ""
echo "========================================="
if [ "$EXISTING_WORKING" = true ] && [ "$FORCE" = true ]; then
    echo -e "${GREEN}Reinstallation Complete!${NC}"
elif [ "$EXISTING_WORKING" = true ] && [ "$UPDATE" = true ]; then
    echo -e "${GREEN}Update Complete!${NC}"
else
    echo -e "${GREEN}Installation Complete!${NC}"
fi
echo "========================================="
echo ""
echo "signal-cli has been installed to:"
echo "  Binary: $TARGET_DIR/bin/signal-cli"
echo "  Symlink: /usr/local/bin/signal-cli"
echo ""
echo "Test the installation:"
echo "  signal-cli --version"
echo ""
echo "If 'signal-cli' command not found, run:"
echo "  export PATH=/usr/local/bin:\$PATH"
echo ""
echo "Next steps:"
echo "1. Register your phone number:"
echo "   signal-cli -u +YOURPHONE register"
echo ""
echo "2. Verify with SMS code:"
echo "   signal-cli -u +YOURPHONE verify CODE"
echo ""
echo "3. Run the bot:"
echo "   python3 signal_bot.py"
echo ""
echo -e "${GREEN}✓ Ready to use!${NC}"