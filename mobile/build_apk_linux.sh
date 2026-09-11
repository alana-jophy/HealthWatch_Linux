#!/usr/bin/env bash
set -e

echo "============================================================"
echo "HEALTHWATCH ANDROID APK BUILD SCRIPT (LINUX NATIVE)"
echo "============================================================"

if [ -d "$HOME/jdk-17" ]; then
    export JAVA_HOME="$HOME/jdk-17"
else
    export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
fi
export PATH="$JAVA_HOME/bin:$PATH"

export ANDROID_HOME="$HOME/android-sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

echo "sdk.dir=$ANDROID_HOME" > "/home/alana/Desktop/healthwatch/mobile/local.properties"

# 1. Download command line tools if not present
if [ ! -d "$ANDROID_HOME/cmdline-tools/latest" ]; then
    echo "[INFO] Downloading Android command line tools..."
    cd "$HOME"
    curl -sLo cmdline-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
    unzip -q cmdline-tools.zip -d "$ANDROID_HOME/cmdline-tools"
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

# 4. Build APK
echo "[INFO] Building HealthWatch Android APK..."
cd "/home/alana/Desktop/healthwatch/mobile"
gradle assembleDebug --no-daemon

# 5. Copy output APK to frontend/public for phone download
APK_SRC="/home/alana/Desktop/healthwatch/mobile/app/build/outputs/apk/debug/app-debug.apk"
APK_DEST="/home/alana/Desktop/healthwatch/frontend/public/HealthWatch.apk"
if [ -f "$APK_SRC" ]; then
    cp "$APK_SRC" "$APK_DEST"
    echo "[SUCCESS] Real Android APK created and deployed to: $APK_DEST"
    ls -lh "$APK_DEST"
else
    echo "[ERROR] APK build output not found at $APK_SRC"
    exit 1
fi
