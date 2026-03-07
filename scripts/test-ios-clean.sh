#!/usr/bin/env bash
set -euo pipefail

# SwiftPM / Xcode iOS 테스트를 로컬 프로젝트를 오염시키지 않는 임시 경로에서 실행
#
# 사용:
#   ./scripts/test-ios-clean.sh
#   ./scripts/test-ios-clean.sh --ui
#
# UI 테스트 실행 시:
#   IOS_SCHEME="LunchMenuRecommender" ./scripts/test-ios-clean.sh --ui

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOS_DIR="$ROOT_DIR/ios/LunchMenuRecommender"
RUN_UI="${1:-}"
SWIFT_TOOLCHAIN_BIN="$(xcrun --find swift 2>/dev/null || true)"
SWIFT_BIN="${SWIFT_TOOLCHAIN_BIN:-swift}"

if [[ "$RUN_UI" != "" && "$RUN_UI" != "--ui" ]]; then
  echo "Usage: $0 [--ui]"
  echo "Use --ui only when an Xcode app target exists."
  exit 64
fi

if [ ! -d "$IOS_DIR" ]; then
  echo "iOS package directory not found: $IOS_DIR"
  exit 1
fi

if [ -n "${IOS_TEST_ROOT:-}" ]; then
  TEST_ROOT="$IOS_TEST_ROOT"
  CLEANUP_ROOT=0
else
  TEST_ROOT="$(mktemp -d /tmp/lunch-ios-test-XXXXXX)"
  CLEANUP_ROOT=1
fi

export SWIFT_MODULE_CACHE_PATH="$TEST_ROOT/ModuleCache"
export SWIFT_PACKAGE_CACHE_PATH="$TEST_ROOT/PackageCache"
export CLANG_MODULE_CACHE_PATH="$TEST_ROOT/ClangModuleCache"
export XDG_CACHE_HOME="$TEST_ROOT/cache"
export SWIFTPM_CONFIG_PATH="$TEST_ROOT/Config"
export HOME="$TEST_ROOT"
mkdir -p "$SWIFT_MODULE_CACHE_PATH" "$SWIFT_PACKAGE_CACHE_PATH" "$CLANG_MODULE_CACHE_PATH" "$XDG_CACHE_HOME" "$SWIFTPM_CONFIG_PATH"

if [ -n "$SWIFT_TOOLCHAIN_BIN" ]; then
  echo "▶ Using swift from: $SWIFT_TOOLCHAIN_BIN"
fi

cleanup() {
  if [ "${CLEANUP_ROOT}" = "1" ] && [ -d "$TEST_ROOT" ]; then
    rm -rf "$TEST_ROOT"
  fi
}
trap cleanup EXIT INT TERM

echo "▶ SwiftPM tests (isolated path: $TEST_ROOT)"
$SWIFT_BIN test \
  --disable-sandbox \
  --package-path "$IOS_DIR" \
  --scratch-path "$TEST_ROOT/.build" \
  --cache-path "$TEST_ROOT/PackageCache" \
  --config-path "$TEST_ROOT/Config"

if [[ "$RUN_UI" == "--ui" ]]; then
  if ! command -v xcodebuild >/dev/null 2>&1; then
    echo "xcodebuild not found. Xcode is required for UI tests."
    exit 1
  fi

  PROJECT_FILE="$(find "$IOS_DIR" -maxdepth 2 \( -name '*.xcodeproj' -o -name '*.xcworkspace' \) | head -n 1 || true)"
  if [ -z "$PROJECT_FILE" ]; then
    echo "No .xcodeproj/.xcworkspace found under $IOS_DIR"
    echo "SwiftPM tests completed. Add an iOS app target/project for simulator UI testing."
    exit 0
  fi

  SCHEME="${IOS_SCHEME:-}"
  if [ -z "$SCHEME" ]; then
    echo "IOS_SCHEME is not set. UI tests were skipped."
    echo "Set IOS_SCHEME and retry (example: IOS_SCHEME=LunchMenuRecommender)."
    exit 0
  fi

  DESTINATION="${IOS_SIMULATOR:-platform=iOS Simulator,name=iPhone 15,OS=latest}"
  BUILD_ARGS=(
    test
    -derivedDataPath "$TEST_ROOT/DerivedData"
    -clonedSourcePackagesDirPath "$TEST_ROOT/SourcePackages"
    -resultBundlePath "$TEST_ROOT/result.xcresult"
    -scheme "$SCHEME"
    -destination "$DESTINATION"
  )

  if [[ "$PROJECT_FILE" == *.xcodeproj ]]; then
    BUILD_ARGS=( -project "$PROJECT_FILE" "${BUILD_ARGS[@]}" )
  else
    BUILD_ARGS=( -workspace "$PROJECT_FILE" "${BUILD_ARGS[@]}" )
  fi

  echo "▶ UI tests via xcodebuild (isolated path: $TEST_ROOT)"
  xcodebuild "${BUILD_ARGS[@]}"
fi
