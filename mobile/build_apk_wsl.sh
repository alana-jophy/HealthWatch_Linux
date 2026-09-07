#!/usr/bin/env bash
set -e

export ANDROID_HOME="$HOME/android-sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

mkdir -p "$ANDROID_HOME/cmdline-tools"

# 1. Download command line tools if not present
if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
    echo "[INFO] Downloading Android command line tools..."
    cd "$HOME"
    curl -sLo cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
    unzip -q cmdline-tools.zip -d "$ANDROID_HOME/cmdline-tools"
    mv "$ANDROID_HOME/cmdline-tools/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
    rm -f cmdline-tools.zip
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
fi
export PATH="$GRADLE_DIR/bin:$PATH"

# 4. Build APK
echo "[INFO] Building HealthWatch Android APK..."
cd "/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch/mobile"
gradle assembleDebug --no-daemon

# 5. Copy output APK to frontend/public for instant phone download
APK_SRC="/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch/mobile/app/build/outputs/apk/debug/app-debug.apk"
APK_DEST="/mnt/c/Users/Alana P J/.gemini/antigravity-ide/scratch/healthwatch/frontend/public/HealthWatch.apk"
if [ -f "$APK_SRC" ]; then
    cp "$APK_SRC" "$APK_DEST"
    echo "[SUCCESS] Real Android APK created and deployed to: $APK_DEST"
    ls -lh "$APK_DEST"
else
    echo "[ERROR] APK build output not found at $APK_SRC"
    exit 1
fi
