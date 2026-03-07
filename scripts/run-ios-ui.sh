#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[error] failed during: $LAST_PHASE" >&2; exit 1' ERR

DEVELOPER_DIR_PATH="/Applications/Xcode.app/Contents/Developer"
export DEVELOPER_DIR="$DEVELOPER_DIR_PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="$ROOT_DIR/ios/LunchMenuRecommender"
SCHEME="${IOS_SCHEME:-LunchMenuRecommender}"
DESTINATION="${IOS_SIMULATOR:-platform=iOS Simulator,name=iPhone 15,OS=latest}"
BUILD_DESTINATION="${IOS_BUILD_DESTINATION:-generic/platform=iOS Simulator}"
DERIVED_DATA="${IOS_DERIVED_DATA:-/tmp/LunchMenuRecommenderBuild}"
BUNDLE_ID="${IOS_BUNDLE_ID:-com.example.lunchmenurecommender}"
APP_NAME="${IOS_APP_NAME:-LunchMenuRecommender}"
SIM_UDID="${IOS_SIMULATOR_UDID:-}"
LAST_PHASE="init"

if [ ! -d "$IOS_DIR" ]; then
  echo "iOS directory not found: $IOS_DIR" >&2
  exit 1
fi

# Use Xcode's bundled utilities directly to avoid xcode-select/PATH issues.
XCODEBUILD="$DEVELOPER_DIR_PATH/usr/bin/xcodebuild"
SIMCTL="$DEVELOPER_DIR_PATH/usr/bin/simctl"

if [ ! -x "$XCODEBUILD" ]; then
  echo "xcodebuild not found at $XCODEBUILD" >&2
  exit 1
fi

if [ ! -x "$SIMCTL" ]; then
  echo "simctl not found at $SIMCTL" >&2
  exit 1
fi

PROJECT_FILE="$(find "$IOS_DIR" -maxdepth 2 \( -name '*.xcodeproj' -o -name '*.xcworkspace' \) | head -n 1 || true)"
if [ -z "$PROJECT_FILE" ]; then
  echo "No .xcodeproj or .xcworkspace found in $IOS_DIR" >&2
  exit 1
fi

mkdir -p "$DERIVED_DATA"

# Parse simulator name from destination to resolve UDID.
SIMULATOR_NAME=""
if [[ "$DESTINATION" == *"name="* ]]; then
  SIMULATOR_NAME="$(printf '%s' "$DESTINATION" | sed -E 's/.*name=([^,]+).*/\1/' | xargs)"
fi

if [ -n "$SIM_UDID" ]; then
  TARGET_SIM="$SIM_UDID"
elif [ -n "$SIMULATOR_NAME" ]; then
  AVAILABLE_SIM_LIST="$($SIMCTL list devices available 2>/dev/null || true)"
  if [ -z "$AVAILABLE_SIM_LIST" ]; then
    echo "No simulators are currently available from simctl." >&2
    echo "Check if iOS simulator runtime/device is installed and simulators are healthy." >&2
    exit 1
  fi
  TARGET_SIM="$(printf '%s\n' "$AVAILABLE_SIM_LIST" | grep -F "${SIMULATOR_NAME}" | grep -Eo '[0-9A-Fa-f-]{36}' | head -n 1 || true)"

  if [ -z "$TARGET_SIM" ]; then
    echo "No simulator found matching name '${SIMULATOR_NAME}'."
    echo "Falling back to first available iOS simulator (if any)."
    TARGET_SIM="$(printf '%s\n' "$AVAILABLE_SIM_LIST" | grep -Eo '[0-9A-Fa-f-]{36}' | head -n 1 || true)"
    if [ -n "$TARGET_SIM" ]; then
      BUILD_DESTINATION="generic/platform=iOS Simulator"
    fi
  fi
else
  echo "Could not parse simulator name from destination: $DESTINATION" >&2
  echo "Set IOS_SIMULATOR=name or IOS_SIMULATOR_UDID manually."
  exit 1
fi

if [ -z "$TARGET_SIM" ]; then
  echo "No available simulator found for destination: $DESTINATION" >&2
  echo "Check devices with: $SIMCTL list devices available" >&2
  exit 1
fi

echo "[info] Using simulator UUID: $TARGET_SIM"
if [ "$BUILD_DESTINATION" != "$DESTINATION" ]; then
  echo "[info] Build destination adjusted from '$DESTINATION' to '$BUILD_DESTINATION' for build compatibility."
fi

echo "[info] Build destination: $BUILD_DESTINATION"

BUILD_ARGS=(
  -scheme "$SCHEME"
  -destination "$BUILD_DESTINATION"
  -derivedDataPath "$DERIVED_DATA"
  build
)

if [[ "$PROJECT_FILE" == *.xcworkspace ]]; then
  BUILD_ARGS=( -workspace "$PROJECT_FILE" "${BUILD_ARGS[@]}" )
else
  BUILD_ARGS=( -project "$PROJECT_FILE" "${BUILD_ARGS[@]}" )
fi

echo "[step] build start"
LAST_PHASE="xcodebuild"
"$XCODEBUILD" "${BUILD_ARGS[@]}"
echo "[step] build done"

echo "[step] simulator boot"
LAST_PHASE="simctl boot"
"$SIMCTL" boot "$TARGET_SIM"
echo "[step] simulator boot requested: $TARGET_SIM"

APP_PATH="$(find "$DERIVED_DATA/Build/Products" -type d -name "$APP_NAME.app" | head -n 1 || true)"
if [ -z "$APP_PATH" ]; then
  echo "Built app not found in derived data: $DERIVED_DATA/Build/Products" >&2
  exit 1
fi

echo "[step] install app: $APP_PATH"
LAST_PHASE="simctl install"
"$SIMCTL" install booted "$APP_PATH"
echo "[step] launch app: $BUNDLE_ID"
LAST_PHASE="simctl launch"
"$SIMCTL" launch booted "$BUNDLE_ID"

echo "[done] Installed: $APP_PATH"
echo "[done] Launched bundle: $BUNDLE_ID"

echo "[done] Phase completed: $LAST_PHASE"
