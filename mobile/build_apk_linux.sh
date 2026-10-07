#!/usr/bin/env bash
set -e

echo "============================================================"
echo "HEALTHWATCH ANDROID APK BUILD SCRIPT (LINUX NATIVE)"
echo "============================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -d "$HOME/jdk-17" ]; then
    export JAVA_HOME="$HOME/jdk-17"
else
    export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
fi
export PATH="$JAVA_HOME/bin:$PATH"

export ANDROID_HOME="$HOME/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

echo "sdk.dir=$ANDROID_HOME" > "$REPO_ROOT/mobile/local.properties"

# 1. Download command line tools if not present
if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
    echo "[INFO] Downloading Android command line tools..."
    mkdir -p "$ANDROID_HOME/cmdline-tools"
    curl -sLo cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
    unzip -q cmdline-tools.zip -d "$ANDROID_HOME/cmdline-tools"
    rm -rf "$ANDROID_HOME/cmdline-tools/latest"
    mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
    rm -f cmdline-tools.zip
    echo "[INFO] Command line tools installed."
fi

# 2. Accept licenses and install platform-34 and build-tools
echo "[INFO] Accepting SDK licenses and installing Android Platform 34..."
yes | "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" --licenses > /dev/null 2>&1 || true
"$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" "platforms;android-34" "build-tools;34.0.0"

# 3. Download Gradle if not present
GRADLE_DIR="$HOME/gradle-8.7"
if [ ! -d "$GRADLE_DIR" ]; then
    echo "[INFO] Downloading Gradle 8.7..."
    cd "$HOME"
    curl -sLo gradle-8.7.zip https://services.gradle.org/distributions/gradle-8.7-bin.zip
    unzip -q gradle-8.7.zip
    rm -f gradle-8.7.zip
    echo "[INFO] Gradle 8.7 installed."
fi
export PATH="$GRADLE_DIR/bin:$PATH"

# 4. Detect Configuration from environment or .env files
ENV_FILE=""
if [ -f "$REPO_ROOT/.env.production" ]; then
    ENV_FILE="$REPO_ROOT/.env.production"
elif [ -f "$REPO_ROOT/.env" ]; then
    ENV_FILE="$REPO_ROOT/.env"
fi

# A. Version detection
TARGET_APP_VERSION="${APP_VERSION:-}"
if [ -z "$TARGET_APP_VERSION" ] && [ -n "$ENV_FILE" ]; then
    TARGET_APP_VERSION=$(grep -E '^APP_VERSION=' "$ENV_FILE" | head -n 1 | cut -d'=' -f2- | tr -d '"\r ')
fi
TARGET_APP_VERSION="${TARGET_APP_VERSION:-1.0.0}"
echo "[INFO] Building APK for Application Version: $TARGET_APP_VERSION"

# B. Server domain detection
TARGET_DOMAIN="${SERVER_DOMAIN:-}"
if [ -z "$TARGET_DOMAIN" ] && [ -n "$ENV_FILE" ]; then
    echo "[INFO] Reading server domain configuration from $ENV_FILE..."
    FILE_DOMAIN=$(grep -E '^(SERVER_DOMAIN|DOMAIN_NAME)=' "$ENV_FILE" | head -n 1 | cut -d'=' -f2- | tr -d '"\r ')
    FILE_HTTPS=$(grep -E '^ENABLE_HTTPS=' "$ENV_FILE" | head -n 1 | cut -d'=' -f2- | tr -d '"\r ')
    if [ -n "$FILE_DOMAIN" ]; then
        if [[ ! "$FILE_DOMAIN" =~ ^https?:// ]]; then
            if [ "$FILE_HTTPS" = "true" ]; then
                TARGET_DOMAIN="https://$FILE_DOMAIN"
            else
                TARGET_DOMAIN="http://$FILE_DOMAIN"
            fi
        else
            TARGET_DOMAIN="$FILE_DOMAIN"
        fi
    fi
fi

GRADLE_ARGS="-PAPP_VERSION=$TARGET_APP_VERSION"
if [ -n "$TARGET_DOMAIN" ]; then
    echo "[INFO] Injected Server Domain into APK: $TARGET_DOMAIN"
    GRADLE_ARGS="$GRADLE_ARGS -PSERVER_DOMAIN=$TARGET_DOMAIN"
else
    echo "[INFO] No SERVER_DOMAIN or DOMAIN_NAME detected; using default fallback."
fi

# 5. Build APK
echo "[INFO] Building HealthWatch Android APK..."
cd "$REPO_ROOT/mobile"
gradle assembleDebug $GRADLE_ARGS --no-daemon

# 6. Locate generated APK and deploy with versioned filename
APK_OUTPUT_DIR="$REPO_ROOT/mobile/app/build/outputs/apk/debug"
APK_SRC=""

if [ -f "$APK_OUTPUT_DIR/HealthWatch-v${TARGET_APP_VERSION}.apk" ]; then
    APK_SRC="$APK_OUTPUT_DIR/HealthWatch-v${TARGET_APP_VERSION}.apk"
elif [ -f "$APK_OUTPUT_DIR/app-debug.apk" ]; then
    APK_SRC="$APK_OUTPUT_DIR/app-debug.apk"
else
    APK_SRC=$(find "$APK_OUTPUT_DIR" -name "*.apk" -type f | head -n 1)
fi

VERSIONED_NAME="HealthWatch-v${TARGET_APP_VERSION}.apk"

if [ -n "$APK_SRC" ] && [ -f "$APK_SRC" ]; then
    echo "[INFO] Cleaning up older APK files from frontend and backend directories..."
    # 1. Clean old APK versions from Frontend public directory
    mkdir -p "$REPO_ROOT/frontend/public"
    find "$REPO_ROOT/frontend/public" -maxdepth 1 -name "HealthWatch-*.apk" ! -name "$VERSIONED_NAME" -type f -exec rm -v {} + 2>/dev/null || true

    # 2. Clean old APK versions from Backend app directory
    mkdir -p "$REPO_ROOT/backend/app"
    find "$REPO_ROOT/backend/app" -maxdepth 1 -name "HealthWatch-*.apk" ! -name "$VERSIONED_NAME" -type f -exec rm -v {} + 2>/dev/null || true

    # 3. Deploy new active APK to Frontend
    cp -f "$APK_SRC" "$REPO_ROOT/frontend/public/$VERSIONED_NAME"
    cp -f "$APK_SRC" "$REPO_ROOT/frontend/public/HealthWatch.apk"

    # 4. Deploy new active APK to Backend
    cp -f "$APK_SRC" "$REPO_ROOT/backend/app/$VERSIONED_NAME"
    cp -f "$APK_SRC" "$REPO_ROOT/backend/app/HealthWatch.apk"

    # 5. Clean stale build output artifacts
    find "$APK_OUTPUT_DIR" -maxdepth 1 -name "*.apk" ! -name "$VERSIONED_NAME" -type f -delete 2>/dev/null || true

    echo "[SUCCESS] Real Android APK created and deployed:"
    echo "  -> $REPO_ROOT/frontend/public/$VERSIONED_NAME"
    echo "  -> $REPO_ROOT/frontend/public/HealthWatch.apk"
    echo "  -> $REPO_ROOT/backend/app/$VERSIONED_NAME"
    echo "  -> $REPO_ROOT/backend/app/HealthWatch.apk"
    ls -lh "$REPO_ROOT/frontend/public/$VERSIONED_NAME"
else
    echo "[ERROR] APK build output not found in $APK_OUTPUT_DIR"
    exit 1
fi
